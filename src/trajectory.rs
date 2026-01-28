//! Trajectory Capture System
//!
//! TigerStyle: Capture agent task trajectories for training and analysis.
//!
//! Trajectories follow a hot→cold pattern:
//! - Hot: Active trajectory in agent's working memory
//! - Cold: Completed trajectory saved to storage
//! - Export: Can be exported as training data
//!
//! Each trajectory captures:
//! - The task description (what the user asked)
//! - Each step the agent took (tool calls, reasoning)
//! - Whether the task succeeded
//! - User feedback (if provided)

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// =============================================================================
// TigerStyle Constants
// =============================================================================

/// Maximum number of steps in a trajectory
pub const TRAJECTORY_STEPS_COUNT_MAX: usize = 100;

/// Maximum task description length in bytes
pub const TASK_DESCRIPTION_BYTES_MAX: usize = 10_000;

/// Maximum reasoning length per step in bytes
pub const STEP_REASONING_BYTES_MAX: usize = 5_000;

/// Maximum tool input/output length per step in bytes
pub const STEP_TOOL_DATA_BYTES_MAX: usize = 50_000;

/// Trajectory ID prefix
pub const TRAJECTORY_ID_PREFIX: &str = "traj_";

/// Maximum hot trajectories per user
pub const HOT_TRAJECTORIES_COUNT_MAX: usize = 10;

// =============================================================================
// Types
// =============================================================================

/// A single step in a trajectory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrajectoryStep {
    /// Step number (0-indexed)
    pub step_number: u32,
    /// When this step occurred
    pub timestamp: DateTime<Utc>,
    /// What the agent was thinking/reasoning
    pub reasoning: Option<String>,
    /// Tool call (if any)
    pub tool_call: Option<ToolCall>,
    /// Result of the tool call (if any)
    pub tool_result: Option<String>,
    /// Any assistant message to the user
    pub assistant_message: Option<String>,
}

/// A tool call within a trajectory step
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    /// Tool name
    pub name: String,
    /// Tool input (JSON)
    pub input: serde_json::Value,
}

/// Outcome of a trajectory
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TrajectoryOutcome {
    /// Task completed successfully
    Success,
    /// Task failed
    Failure {
        /// Why it failed
        reason: String,
    },
    /// Task was abandoned/cancelled
    Abandoned,
    /// Still in progress
    InProgress,
}

/// User feedback on a trajectory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrajectoryFeedback {
    /// Rating (1-5)
    pub rating: u8,
    /// Optional comment
    pub comment: Option<String>,
    /// When feedback was given
    pub timestamp: DateTime<Utc>,
}

/// A complete task trajectory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskTrajectory {
    /// Unique trajectory ID
    pub id: String,
    /// Task description (what the user asked)
    pub task_description: String,
    /// Steps taken to complete the task
    pub steps: Vec<TrajectoryStep>,
    /// Outcome of the task
    pub outcome: TrajectoryOutcome,
    /// User feedback (if provided)
    pub feedback: Option<TrajectoryFeedback>,
    /// When the trajectory started
    pub started_at: DateTime<Utc>,
    /// When the trajectory ended (if ended)
    pub ended_at: Option<DateTime<Utc>>,
    /// Agent ID
    pub agent_id: String,
    /// User ID
    pub user_id: i64,
    /// Total tokens used (input + output)
    pub tokens_total: u64,
}

impl TaskTrajectory {
    /// Create a new trajectory
    pub fn new(task_description: String, agent_id: String, user_id: i64) -> Self {
        assert!(
            task_description.len() <= TASK_DESCRIPTION_BYTES_MAX,
            "task description too long: {} > {}",
            task_description.len(),
            TASK_DESCRIPTION_BYTES_MAX
        );

        Self {
            id: format!(
                "{}{}",
                TRAJECTORY_ID_PREFIX,
                &Uuid::new_v4().to_string()[..8]
            ),
            task_description,
            steps: Vec::new(),
            outcome: TrajectoryOutcome::InProgress,
            feedback: None,
            started_at: Utc::now(),
            ended_at: None,
            agent_id,
            user_id,
            tokens_total: 0,
        }
    }

    /// Add a step to the trajectory
    pub fn add_step(&mut self, step: TrajectoryStep) -> Result<(), TrajectoryError> {
        if self.steps.len() >= TRAJECTORY_STEPS_COUNT_MAX {
            return Err(TrajectoryError::TooManySteps {
                trajectory_id: self.id.clone(),
                count: self.steps.len(),
                max: TRAJECTORY_STEPS_COUNT_MAX,
            });
        }

        if !matches!(self.outcome, TrajectoryOutcome::InProgress) {
            return Err(TrajectoryError::AlreadyEnded {
                trajectory_id: self.id.clone(),
            });
        }

        self.steps.push(step);
        Ok(())
    }

