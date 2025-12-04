"""OpenMemory memory operations via REST API.

This module provides the memory integration layer for the ElevenLabs OpenMemory
integration. It includes:

- Profiles: Caller profile management and dynamic variable building
- Extraction: Transcript processing and memory storage

All memory operations use direct HTTP calls via httpx.AsyncClient to avoid
async event loop conflicts. Phone numbers are used as userId for multi-tenant
isolation, and memories are stored with decayLambda=0 for permanent retention.
"""

from app.memory.profiles import (
    get_user_profile,
    get_user_summary,
    build_dynamic_variables,
    build_conversation_override,
    build_profile_data,
)

from app.memory.extraction import (
    extract_user_info,
    extract_user_messages,
    create_profile_memories,
    store_conversation_memories,
    search_memories,
)

__all__ = [
    # Profiles
    "get_user_profile",
    "get_user_summary",
    "build_dynamic_variables",
    "build_conversation_override",
    "build_profile_data",
    # Extraction
    "extract_user_info",
    "extract_user_messages",
    "create_profile_memories",
    "store_conversation_memories",
    "search_memories",
]
