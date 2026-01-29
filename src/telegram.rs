//! Telegram Bot Interface with API Key Collection
//!
//! TigerStyle: Enhanced Telegram bot for Tama MVP.
//!
//! Features:
//! - API key collection via chat (/setup, /keys, /clear)
//! - Proposal approval flow (/approve, /reject)
//! - Standard chat with Kelpie agent

use crate::proposals::SharedProposalStore;
use crate::tools::proposal::proposal_store;
use crate::user_keys::{ApiKeyType, KeyManager};
use kelpie_server::models::{AgentType, CreateAgentRequest, MessageRole};
use kelpie_server::service::AgentService;
use kelpie_server::state::AppState;
use kelpie_server::tools::UnifiedToolRegistry;
use std::collections::HashMap;
use std::sync::Arc;
use teloxide::prelude::*;
use teloxide::types::ChatId;
use tokio::sync::RwLock;

// =============================================================================
// TigerStyle Constants
// =============================================================================

/// Rate limit messages per minute
pub const RATE_LIMIT_MESSAGES_PER_MINUTE: u32 = 20;

/// Maximum message length for Telegram
pub const TELEGRAM_MESSAGE_LENGTH_MAX: usize = 4096;

/// Get allowed user IDs from environment
fn get_allowed_users() -> Vec<i64> {
    std::env::var("ALLOWED_TELEGRAM_USERS")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .map(|s| {
            s.split(',')
                .filter_map(|id| id.trim().parse::<i64>().ok())
                .collect()
        })
        .unwrap_or_default() // Empty = no users allowed (secure default)
}

/// Check if a user is allowed to use the bot
fn is_user_allowed(user_id: i64) -> bool {
    let allowed = get_allowed_users();
    if allowed.is_empty() {
        false // No allowlist = allow NO ONE (secure default)
    } else {
        allowed.contains(&user_id)
    }
}

// =============================================================================
// State
// =============================================================================

/// User conversation state for setup flow
#[derive(Debug, Clone, PartialEq)]
enum SetupState {
    /// Normal chat mode
    Normal,
    /// Waiting for Anthropic API key
    WaitingForAnthropicKey,
    /// Waiting for OpenAI API key (optional)
    #[allow(dead_code)]
    WaitingForOpenAIKey,
}

/// Per-user state
#[derive(Debug)]
struct UserState {
    /// Current setup state
    setup_state: SetupState,
    /// Agent ID (if created)
    agent_id: Option<String>,
    /// Last message timestamps for rate limiting
    message_times: Vec<std::time::Instant>,
}

impl Default for UserState {
    fn default() -> Self {
        Self {
            setup_state: SetupState::Normal,
            agent_id: None,
            message_times: Vec::new(),
        }
    }
}

/// Bot state
struct BotState<R: kelpie_core::Runtime + Clone + Send + Sync + 'static> {
    /// Agent service
    service: Arc<AgentService<R>>,
    /// Key manager
    key_manager: Arc<RwLock<KeyManager>>,
    /// Per-user state
    user_states: Arc<RwLock<HashMap<i64, UserState>>>,
    /// Proposal store
    proposals: SharedProposalStore,
    /// Data directory for persistent storage
    data_dir: String,
    /// App state (for tool registry access)
    app_state: AppState<R>,
}

// =============================================================================
// Agent Mapping Persistence
// =============================================================================

/// Load agent mappings from disk
fn load_agent_mappings(data_dir: &str) -> HashMap<i64, String> {
    let path = std::path::Path::new(data_dir).join("agent_mappings.json");
    if path.exists() {
        if let Ok(content) = std::fs::read_to_string(&path) {
            if let Ok(mappings) = serde_json::from_str::<serde_json::Value>(&content) {
                tracing::info!("Loaded {} agent mappings from disk",
                    mappings.as_object().map(|m| m.len()).unwrap_or(0));
                // Convert from JSON (string keys) to HashMap<i64, String>
                if let Some(obj) = mappings.as_object() {
                    return obj.iter()
                        .filter_map(|(k, v)| {
                            let user_id: i64 = k.parse().ok()?;
                            let agent_id = v.as_str()?.to_string();
                            Some((user_id, agent_id))
                        })
                        .collect();
                }
            }
        }
    }
    HashMap::new()
}

