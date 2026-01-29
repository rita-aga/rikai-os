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

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
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

/// Days after which non-pending proposals are cleaned up
pub const PROPOSAL_CLEANUP_DAYS: i64 = 30;

/// Maximum tool name length
pub const TOOL_NAME_LENGTH_MAX: usize = 64;

// =============================================================================
// Dangerous Code Patterns
// =============================================================================

/// Patterns that are potentially dangerous in shell scripts
const DANGEROUS_SHELL_PATTERNS: &[&str] = &[
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $HOME",
    ":(){ :|:& };:", // Fork bomb
    "> /dev/sda",
    "mkfs.",
    "dd if=",
    "wget -O- | sh",
    "curl.*| sh",
    "curl.*| bash",
    "eval $(curl",
    "eval $(wget",
    "/etc/passwd",
    "/etc/shadow",
    "chmod 777 /",
    "chown -R",
    "nc -e",    // Netcat reverse shell
    "bash -i",  // Interactive bash
    "0>&1",     // File descriptor manipulation for shells
];

/// Patterns that are potentially dangerous in Python
const DANGEROUS_PYTHON_PATTERNS: &[&str] = &[
    "os.system(",
    "subprocess.call(",
    "eval(",
    "exec(",
    "__import__('os')",
    "open('/etc/",
    "shutil.rmtree('/'",
    "shutil.rmtree(os.path.expanduser",
];

/// Patterns that are potentially dangerous in JavaScript/Node.js
const DANGEROUS_JAVASCRIPT_PATTERNS: &[&str] = &[
    "child_process",           // Shell execution
    "exec(",                   // Command execution
    "execSync(",               // Synchronous command execution
    "spawn(",                  // Process spawning
    "eval(",                   // Code evaluation
    "Function(",               // Dynamic function creation
    "require('child_process",  // Importing child_process
    "require(\"child_process", // Importing child_process (double quotes)
    "import('child_process",   // Dynamic import of child_process
    "fs.rmSync('/'",           // Recursive delete root
    "fs.rmdirSync('/'",        // Delete root directory
    "process.env",             // Environment variable access
    "Buffer.from(",            // Potential for buffer overflow attacks
    "new Function(",           // Dynamic code execution
    "__dirname + '/..'",       // Path traversal
    "readFileSync('/etc/",     // Reading sensitive files
];

// =============================================================================
// Types
// =============================================================================

