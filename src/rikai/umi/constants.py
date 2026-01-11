"""
Umi Constants - TigerStyle

All limits are explicit, named with units, big-endian naming convention.
Category comes first, specifics last: ENTITY_CONTENT_BYTES_MAX not MAX_ENTITY_CONTENT.
"""

# =============================================================================
# Core Memory Limits
# =============================================================================

CORE_MEMORY_SIZE_BYTES_MAX: int = 32 * 1024  # 32KB - always in LLM context
CORE_MEMORY_SIZE_BYTES_MIN: int = 4 * 1024   # 4KB minimum
CORE_MEMORY_BLOCK_SIZE_BYTES_MAX: int = 8 * 1024  # 8KB per block

# =============================================================================
# Working Memory Limits
# =============================================================================

WORKING_MEMORY_SIZE_BYTES_MAX: int = 1024 * 1024  # 1MB total
WORKING_MEMORY_ENTRY_SIZE_BYTES_MAX: int = 64 * 1024  # 64KB per entry
WORKING_MEMORY_TTL_SECS_DEFAULT: int = 3600  # 1 hour default TTL
WORKING_MEMORY_ENTRIES_COUNT_MAX: int = 10_000  # Max entries

# =============================================================================
# Entity Limits
# =============================================================================

ENTITY_CONTENT_BYTES_MAX: int = 1_000_000  # 1MB max content
ENTITY_LABEL_CHARS_MAX: int = 256  # Max label length
ENTITY_TAGS_COUNT_MAX: int = 50  # Max tags per entity

# =============================================================================
# Search Limits
# =============================================================================

SEARCH_RESULTS_COUNT_MAX: int = 100  # Max results per query
SEARCH_RESULTS_COUNT_DEFAULT: int = 10  # Default results
SEARCH_QUERY_CHARS_MAX: int = 10_000  # Max query length

# =============================================================================
# Embedding Limits
# =============================================================================

EMBEDDING_DIMENSIONS_COUNT: int = 1536  # OpenAI text-embedding-3-small
EMBEDDING_BATCH_SIZE_MAX: int = 100  # Max batch for embedding

# =============================================================================
# Storage Limits
# =============================================================================

STORAGE_RETRY_COUNT_MAX: int = 3  # Max retries on failure
STORAGE_TIMEOUT_SECS_DEFAULT: int = 30  # Default timeout
STORAGE_BATCH_SIZE_MAX: int = 1000  # Max batch operations

# =============================================================================
# DST (Deterministic Simulation Testing) Limits
# =============================================================================

DST_SIMULATION_STEPS_MAX: int = 1_000_000  # Max simulation steps
DST_FAULT_PROBABILITY_MAX: float = 1.0  # Max fault probability
DST_FAULT_PROBABILITY_MIN: float = 0.0  # Min fault probability

# =============================================================================
# Time Constants
# =============================================================================

TIME_EPOCH_MS: int = 0  # Simulation start time
TIME_ADVANCE_MS_MAX: int = 86_400_000  # Max advance = 1 day