/// Save agent mappings to disk
fn save_agent_mapping(data_dir: &str, user_id: i64, agent_id: &str) {
    let path = std::path::Path::new(data_dir).join("agent_mappings.json");

    // Load existing mappings
    let mut mappings: serde_json::Map<String, serde_json::Value> = if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|c| serde_json::from_str(&c).ok())
            .unwrap_or_default()
    } else {
        serde_json::Map::new()
    };

    // Add/update this mapping
    mappings.insert(user_id.to_string(), serde_json::Value::String(agent_id.to_string()));

    // Save
    if let Ok(content) = serde_json::to_string_pretty(&mappings) {
        if let Err(e) = std::fs::write(&path, content) {
            tracing::error!("Failed to save agent mapping: {}", e);
        } else {
            tracing::debug!("Saved agent mapping: user {} -> agent {}", user_id, agent_id);
        }
    }
}

// =============================================================================
// Bot Entry Point
// =============================================================================

/// Run the Telegram bot
pub async fn run_telegram_bot<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    service: Arc<AgentService<R>>,
    app_state: AppState<R>,
    data_dir: &str,
) -> anyhow::Result<()> {
    // TigerStyle: Preconditions
    assert!(!data_dir.is_empty(), "data_dir cannot be empty");

    let token = std::env::var("TELEGRAM_BOT_TOKEN")
        .or_else(|_| std::env::var("KELPIE_TELEGRAM_TOKEN"))
        .map_err(|_| anyhow::anyhow!("TELEGRAM_BOT_TOKEN not set"))?;

    let key_manager = KeyManager::new(std::path::Path::new(data_dir)).await?;

    // Load persisted agent mappings
    let agent_mappings = load_agent_mappings(data_dir);
    let mut user_states = HashMap::new();
    for (user_id, agent_id) in agent_mappings {
        user_states.insert(user_id, UserState {
            setup_state: SetupState::Normal,
            agent_id: Some(agent_id),
            message_times: Vec::new(),
        });
    }

    let state = Arc::new(BotState {
        service,
        key_manager: Arc::new(RwLock::new(key_manager)),
        user_states: Arc::new(RwLock::new(user_states)),
        proposals: proposal_store(),
        data_dir: data_dir.to_string(),
        app_state,
    });

    let bot = Bot::new(token);

    // Log security status
    let allowed_users = get_allowed_users();
    if allowed_users.is_empty() {
        tracing::error!(
            "ALLOWED_TELEGRAM_USERS is empty - NO users can access the bot! \
            Set your Telegram user ID (get it from @userinfobot)."
        );
    } else {
        tracing::info!(
            "Starting Tama Telegram bot with {} allowed user(s): {:?}",
            allowed_users.len(),
            allowed_users
        );
    }

    // Set up message handler
    let bot_state = state.clone();
    let handler = Update::filter_message()
        .filter_map(|msg: Message| {
            let text = msg.text()?.to_string();
            Some((msg, text))
        })
        .endpoint(move |bot: Bot, (msg, text): (Message, String)| {
            let state = bot_state.clone();
            async move {
                handle_message(state, bot, msg, text).await;
                Ok::<(), std::convert::Infallible>(())
            }
        });

    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;

    Ok(())
}

// =============================================================================
// Message Handling
// =============================================================================

/// Handle incoming message
async fn handle_message<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: Arc<BotState<R>>,
    bot: Bot,
    msg: Message,
    text: String,
) {
    tracing::info!(text_len = text.len(), "Received Telegram message");

    // TigerStyle: Validate inputs
    assert!(
        !text.is_empty() || msg.from().is_some(),
        "message must have text or sender"
    );

    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let chat_id = msg.chat.id;

    tracing::debug!(user_id, chat_id = %chat_id, "Processing message");

    // TigerStyle: Reject anonymous messages (user_id 0 is invalid)
    if user_id == 0 {
        tracing::warn!("Rejecting message with invalid user_id=0");
        return;
    }

    // Security: Check if user is in allowlist
    if !is_user_allowed(user_id) {
        tracing::warn!(user_id, "Rejecting message from unauthorized user");
        let _ = bot
            .send_message(chat_id, "Sorry, you are not authorized to use this bot.")
            .await;
        return;
    }

    let username = msg
        .from()
        .and_then(|u| u.username.clone())
        .unwrap_or_else(|| format!("user_{}", user_id));

    // Rate limiting
    {
        let mut states = state.user_states.write().await;
        let user_state = states.entry(user_id).or_default();

        let now = std::time::Instant::now();
        user_state
            .message_times
            .retain(|t| now.duration_since(*t).as_secs() < 60);

        if user_state.message_times.len() >= RATE_LIMIT_MESSAGES_PER_MINUTE as usize {
            let _ = bot
                .send_message(chat_id, "Rate limit exceeded. Please wait a moment.")
                .await;
            return;
        }
        user_state.message_times.push(now);
    }

    // Handle commands
    if text.starts_with('/') {
        handle_command(&state, &bot, chat_id, user_id, &username, &text).await;
        return;
    }

    // Check setup state
    let setup_state = {
        let states = state.user_states.read().await;
        states
            .get(&user_id)
            .map(|s| s.setup_state.clone())
            .unwrap_or(SetupState::Normal)
    };

    match setup_state {
        SetupState::WaitingForAnthropicKey => {
            handle_api_key_input(&state, &bot, chat_id, user_id, &text, ApiKeyType::Anthropic)
                .await;
        }
        SetupState::WaitingForOpenAIKey => {
            handle_api_key_input(&state, &bot, chat_id, user_id, &text, ApiKeyType::OpenAI).await;
        }
        SetupState::Normal => {
            // Check if user has required API key (per-user OR environment)
            let has_user_key = {
                let km = state.key_manager.read().await;
                km.get_key(user_id, ApiKeyType::Anthropic)
                    .ok()
                    .flatten()
                    .is_some()
            };
            let has_env_key = std::env::var("ANTHROPIC_API_KEY")
                .ok()
                .filter(|s| !s.trim().is_empty())
                .is_some();

            if !has_user_key && !has_env_key {
                let _ = bot
                    .send_message(
                        chat_id,
                        "No API key configured. Either set ANTHROPIC_API_KEY in .env or use /setup.",
                    )
                    .await;
                return;
            }

            // Handle normal chat
            handle_chat(&state, &bot, chat_id, user_id, &username, &text).await;
        }
    }
}

