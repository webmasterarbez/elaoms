# ELAOMS Codebase Refactor Plan

**Created**: 2025-12-10
**Status**: In Progress

## Overview

This document tracks the systematic refactoring and documentation improvements for the ElevenLabs OpenMemory Integration Service (ELAOMS).

### Codebase Summary

The codebase is a FastAPI application integrating ElevenLabs voice agents with OpenMemory for persistent caller profiles. Key components:

| Directory | Purpose |
|-----------|---------|
| `app/` | Main application code |
| `app/webhooks/` | Three webhook handlers: client-data, search-data, post-call |
| `app/memory/` | OpenMemory client, profile management, memory extraction |
| `app/services/` | OpenAI greeting generation, agent profile caching |
| `app/auth/` | HMAC signature verification |
| `app/models/` | Pydantic request/response models |
| `app/utils/` | Structured logging utilities |
| `tests/` | Pytest test suite |

---

## Refactoring Opportunities

### 1. HIGH PRIORITY: Extract Shared HTTP Client Utilities

**Problem**: HTTP client setup is duplicated across multiple modules:
- `app/memory/profiles.py` - 5+ locations with identical httpx setup
- `app/memory/extraction.py` - 4+ locations
- `app/services/openai_service.py` - 1 location
- `app/services/agent_cache.py` - 1 location

**Impact**: ~50 lines of duplicated boilerplate

**Solution**: Create `app/utils/http_client.py` with:
```python
async def get_openmemory_client() -> httpx.AsyncClient:
    """Get configured httpx client for OpenMemory API."""

async def get_openai_client() -> httpx.AsyncClient:
    """Get configured httpx client for OpenAI API."""

async def get_elevenlabs_client() -> httpx.AsyncClient:
    """Get configured httpx client for ElevenLabs API."""
```

**Files to modify**:
- [x] Create `app/utils/http_client.py`
- [x] Update `app/memory/profiles.py`
- [x] Update `app/memory/extraction.py`
- [x] Update `app/services/openai_service.py`
- [x] Update `app/services/agent_cache.py`

---

### 2. HIGH PRIORITY: Consolidate Duplicate Name Extraction

**Problem**: Name extraction logic is duplicated:

Location 1: `profiles.py:421-488` - `extract_name_from_transcript()`
Location 2: `profiles.py:887-960` - `_extract_name_from_memories()`

Both contain:
- Identical `not_names` set (40+ entries)
- Same regex patterns
- Similar validation logic

**Solution**: Create single source of truth:
```python
# In app/memory/extraction.py or new app/utils/name_extraction.py

NOT_NAMES: frozenset[str] = frozenset({...})  # Define once

def extract_name(text: str, source_type: Literal["transcript", "memory"]) -> Optional[str]:
    """Extract name from text using standardized patterns."""
```

**Files to modify**:
- [ ] Create extraction utility or extend `app/memory/extraction.py`
- [ ] Update `app/memory/profiles.py` to use shared function
- [ ] Add tests for edge cases

---

### 3. MEDIUM PRIORITY: Split profiles.py (1103 lines)

**Problem**: `app/memory/profiles.py` handles too many concerns:
1. Tier 1 universal profile operations (lines 40-218)
2. Tier 2 agent-specific state operations (lines 220-413)
3. Name extraction utilities (lines 416-488)
4. Legacy profile functions (lines 491-660)
5. Response building functions (lines 712-832)
6. Text processing helpers (lines 834-1103)

**Solution**: Split into focused modules:

```
app/memory/
├── profiles.py          # Keep Tier 1/2 operations (~400 lines)
├── text_processing.py   # _truncate_at_sentence, _is_conversational_filler (~200 lines)
├── legacy.py            # Backward-compatible functions (~200 lines)
└── response_builders.py # build_dynamic_variables, build_conversation_override (~150 lines)
```

**Files to modify**:
- [ ] Create `app/memory/text_processing.py`
- [ ] Create `app/memory/legacy.py`
- [ ] Create `app/memory/response_builders.py`
- [ ] Update `app/memory/profiles.py` imports
- [ ] Update `app/memory/__init__.py` exports

---

### 4. LOW PRIORITY: Add Module Docstrings

**Problem**: `__init__.py` files lack documentation:
- `app/__init__.py` - empty
- `app/models/__init__.py` - empty
- `app/webhooks/__init__.py` - empty
- `app/services/__init__.py` - empty

**Solution**: Add module-level docstrings explaining the package structure and public exports.

**Files to modify**:
- [ ] `app/__init__.py`
- [ ] `app/models/__init__.py`
- [ ] `app/webhooks/__init__.py`
- [ ] `app/services/__init__.py`
- [ ] `app/auth/__init__.py`

---

### 5. LOW PRIORITY: Improve Inline Comments

**Problem**: Some complex functions lack "why" comments:

- `post_call.py:226-383` - `_process_memories()` is complex but well-sectioned
- `profiles.py:834-884` - `_is_conversational_filler()` filter logic
- `openai_service.py:92-204` - `_build_greeting_prompt()` XML structure

**Solution**: Add targeted comments explaining non-obvious decisions.

---

## Documentation Status

### Well-Documented (No Changes Needed)
- `app/main.py` - Excellent module docstring
- `app/config.py` - Comprehensive docstrings
- `app/auth/hmac.py` - Clear function documentation
- `app/services/openai_service.py` - Good documentation
- `app/services/agent_cache.py` - Good documentation
- `app/utils/logging.py` - Well documented
- `app/models/requests.py` - Pydantic models with descriptions
- `app/models/responses.py` - Pydantic models with descriptions

### Partially Documented (Minor Improvements)
- `app/memory/profiles.py` - Has docstrings, could use more inline comments
- `app/memory/extraction.py` - Has docstrings, helper functions need context
- `app/webhooks/*.py` - Good endpoint docs, could use flow comments

---

## Implementation Order

1. **Phase 1**: HTTP Client Extraction (reduces duplication, low risk)
2. **Phase 2**: Name Extraction Consolidation (reduces duplication, medium risk)
3. **Phase 3**: Module Docstrings (documentation only, no risk)
4. **Phase 4**: profiles.py Split (larger refactor, needs careful testing)
5. **Phase 5**: Inline Comments (documentation only, no risk)

---

## Progress Tracking

| Task | Status | Completed Date |
|------|--------|----------------|
| Explore codebase | ✅ Complete | 2025-12-10 |
| Create refactor plan | ✅ Complete | 2025-12-10 |
| Extract HTTP client utilities | ✅ Complete | 2025-12-10 |
| Consolidate name extraction | ⏳ Pending | |
| Add module docstrings | ⏳ Pending | |
| Split profiles.py | ⏳ Pending | |
| Add inline comments | ⏳ Pending | |

### Completed Changes (Phase 1)

**Files created:**
- `app/utils/http_client.py` - Centralized HTTP client factories for OpenMemory, OpenAI, and ElevenLabs APIs

**Files modified:**
- `app/utils/__init__.py` - Added HTTP client exports
- `app/services/agent_cache.py` - Now uses `get_elevenlabs_client()`
- `app/services/openai_service.py` - Now uses `get_openai_client()`
- `app/memory/extraction.py` - Now uses `get_openmemory_client()`
- `app/memory/profiles.py` - Now uses `get_openmemory_client()` (6 functions updated)

**Lines of duplicate code removed:** ~80 lines of repeated httpx client setup

---

## Notes

- The codebase is already well-structured with good separation of concerns
- Existing tests provide safety net for refactoring
- Two-tier memory architecture is well-documented in `docs/TWO_TIER_MEMORY.md`
- No security issues identified during review