/// What kind of improvement is being proposed
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum ProposalType {
    /// A new tool to register with the agent
    NewTool {
        /// Tool name (must be unique per user)
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

/// Security warnings found during code analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityWarnings {
    /// Patterns found that may be dangerous
    pub patterns: Vec<String>,
    /// Overall risk level: "low", "medium", "high"
    pub risk_level: String,
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
    /// Security warnings (if any)
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub security_warnings: Option<SecurityWarnings>,
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

        // Analyze code for security warnings
        let security_warnings = match &proposal_type {
            ProposalType::NewTool {
                source_code,
                language,
                ..
            } => analyze_code_security(source_code, language),
            _ => None,
        };

        Self {
            id: format!("{}{}", PROPOSAL_ID_PREFIX, &Uuid::new_v4().to_string()[..8]),
            trigger,
            proposal_type,
            status: ProposalStatus::Pending,
            created_at: now,
            updated_at: now,
            agent_id,
            user_id,
            security_warnings,
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
        let base = match &self.proposal_type {
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
        };

        // Add security warning if present
        if let Some(ref warnings) = self.security_warnings {
            if warnings.risk_level == "high" {
                format!("{} ⚠️ HIGH RISK", base)
            } else if warnings.risk_level == "medium" {
                format!("{} ⚠️ REVIEW CAREFULLY", base)
            } else {
                base
            }
        } else {
            base
        }
    }

    /// Get the namespaced tool name (user_id prefix for collision prevention)
    pub fn namespaced_tool_name(&self) -> Option<String> {
        match &self.proposal_type {
            ProposalType::NewTool { name, .. } => {
                Some(format!("user{}_{}", self.user_id, name))
            }
            _ => None,
        }
    }
}

// =============================================================================
// Code Security Analysis
// =============================================================================

/// Analyze source code for potentially dangerous patterns
fn analyze_code_security(source_code: &str, language: &ToolLanguage) -> Option<SecurityWarnings> {
    let patterns = match language {
        ToolLanguage::Shell => DANGEROUS_SHELL_PATTERNS,
        ToolLanguage::Python => DANGEROUS_PYTHON_PATTERNS,
        ToolLanguage::JavaScript => DANGEROUS_JAVASCRIPT_PATTERNS,
    };

    let code_lower = source_code.to_lowercase();
    let found: Vec<String> = patterns
        .iter()
        .filter(|p| code_lower.contains(&p.to_lowercase()))
        .map(|p| (*p).to_string())
        .collect();

    if found.is_empty() {
        None
    } else {
        let risk_level = if found.len() >= 3 {
            "high"
        } else if found.len() >= 1 {
            "medium"
        } else {
            "low"
        };

        Some(SecurityWarnings {
            patterns: found,
            risk_level: risk_level.to_string(),
        })
    }
}

/// Validate tool name format
pub fn validate_tool_name(name: &str) -> Result<(), ProposalError> {
    if name.is_empty() {
        return Err(ProposalError::Invalid("tool name cannot be empty".to_string()));
    }
    if name.len() > TOOL_NAME_LENGTH_MAX {
        return Err(ProposalError::Invalid(format!(
            "tool name too long ({} > {})",
            name.len(),
            TOOL_NAME_LENGTH_MAX
        )));
    }
    if !name.chars().all(|c| c.is_ascii_lowercase() || c == '_' || c.is_ascii_digit()) {
        return Err(ProposalError::Invalid(
            "tool name must be lowercase letters, underscores, and digits only".to_string(),
        ));
    }
    if name.starts_with('_') || name.starts_with(char::is_numeric) {
        return Err(ProposalError::Invalid(
            "tool name must start with a letter".to_string(),
        ));
    }
    Ok(())
}

/// Validate parameters_schema is a valid JSON Schema structure
pub fn validate_parameters_schema(schema: &serde_json::Value) -> Result<(), ProposalError> {
    // Must be an object
    if !schema.is_object() {
        return Err(ProposalError::Invalid(
            "parameters_schema must be an object".to_string(),
        ));
    }

    let obj = schema.as_object().unwrap();

    // Should have "type" field
    if let Some(type_val) = obj.get("type") {
        if type_val.as_str() != Some("object") {
            return Err(ProposalError::Invalid(
                "parameters_schema type must be 'object'".to_string(),
            ));
        }
    }

    // If "properties" exists, it should be an object
    if let Some(props) = obj.get("properties") {
        if !props.is_object() {
            return Err(ProposalError::Invalid(
                "parameters_schema.properties must be an object".to_string(),
            ));
        }
    }

    // If "required" exists, it should be an array of strings
    if let Some(required) = obj.get("required") {
        if !required.is_array() {
            return Err(ProposalError::Invalid(
                "parameters_schema.required must be an array".to_string(),
            ));
        }
        for item in required.as_array().unwrap() {
            if !item.is_string() {
                return Err(ProposalError::Invalid(
                    "parameters_schema.required items must be strings".to_string(),
                ));
            }
        }
    }

    Ok(())
}

// =============================================================================
// Proposal Store with Persistence
// =============================================================================

/// Proposal store with file-based persistence
#[derive(Debug)]
pub struct ProposalStore {
    /// Proposals by ID
    proposals: HashMap<String, Proposal>,
    /// Proposals by user ID for quick lookup
    by_user: HashMap<i64, Vec<String>>,
    /// Data directory for persistence (None = in-memory only)
    data_dir: Option<String>,
}

impl Default for ProposalStore {
    fn default() -> Self {
        Self {
            proposals: HashMap::new(),
            by_user: HashMap::new(),
            data_dir: None,
        }
    }
}

impl ProposalStore {
    /// Create a new in-memory proposal store
    pub fn new() -> Self {
        Self::default()
    }

    /// Create a proposal store with file persistence
    pub fn with_persistence(data_dir: &str) -> Self {
        let mut store = Self {
            proposals: HashMap::new(),
            by_user: HashMap::new(),
            data_dir: Some(data_dir.to_string()),
        };

        // Load existing proposals from disk
        if let Err(e) = store.load_from_disk() {
            tracing::warn!("Failed to load proposals from disk: {}", e);
        }

        store
    }

    /// Load proposals from disk
    fn load_from_disk(&mut self) -> Result<(), ProposalError> {
        let data_dir = match &self.data_dir {
            Some(d) => d,
            None => return Ok(()),
        };

        let path = Path::new(data_dir).join("proposals.json");
        if !path.exists() {
            return Ok(());
        }

        let content = std::fs::read_to_string(&path)
            .map_err(|e| ProposalError::StorageError(format!("Failed to read proposals: {}", e)))?;

        let proposals: Vec<Proposal> = serde_json::from_str(&content)
            .map_err(|e| ProposalError::StorageError(format!("Failed to parse proposals: {}", e)))?;

        for proposal in proposals {
            let id = proposal.id.clone();
            let user_id = proposal.user_id;
            self.proposals.insert(id.clone(), proposal);
            self.by_user.entry(user_id).or_default().push(id);
        }

        tracing::info!("Loaded {} proposals from disk", self.proposals.len());
        Ok(())
    }

    /// Save proposals to disk
    fn save_to_disk(&self) -> Result<(), ProposalError> {
        let data_dir = match &self.data_dir {
            Some(d) => d,
            None => return Ok(()),
        };

        let path = Path::new(data_dir).join("proposals.json");
        let proposals: Vec<&Proposal> = self.proposals.values().collect();
        let content = serde_json::to_string_pretty(&proposals)
            .map_err(|e| ProposalError::StorageError(format!("Failed to serialize proposals: {}", e)))?;

        std::fs::write(&path, content)
            .map_err(|e| ProposalError::StorageError(format!("Failed to write proposals: {}", e)))?;

        Ok(())
    }

    /// Add a proposal
    pub fn add(&mut self, proposal: Proposal) -> Result<(), ProposalError> {
        // Validate tool name for NewTool proposals
        if let ProposalType::NewTool { name, parameters_schema, .. } = &proposal.proposal_type {
            validate_tool_name(name)?;
            validate_parameters_schema(parameters_schema)?;
        }

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

        // Persist to disk
        if let Err(e) = self.save_to_disk() {
            tracing::error!("Failed to persist proposal: {}", e);
        }

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

    /// Update a proposal and persist
    pub fn update(&mut self, id: &str, updater: impl FnOnce(&mut Proposal)) -> Result<(), ProposalError> {
        if let Some(proposal) = self.proposals.get_mut(id) {
            updater(proposal);
            if let Err(e) = self.save_to_disk() {
                tracing::error!("Failed to persist proposal update: {}", e);
            }
            Ok(())
        } else {
            Err(ProposalError::NotFound(id.to_string()))
        }
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

    /// Clean up old proposals (older than PROPOSAL_CLEANUP_DAYS)
    pub fn cleanup_old_proposals(&mut self) -> usize {
        let cutoff = Utc::now() - Duration::days(PROPOSAL_CLEANUP_DAYS);
        let mut removed = 0;

        // Find proposals to remove (non-pending, older than cutoff)
        let to_remove: Vec<String> = self
            .proposals
            .iter()
            .filter(|(_, p)| !p.is_pending() && p.updated_at < cutoff)
            .map(|(id, _)| id.clone())
            .collect();

        for id in &to_remove {
            if let Some(proposal) = self.proposals.remove(id) {
                // Remove from user index
                if let Some(user_ids) = self.by_user.get_mut(&proposal.user_id) {
                    user_ids.retain(|i| i != id);
                }
                removed += 1;
            }
        }

        if removed > 0 {
            if let Err(e) = self.save_to_disk() {
                tracing::error!("Failed to persist after cleanup: {}", e);
            }
            tracing::info!("Cleaned up {} old proposals", removed);
        }

        removed
    }
}

/// Thread-safe proposal store
pub type SharedProposalStore = Arc<RwLock<ProposalStore>>;

/// Create a new shared proposal store with persistence
pub fn new_shared_store_with_persistence(data_dir: &str) -> SharedProposalStore {
    Arc::new(RwLock::new(ProposalStore::with_persistence(data_dir)))
}

/// Create a new shared in-memory proposal store
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

    #[error("storage error: {0}")]
    StorageError(String),
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

    #[test]
    fn test_dangerous_code_detection() {
        // Safe shell code - normal rm command
        let warnings = analyze_code_security("rm file.txt", &ToolLanguage::Shell);
        assert!(warnings.is_none());

        // Dangerous shell code - recursive delete of root
        let warnings = analyze_code_security("rm -rf /", &ToolLanguage::Shell);
        assert!(warnings.is_some());
        assert_eq!(warnings.unwrap().risk_level, "medium");

        // Dangerous Python code
        let warnings = analyze_code_security("eval(user_input)", &ToolLanguage::Python);
        assert!(warnings.is_some());

        // Dangerous JavaScript code
        let warnings = analyze_code_security(
            "const { exec } = require('child_process'); exec('ls');",
            &ToolLanguage::JavaScript,
        );
        assert!(warnings.is_some());
        let w = warnings.unwrap();
        assert!(w.patterns.iter().any(|p| p.contains("child_process")));

        // Safe JavaScript code
        let warnings = analyze_code_security(
            "const result = await fetch('https://api.example.com');",
            &ToolLanguage::JavaScript,
        );
        assert!(warnings.is_none());
    }

    #[test]
    fn test_tool_name_validation() {
        assert!(validate_tool_name("hello").is_ok());
        assert!(validate_tool_name("get_weather").is_ok());
        assert!(validate_tool_name("tool123").is_ok());

        assert!(validate_tool_name("").is_err());
        assert!(validate_tool_name("Hello").is_err()); // Uppercase
        assert!(validate_tool_name("_private").is_err()); // Starts with underscore
        assert!(validate_tool_name("123tool").is_err()); // Starts with number
        assert!(validate_tool_name("hello-world").is_err()); // Contains hyphen
    }

    #[test]
    fn test_schema_validation() {
        // Valid schema
        assert!(validate_parameters_schema(&serde_json::json!({
            "type": "object",
            "properties": {},
            "required": []
        }))
        .is_ok());

        // Invalid: not an object
        assert!(validate_parameters_schema(&serde_json::json!("string")).is_err());

        // Invalid: wrong type
        assert!(validate_parameters_schema(&serde_json::json!({
            "type": "array"
        }))
        .is_err());

        // Invalid: required not array
        assert!(validate_parameters_schema(&serde_json::json!({
            "type": "object",
            "required": "name"
        }))
        .is_err());
    }

    #[test]
    fn test_namespaced_tool_name() {
        let proposal = Proposal::new(
            ProposalTrigger::UserRequested,
            ProposalType::NewTool {
                name: "weather".to_string(),
                description: "Get weather".to_string(),
                parameters_schema: serde_json::json!({"type": "object"}),
                source_code: "curl wttr.in".to_string(),
                language: ToolLanguage::Shell,
            },
            "agent_123".to_string(),
            12345,
        );

        assert_eq!(
            proposal.namespaced_tool_name(),
            Some("user12345_weather".to_string())
        );
    }
}