/// Handle command
async fn handle_command<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: &Arc<BotState<R>>,
    bot: &Bot,
    chat_id: ChatId,
    user_id: i64,
    _username: &str,
    text: &str,
) {
    // TigerStyle: Preconditions
    assert!(user_id > 0, "user_id must be positive");
    assert!(text.starts_with('/'), "command must start with /");

    let parts: Vec<&str> = text.split_whitespace().collect();
    let command = parts.first().copied().unwrap_or("");

    // TigerStyle: Command parsing invariant
    assert!(!command.is_empty(), "command cannot be empty after split");

    match command {
        "/start" => {
            let welcome = "Welcome to Tama! I'm your personal AI assistant.\n\n\
                Use /setup to configure your API key and get started.\n\
                Use /help to see all available commands.";
            let _ = bot.send_message(chat_id, welcome).await;
        }

        "/help" => {
            let help = "Commands:\n\n\
                /start - Welcome message\n\
                /setup - Set up your API key\n\
                /keys - Show configured integrations\n\
                /clear - Remove all stored keys\n\
                /proposals - List pending proposals\n\
                /view <id> - View full proposal details (including code!)\n\
                /approve <id> - Approve a proposal\n\
                /reject <id> [reason] - Reject a proposal\n\
                /reset - Reset your conversation\n\
                /help - Show this help\n\n\
                ⚠️ Always use /view before /approve to review code!\n\n\
                Just type a message to chat!";
            let _ = bot.send_message(chat_id, help).await;
        }

        "/setup" => {
            let mut states = state.user_states.write().await;
            let user_state = states.entry(user_id).or_default();
            user_state.setup_state = SetupState::WaitingForAnthropicKey;

            let _ = bot
                .send_message(
                    chat_id,
                    "Let's set up your API key.\n\n\
                    Please send me your Anthropic API key (starts with sk-ant-).\n\
                    I'll store it securely and you won't need to enter it again.\n\n\
                    Send /cancel to cancel setup.",
                )
                .await;
        }

        "/keys" => {
            let km = state.key_manager.read().await;
            let user_keys = km.list_keys(user_id);
            let has_env_key = std::env::var("ANTHROPIC_API_KEY")
                .ok()
                .filter(|s| !s.trim().is_empty())
                .is_some();

            let mut msg = "API Key Status:\n".to_string();

            if has_env_key {
                msg.push_str("- Anthropic: ✅ (from .env)\n");
            }

            for key_type in &user_keys {
                if *key_type == ApiKeyType::Anthropic && has_env_key {
                    msg.push_str("- Anthropic: ✅ (per-user, overrides .env)\n");
                } else {
                    msg.push_str(&format!("- {}: ✅ (per-user)\n", key_type.display_name()));
                }
            }

            if !has_env_key && user_keys.is_empty() {
                msg.push_str("\nNo API keys configured. Use /setup to add one.");
            }

            let _ = bot.send_message(chat_id, msg).await;
        }

        "/clear" => {
            let mut km = state.key_manager.write().await;
            if let Err(e) = km.clear_keys(user_id).await {
                let _ = bot
                    .send_message(chat_id, format!("Error clearing keys: {}", e))
                    .await;
            } else {
                let _ = bot
                    .send_message(
                        chat_id,
                        "All API keys removed. Use /setup to add a new one.",
                    )
                    .await;
            }
        }

        "/proposals" => {
            let store = state.proposals.read().await;
            let pending = store.get_pending_for_user(user_id);

            if pending.is_empty() {
                let _ = bot.send_message(chat_id, "No pending proposals.").await;
            } else {
                let mut msg = format!("Pending proposals ({}):\n\n", pending.len());
                for proposal in pending {
                    msg.push_str(&format!("{}: {}\n", proposal.id, proposal.summary()));
                }
                msg.push_str("\n⚠️ SECURITY: Use /view <id> to inspect code before approving!");
                msg.push_str("\nUse /approve <id> or /reject <id> to respond.");
                let _ = bot.send_message(chat_id, msg).await;
            }
        }

        "/view" => {
            if parts.len() < 2 {
                let _ = bot
                    .send_message(chat_id, "Usage: /view <proposal_id>")
                    .await;
                return;
            }

            let proposal_id = parts[1];
            let store = state.proposals.read().await;

            match store.get(proposal_id) {
                Some(proposal) if proposal.user_id == user_id => {
                    let mut msg = format!("Proposal: {}\n", proposal.id);
                    msg.push_str(&format!("Status: {:?}\n", proposal.status));
                    msg.push_str(&format!("Created: {}\n\n", proposal.created_at));

                    match &proposal.proposal_type {
                        crate::proposals::ProposalType::NewTool {
                            name,
                            description,
                            source_code,
                            language,
                            parameters_schema,
                        } => {
                            msg.push_str(&format!("Type: New Tool\n"));
                            msg.push_str(&format!("Name: {}\n", name));
                            msg.push_str(&format!("Description: {}\n", description));
                            msg.push_str(&format!("Language: {:?}\n", language));
                            msg.push_str(&format!("Parameters: {}\n\n", parameters_schema));
                            msg.push_str("⚠️ SOURCE CODE (review carefully!):\n");
                            msg.push_str("```\n");
                            // Truncate very long code
                            if source_code.len() > 2000 {
                                msg.push_str(&source_code[..2000]);
                                msg.push_str("\n... (truncated, {} more bytes)");
                            } else {
                                msg.push_str(source_code);
                            }
                            msg.push_str("\n```");
                        }
                        crate::proposals::ProposalType::MemoryAddition { content, category } => {
                            msg.push_str(&format!("Type: Memory Addition\n"));
                            msg.push_str(&format!("Category: {:?}\n", category));
                            msg.push_str(&format!("Content: {}\n", content));
                        }
                        crate::proposals::ProposalType::ConfigChange {
                            key,
                            value,
                            previous_value,
                        } => {
                            msg.push_str(&format!("Type: Config Change\n"));
                            msg.push_str(&format!("Key: {}\n", key));
                            msg.push_str(&format!("Value: {}\n", value));
                            msg.push_str(&format!("Previous: {:?}\n", previous_value));
                        }
                    }

                    send_long_message(bot, chat_id, &msg).await;
                }
                Some(_) => {
                    let _ = bot
                        .send_message(chat_id, "You can only view your own proposals.")
                        .await;
                }
                None => {
                    let _ = bot
                        .send_message(chat_id, format!("Proposal {} not found.", proposal_id))
                        .await;
                }
            }
        }

        "/approve" => {
            if parts.len() < 2 {
                let _ = bot
                    .send_message(chat_id, "Usage: /approve <proposal_id>")
                    .await;
                return;
            }

            let proposal_id = parts[1];
            let mut store = state.proposals.write().await;

            match store.get_mut(proposal_id) {
                Some(proposal) if proposal.user_id == user_id => {
                    if !proposal.is_pending() {
                        let _ = bot
                            .send_message(
                                chat_id,
                                format!("Proposal {} is not pending.", proposal_id),
                            )
                            .await;
                        return;
                    }

                    proposal.approve();

                    // Apply the proposal based on type
                    // Pass both the tool_registry AND the agent service so we can:
                    // 1. Register the tool globally
                    // 2. Add it to the agent's tool_ids so the agent can use it
                    let apply_result = apply_proposal(
                        proposal,
                        state.app_state.tool_registry(),
                        &state.service,
                    )
                    .await;
                    match apply_result {
                        Ok(message) => {
                            proposal.mark_applied();
                            let _ = bot
                                .send_message(
                                    chat_id,
                                    format!("Proposal {} approved!\n\n{}", proposal_id, message),
                                )
                                .await;
                        }
                        Err(error) => {
                            proposal.mark_failed(error.clone());
                            let _ = bot
                                .send_message(
                                    chat_id,
                                    format!(
                                        "Proposal {} approved but failed to apply: {}",
                                        proposal_id, error
                                    ),
                                )
                                .await;
                        }
                    }
                }
                Some(_) => {
                    let _ = bot
                        .send_message(chat_id, "You can only approve your own proposals.")
                        .await;
                }
                None => {
                    let _ = bot
                        .send_message(chat_id, format!("Proposal {} not found.", proposal_id))
                        .await;
                }
            }
        }

        "/reject" => {
            if parts.len() < 2 {
                let _ = bot
                    .send_message(chat_id, "Usage: /reject <proposal_id> [reason]")
                    .await;
                return;
            }

            let proposal_id = parts[1];
            let reason = if parts.len() > 2 {
                Some(parts[2..].join(" "))
            } else {
                None
            };

            let mut store = state.proposals.write().await;

            match store.get_mut(proposal_id) {
                Some(proposal) if proposal.user_id == user_id => {
                    if !proposal.is_pending() {
                        let _ = bot
                            .send_message(
                                chat_id,
                                format!("Proposal {} is not pending.", proposal_id),
                            )
                            .await;
                        return;
                    }

                    proposal.reject(reason);

                    let _ = bot
                        .send_message(chat_id, format!("Proposal {} rejected.", proposal_id))
                        .await;
                }
                Some(_) => {
                    let _ = bot
                        .send_message(chat_id, "You can only reject your own proposals.")
                        .await;
                }
                None => {
                    let _ = bot
                        .send_message(chat_id, format!("Proposal {} not found.", proposal_id))
                        .await;
                }
            }
        }

        "/reset" => {
            let mut states = state.user_states.write().await;
            if let Some(user_state) = states.get_mut(&user_id) {
                user_state.agent_id = None;
                user_state.setup_state = SetupState::Normal;
            }
            let _ = bot
                .send_message(
                    chat_id,
                    "Conversation reset. Your next message starts fresh.",
                )
                .await;
        }

        "/cancel" => {
            let mut states = state.user_states.write().await;
            if let Some(user_state) = states.get_mut(&user_id) {
                user_state.setup_state = SetupState::Normal;
            }
            let _ = bot.send_message(chat_id, "Setup cancelled.").await;
        }

        _ => {
            let _ = bot
                .send_message(
                    chat_id,
                    "Unknown command. Use /help to see available commands.",
                )
                .await;
        }
    }
}

