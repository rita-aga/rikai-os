//! Proposal Tool
//!
//! TigerStyle: Agent-facing tool for creating self-improvement proposals.
//!
//! This tool allows the agent to propose new tools, memory additions, or
//! configuration changes. All proposals require human approval.

use crate::proposals::{
    MemoryCategory, Proposal, ProposalTrigger, ProposalType, SharedProposalStore, ToolLanguage,
    PROPOSAL_DESCRIPTION_BYTES_MAX, PROPOSAL_SOURCE_CODE_BYTES_MAX,
};
use kelpie_server::tools::UnifiedToolRegistry;
use serde_json::Value;
use std::sync::Arc;
use tokio::sync::RwLock;

// =============================================================================
// Global State
// =============================================================================

/// Global proposal store (shared across tool invocations)
static PROPOSAL_STORE: once_cell::sync::OnceCell<SharedProposalStore> = once_cell::sync::OnceCell::new();

/// Get or initialize the global proposal store
fn get_proposal_store() -> SharedProposalStore {
    PROPOSAL_STORE
        .get_or_init(|| Arc::new(RwLock::new(crate::proposals::ProposalStore::new())))
        .clone()
}

/// Get the proposal store (for external access)
pub fn proposal_store() -> SharedProposalStore {
    get_proposal_store()
}

// =============================================================================
// Tool Registration
// =============================================================================

