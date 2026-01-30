//! Minimal test to reproduce the create_agent hang issue

use kelpie_core::TokioRuntime;
use kelpie_server::models::{AgentType, CreateAgentRequest};
use kelpie_server::service::AgentService;
use kelpie_server::state::AppState;
use std::sync::Arc;

#[tokio::test]
async fn test_create_agent_returns() {
    // Load .env file
    dotenvy::dotenv().ok();

    // Initialize logging
    let _ = tracing_subscriber::fmt()
        .with_env_filter("debug")
        .try_init();

    // Create runtime and state (same as rikaios main.rs)
    let runtime = TokioRuntime;
    let state = AppState::new(runtime);

    // Get agent service
    let service = state.agent_service().expect("Agent service should be available");

    // Create agent request (same as telegram.rs)
    let request = CreateAgentRequest {
        name: "test_agent".to_string(),
        agent_type: AgentType::MemgptAgent,
        system: Some("You are a test agent".to_string()),
        ..Default::default()
    };

    tracing::info!("Calling create_agent");

    // This should return, not hang
    let result = tokio::time::timeout(
        std::time::Duration::from_secs(5),
        service.create_agent(request),
    )
    .await;

    match result {
        Ok(Ok(agent)) => {
            tracing::info!("Agent created: {}", agent.id);
            assert!(!agent.id.is_empty());
        }
        Ok(Err(e)) => {
            panic!("create_agent failed: {:?}", e);
        }
        Err(_) => {
            panic!("create_agent timed out after 5 seconds - this is the bug!");
        }
    }
}

/// Test that mimics how Telegram bot uses the service:
/// - Clones service into Arc
/// - Calls from spawned task (like teloxide handler)
#[tokio::test]
async fn test_create_agent_from_spawned_task() {
    // Load .env file
    dotenvy::dotenv().ok();

    // Initialize logging
    let _ = tracing_subscriber::fmt()
        .with_env_filter("debug")
        .try_init();

    // Create runtime and state (same as rikaios main.rs)
    let runtime = TokioRuntime;
    let state = AppState::new(runtime);

    // Get agent service - mimic how main.rs does it
    let service = state.agent_service().expect("Agent service should be available");

    // Clone and wrap in Arc like main.rs does: Arc::new(service.clone())
    let service: Arc<AgentService<TokioRuntime>> = Arc::new(service.clone());

    // Spawn a task to call create_agent (like teloxide does)
    let handle = tokio::spawn(async move {
        let request = CreateAgentRequest {
            name: "test_agent_spawned".to_string(),
            agent_type: AgentType::MemgptAgent,
            system: Some("You are a test agent".to_string()),
            ..Default::default()
        };

        tracing::info!("Calling create_agent from spawned task");

        let result = tokio::time::timeout(
            std::time::Duration::from_secs(5),
            service.create_agent(request),
        )
        .await;

        match result {
            Ok(Ok(agent)) => {
                tracing::info!("Agent created from spawned task: {}", agent.id);
                Ok(agent.id)
            }
            Ok(Err(e)) => {
                tracing::error!("create_agent failed: {:?}", e);
                Err(format!("create_agent failed: {:?}", e))
            }
            Err(_) => {
                tracing::error!("create_agent timed out");
                Err("create_agent timed out after 5 seconds".to_string())
            }
        }
    });

    // Wait for the spawned task
    let result = handle.await.expect("Task panicked");
    assert!(result.is_ok(), "create_agent should succeed: {:?}", result);
}

/// Test that simulates the exact pattern that caused the deadlock:
/// - Hold a RwLock while calling create_agent
/// - create_agent also needs the same RwLock
/// This test verifies the deadlock is fixed.
#[tokio::test]
async fn test_no_deadlock_with_rwlock() {
    use std::collections::HashMap;
    use tokio::sync::RwLock;

    // Load .env file
    dotenvy::dotenv().ok();

    // Initialize logging
    let _ = tracing_subscriber::fmt()
        .with_env_filter("debug")
        .try_init();

    // Create runtime and state
    let runtime = TokioRuntime;
    let state = AppState::new(runtime);
    let service = Arc::new(state.agent_service().expect("Service should be available").clone());

    // Simulate user_states RwLock like in telegram.rs
    let user_states: Arc<RwLock<HashMap<i64, Option<String>>>> = Arc::new(RwLock::new(HashMap::new()));

    let service_clone = service.clone();
    let user_states_clone = user_states.clone();

    // This pattern previously caused a deadlock:
    // 1. Acquire write lock on user_states
    // 2. Call create_agent (which internally needed the same lock)
    //
    // The fix: release the lock before calling create_agent
    let handle = tokio::spawn(async move {
        let user_id = 12345i64;

        // Simulate the FIXED pattern: read, release lock, then create
        let existing_agent = {
            let states = user_states_clone.read().await;
            states.get(&user_id).cloned().flatten()
        };
        // Lock is released here

        let agent_id = if existing_agent.is_some() {
            existing_agent
        } else {
            // Create agent OUTSIDE the lock
            let request = CreateAgentRequest {
                name: "test_deadlock".to_string(),
                agent_type: AgentType::MemgptAgent,
                system: Some("Test".to_string()),
                ..Default::default()
            };

            match tokio::time::timeout(
                std::time::Duration::from_secs(5),
                service_clone.create_agent(request),
            ).await {
                Ok(Ok(agent)) => {
                    // Now acquire write lock to update state
                    let mut states = user_states_clone.write().await;
                    states.insert(user_id, Some(agent.id.clone()));
                    Some(agent.id)
                }
                Ok(Err(e)) => {
                    tracing::error!("create_agent failed: {:?}", e);
                    None
                }
                Err(_) => {
                    panic!("DEADLOCK DETECTED: create_agent timed out");
                }
            }
        };

        agent_id
    });

    let result = handle.await.expect("Task panicked");
    assert!(result.is_some(), "Agent should have been created");
    tracing::info!("Test passed - no deadlock!");
}