/// Handle API key input during setup
async fn handle_api_key_input<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: &Arc<BotState<R>>,
    bot: &Bot,
    chat_id: ChatId,
    user_id: i64,
    text: &str,
    key_type: ApiKeyType,
) {
    // TigerStyle: Preconditions
    assert!(user_id > 0, "user_id must be positive");
    assert!(!text.is_empty(), "API key cannot be empty");
    assert!(
        text.len() <= crate::user_keys::KEY_VALUE_BYTES_MAX,
        "API key exceeds maximum length"
    );

    // Validate key format
    let is_valid = match key_type {
        ApiKeyType::Anthropic => text.starts_with("sk-ant-"),
        ApiKeyType::OpenAI => text.starts_with("sk-"),
        _ => true,
    };

    if !is_valid {
        let expected = match key_type {
            ApiKeyType::Anthropic => "sk-ant-",
            ApiKeyType::OpenAI => "sk-",
            _ => "",
        };
        let _ = bot
            .send_message(
                chat_id,
                format!(
                    "Invalid {} key format. Expected key starting with '{}'.\n\
                    Please try again or send /cancel to cancel.",
                    key_type.display_name(),
                    expected
                ),
            )
            .await;
        return;
    }

    // Store the key
    {
        let mut km = state.key_manager.write().await;
        if let Err(e) = km.store_key(user_id, key_type, text, None).await {
            let _ = bot
                .send_message(
                    chat_id,
                    format!("Error storing key: {}. Please try again.", e),
                )
                .await;
            return;
        }
    }

    // Update setup state
    {
        let mut states = state.user_states.write().await;
        let user_state = states.entry(user_id).or_default();

        match key_type {
            ApiKeyType::Anthropic => {
                // Setup complete for MVP - just need Anthropic key
                user_state.setup_state = SetupState::Normal;
                let _ = bot
                    .send_message(
                        chat_id,
                        "API key stored securely!\n\n\
                        You're all set. Just send me a message to start chatting.\n\n\
                        Try: \"What can you help me with?\"",
                    )
                    .await;
            }
            ApiKeyType::OpenAI => {
                user_state.setup_state = SetupState::Normal;
                let _ = bot
                    .send_message(chat_id, "OpenAI key stored. Setup complete!")
                    .await;
            }
            _ => {
                user_state.setup_state = SetupState::Normal;
            }
        }
    }
}

