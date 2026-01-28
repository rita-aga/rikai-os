//! Trajectory Tools
//!
//! TigerStyle: Agent-facing tools for trajectory capture and feedback.

use crate::trajectory::{SharedTrajectoryStore, TaskTrajectory, ToolCall, TrajectoryOutcome, TrajectoryStep};
use chrono::Utc;
use kelpie_server::tools::UnifiedToolRegistry;
use serde_json::Value;
use std::sync::Arc;
use tokio::sync::RwLock;

// =============================================================================
// Global State
// =============================================================================

/// Global trajectory store
static TRAJECTORY_STORE: once_cell::sync::OnceCell<SharedTrajectoryStore> =
    once_cell::sync::OnceCell::new();

/// Get or initialize the global trajectory store
fn get_trajectory_store() -> SharedTrajectoryStore {
    TRAJECTORY_STORE
        .get_or_init(|| Arc::new(RwLock::new(crate::trajectory::TrajectoryStore::new())))
        .clone()
}

/// Get the trajectory store (for external access)
pub fn trajectory_store() -> SharedTrajectoryStore {
    get_trajectory_store()
}

// =============================================================================
// Tool Registration
// =============================================================================

/// Register trajectory-related tools
pub async fn register_trajectory_tools(registry: &UnifiedToolRegistry) {
    // Start trajectory tool
    let start_handler: kelpie_server::tools::BuiltinToolHandler = Arc::new(|input: &Value| {
        let input = input.clone();
        Box::pin(async move { execute_start_trajectory(&input).await })
    });

    registry
        .register_builtin(
            "start_trajectory",
            "Start capturing a new task trajectory. Call this at the beginning of a task to \
             enable trajectory recording for training data.",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Description of the task being performed"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Your agent ID"
                    },
                    "user_id": {
                        "type": "integer",
                        "description": "The user's Telegram ID"
                    }
                },
                "required": ["task_description", "agent_id", "user_id"]
            }),
            start_handler,
        )
        .await;

    // Add step tool
    let step_handler: kelpie_server::tools::BuiltinToolHandler = Arc::new(|input: &Value| {
        let input = input.clone();
        Box::pin(async move { execute_add_step(&input).await })
    });

    registry
        .register_builtin(
            "trajectory_step",
            "Record a step in the current trajectory. Call this after each significant action.",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "trajectory_id": {
                        "type": "string",
                        "description": "ID of the trajectory to add step to"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning for this step"
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Name of tool called (if any)"
                    },
                    "tool_input": {
                        "type": "object",
                        "description": "Input to the tool (if any)"
                    },
                    "tool_result": {
                        "type": "string",
                        "description": "Result from the tool (if any)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message to the user (if any)"
                    }
                },
                "required": ["trajectory_id"]
            }),
            step_handler,
        )
        .await;

    // Complete trajectory tool
    let complete_handler: kelpie_server::tools::BuiltinToolHandler = Arc::new(|input: &Value| {
        let input = input.clone();
        Box::pin(async move { execute_complete_trajectory(&input).await })
    });

    registry
        .register_builtin(
            "complete_trajectory",
            "Mark a trajectory as complete. Call this when the task is done.",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "trajectory_id": {
                        "type": "string",
                        "description": "ID of the trajectory to complete"
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the task was successful"
                    },
                    "failure_reason": {
                        "type": "string",
                        "description": "Reason for failure (if success=false)"
                    }
                },
                "required": ["trajectory_id", "success"]
            }),
            complete_handler,
        )
        .await;

    tracing::info!("Registered trajectory tools: start_trajectory, trajectory_step, complete_trajectory");
}

/// Execute start_trajectory tool
async fn execute_start_trajectory(input: &Value) -> String {
    let task_description = match input.get("task_description").and_then(|v| v.as_str()) {
        Some(d) => d.to_string(),
        None => return "Error: task_description is required".to_string(),
    };

    let agent_id = match input.get("agent_id").and_then(|v| v.as_str()) {
        Some(id) => id.to_string(),
        None => return "Error: agent_id is required".to_string(),
    };

    let user_id = match input.get("user_id").and_then(|v| v.as_i64()) {
        Some(id) => id,
        None => return "Error: user_id is required".to_string(),
    };

    let trajectory = TaskTrajectory::new(task_description, agent_id, user_id);
    let trajectory_id = trajectory.id.clone();

    let store = get_trajectory_store();
    let mut store = store.write().await;
    if let Err(e) = store.start(trajectory) {
        return format!("Error starting trajectory: {}", e);
    }

    format!(
        "Trajectory {} started. Use trajectory_step to record steps and complete_trajectory when done.",
        trajectory_id
    )
}

/// Execute trajectory_step tool
async fn execute_add_step(input: &Value) -> String {
    let trajectory_id = match input.get("trajectory_id").and_then(|v| v.as_str()) {
        Some(id) => id,
        None => return "Error: trajectory_id is required".to_string(),
    };

    let store = get_trajectory_store();
    let mut store = store.write().await;

    let trajectory = match store.get_hot_mut(trajectory_id) {
        Some(t) => t,
        None => return format!("Error: trajectory {} not found or not active", trajectory_id),
    };

    let step_number = trajectory.steps.len() as u32;

    let tool_call = input
        .get("tool_name")
        .and_then(|v| v.as_str())
        .map(|name| ToolCall {
            name: name.to_string(),
            input: input
                .get("tool_input")
                .cloned()
                .unwrap_or(serde_json::json!({})),
        });

    let step = TrajectoryStep {
        step_number,
        timestamp: Utc::now(),
        reasoning: input.get("reasoning").and_then(|v| v.as_str()).map(String::from),
        tool_call,
        tool_result: input.get("tool_result").and_then(|v| v.as_str()).map(String::from),
        assistant_message: input.get("message").and_then(|v| v.as_str()).map(String::from),
    };

    if let Err(e) = trajectory.add_step(step) {
        return format!("Error adding step: {}", e);
    }

    format!("Step {} added to trajectory {}", step_number, trajectory_id)
}

/// Execute complete_trajectory tool
async fn execute_complete_trajectory(input: &Value) -> String {
    let trajectory_id = match input.get("trajectory_id").and_then(|v| v.as_str()) {
        Some(id) => id.to_string(),
        None => return "Error: trajectory_id is required".to_string(),
    };

    let success = match input.get("success").and_then(|v| v.as_bool()) {
        Some(s) => s,
        None => return "Error: success is required".to_string(),
    };

    let outcome = if success {
        TrajectoryOutcome::Success
    } else {
        let reason = input
            .get("failure_reason")
            .and_then(|v| v.as_str())
            .unwrap_or("Unknown failure")
            .to_string();
        TrajectoryOutcome::Failure { reason }
    };

    let store = get_trajectory_store();
    let mut store = store.write().await;

    // Complete the trajectory
    {
        let trajectory = match store.get_hot_mut(&trajectory_id) {
            Some(t) => t,
            None => return format!("Error: trajectory {} not found or not active", trajectory_id),
        };
        trajectory.complete(outcome.clone());
    }

    // Archive it
    if let Err(e) = store.archive(&trajectory_id) {
        return format!("Error archiving trajectory: {}", e);
    }

    let status = if success { "successfully" } else { "with failure" };
    format!("Trajectory {} completed {} and archived", trajectory_id, status)
}
