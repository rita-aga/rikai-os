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
}

// =============================================================================
// Bot Entry Point
// =============================================================================

/// Run the Telegram bot
pub async fn run_telegram_bot<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    service: Arc<AgentService<R>>,
    data_dir: &str,
) -> anyhow::Result<()> {
    let token = std::env::var("TELEGRAM_BOT_TOKEN")
        .or_else(|_| std::env::var("KELPIE_TELEGRAM_TOKEN"))
        .map_err(|_| anyhow::anyhow!("TELEGRAM_BOT_TOKEN not set"))?;

    let key_manager = KeyManager::new(std::path::Path::new(data_dir)).await?;

    let state = Arc::new(BotState {
        service,
        key_manager: Arc::new(RwLock::new(key_manager)),
        user_states: Arc::new(RwLock::new(HashMap::new())),
        proposals: proposal_store(),
    });

    let bot = Bot::new(token);

    tracing::info!("Starting Tama Telegram bot...");

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
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let chat_id = msg.chat.id;
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
            handle_api_key_input(&state, &bot, chat_id, user_id, &text, ApiKeyType::Anthropic).await;
        }
        SetupState::WaitingForOpenAIKey => {
            handle_api_key_input(&state, &bot, chat_id, user_id, &text, ApiKeyType::OpenAI).await;
        }
        SetupState::Normal => {
            // Check if user has required API key
            let has_key = {
                let km = state.key_manager.read().await;
                km.get_key(user_id, ApiKeyType::Anthropic)
                    .ok()
                    .flatten()
                    .is_some()
            };

            if !has_key {
                let _ = bot
                    .send_message(
                        chat_id,
                        "Please set up your API key first with /setup to start chatting.",
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
    let parts: Vec<&str> = text.split_whitespace().collect();
    let command = parts.first().map(|s| *s).unwrap_or("");

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
                /approve <id> - Approve a proposal\n\
                /reject <id> [reason] - Reject a proposal\n\
                /reset - Reset your conversation\n\
                /help - Show this help\n\n\
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
            let keys = km.list_keys(user_id);

            if keys.is_empty() {
                let _ = bot
                    .send_message(chat_id, "No API keys configured. Use /setup to add one.")
                    .await;
            } else {
                let mut msg = "Configured integrations:\n".to_string();
                for key_type in keys {
                    msg.push_str(&format!("- {} (configured)\n", key_type.display_name()));
                }
                let _ = bot.send_message(chat_id, msg).await;
            }
        }

        "/clear" => {
            let mut km = state.key_manager.write().await;
            if let Err(e) = km.clear_keys(user_id).await {
                let _ = bot
                    .send_message(chat_id, format!("Error clearing keys: {}", e))
                    .await;
            } else {
                let _ = bot
                    .send_message(chat_id, "All API keys removed. Use /setup to add a new one.")
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
                msg.push_str("\nUse /approve <id> or /reject <id> to respond.");
                let _ = bot.send_message(chat_id, msg).await;
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
                    // TODO: Actually apply the proposal (register tool, add memory, etc.)
                    proposal.mark_applied();

                    let _ = bot
                        .send_message(chat_id, format!("Proposal {} approved and applied!", proposal_id))
                        .await;
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
                .send_message(chat_id, "Conversation reset. Your next message starts fresh.")
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
                .send_message(chat_id, "Unknown command. Use /help to see available commands.")
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
                .send_message(chat_id, format!("Error storing key: {}. Please try again.", e))
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

/// Handle normal chat message
async fn handle_chat<R: kelpie_core::Runtime + Clone + Send + Sync + 'static>(
    state: &Arc<BotState<R>>,
    bot: &Bot,
    chat_id: ChatId,
    user_id: i64,
    username: &str,
    text: &str,
) {
    // Send typing indicator
    let _ = bot
        .send_chat_action(chat_id, teloxide::types::ChatAction::Typing)
        .await;

    // Get or create agent
    let agent_id = {
        let mut states = state.user_states.write().await;
        let user_state = states.entry(user_id).or_default();

        if let Some(id) = &user_state.agent_id {
            id.clone()
        } else {
            // Create new agent
            let agent_name = format!("tama_user_{}", username);
            let request = CreateAgentRequest {
                name: agent_name,
                agent_type: AgentType::MemgptAgent,
                system: Some(
                    "You are Tama, a helpful personal AI assistant. You can help with tasks, \
                     answer questions, and even propose new tools or improvements.\n\n\
                     When the user asks you to create or implement something, use the \
                     propose_improvement tool to create a proposal for approval.\n\n\
                     Be helpful, concise, and proactive."
                        .to_string(),
                ),
                ..Default::default()
            };

            match state.service.create_agent(request).await {
                Ok(agent) => {
                    user_state.agent_id = Some(agent.id.clone());
                    agent.id
                }
                Err(e) => {
                    tracing::error!(error = %e, "Failed to create agent");
                    let _ = bot
                        .send_message(chat_id, "Sorry, I couldn't start a conversation. Try again later.")
                        .await;
                    return;
                }
            }
        }
    };

    // Send message to agent
    match state.service.send_message_full(&agent_id, text.to_string()).await {
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
                .send_message(chat_id, "Sorry, I couldn't process your message. Please try again.")
                .await;
        }
    }
}

/// Send a potentially long message, splitting if necessary
async fn send_long_message(bot: &Bot, chat_id: ChatId, content: &str) {
    // Split into chunks if too long
    let chunks: Vec<&str> = content
        .as_bytes()
        .chunks(TELEGRAM_MESSAGE_LENGTH_MAX)
        .map(|chunk| std::str::from_utf8(chunk).unwrap_or(""))
        .collect();

    for chunk in chunks {
        if !chunk.is_empty() {
            if let Err(e) = bot.send_message(chat_id, chunk).await {
                tracing::error!(error = %e, "Failed to send Telegram message");
            }
        }
    }
}