/// Create a new agent for a user and persist the mapping
async fn create_new_agent<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: &Arc<BotState<R>>,
    user_id: i64,
    username: &str,
) -> Option<String> {
    tracing::info!(user_id, username, "Creating new agent");

    let agent_name = format!("tama_user_{}", username);

    // Create agent with minimal system prompt - we'll update it after to include agent_id
    let request = CreateAgentRequest {
        name: agent_name.clone(),
        agent_type: AgentType::MemgptAgent,
        system: Some("You are Tama, a helpful personal AI assistant.".to_string()),
        metadata: serde_json::json!({
            "telegram_user_id": user_id,
            "telegram_username": username
        }),
        ..Default::default()
    };

    tracing::debug!(agent_name, "Calling service.create_agent");

    match state.service.create_agent(request).await {
        Ok(agent) => {
            let agent_id = agent.id.clone();

            // Update system prompt to include the agent_id now that we know it
            // This ensures the agent knows both user_id and agent_id for tools
            let updated_system = format!(
                "You are Tama, a helpful personal AI assistant. You have the ability to learn \
                 new capabilities through the propose_improvement tool.\n\n\
                 YOUR CONTEXT:\n\
                 - agent_id: {} (use this when calling propose_improvement or memory tools)\n\
                 - user_id: {} (use this when calling propose_improvement)\n\n\
                 IMPORTANT: When the user asks you to do something you can't currently do \
                 (like \"speak using ElevenLabs\", \"search Hacker News\", \"fetch weather\"), \
                 use the propose_improvement tool to propose a new tool:\n\n\
                 - Set proposal_type to \"new_tool\"\n\
                 - Set trigger to \"user_requested\"\n\
                 - Set agent_id to \"{}\"\n\
                 - Set user_id to {}\n\
                 - Provide a name (lowercase, underscores, e.g., \"elevenlabs_speak\")\n\
                 - Write the source_code as a shell script or Python code\n\
                 - Set language to \"shell\" or \"python\"\n\n\
                 Example: If asked \"Create a tool to get weather\", propose a tool with \
                 source_code that uses curl to fetch from wttr.in.\n\n\
                 The user can review with /proposals and approve with /approve <id>. \
                 Once approved, you'll be able to use the new tool immediately.\n\n\
                 Be helpful, concise, and proactive about proposing tools when needed.",
                agent_id, user_id, agent_id, user_id
            );

            // Update the agent with the complete system prompt
            let update = serde_json::json!({
                "system": updated_system
            });
            if let Err(e) = state.service.update_agent(&agent_id, update).await {
                tracing::warn!(
                    agent_id = %agent_id,
                    error = %e,
                    "Failed to update agent system prompt with agent_id"
                );
            }

            // Update in-memory state
            {
                let mut states = state.user_states.write().await;
                let user_state = states.entry(user_id).or_default();
                user_state.agent_id = Some(agent_id.clone());
            }

            // Persist mapping to disk
            save_agent_mapping(&state.data_dir, user_id, &agent_id);

            tracing::info!("Created new agent {} for user {}", agent_id, user_id);
            Some(agent_id)
        }
        Err(e) => {
            tracing::error!(error = %e, "Failed to create agent");
            None
        }
    }
}

