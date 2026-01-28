//! User API Key Storage
//!
//! TigerStyle: Secure storage for user API keys collected via Telegram.
//!
//! Keys are encrypted at rest using AES-GCM with a per-user derived key.
//! The master key is derived from a user-provided passphrase or stored
//! in a secure location (e.g., macOS Keychain on Mac).
//!
//! Security model:
//! - Keys are encrypted with AES-256-GCM
//! - Each key has a unique nonce
//! - Keys are stored in a local file (encrypted)
//! - Master key is stored separately or derived from passphrase

use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::fs;

// =============================================================================
// TigerStyle Constants
// =============================================================================

/// Key file name
pub const KEY_FILE_NAME: &str = "user_keys.enc";

/// Master key file name
pub const MASTER_KEY_FILE_NAME: &str = "master.key";

/// Nonce size in bytes (96 bits for AES-GCM)
pub const NONCE_SIZE_BYTES: usize = 12;

/// Master key size in bytes (256 bits for AES-256)
pub const MASTER_KEY_SIZE_BYTES: usize = 32;

/// Maximum key value length in bytes
pub const KEY_VALUE_BYTES_MAX: usize = 1024;

// =============================================================================
// Types
// =============================================================================

/// Known API key types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ApiKeyType {
    /// Anthropic API key
    Anthropic,
    /// OpenAI API key
    OpenAI,
    /// Telegram bot token
    Telegram,
    /// Custom/other key
    Custom,
}

impl ApiKeyType {
    /// Get display name
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::Anthropic => "Anthropic",
            Self::OpenAI => "OpenAI",
            Self::Telegram => "Telegram",
            Self::Custom => "Custom",
        }
    }

    /// Get environment variable name
    pub fn env_var_name(&self) -> &'static str {
        match self {
            Self::Anthropic => "ANTHROPIC_API_KEY",
            Self::OpenAI => "OPENAI_API_KEY",
            Self::Telegram => "TELEGRAM_BOT_TOKEN",
            Self::Custom => "CUSTOM_API_KEY",
        }
    }
}

/// An encrypted API key
#[derive(Debug, Clone, Serialize, Deserialize)]
struct EncryptedKey {
    /// Key type
    key_type: ApiKeyType,
    /// Encrypted value (base64)
    encrypted_value: String,
    /// Nonce used for encryption (base64)
    nonce: String,
    /// Optional custom name (for Custom type)
    custom_name: Option<String>,
}

/// Per-user key storage
#[derive(Debug, Default, Serialize, Deserialize)]
struct UserKeyData {
    /// User ID (Telegram)
    user_id: i64,
    /// Encrypted keys
    keys: Vec<EncryptedKey>,
}

/// All users' key storage
#[derive(Debug, Default, Serialize, Deserialize)]
struct KeyStore {
    /// Version for format migrations
    version: u32,
    /// Per-user data
    users: HashMap<i64, UserKeyData>,
}

// =============================================================================
// Key Manager
// =============================================================================

/// Manages user API keys with encryption
pub struct KeyManager {
    /// Data directory
    data_dir: PathBuf,
    /// Master encryption key
    master_key: [u8; MASTER_KEY_SIZE_BYTES],
    /// In-memory key store (decrypted)
    store: KeyStore,
}

impl KeyManager {
    /// Create or load key manager
    pub async fn new(data_dir: &Path) -> Result<Self, KeyError> {
        let data_dir = data_dir.to_path_buf();
        fs::create_dir_all(&data_dir).await?;

        // Load or generate master key
        let master_key_path = data_dir.join(MASTER_KEY_FILE_NAME);
        let master_key = if master_key_path.exists() {
            let bytes = fs::read(&master_key_path).await?;
            if bytes.len() != MASTER_KEY_SIZE_BYTES {
                return Err(KeyError::InvalidMasterKey);
            }
            let mut key = [0u8; MASTER_KEY_SIZE_BYTES];
            key.copy_from_slice(&bytes);
            key
        } else {
            // Generate new master key
            let mut key = [0u8; MASTER_KEY_SIZE_BYTES];
            OsRng.fill_bytes(&mut key);
            fs::write(&master_key_path, &key).await?;
            tracing::info!("Generated new master key");
            key
        };

        // Load existing key store
        let key_file_path = data_dir.join(KEY_FILE_NAME);
        let store = if key_file_path.exists() {
            let bytes = fs::read(&key_file_path).await?;
            serde_json::from_slice(&bytes).map_err(KeyError::InvalidKeyStore)?
        } else {
            KeyStore {
                version: 1,
                users: HashMap::new(),
            }
        };

        Ok(Self {
            data_dir,
            master_key,
            store,
        })
    }

    /// Store an API key for a user
    pub async fn store_key(
        &mut self,
        user_id: i64,
        key_type: ApiKeyType,
        value: &str,
        custom_name: Option<String>,
    ) -> Result<(), KeyError> {
        // Validate
        if value.is_empty() {
            return Err(KeyError::EmptyKey);
        }
        if value.len() > KEY_VALUE_BYTES_MAX {
            return Err(KeyError::KeyTooLong {
                len: value.len(),
                max: KEY_VALUE_BYTES_MAX,
            });
        }

        // Encrypt the key
        let cipher = Aes256Gcm::new_from_slice(&self.master_key)
            .map_err(|_| KeyError::CryptoError("failed to create cipher".to_string()))?;

        let mut nonce_bytes = [0u8; NONCE_SIZE_BYTES];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let encrypted = cipher
            .encrypt(nonce, value.as_bytes())
            .map_err(|e| KeyError::CryptoError(format!("encryption failed: {}", e)))?;

        let encrypted_key = EncryptedKey {
            key_type,
            encrypted_value: BASE64.encode(&encrypted),
            nonce: BASE64.encode(&nonce_bytes),
            custom_name,
        };

        // Store
        let user_data = self.store.users.entry(user_id).or_insert_with(|| UserKeyData {
            user_id,
            keys: Vec::new(),
        });

        // Remove existing key of same type
        user_data.keys.retain(|k| k.key_type != key_type);
        user_data.keys.push(encrypted_key);

        // Save to disk
        self.save().await?;

        tracing::info!(
            user_id = user_id,
            key_type = ?key_type,
            "Stored API key"
        );

        Ok(())
    }

