//! Tama MVP - Secure Self-Improving AI Assistant
//!
//! A minimal, security-first AI assistant using Kelpie that can bootstrap
//! its own development.
//!
//! Features:
//! - Sandbox-first security (Apple VZ on Mac, Firecracker on Linux)
//! - Self-improvement via proposals (user-driven or agent-suggested)
//! - Trajectory capture for training data
//! - Telegram-first UX

pub mod proposals;
pub mod telegram;
pub mod trajectory;
pub mod tools;
pub mod user_keys;

use clap::Parser;
use kelpie_core::TokioRuntime;
use kelpie_server::state::AppState;
use std::sync::Arc;

// =============================================================================
// TigerStyle Constants
// =============================================================================

/// Default HTTP bind address
pub const HTTP_BIND_ADDRESS_DEFAULT: &str = "127.0.0.1:8284";

/// Application name
pub const APP_NAME: &str = "rikai";

/// Application version
pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

// =============================================================================
// CLI
// =============================================================================

/// Tama MVP - Secure Self-Improving AI Assistant
#[derive(Parser, Debug)]
#[command(name = APP_NAME)]
#[command(about = "Secure self-improving AI assistant using Kelpie")]
#[command(version)]
struct Cli {
    /// HTTP API bind address (for local tools/debugging)
    #[arg(short, long, default_value = HTTP_BIND_ADDRESS_DEFAULT)]
    bind: String,

    /// Enable verbose logging
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

    /// Run in Telegram mode (interactive chat)
    #[arg(long)]
    telegram: bool,

    /// User data directory for encrypted keys and trajectories
    #[arg(long, default_value = "~/.rikai")]
    data_dir: String,
}

// =============================================================================
// Main
// =============================================================================

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    // Initialize logging
    let filter = match cli.verbose {
        0 => "info,tower_http=debug",
        1 => "debug",
        _ => "trace",
    };

    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| filter.into()),
        )
        .init();

    tracing::info!("Tama MVP v{}", APP_VERSION);

    // Expand data directory
    let data_dir = shellexpand::tilde(&cli.data_dir).to_string();
    std::fs::create_dir_all(&data_dir)?;
    tracing::info!("Data directory: {}", data_dir);

    // Create Kelpie runtime
    let runtime = TokioRuntime;

    // Create application state (in-memory for MVP, can add FDB later)
    // This will automatically create an AgentService if ANTHROPIC_API_KEY is set
    let state = AppState::new(runtime.clone());

    // Register proposal tool
    tools::register_proposal_tool(state.tool_registry()).await;

    // Register trajectory tools
    tools::register_trajectory_tools(state.tool_registry()).await;

    if cli.telegram {
        // Get agent service from AppState
        let service = state
            .agent_service()
            .ok_or_else(|| anyhow::anyhow!(
                "Agent service not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable."
            ))?;

        // Run Telegram bot
        tracing::info!("Starting Telegram interface...");
        telegram::run_telegram_bot(Arc::new(service.clone()), &data_dir).await?;
    } else {
        // Run HTTP server for local development
        tracing::info!("Starting HTTP server on {}", cli.bind);
        tracing::info!("Use --telegram flag to start the Telegram bot");

        // Just start the basic Kelpie HTTP server
        let addr: std::net::SocketAddr = cli.bind.parse()?;
        let app = kelpie_server::api::router(state);

        let listener = tokio::net::TcpListener::bind(addr).await?;
        axum::serve(listener, app).await?;
    }

    Ok(())
}