/// Register the proposal tool with the tool registry
pub async fn register_proposal_tool(registry: &UnifiedToolRegistry) {
    let handler: kelpie_server::tools::BuiltinToolHandler = Arc::new(|input: &Value| {
        let input = input.clone();
        Box::pin(async move { execute_proposal_tool(&input).await })
    });

    registry
        .register_builtin(
            "propose_improvement",
            "Propose a new capability or improvement. Use this when the user asks you to implement \
             something new, or when you notice a pattern that could be automated. All proposals \
             require human approval before being applied.\n\n\
             Examples:\n\
             - User: 'Create a tool to search Hacker News' -> Use type='new_tool'\n\
             - User: 'Remember that I prefer dark mode' -> Use type='memory'\n\
             - Agent notices repeated task -> Use type='new_tool' with trigger='agent_suggested'",
            serde_json::json!({
                "type": "object",
                "properties": {
                    "proposal_type": {
                        "type": "string",
                        "enum": ["new_tool", "memory"],
                        "description": "Type of proposal: 'new_tool' for a new tool, 'memory' for a memory addition"
                    },
                    "trigger": {
                        "type": "string",
                        "enum": ["user_requested", "agent_suggested"],
                        "description": "What triggered this proposal"
                    },
                    "name": {
                        "type": "string",
                        "description": "For new_tool: tool name (lowercase, underscores)"
                    },
                    "description": {
                        "type": "string",
                        "description": "For new_tool: description of what the tool does. For memory: the content to remember"
                    },
                    "source_code": {
                        "type": "string",
                        "description": "For new_tool: shell script or Python code"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["shell", "python"],
                        "description": "For new_tool: programming language"
                    },
                    "memory_category": {
                        "type": "string",
                        "enum": ["persona", "human", "knowledge", "preferences"],
                        "description": "For memory: category of the memory"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "For agent_suggested: why you're suggesting this"
                    },
                    "observation_count": {
                        "type": "integer",
                        "description": "For agent_suggested: how many times you observed the pattern"
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
                "required": ["proposal_type", "trigger", "description", "agent_id", "user_id"]
            }),
            handler,
        )
        .await;

    tracing::info!("Registered propose_improvement tool");
}

/// Execute the proposal tool
async fn execute_proposal_tool(input: &Value) -> String {
    // Parse proposal type
    let proposal_type_str = match input.get("proposal_type").and_then(|v| v.as_str()) {
        Some(t) => t,
        None => return "Error: proposal_type is required".to_string(),
    };

    // Parse trigger
    let trigger_str = match input.get("trigger").and_then(|v| v.as_str()) {
        Some(t) => t,
        None => return "Error: trigger is required".to_string(),
    };

    let trigger = match trigger_str {
        "user_requested" => ProposalTrigger::UserRequested,
        "agent_suggested" => {
            let reasoning = input
                .get("reasoning")
                .and_then(|v| v.as_str())
                .unwrap_or("No reasoning provided")
                .to_string();
            let observation_count = input
                .get("observation_count")
                .and_then(|v| v.as_u64())
                .unwrap_or(1) as u32;
            ProposalTrigger::AgentSuggested {
                reasoning,
                observation_count,
            }
        }
        _ => return format!("Error: invalid trigger '{}'", trigger_str),
    };

    // Parse agent_id and user_id
    let agent_id = match input.get("agent_id").and_then(|v| v.as_str()) {
        Some(id) => id.to_string(),
        None => return "Error: agent_id is required".to_string(),
    };

    let user_id = match input.get("user_id").and_then(|v| v.as_i64()) {
        Some(id) => id,
        None => return "Error: user_id is required".to_string(),
    };

    // Build proposal based on type
    let proposal_type = match proposal_type_str {
        "new_tool" => {
            let name = match input.get("name").and_then(|v| v.as_str()) {
                Some(n) => n.to_string(),
                None => return "Error: name is required for new_tool".to_string(),
            };

            let description = match input.get("description").and_then(|v| v.as_str()) {
                Some(d) => d.to_string(),
                None => return "Error: description is required".to_string(),
            };

            if description.len() > PROPOSAL_DESCRIPTION_BYTES_MAX {
                return format!(
                    "Error: description too long ({} > {})",
                    description.len(),
                    PROPOSAL_DESCRIPTION_BYTES_MAX
                );
            }

            let source_code = match input.get("source_code").and_then(|v| v.as_str()) {
                Some(c) => c.to_string(),
                None => return "Error: source_code is required for new_tool".to_string(),
            };

            if source_code.len() > PROPOSAL_SOURCE_CODE_BYTES_MAX {
                return format!(
                    "Error: source_code too long ({} > {})",
                    source_code.len(),
                    PROPOSAL_SOURCE_CODE_BYTES_MAX
                );
            }

            let language = match input.get("language").and_then(|v| v.as_str()) {
                Some("shell") => ToolLanguage::Shell,
                Some("python") => ToolLanguage::Python,
                Some("javascript") => ToolLanguage::JavaScript,
                Some(l) => return format!("Error: unsupported language '{}'", l),
                None => return "Error: language is required for new_tool".to_string(),
            };

            ProposalType::NewTool {
                name,
                description,
                parameters_schema: serde_json::json!({
                    "type": "object",
                    "properties": {},
                    "required": []
                }),
                source_code,
                language,
            }
        }
        "memory" => {
            let content = match input.get("description").and_then(|v| v.as_str()) {
                Some(c) => c.to_string(),
                None => return "Error: description (content) is required for memory".to_string(),
            };

            let category = match input.get("memory_category").and_then(|v| v.as_str()) {
                Some("persona") => MemoryCategory::Persona,
                Some("human") => MemoryCategory::Human,
                Some("knowledge") => MemoryCategory::Knowledge,
                Some("preferences") => MemoryCategory::Preferences,
                Some(c) => return format!("Error: invalid memory_category '{}'", c),
                None => MemoryCategory::Knowledge, // default
            };

            ProposalType::MemoryAddition { content, category }
        }
        _ => return format!("Error: invalid proposal_type '{}'", proposal_type_str),
    };

    // Create proposal
    let proposal = Proposal::new(trigger, proposal_type, agent_id, user_id);
    let proposal_id = proposal.id.clone();
    let summary = proposal.summary();

    // Store proposal
    let store = get_proposal_store();
    let mut store = store.write().await;
    if let Err(e) = store.add(proposal) {
        return format!("Error creating proposal: {}", e);
    }

    format!(
        "Proposal {} created successfully.\n\nSummary: {}\n\n\
         The user can approve with /approve {} or reject with /reject {}",
        proposal_id, summary, proposal_id, proposal_id
    )
}
