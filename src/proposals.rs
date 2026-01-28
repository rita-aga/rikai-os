//! Proposal System
//!
//! TigerStyle: Self-improvement through human-approved proposals.
//!
//! The agent can propose new tools, memory additions, or configuration changes.
//! All proposals require explicit human approval before being applied.
//!
//! Flow:
//! 1. User requests ("implement a tool that...") OR agent suggests
//! 2. Agent creates proposal with code/content
//! 3. Human reviews proposal
//! 4. Human approves/rejects via command
//! 5. If approved, proposal is applied

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// =============================================================================
// TigerStyle Constants
// =============================================================================

/// Maximum proposal description length in bytes
pub const PROPOSAL_DESCRIPTION_BYTES_MAX: usize = 10_000;

/// Maximum source code length in bytes
pub const PROPOSAL_SOURCE_CODE_BYTES_MAX: usize = 100_000;

/// Maximum number of pending proposals per user
pub const PROPOSALS_PENDING_COUNT_MAX: usize = 50;

/// Proposal ID prefix for readability
pub const PROPOSAL_ID_PREFIX: &str = "prop_";

// =============================================================================
// Types
// =============================================================================

/// What kind of improvement is being proposed
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum ProposalType {
    /// A new tool to register with the agent
    NewTool {
        /// Tool name (must be unique)
        name: String,
        /// Tool description for the LLM
        description: String,
        /// JSON Schema for the tool parameters
        parameters_schema: serde_json::Value,
        /// Source code (currently: shell script or Python)
        source_code: String,
        /// Language of the source code
        language: ToolLanguage,
    },
    /// Addition to the agent's memory
    MemoryAddition {
        /// Content to add
        content: String,
        /// Memory category (persona, human, etc.)
        category: MemoryCategory,
    },
    /// Update to system configuration
    ConfigChange {
        /// Configuration key
        key: String,
        /// New value
        value: serde_json::Value,
        /// Previous value (for rollback)
        previous_value: Option<serde_json::Value>,
    },
}

/// Language for tool source code
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ToolLanguage {
    Shell,
    Python,
    JavaScript,
}

/// Memory category for additions
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum MemoryCategory {
    /// User persona information
    Persona,
    /// Information about the human user
    Human,
    /// General facts and knowledge
    Knowledge,
    /// Learned preferences
    Preferences,
}

/// What triggered this proposal
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ProposalTrigger {
    /// User explicitly requested ("implement X")
    UserRequested,
    /// Agent noticed a pattern and suggested improvement
    AgentSuggested {
        /// Why the agent is suggesting this
        reasoning: String,
        /// Number of times the pattern was observed
        observation_count: u32,
    },
}

/// Status of a proposal
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ProposalStatus {
    /// Awaiting human review
    Pending,
    /// Human approved, being applied
    Approved,
    /// Human rejected
    Rejected {
        /// Reason for rejection (optional)
        reason: Option<String>,
    },
    /// Successfully applied
    Applied,
    /// Application failed
    Failed {
        /// Error message
        error: String,
    },
}

/// A proposal for self-improvement
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proposal {
    /// Unique proposal ID
    pub id: String,
    /// What triggered this proposal
    pub trigger: ProposalTrigger,
    /// Type of proposal
    pub proposal_type: ProposalType,
    /// Current status
    pub status: ProposalStatus,
    /// When the proposal was created
    pub created_at: DateTime<Utc>,
    /// When the status last changed
    pub updated_at: DateTime<Utc>,
    /// Agent ID that created this proposal
    pub agent_id: String,
    /// User ID (Telegram user) who can approve/reject
    pub user_id: i64,
}

impl Proposal {
    /// Create a new proposal
    pub fn new(
        trigger: ProposalTrigger,
        proposal_type: ProposalType,
        agent_id: String,
        user_id: i64,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: format!("{}{}", PROPOSAL_ID_PREFIX, &Uuid::new_v4().to_string()[..8]),
            trigger,
            proposal_type,
            status: ProposalStatus::Pending,
            created_at: now,
            updated_at: now,
            agent_id,
            user_id,
        }
    }

    /// Check if proposal is still pending
    pub fn is_pending(&self) -> bool {
        matches!(self.status, ProposalStatus::Pending)
    }

    /// Check if proposal has been approved (ready to apply)
    pub fn is_approved(&self) -> bool {
        matches!(self.status, ProposalStatus::Approved)
    }

    /// Approve this proposal
    pub fn approve(&mut self) {
        assert!(self.is_pending(), "can only approve pending proposals");
        self.status = ProposalStatus::Approved;
        self.updated_at = Utc::now();
    }

    /// Reject this proposal
    pub fn reject(&mut self, reason: Option<String>) {
        assert!(self.is_pending(), "can only reject pending proposals");
        self.status = ProposalStatus::Rejected { reason };
        self.updated_at = Utc::now();
    }

    /// Mark as successfully applied
    pub fn mark_applied(&mut self) {
        assert!(
            matches!(self.status, ProposalStatus::Approved),
            "can only apply approved proposals"
        );
        self.status = ProposalStatus::Applied;
        self.updated_at = Utc::now();
    }

    /// Mark as failed to apply
    pub fn mark_failed(&mut self, error: String) {
        assert!(
            matches!(self.status, ProposalStatus::Approved),
            "can only fail approved proposals"
        );
        self.status = ProposalStatus::Failed { error };
        self.updated_at = Utc::now();
    }

    /// Get a human-readable summary
    pub fn summary(&self) -> String {
        match &self.proposal_type {
            ProposalType::NewTool {
                name, description, ..
            } => {
                format!("New Tool: {} - {}", name, description)
            }
            ProposalType::MemoryAddition { category, content } => {
                let preview = if content.len() > 50 {
                    format!("{}...", &content[..50])
                } else {
                    content.clone()
                };
                format!("Memory ({:?}): {}", category, preview)
            }
            ProposalType::ConfigChange { key, value, .. } => {
                format!("Config: {} = {}", key, value)
            }
        }
    }
}

