"""OpenMemory client and memory operations.

This module provides the memory integration layer for the ElevenLabs OpenMemory
integration. It includes:

- Client: OpenMemory SDK client wrapper for remote mode operations
- Profiles: Caller profile management and dynamic variable building
- Extraction: Transcript processing and memory storage

All memory operations use phone numbers as the userId for multi-tenant isolation,
and store memories with decayLambda=0 for permanent retention.
"""

from app.memory.client import (
    get_openmemory_client,
    reset_client,
    close_client,
    OpenMemoryConnectionError,
)

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
    # Client
    "get_openmemory_client",
    "reset_client",
    "close_client",
    "OpenMemoryConnectionError",
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
