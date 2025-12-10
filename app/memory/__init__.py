"""OpenMemory integration for caller profile and memory management.

This module provides the memory integration layer with two-tier architecture:

Tier 1 (Universal Profile):
- Cross-agent user profiles shared across all agents
- Basic user info: name, first_seen, total_interactions

Tier 2 (Agent-Specific State):
- Per-agent conversation states
- Pre-generated greetings, topics, sentiment, summaries

Key Components:
- profiles.py: Tier 1/2 profile operations and dynamic variable building
- extraction.py: Transcript processing and memory storage

All operations use shared HTTP clients from app.utils.http_client and phone
numbers as userId for multi-tenant isolation.
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
