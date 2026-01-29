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
pub mod tools;
pub mod trajectory;
pub mod user_keys;

use clap::Parser;
use kelpie_core::TokioRuntime;
use kelpie_sandbox::{PoolConfig, ProcessSandboxFactory, ResourceLimits, SandboxConfig, SandboxPool};
use kelpie_server::state::AppState;
use kelpie_server::storage::{AgentStorage, FdbAgentRegistry};
use kelpie_server::tools::register_memory_tools;
use kelpie_storage::FdbKV;
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

/// Minimum sandboxes in pool
pub const SANDBOX_POOL_SIZE_MIN: usize = 2;

/// Maximum sandboxes in pool
pub const SANDBOX_POOL_SIZE_MAX: usize = 10;

/// Sandbox memory limit in bytes (512MB)
pub const SANDBOX_MEMORY_BYTES_MAX: u64 = 512 * 1024 * 1024;

/// Sandbox execution timeout in milliseconds (30 seconds)
pub const SANDBOX_TIMEOUT_MS_DEFAULT: u64 = 30_000;

/// Standard paths to check for FDB cluster file
const FDB_CLUSTER_PATHS: &[&str] = &[
    "/etc/foundationdb/fdb.cluster",
    "/usr/local/etc/foundationdb/fdb.cluster",
    "/opt/foundationdb/fdb.cluster",
    "/var/foundationdb/fdb.cluster",
];

/// Detect FDB cluster file from env vars or standard paths
fn detect_fdb_cluster_file() -> Option<String> {
    // 1. Check KELPIE_FDB_CLUSTER env var
    if let Ok(cluster_file) = std::env::var("KELPIE_FDB_CLUSTER") {
        if !cluster_file.is_empty() {
            tracing::info!("Storage: Using FDB from KELPIE_FDB_CLUSTER: {}", cluster_file);
            return Some(cluster_file);
        }
    }

    // 2. Check FDB_CLUSTER_FILE env var (standard FDB env var)
    if let Ok(cluster_file) = std::env::var("FDB_CLUSTER_FILE") {
        if !cluster_file.is_empty() {
            tracing::info!("Storage: Using FDB from FDB_CLUSTER_FILE: {}", cluster_file);
            return Some(cluster_file);
        }
    }

    // 3. Auto-detect from standard paths
    for path in FDB_CLUSTER_PATHS {
        if std::path::Path::new(path).exists() {
            tracing::info!("Storage: Auto-detected FDB at: {}", path);
            return Some((*path).to_string());
        }
    }

    None
}

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
    // Load .env file (if present)
    dotenvy::dotenv().ok();

    let cli = Cli::parse();

    // Initialize logging
    let filter = match cli.verbose {
        0 => "info,tower_http=debug",
        1 => "debug",
        _ => "trace",
    };

    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| filter.into()),
        )
        .init();

    tracing::info!("Tama MVP v{}", APP_VERSION);

    // Expand data directory
    let data_dir = shellexpand::tilde(&cli.data_dir).to_string();
    std::fs::create_dir_all(&data_dir)?;
    tracing::info!("Data directory: {}", data_dir);

    // Create Kelpie runtime
    let runtime = TokioRuntime;

    // Detect and connect to FDB if available
    let state = if let Some(cluster_file) = detect_fdb_cluster_file() {
        tracing::info!("Connecting to FoundationDB...");
        let fdb_kv = FdbKV::connect(Some(&cluster_file))
            .await
            .map_err(|e| anyhow::anyhow!("Failed to connect to FDB: {}", e))?;

        let storage: Arc<dyn AgentStorage> = Arc::new(FdbAgentRegistry::new(Arc::new(fdb_kv)));
        tracing::info!("FDB storage initialized - data WILL be persisted");
        AppState::with_storage(runtime.clone(), storage)
    } else {
        tracing::warn!("No FDB cluster file found - using in-memory storage");
        tracing::warn!("Data will NOT persist across restarts!");
        tracing::warn!("To enable persistence, install FDB or set KELPIE_FDB_CLUSTER");
        AppState::new(runtime.clone())
    };

    // Initialize sandbox pool for custom tool execution
    let limits = ResourceLimits::default()
        .with_memory(SANDBOX_MEMORY_BYTES_MAX)
        .with_exec_timeout(std::time::Duration::from_millis(SANDBOX_TIMEOUT_MS_DEFAULT));
    let sandbox_config = SandboxConfig::default().with_limits(limits);

    let pool_config = PoolConfig::new(sandbox_config)
        .with_min_size(SANDBOX_POOL_SIZE_MIN)
        .with_max_size(SANDBOX_POOL_SIZE_MAX);

    match SandboxPool::new(ProcessSandboxFactory::new(), pool_config) {
        Ok(sandbox_pool) => {
            state
                .tool_registry()
                .set_sandbox_pool(Arc::new(sandbox_pool))
                .await;
            tracing::info!(
                min = SANDBOX_POOL_SIZE_MIN,
                max = SANDBOX_POOL_SIZE_MAX,
                "Sandbox pool initialized for custom tool execution"
            );
        }
        Err(e) => {
            tracing::warn!(
                error = %e,
                "Failed to create sandbox pool - custom tools will use one-off sandboxes"
            );
        }
    }

    // Register Kelpie memory tools (core_memory_append, core_memory_replace, etc.)
    register_memory_tools(state.tool_registry(), state.clone()).await;

    // Register proposal tool
    tools::register_proposal_tool(state.tool_registry()).await;

    // Register trajectory tools
    tools::register_trajectory_tools(state.tool_registry()).await;

    if cli.telegram {
        // Get agent service from AppState
        let service = state.agent_service().ok_or_else(|| {
            anyhow::anyhow!(
                "Agent service not available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable."
            )
        })?;

        // Run Telegram bot with full state for tool registration
        tracing::info!("Starting Telegram interface...");
        telegram::run_telegram_bot(Arc::new(service.clone()), state.clone(), &data_dir).await?;
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