// =============================================================================
// Proposal Store
// =============================================================================

/// In-memory proposal store (can be backed by FDB later)
#[derive(Debug, Default)]
pub struct ProposalStore {
    /// Proposals by ID
    proposals: HashMap<String, Proposal>,
    /// Proposals by user ID for quick lookup
    by_user: HashMap<i64, Vec<String>>,
}

impl ProposalStore {
    /// Create a new proposal store
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a proposal
    pub fn add(&mut self, proposal: Proposal) -> Result<(), ProposalError> {
        // Check pending count limit
        let user_proposals = self.by_user.entry(proposal.user_id).or_default();
        let pending_count = user_proposals
            .iter()
            .filter(|id| {
                self.proposals
                    .get(*id)
                    .map(|p| p.is_pending())
                    .unwrap_or(false)
            })
            .count();

        if pending_count >= PROPOSALS_PENDING_COUNT_MAX {
            return Err(ProposalError::TooManyPending {
                user_id: proposal.user_id,
                count: pending_count,
                max: PROPOSALS_PENDING_COUNT_MAX,
            });
        }

        let id = proposal.id.clone();
        user_proposals.push(id.clone());
        self.proposals.insert(id, proposal);

        Ok(())
    }

    /// Get a proposal by ID
    pub fn get(&self, id: &str) -> Option<&Proposal> {
        self.proposals.get(id)
    }

    /// Get a mutable proposal by ID
    pub fn get_mut(&mut self, id: &str) -> Option<&mut Proposal> {
        self.proposals.get_mut(id)
    }

    /// Get all pending proposals for a user
    pub fn get_pending_for_user(&self, user_id: i64) -> Vec<&Proposal> {
        self.by_user
            .get(&user_id)
            .map(|ids| {
                ids.iter()
                    .filter_map(|id| self.proposals.get(id))
                    .filter(|p| p.is_pending())
                    .collect()
            })
            .unwrap_or_default()
    }

    /// Get all proposals for a user
    pub fn get_all_for_user(&self, user_id: i64) -> Vec<&Proposal> {
        self.by_user
            .get(&user_id)
            .map(|ids| ids.iter().filter_map(|id| self.proposals.get(id)).collect())
            .unwrap_or_default()
    }
}

/// Thread-safe proposal store
pub type SharedProposalStore = Arc<RwLock<ProposalStore>>;

/// Create a new shared proposal store
pub fn new_shared_store() -> SharedProposalStore {
    Arc::new(RwLock::new(ProposalStore::new()))
}

// =============================================================================
// Errors
// =============================================================================

/// Proposal-related errors
#[derive(Debug, thiserror::Error)]
pub enum ProposalError {
    #[error("too many pending proposals for user {user_id}: {count} >= {max}")]
    TooManyPending {
        user_id: i64,
        count: usize,
        max: usize,
    },

    #[error("proposal not found: {0}")]
    NotFound(String),

    #[error("proposal {id} is not pending (status: {status})")]
    NotPending { id: String, status: String },

    #[error("invalid proposal: {0}")]
    Invalid(String),
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proposal_lifecycle() {
        let mut proposal = Proposal::new(
            ProposalTrigger::UserRequested,
            ProposalType::NewTool {
                name: "hello".to_string(),
                description: "Say hello".to_string(),
                parameters_schema: serde_json::json!({"type": "object"}),
                source_code: "echo hello".to_string(),
                language: ToolLanguage::Shell,
            },
            "agent_123".to_string(),
            12345,
        );

        assert!(proposal.is_pending());
        assert!(proposal.id.starts_with(PROPOSAL_ID_PREFIX));

        proposal.approve();
        assert!(!proposal.is_pending());
        assert!(matches!(proposal.status, ProposalStatus::Approved));

        proposal.mark_applied();
        assert!(matches!(proposal.status, ProposalStatus::Applied));
    }

    #[test]
    fn test_proposal_store_limits() {
        let mut store = ProposalStore::new();
        let user_id = 12345;

        // Add proposals up to the limit
        for i in 0..PROPOSALS_PENDING_COUNT_MAX {
            let proposal = Proposal::new(
                ProposalTrigger::UserRequested,
                ProposalType::MemoryAddition {
                    content: format!("Memory {}", i),
                    category: MemoryCategory::Knowledge,
                },
                "agent_123".to_string(),
                user_id,
            );
            assert!(store.add(proposal).is_ok());
        }

        // Next one should fail
        let proposal = Proposal::new(
            ProposalTrigger::UserRequested,
            ProposalType::MemoryAddition {
                content: "One too many".to_string(),
                category: MemoryCategory::Knowledge,
            },
            "agent_123".to_string(),
            user_id,
        );
        assert!(matches!(
            store.add(proposal),
            Err(ProposalError::TooManyPending { .. })
        ));
    }
}
