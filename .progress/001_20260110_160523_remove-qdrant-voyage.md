# Plan: Remove Qdrant and Voyage, Switch to OpenAI Embeddings

**Status**: COMPLETED
**Created**: 2026-01-10 16:05
**Completed**: 2026-01-10 15:39 (retrospective documentation)

## Goal

Remove Qdrant vector database and Voyage AI embeddings, switch to OpenAI embeddings with pgvector storage.

## Context

- User asked: "remove qdrant, switch to openai embeddings, remove voyage"
- Qdrant was a legacy vector backend (already not the default)
- Voyage AI was the embedding provider (requires paid API key)
- OpenAI embeddings are more commonly available (user likely has key)

## Changes Made

### Files Deleted
- `src/rikai/umi/storage/vectors.py` - Qdrant adapter (422 lines removed)

### Files Modified

| File | Changes |
|------|---------|
| `src/rikai/umi/storage/base.py` | Added `OpenAIEmbeddings` and `OllamaEmbeddings` classes |
| `src/rikai/core/config.py` | `voyage_api_key` → `openai_api_key`, `voyage_model` → `openai_embedding_model` |
| `src/rikai/core/models.py` | Updated `UmiConfig` with OpenAI fields, removed Qdrant fields |
| `src/rikai/umi/client.py` | Updated imports, removed Qdrant backend selection |
| `src/rikai/umi/storage/pgvector.py` | Updated docs and default dimension (1024 → 1536) |
| `src/rikai/cli/main.py` | Removed `_check_qdrant()` and Qdrant status checks |
| `pyproject.toml` | Removed `voyageai` dependency and `qdrant` optional |
| `.env` | Changed to `RIKAI_OPENAI_API_KEY` |
| `tests/conftest.py` | Updated mock embeddings to 1536 dims |
| `tests/test_core_models.py` | Updated config assertions |
| `tests/test_umi_client.py` | Updated to use `openai_api_key` |
| `tests/test_umi_storage_vectors.py` | Updated dimension assertion |

### Configuration Changes

| Old | New |
|-----|-----|
| `RIKAI_VOYAGE_API_KEY` | `RIKAI_OPENAI_API_KEY` |
| `RIKAI_VOYAGE_MODEL` | `RIKAI_OPENAI_EMBEDDING_MODEL` |
| `RIKAI_VECTOR_BACKEND` | Removed (pgvector only) |
| `RIKAI_QDRANT_URL` | Removed |
| Embedding dim: 1024 | Embedding dim: 1536 |

## Decisions Made

1. **Keep OllamaEmbeddings** - Useful for local/offline embedding generation
2. **Default to text-embedding-3-small** - Good balance of cost/quality
3. **1536 dimensions** - Standard for OpenAI's small model
4. **Single vector backend** - pgvector only, simpler architecture

## Verification

- [x] Tests collect successfully (194 tests)
- [x] No voyage/qdrant references in core code
- [x] Linting passes on modified base.py
- [x] Changes committed and pushed

## Notes

This was documented retrospectively - should have created plan file before starting per CLAUDE.md workflow.