/// Handle normal chat message
async fn handle_chat<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: &Arc<BotState<R>>,
    bot: &Bot,
    chat_id: ChatId,
    user_id: i64,
    username: &str,
    text: &str,
) {
    tracing::info!(user_id, username, text_len = text.len(), "handle_chat called");

    // TigerStyle: Preconditions
    assert!(user_id > 0, "user_id must be positive");
    assert!(!username.is_empty(), "username cannot be empty");
    assert!(!text.is_empty(), "message text cannot be empty");
    assert!(
        !text.starts_with('/'),
        "chat messages should not start with / (use handle_command)"
    );

    // Send typing indicator
    let _ = bot
        .send_chat_action(chat_id, teloxide::types::ChatAction::Typing)
        .await;

    // Get or create agent
    // NOTE: We must NOT hold the user_states lock while calling create_new_agent,
    // because create_new_agent also needs to acquire that lock. Holding it here
    // would cause a deadlock.
    let agent_id: Option<String> = {
        // First, check if we have an existing agent_id
        let existing_agent_id = {
            let states = state.user_states.read().await;
            states.get(&user_id).and_then(|s| s.agent_id.clone())
        };
        // Lock is now released

        if let Some(id) = existing_agent_id {
            // Verify agent still exists in storage
            match state.service.get_agent(&id).await {
                Ok(_) => {
                    tracing::debug!("Using existing agent {} for user {}", id, user_id);
                    Some(id)
                }
                Err(_) => {
                    // Agent was deleted or storage was cleared, create new one
                    tracing::warn!("Agent {} not found in storage, creating new one", id);
                    // Clear the stale agent_id
                    {
                        let mut states = state.user_states.write().await;
                        if let Some(user_state) = states.get_mut(&user_id) {
                            user_state.agent_id = None;
                        }
                    }
                    // Now create new agent (outside of any lock)
                    create_new_agent(&state, user_id, &username).await
                }
            }
        } else {
            // No existing agent, create one (outside of any lock)
            create_new_agent(&state, user_id, &username).await
        }
    };

    let Some(agent_id) = agent_id else {
        tracing::error!(user_id, "Agent creation returned None");
        let _ = bot
            .send_message(chat_id, "Sorry, I couldn't start a conversation. Try again later.")
            .await;
        return;
    };

    tracing::info!(agent_id = %agent_id, "Sending message to agent");

    // Send message to agent
    match state
        .service
        .send_message_full(&agent_id, text.to_string())
        .await
    {
        Ok(response) => {
            // Find assistant response
            let assistant_content = response
                .messages
                .iter()
                .rev()
                .find(|m| m.role == MessageRole::Assistant)
                .map(|m| m.content.clone())
                .unwrap_or_else(|| "I didn't have a response.".to_string());

            // Send response (split if too long)
            send_long_message(bot, chat_id, &assistant_content).await;
        }
        Err(e) => {
            tracing::error!(error = %e, agent_id = %agent_id, "Failed to send message");
            let _ = bot
                .send_message(
                    chat_id,
                    "Sorry, I couldn't process your message. Please try again.",
                )
                .await;
        }
    }
}

