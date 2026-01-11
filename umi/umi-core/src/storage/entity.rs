//! Entity - Structured data for Archival Memory
//!
//! TigerStyle: Explicit types, validation, builder pattern.

use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::constants::{ENTITY_CONTENT_BYTES_MAX, ENTITY_NAME_BYTES_MAX};

// =============================================================================
// Entity Type
// =============================================================================

/// Types of entities in archival memory.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EntityType {
    /// User's self-representation
    #[serde(rename = "self")]
    Self_,
    /// Other people
    Person,
    /// Projects/initiatives
    Project,
    /// Topics/concepts
    Topic,
    /// General notes
    Note,
    /// Tasks/todos
    Task,
}

impl EntityType {
    /// Get string representation.
    #[must_use]
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Self_ => "self",
            Self::Person => "person",
            Self::Project => "project",
            Self::Topic => "topic",
            Self::Note => "note",
            Self::Task => "task",
        }
    }

    /// Parse from string.
    #[must_use]
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "self" => Some(Self::Self_),
            "person" => Some(Self::Person),
            "project" => Some(Self::Project),
            "topic" => Some(Self::Topic),
            "note" => Some(Self::Note),
            "task" => Some(Self::Task),
            _ => None,
        }
    }

    /// Get all entity types in order.
    #[must_use]
    pub fn all() -> &'static [EntityType] {
        &[
            Self::Self_,
            Self::Person,
            Self::Project,
            Self::Topic,
            Self::Note,
            Self::Task,
        ]
    }
}

impl std::fmt::Display for EntityType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// =============================================================================
// Entity
// =============================================================================

/// An entity in archival memory.
///
/// TigerStyle: Explicit fields, no Option where not needed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    /// Unique identifier (UUID v4)
    pub id: String,
    /// Type of entity
    pub entity_type: EntityType,
    /// Display name
    pub name: String,
    /// Main content
    pub content: String,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
    /// Embedding vector (for semantic search)
    pub embedding: Option<Vec<f32>>,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last update timestamp
    pub updated_at: DateTime<Utc>,
}

impl Entity {
    /// Create a new entity with required fields.
    ///
    /// # Panics
    /// Panics if name or content exceed limits.
    #[must_use]
    pub fn new(entity_type: EntityType, name: String, content: String) -> Self {
        // Preconditions
        assert!(
            name.len() <= ENTITY_NAME_BYTES_MAX,
            "name {} bytes exceeds max {}",
            name.len(),
            ENTITY_NAME_BYTES_MAX
        );
        assert!(
            content.len() <= ENTITY_CONTENT_BYTES_MAX,
            "content {} bytes exceeds max {}",
            content.len(),
            ENTITY_CONTENT_BYTES_MAX
        );

        let now = Utc::now();
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            entity_type,
            name,
            content,
            metadata: HashMap::new(),
            embedding: None,
            created_at: now,
            updated_at: now,
        }
    }

    /// Create a builder for more complex entity construction.
    #[must_use]
    pub fn builder(entity_type: EntityType, name: String, content: String) -> EntityBuilder {
        EntityBuilder::new(entity_type, name, content)
    }

    /// Check if entity has an embedding.
    #[must_use]
    pub fn has_embedding(&self) -> bool {
        self.embedding.is_some()
    }

    /// Get metadata value.
    #[must_use]
    pub fn get_metadata(&self, key: &str) -> Option<&str> {
        self.metadata.get(key).map(String::as_str)
    }

    /// Update content and timestamp.
    pub fn update_content(&mut self, content: String) {
        assert!(
            content.len() <= ENTITY_CONTENT_BYTES_MAX,
            "content {} bytes exceeds max {}",
            content.len(),
            ENTITY_CONTENT_BYTES_MAX
        );
        self.content = content;
        self.updated_at = Utc::now();
    }

    /// Set embedding.
    pub fn set_embedding(&mut self, embedding: Vec<f32>) {
        self.embedding = Some(embedding);
        self.updated_at = Utc::now();
    }
}

// =============================================================================
// Entity Builder
// =============================================================================

/// Builder for Entity with fluent API.
#[derive(Debug)]
pub struct EntityBuilder {
    entity_type: EntityType,
    name: String,
    content: String,
    id: Option<String>,
    metadata: HashMap<String, String>,
    embedding: Option<Vec<f32>>,
    created_at: Option<DateTime<Utc>>,
    updated_at: Option<DateTime<Utc>>,
}

impl EntityBuilder {
    /// Create a new builder.
    #[must_use]
    pub fn new(entity_type: EntityType, name: String, content: String) -> Self {
        Self {
            entity_type,
            name,
            content,
            id: None,
            metadata: HashMap::new(),
            embedding: None,
            created_at: None,
            updated_at: None,
        }
    }