    /// Mark the trajectory as complete
    pub fn complete(&mut self, outcome: TrajectoryOutcome) {
        assert!(
            matches!(self.outcome, TrajectoryOutcome::InProgress),
            "trajectory already ended"
        );
        self.outcome = outcome;
        self.ended_at = Some(Utc::now());
    }

    /// Add user feedback
    pub fn add_feedback(&mut self, rating: u8, comment: Option<String>) {
        assert!((1..=5).contains(&rating), "rating must be 1-5");
        self.feedback = Some(TrajectoryFeedback {
            rating,
            comment,
            timestamp: Utc::now(),
        });
    }

    /// Check if trajectory is still in progress
    pub fn is_in_progress(&self) -> bool {
        matches!(self.outcome, TrajectoryOutcome::InProgress)
    }

    /// Get duration in seconds (or None if still in progress)
    pub fn duration_seconds(&self) -> Option<i64> {
        self.ended_at
            .map(|end| (end - self.started_at).num_seconds())
    }

    /// Export as training data format (simplified)
    pub fn export_for_training(&self) -> TrainingExample {
        TrainingExample {
            task: self.task_description.clone(),
            steps: self
                .steps
                .iter()
                .map(|s| TrainingStep {
                    reasoning: s.reasoning.clone(),
                    tool_call: s.tool_call.clone(),
                    tool_result: s.tool_result.clone(),
                    message: s.assistant_message.clone(),
                })
                .collect(),
            success: matches!(self.outcome, TrajectoryOutcome::Success),
            rating: self.feedback.as_ref().map(|f| f.rating),
        }
    }
}

/// Training data format for export
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingExample {
    pub task: String,
    pub steps: Vec<TrainingStep>,
    pub success: bool,
    pub rating: Option<u8>,
}

/// Training step (simplified)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingStep {
    pub reasoning: Option<String>,
    pub tool_call: Option<ToolCall>,
    pub tool_result: Option<String>,
    pub message: Option<String>,
}

// =============================================================================
// Trajectory Store
// =============================================================================

/// Trajectory storage with hot/cold separation
#[derive(Debug, Default)]
pub struct TrajectoryStore {
    /// Hot trajectories (in progress)
    hot: HashMap<String, TaskTrajectory>,
    /// Cold trajectories (completed) - in production, these go to archival storage
    cold: HashMap<String, TaskTrajectory>,
    /// Index: user_id -> trajectory IDs (hot)
    hot_by_user: HashMap<i64, Vec<String>>,
    /// Index: user_id -> trajectory IDs (cold, recent only)
    cold_by_user: HashMap<i64, Vec<String>>,
}

impl TrajectoryStore {
    /// Create a new trajectory store
    pub fn new() -> Self {
        Self::default()
    }

    /// Start a new trajectory (adds to hot storage)
    pub fn start(&mut self, trajectory: TaskTrajectory) -> Result<(), TrajectoryError> {
        // Check hot count limit
        let user_hot = self.hot_by_user.entry(trajectory.user_id).or_default();
        if user_hot.len() >= HOT_TRAJECTORIES_COUNT_MAX {
            return Err(TrajectoryError::TooManyHot {
                user_id: trajectory.user_id,
                count: user_hot.len(),
                max: HOT_TRAJECTORIES_COUNT_MAX,
            });
        }

        let id = trajectory.id.clone();
        let user_id = trajectory.user_id;
        self.hot.insert(id.clone(), trajectory);
        self.hot_by_user.entry(user_id).or_default().push(id);

        Ok(())
    }

    /// Get a hot trajectory
    pub fn get_hot(&self, id: &str) -> Option<&TaskTrajectory> {
        self.hot.get(id)
    }

    /// Get a mutable hot trajectory
    pub fn get_hot_mut(&mut self, id: &str) -> Option<&mut TaskTrajectory> {
        self.hot.get_mut(id)
    }

    /// Move a trajectory from hot to cold (after completion)
    pub fn archive(&mut self, id: &str) -> Result<(), TrajectoryError> {
        let trajectory = self
            .hot
            .remove(id)
            .ok_or_else(|| TrajectoryError::NotFound(id.to_string()))?;

        if trajectory.is_in_progress() {
            // Put it back and error
            self.hot.insert(id.to_string(), trajectory);
            return Err(TrajectoryError::StillInProgress(id.to_string()));
        }

        let user_id = trajectory.user_id;

        // Remove from hot index
        if let Some(ids) = self.hot_by_user.get_mut(&user_id) {
            ids.retain(|i| i != id);
        }

        // Add to cold storage
        self.cold.insert(id.to_string(), trajectory);
        self.cold_by_user
            .entry(user_id)
            .or_default()
            .push(id.to_string());

        Ok(())
    }