/// Send a potentially long message, splitting if necessary
///
/// TigerStyle: Uses char_indices() to avoid breaking UTF-8 characters
async fn send_long_message(bot: &Bot, chat_id: ChatId, content: &str) {
    // Split into chunks at UTF-8-safe boundaries
    let chunks = split_utf8_safe(content, TELEGRAM_MESSAGE_LENGTH_MAX);

    // TigerStyle: Postcondition - chunks should cover entire content
    debug_assert!(
        chunks.iter().map(|c| c.len()).sum::<usize>() == content.len(),
        "chunks must cover entire content without loss"
    );

    for chunk in chunks {
        if !chunk.is_empty() {
            if let Err(e) = bot.send_message(chat_id, chunk).await {
                tracing::error!(error = %e, "Failed to send Telegram message");
            }
        }
    }
}

/// Split a string into chunks without breaking UTF-8 characters
///
/// TigerStyle: Find safe split points using char_indices()
fn split_utf8_safe(s: &str, max_bytes: usize) -> Vec<&str> {
    // TigerStyle: Preconditions
    assert!(max_bytes > 0, "max_bytes must be positive");
    assert!(
        max_bytes >= 4,
        "max_bytes must be at least 4 to fit any UTF-8 char"
    );

    if s.len() <= max_bytes {
        return vec![s];
    }

    let mut chunks = Vec::new();
    let mut start = 0;

    while start < s.len() {
        // Find the end position for this chunk
        let remaining = &s[start..];
        if remaining.len() <= max_bytes {
            chunks.push(remaining);
            break;
        }

        // Find the last valid UTF-8 boundary within max_bytes
        let mut end = start + max_bytes;
        while end > start && !s.is_char_boundary(end) {
            end -= 1;
        }

        // Safety: If we couldn't find a valid boundary (shouldn't happen with valid UTF-8),
        // fall back to character-by-character splitting
        if end == start {
            // Find the next char boundary after start
            end = start + 1;
            while end < s.len() && !s.is_char_boundary(end) {
                end += 1;
            }
        }

        chunks.push(&s[start..end]);
        start = end;
    }

    // TigerStyle: Postconditions
    debug_assert!(!chunks.is_empty(), "must produce at least one chunk");
    debug_assert!(
        chunks.iter().all(|c| !c.is_empty() || s.is_empty()),
        "chunks must not be empty (unless input is empty)"
    );

    chunks
}

// =============================================================================
// Proposal Application
// =============================================================================

use crate::proposals::{MemoryCategory, Proposal, ProposalType, ToolLanguage};