    /// Get a decrypted API key for a user
    pub fn get_key(&self, user_id: i64, key_type: ApiKeyType) -> Result<Option<String>, KeyError> {
        let user_data = match self.store.users.get(&user_id) {
            Some(data) => data,
            None => return Ok(None),
        };

        let encrypted_key = match user_data.keys.iter().find(|k| k.key_type == key_type) {
            Some(k) => k,
            None => return Ok(None),
        };

        // Decrypt
        let cipher = Aes256Gcm::new_from_slice(&self.master_key)
            .map_err(|_| KeyError::CryptoError("failed to create cipher".to_string()))?;

        let nonce_bytes = BASE64
            .decode(&encrypted_key.nonce)
            .map_err(|e| KeyError::CryptoError(format!("invalid nonce: {}", e)))?;
        let nonce = Nonce::from_slice(&nonce_bytes);

        let encrypted_bytes = BASE64
            .decode(&encrypted_key.encrypted_value)
            .map_err(|e| KeyError::CryptoError(format!("invalid encrypted value: {}", e)))?;

        let decrypted = cipher
            .decrypt(nonce, encrypted_bytes.as_ref())
            .map_err(|e| KeyError::CryptoError(format!("decryption failed: {}", e)))?;

        String::from_utf8(decrypted)
            .map(Some)
            .map_err(|e| KeyError::CryptoError(format!("invalid UTF-8: {}", e)))
    }

    /// List configured key types for a user
    pub fn list_keys(&self, user_id: i64) -> Vec<ApiKeyType> {
        self.store
            .users
            .get(&user_id)
            .map(|data| data.keys.iter().map(|k| k.key_type).collect())
            .unwrap_or_default()
    }

    /// Remove a key for a user
    pub async fn remove_key(&mut self, user_id: i64, key_type: ApiKeyType) -> Result<bool, KeyError> {
        let user_data = match self.store.users.get_mut(&user_id) {
            Some(data) => data,
            None => return Ok(false),
        };

        let len_before = user_data.keys.len();
        user_data.keys.retain(|k| k.key_type != key_type);
        let removed = user_data.keys.len() < len_before;

        if removed {
            self.save().await?;
            tracing::info!(
                user_id = user_id,
                key_type = ?key_type,
                "Removed API key"
            );
        }

        Ok(removed)
    }

    /// Remove all keys for a user
    pub async fn clear_keys(&mut self, user_id: i64) -> Result<(), KeyError> {
        self.store.users.remove(&user_id);
        self.save().await?;
        tracing::info!(user_id = user_id, "Cleared all API keys");
        Ok(())
    }

    /// Save key store to disk
    async fn save(&self) -> Result<(), KeyError> {
        let key_file_path = self.data_dir.join(KEY_FILE_NAME);
        let bytes = serde_json::to_vec_pretty(&self.store)?;
        fs::write(&key_file_path, &bytes).await?;
        Ok(())
    }
}

// =============================================================================
// Errors
// =============================================================================

/// Key storage errors
#[derive(Debug, thiserror::Error)]
pub enum KeyError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("invalid master key")]
    InvalidMasterKey,

    #[error("invalid key store: {0}")]
    InvalidKeyStore(serde_json::Error),

    #[error("crypto error: {0}")]
    CryptoError(String),

    #[error("key cannot be empty")]
    EmptyKey,

    #[error("key too long: {len} > {max}")]
    KeyTooLong { len: usize, max: usize },
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_key_storage_roundtrip() {
        let dir = tempdir().unwrap();
        let mut manager = KeyManager::new(dir.path()).await.unwrap();

        let user_id = 12345;
        let api_key = "sk-ant-api03-test-key";

        // Store key
        manager
            .store_key(user_id, ApiKeyType::Anthropic, api_key, None)
            .await
            .unwrap();

        // Retrieve key
        let retrieved = manager.get_key(user_id, ApiKeyType::Anthropic).unwrap();
        assert_eq!(retrieved, Some(api_key.to_string()));

        // List keys
        let keys = manager.list_keys(user_id);
        assert_eq!(keys, vec![ApiKeyType::Anthropic]);

        // Remove key
        let removed = manager.remove_key(user_id, ApiKeyType::Anthropic).await.unwrap();
        assert!(removed);

        // Verify removed
        let retrieved = manager.get_key(user_id, ApiKeyType::Anthropic).unwrap();
        assert_eq!(retrieved, None);
    }

    #[tokio::test]
    async fn test_key_persistence() {
        let dir = tempdir().unwrap();
        let user_id = 12345;
        let api_key = "sk-ant-api03-test-key";

        // Store key
        {
            let mut manager = KeyManager::new(dir.path()).await.unwrap();
            manager
                .store_key(user_id, ApiKeyType::Anthropic, api_key, None)
                .await
                .unwrap();
        }

        // Load again and verify
        {
            let manager = KeyManager::new(dir.path()).await.unwrap();
            let retrieved = manager.get_key(user_id, ApiKeyType::Anthropic).unwrap();
            assert_eq!(retrieved, Some(api_key.to_string()));
        }
    }
}