    /// Set custom ID.
    #[must_use]
    pub fn with_id(mut self, id: String) -> Self {
        self.id = Some(id);
        self
    }

    /// Add metadata key-value pair.
    #[must_use]
    pub fn with_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// Set embedding.
    #[must_use]
    pub fn with_embedding(mut self, embedding: Vec<f32>) -> Self {
        self.embedding = Some(embedding);
        self
    }

    /// Set creation timestamp (for DST).
    #[must_use]
    pub fn with_created_at(mut self, created_at: DateTime<Utc>) -> Self {
        self.created_at = Some(created_at);
        self
    }

    /// Set update timestamp (for DST).
    #[must_use]
    pub fn with_updated_at(mut self, updated_at: DateTime<Utc>) -> Self {
        self.updated_at = Some(updated_at);
        self
    }

    /// Build the entity.
    ///
    /// # Panics
    /// Panics if name or content exceed limits.
    #[must_use]
    pub fn build(self) -> Entity {
        // Preconditions
        assert!(
            self.name.len() <= ENTITY_NAME_BYTES_MAX,
            "name {} bytes exceeds max {}",
            self.name.len(),
            ENTITY_NAME_BYTES_MAX
        );
        assert!(
            self.content.len() <= ENTITY_CONTENT_BYTES_MAX,
            "content {} bytes exceeds max {}",
            self.content.len(),
            ENTITY_CONTENT_BYTES_MAX
        );

        let now = Utc::now();
        Entity {
            id: self.id.unwrap_or_else(|| uuid::Uuid::new_v4().to_string()),
            entity_type: self.entity_type,
            name: self.name,
            content: self.content,
            metadata: self.metadata,
            embedding: self.embedding,
            created_at: self.created_at.unwrap_or(now),
            updated_at: self.updated_at.unwrap_or(now),
        }
    }
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_entity_type_as_str() {
        assert_eq!(EntityType::Self_.as_str(), "self");
        assert_eq!(EntityType::Person.as_str(), "person");
        assert_eq!(EntityType::Project.as_str(), "project");
        assert_eq!(EntityType::Topic.as_str(), "topic");
        assert_eq!(EntityType::Note.as_str(), "note");
        assert_eq!(EntityType::Task.as_str(), "task");
    }

    #[test]
    fn test_entity_type_from_str() {
        assert_eq!(EntityType::from_str("self"), Some(EntityType::Self_));
        assert_eq!(EntityType::from_str("PERSON"), Some(EntityType::Person));
        assert_eq!(EntityType::from_str("Project"), Some(EntityType::Project));
        assert_eq!(EntityType::from_str("unknown"), None);
    }

    #[test]
    fn test_entity_new() {
        let entity = Entity::new(
            EntityType::Person,
            "Alice".to_string(),
            "My friend Alice".to_string(),
        );

        assert!(!entity.id.is_empty());
        assert_eq!(entity.entity_type, EntityType::Person);
        assert_eq!(entity.name, "Alice");
        assert_eq!(entity.content, "My friend Alice");
        assert!(entity.metadata.is_empty());
        assert!(entity.embedding.is_none());
    }

    #[test]
    fn test_entity_builder() {
        let entity = Entity::builder(
            EntityType::Project,
            "Umi".to_string(),
            "Memory system".to_string(),
        )
        .with_id("custom-id".to_string())
        .with_metadata("status".to_string(), "active".to_string())
        .with_embedding(vec![0.1, 0.2, 0.3])
        .build();

        assert_eq!(entity.id, "custom-id");
        assert_eq!(entity.entity_type, EntityType::Project);
        assert_eq!(entity.get_metadata("status"), Some("active"));
        assert!(entity.has_embedding());
    }

    #[test]
    fn test_entity_update_content() {
        let mut entity = Entity::new(
            EntityType::Note,
            "Test".to_string(),
            "Original content".to_string(),
        );
        let original_updated = entity.updated_at;

        // Small delay to ensure timestamp changes
        std::thread::sleep(std::time::Duration::from_millis(10));

        entity.update_content("New content".to_string());

        assert_eq!(entity.content, "New content");
        assert!(entity.updated_at >= original_updated);
    }

    #[test]
    #[should_panic(expected = "name")]
    fn test_entity_name_too_long() {
        let long_name = "x".repeat(ENTITY_NAME_BYTES_MAX + 1);
        let _ = Entity::new(EntityType::Note, long_name, "content".to_string());
    }

    #[test]
    #[should_panic(expected = "content")]
    fn test_entity_content_too_long() {
        let long_content = "x".repeat(ENTITY_CONTENT_BYTES_MAX + 1);
        let _ = Entity::new(EntityType::Note, "name".to_string(), long_content);
    }
}