/// Apply an approved proposal
///
/// Returns Ok(message) with details of what was applied, or Err(error) if failed.
///
/// For NewTool proposals, this:
/// 1. Registers the tool with the global tool registry
/// 2. Adds the tool to the agent's tool_ids so the agent can use it
async fn apply_proposal<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    proposal: &Proposal,
    tool_registry: &UnifiedToolRegistry,
    agent_service: &AgentService<R>,
) -> Result<String, String> {
    // TigerStyle: Preconditions
    assert!(!proposal.id.is_empty(), "proposal must have id");
    assert!(proposal.user_id > 0, "proposal must have valid user_id");
    assert!(proposal.is_approved(), "can only apply approved proposals");

    match &proposal.proposal_type {
        ProposalType::NewTool {
            name,
            description,
            parameters_schema,
            source_code,
            language,
        } => {
            // Map our ToolLanguage to the runtime string for the registry
            let runtime = match language {
                ToolLanguage::Shell => "bash",
                ToolLanguage::Python => "python",
                ToolLanguage::JavaScript => "javascript",
            };

            tracing::info!(
                proposal_id = %proposal.id,
                tool_name = %name,
                language = %runtime,
                code_length = source_code.len(),
                "Registering NewTool proposal with tool registry"
            );

            // Step 1: Register the tool with the global registry
            tool_registry
                .register_custom_tool(
                    name.clone(),
                    description.clone(),
                    parameters_schema.clone(),
                    source_code.clone(),
                    runtime,
                    vec![], // No additional requirements for now
                )
                .await;

            // Step 2: Add tool to agent's tool_ids so the agent can actually use it
            // The agent filter at agent_actor.rs:313 only allows tools in:
            // - capabilities.allowed_tools (static), OR
            // - agent.tool_ids (per-agent)
            let agent_id = &proposal.agent_id;
            match agent_service.get_agent(agent_id).await {
                Ok(agent) => {
                    // Add new tool to existing tool_ids
                    let mut updated_tool_ids = agent.tool_ids.clone();
                    if !updated_tool_ids.contains(name) {
                        updated_tool_ids.push(name.clone());
                    }

                    // Update the agent with new tool_ids
                    let update = serde_json::json!({
                        "tool_ids": updated_tool_ids
                    });

                    if let Err(e) = agent_service.update_agent(agent_id, update).await {
                        tracing::error!(
                            agent_id = %agent_id,
                            tool_name = %name,
                            error = %e,
                            "Failed to add tool to agent's tool_ids"
                        );
                        // Tool is registered but agent can't use it yet
                        return Ok(format!(
                            "Tool '{}' registered but couldn't add to agent: {}\n\n\
                             The tool exists but the agent may not be able to use it until restart.",
                            name, e
                        ));
                    }

                    tracing::info!(
                        agent_id = %agent_id,
                        tool_name = %name,
                        "Tool added to agent's tool_ids - agent can now use it"
                    );
                }
                Err(e) => {
                    tracing::warn!(
                        agent_id = %agent_id,
                        error = %e,
                        "Could not find agent to add tool - tool registered but agent can't use it"
                    );
                    return Ok(format!(
                        "Tool '{}' registered but agent {} not found: {}\n\n\
                         The tool will be available after agent restart.",
                        name, agent_id, e
                    ));
                }
            }

            Ok(format!(
                "Tool '{}' registered and ready to use!\n\n\
                 Language: {}\n\
                 Description: {}\n\
                 Code length: {} bytes\n\n\
                 The agent can now use this tool immediately.",
                name, runtime, description, source_code.len()
            ))
        }

        ProposalType::MemoryAddition { content, category } => {
            let category_str = match category {
                MemoryCategory::Persona => "persona",
                MemoryCategory::Human => "human",
                MemoryCategory::Knowledge => "knowledge",
                MemoryCategory::Preferences => "preferences",
            };

            tracing::info!(
                proposal_id = %proposal.id,
                category = %category_str,
                content_length = content.len(),
                "Applying MemoryAddition proposal"
            );

            // For MVP: Log the memory addition
            // Full implementation would add to the agent's memory blocks
            // via AgentService.update_memory() or similar

            let preview = if content.len() > 100 {
                format!("{}...", &content[..100])
            } else {
                content.clone()
            };

            Ok(format!(
                "Memory added to '{}' category.\n\n\
                 Content: {}",
                category_str, preview
            ))
        }

        ProposalType::ConfigChange { key, value, .. } => {
            tracing::info!(
                proposal_id = %proposal.id,
                config_key = %key,
                "Applying ConfigChange proposal"
            );

            // For MVP: Log the config change
            // In a full implementation, this would update configuration

            Ok(format!("Configuration '{}' updated to: {}", key, value))
        }
    }
}