    /// Get all hot trajectories for a user
    pub fn get_hot_for_user(&self, user_id: i64) -> Vec<&TaskTrajectory> {
        self.hot_by_user
            .get(&user_id)
            .map(|ids| ids.iter().filter_map(|id| self.hot.get(id)).collect())
            .unwrap_or_default()
    }

    /// Get recent cold trajectories for a user
    pub fn get_cold_for_user(&self, user_id: i64, limit: usize) -> Vec<&TaskTrajectory> {
        self.cold_by_user
            .get(&user_id)
            .map(|ids| {
                ids.iter()
                    .rev()
                    .take(limit)
                    .filter_map(|id| self.cold.get(id))
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Export all trajectories for training
    pub fn export_training_data(&self) -> Vec<TrainingExample> {
        self.cold
            .values()
            .filter(|t| matches!(t.outcome, TrajectoryOutcome::Success))
            .map(|t| t.export_for_training())
            .collect()
    }
}

/// Thread-safe trajectory store
pub type SharedTrajectoryStore = Arc<RwLock<TrajectoryStore>>;

/// Create a new shared trajectory store
pub fn new_shared_store() -> SharedTrajectoryStore {
    Arc::new(RwLock::new(TrajectoryStore::new()))
}

// =============================================================================
// Errors
// =============================================================================

/// Trajectory-related errors
#[derive(Debug, thiserror::Error)]
pub enum TrajectoryError {
    #[error("too many steps in trajectory {trajectory_id}: {count} >= {max}")]
    TooManySteps {
        trajectory_id: String,
        count: usize,
        max: usize,
    },

    #[error("trajectory {trajectory_id} has already ended")]
    AlreadyEnded { trajectory_id: String },

    #[error("trajectory not found: {0}")]
    NotFound(String),

    #[error("trajectory {0} is still in progress")]
    StillInProgress(String),

    #[error("too many hot trajectories for user {user_id}: {count} >= {max}")]
    TooManyHot {
        user_id: i64,
        count: usize,
        max: usize,
    },
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trajectory_lifecycle() {
        let mut traj = TaskTrajectory::new(
            "Search for rust async tutorials".to_string(),
            "agent_123".to_string(),
            12345,
        );

        assert!(traj.is_in_progress());
        assert!(traj.id.starts_with(TRAJECTORY_ID_PREFIX));

        // Add a step
        let step = TrajectoryStep {
            step_number: 0,
            timestamp: Utc::now(),
            reasoning: Some("I'll search the web".to_string()),
            tool_call: Some(ToolCall {
                name: "web_search".to_string(),
                input: serde_json::json!({"query": "rust async tutorials"}),
            }),
            tool_result: Some("Found 10 results...".to_string()),
            assistant_message: None,
        };
        traj.add_step(step).unwrap();

        assert_eq!(traj.steps.len(), 1);

        // Complete
        traj.complete(TrajectoryOutcome::Success);
        assert!(!traj.is_in_progress());
        assert!(traj.duration_seconds().is_some());

        // Add feedback
        traj.add_feedback(5, Some("Great!".to_string()));
        assert_eq!(traj.feedback.as_ref().unwrap().rating, 5);

        // Export
        let training = traj.export_for_training();
        assert!(training.success);
        assert_eq!(training.rating, Some(5));
    }

    #[test]
    fn test_trajectory_store_hot_cold() {
        let mut store = TrajectoryStore::new();
        let user_id = 12345;

        // Start trajectory
        let traj = TaskTrajectory::new("Test task".to_string(), "agent".to_string(), user_id);
        let id = traj.id.clone();

        store.start(traj).unwrap();

        // Verify it's in hot
        assert!(store.get_hot(&id).is_some());
        assert_eq!(store.get_hot_for_user(user_id).len(), 1);

        // Can't archive while in progress
        assert!(store.archive(&id).is_err());

        // Complete it
        store
            .get_hot_mut(&id)
            .unwrap()
            .complete(TrajectoryOutcome::Success);

        // Now archive
        store.archive(&id).unwrap();

        // Verify it moved to cold
        assert!(store.get_hot(&id).is_none());
        assert_eq!(store.get_cold_for_user(user_id, 10).len(), 1);
    }
}
