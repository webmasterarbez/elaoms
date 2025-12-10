"""Caller profile management for OpenMemory integration.

This module provides functions for:
- Two-tier memory architecture:
  - Tier 1: Universal user profiles (cross-agent)
  - Tier 2: Agent-specific conversation states (per-agent)
- Retrieving user profiles from OpenMemory via REST API
- Getting user summaries via the OpenMemory API
- Building dynamic variables for ElevenLabs response

Storage Keys:
- Tier 1: user:{phone_number}:profile (universal profile)
- Tier 2: user:{phone_number}:agent:{agent_id}:next_greeting (agent-specific state)

All operations use the phone number as the userId for multi-tenant isolation.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import settings
from app.models.responses import (
    DynamicVariables,
    ConversationConfigOverride,
    AgentConfig,
    ProfileData,
)

logger = logging.getLogger(__name__)

# Constants for memory storage
PERMANENT_DECAY = 0  # decayLambda=0 for permanent retention
HIGH_SALIENCE = 0.9  # High importance for profile facts and greetings


# =============================================================================
# TIER 1: Universal User Profile Functions (Cross-Agent)
# =============================================================================


async def get_universal_user_profile(phone_number: str) -> Optional[dict[str, Any]]:
    """Query Tier 1: Universal user profile shared across all agents.

    Retrieves the universal profile that is shared across all agents,
    containing basic user information like name and total interactions.

    Storage key pattern: user:{phone_number}:profile

    Args:
        phone_number: The user's phone number in E.164 format.

    Returns:
        Dictionary containing:
            - name: str | None
            - phone_number: str
            - first_seen: str (ISO timestamp)
            - total_interactions: int
        Returns None if user has never called any agent.
    """
    from urllib.parse import quote

    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Query for universal profile memories
        async with httpx.AsyncClient(timeout=10.0) as client:
            query_payload = {
                "query": "universal profile user name",
                "k": 5,
                "filters": {
                    "user_id": phone_number,
                    "tags": ["universal_profile"]
                }
            }
            response = await client.post(
                f"{openmemory_url}/memory/query",
                json=query_payload,
                headers=headers
            )

            if response.status_code != 200:
                logger.warning(f"OpenMemory query failed: {response.status_code}")
                return None

            results = response.json()
            memories = results.get("matches", [])

            if not memories:
                logger.info(f"No universal profile found for {phone_number}")
                return None

            # Parse universal profile from memories
            name = None
            first_seen = None
            total_interactions = 0

            for memory in memories:
                metadata = memory.get("metadata", {})
                if isinstance(metadata, dict):
                    if metadata.get("field") == "name" and metadata.get("value"):
                        name = metadata.get("value")
                    if metadata.get("field") == "first_seen":
                        first_seen = metadata.get("value")
                    if metadata.get("field") == "total_interactions":
                        try:
                            total_interactions = int(metadata.get("value", 0))
                        except (ValueError, TypeError):
                            total_interactions = 0

            return {
                "name": name,
                "phone_number": phone_number,
                "first_seen": first_seen or datetime.utcnow().isoformat(),
                "total_interactions": total_interactions
            }

    except httpx.RequestError as e:
        logger.error(f"HTTP error querying universal profile for {phone_number}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving universal profile for {phone_number}: {e}")
        return None


async def store_universal_user_profile(
    phone_number: str,
    name: Optional[str] = None,
    increment_interactions: bool = True
) -> bool:
    """Create or update Tier 1 universal profile.

    Creates a new universal profile if one doesn't exist, or updates
    the existing profile with new information.

    Args:
        phone_number: The user's phone number in E.164 format.
        name: User's name (if known). Only updates if currently None.
        increment_interactions: Whether to increment total_interactions.

    Returns:
        True if successful, False otherwise.
    """
    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Get existing profile
        existing = await get_universal_user_profile(phone_number)

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Determine values to store
            current_name = existing.get("name") if existing else None
            current_interactions = existing.get("total_interactions", 0) if existing else 0
            first_seen = existing.get("first_seen") if existing else datetime.utcnow().isoformat()

            # Update name only if not already set
            new_name = name if (name and not current_name) else current_name
            new_interactions = current_interactions + 1 if increment_interactions else current_interactions

            # Store profile fields as individual memories
            fields = [
                ("name", new_name),
                ("first_seen", first_seen),
                ("total_interactions", str(new_interactions)),
            ]

            for field_name, field_value in fields:
                if field_value is None:
                    continue

                payload = {
                    "content": f"Universal profile: {field_name} = {field_value}",
                    "tags": ["universal_profile", field_name],
                    "metadata": {
                        "field": field_name,
                        "value": str(field_value),
                        "profile_type": "universal"
                    },
                    "user_id": phone_number,
                    "salience": HIGH_SALIENCE,
                    "decay_lambda": PERMANENT_DECAY
                }

                response = await client.post(
                    f"{openmemory_url}/memory/add",
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    logger.warning(
                        f"Failed to store universal profile field {field_name}: "
                        f"{response.status_code}"
                    )

            logger.info(f"Stored universal profile for {phone_number}")
            return True

    except httpx.RequestError as e:
        logger.error(f"HTTP error storing universal profile: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing universal profile: {e}")
        return False


# =============================================================================
# TIER 2: Agent-Specific Conversation State Functions (Per-Agent)
# =============================================================================


async def get_agent_conversation_state(
    phone_number: str,
    agent_id: str
) -> Optional[dict[str, Any]]:
    """Query Tier 2: Agent-specific conversation state.

    Retrieves the conversation state specific to a particular agent,
    including the pre-generated next greeting.

    Storage key pattern: user:{phone_number}:agent:{agent_id}:next_greeting

    Args:
        phone_number: The user's phone number in E.164 format.
        agent_id: The unique identifier of the ElevenLabs agent.

    Returns:
        Dictionary containing:
            - next_greeting: str | None
            - key_topics: List[str]
            - sentiment: str
            - conversation_summary: str
            - last_call_date: str (ISO timestamp)
            - conversation_count: int
        Returns None if user has never called this specific agent.
    """
    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Query for agent-specific state
        async with httpx.AsyncClient(timeout=10.0) as client:
            query_payload = {
                "query": f"agent greeting {agent_id}",
                "k": 3,
                "filters": {
                    "user_id": phone_number,
                    "tags": ["agent_state", agent_id]
                }
            }
            response = await client.post(
                f"{openmemory_url}/memory/query",
                json=query_payload,
                headers=headers
            )

            if response.status_code != 200:
                logger.warning(f"OpenMemory query failed: {response.status_code}")
                return None

            results = response.json()
            memories = results.get("matches", [])

            if not memories:
                logger.info(f"No agent state found for {phone_number} with agent {agent_id}")
                return None

            # Parse agent-specific state from memories
            state = {
                "next_greeting": None,
                "key_topics": [],
                "sentiment": "neutral",
                "conversation_summary": "",
                "last_call_date": None,
                "conversation_count": 0
            }

            for memory in memories:
                metadata = memory.get("metadata", {})
                if isinstance(metadata, dict):
                    if metadata.get("next_greeting"):
                        state["next_greeting"] = metadata.get("next_greeting")
                    if metadata.get("key_topics"):
                        topics = metadata.get("key_topics")
                        if isinstance(topics, list):
                            state["key_topics"] = topics
                        elif isinstance(topics, str):
                            state["key_topics"] = [t.strip() for t in topics.split(",")]
                    if metadata.get("sentiment"):
                        state["sentiment"] = metadata.get("sentiment")
                    if metadata.get("conversation_summary"):
                        state["conversation_summary"] = metadata.get("conversation_summary")
                    if metadata.get("last_call_date"):
                        state["last_call_date"] = metadata.get("last_call_date")
                    if metadata.get("conversation_count"):
                        try:
                            state["conversation_count"] = int(metadata.get("conversation_count", 0))
                        except (ValueError, TypeError):
                            pass

            return state

    except httpx.RequestError as e:
        logger.error(f"HTTP error querying agent state for {phone_number}/{agent_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving agent state for {phone_number}/{agent_id}: {e}")
        return None


async def store_agent_conversation_state(
    phone_number: str,
    agent_id: str,
    greeting_data: dict[str, Any]
) -> bool:
    """Store Tier 2 agent-specific conversation state.

    Stores the pre-generated greeting and conversation context for
    the next call from this user to this specific agent.

    Args:
        phone_number: The user's phone number in E.164 format.
        agent_id: The unique identifier of the ElevenLabs agent.
        greeting_data: Output from OpenAI generate_next_greeting() containing:
            - next_greeting: str | None
            - key_topics: List[str]
            - sentiment: str
            - conversation_summary: str

    Returns:
        True if successful, False otherwise.
    """
    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Get existing state to increment conversation count
        existing = await get_agent_conversation_state(phone_number, agent_id)
        conversation_count = (existing.get("conversation_count", 0) if existing else 0) + 1

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build metadata
            metadata = {
                "agent_id": agent_id,
                "next_greeting": greeting_data.get("next_greeting"),
                "key_topics": greeting_data.get("key_topics", []),
                "sentiment": greeting_data.get("sentiment", "neutral"),
                "conversation_summary": greeting_data.get("conversation_summary", ""),
                "last_call_date": datetime.utcnow().isoformat(),
                "conversation_count": conversation_count,
                "profile_type": "agent_specific"
            }

            # Build content for embedding
            topics_str = ", ".join(greeting_data.get("key_topics", []))
            content = (
                f"Agent {agent_id} conversation state: "
                f"Next greeting prepared. Topics: {topics_str}. "
                f"Sentiment: {greeting_data.get('sentiment', 'neutral')}. "
                f"Summary: {greeting_data.get('conversation_summary', '')}"
            )

            payload = {
                "content": content,
                "tags": ["agent_state", agent_id, "next_greeting"],
                "metadata": metadata,
                "user_id": phone_number,
                "salience": HIGH_SALIENCE,
                "decay_lambda": PERMANENT_DECAY
            }

            response = await client.post(
                f"{openmemory_url}/memory/add",
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                logger.warning(
                    f"Failed to store agent state: {response.status_code} - {response.text}"
                )
                return False

            logger.info(f"Stored agent state for {phone_number} with agent {agent_id}")
            return True

    except httpx.RequestError as e:
        logger.error(f"HTTP error storing agent state: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing agent state: {e}")
        return False


# =============================================================================
# Name Extraction Utilities
# =============================================================================


def extract_name_from_transcript(transcript: str) -> Optional[str]:
    """Extract user's name from transcript using regex patterns.

    Searches for common name introduction patterns in the transcript
    and returns the first valid name found.

    Patterns (in priority order):
    1. "my name is {Name}"
    2. "I'm {Name}" / "I am {Name}"
    3. "call me {Name}"
    4. "this is {Name}"

    Args:
        transcript: The conversation transcript as a string.

    Returns:
        Capitalized name or None if no name found.
    """
    # Common words that are NOT names
    not_names = {
        "a", "an", "the", "so", "just", "really", "very", "not", "also",
        "doing", "going", "trying", "looking", "working", "thinking",
        "sure", "glad", "happy", "sorry", "afraid", "excited", "worried",
        "here", "there", "back", "home", "now", "still", "always",
        "me", "him", "her", "them", "us", "it", "that", "this",
        "for", "to", "by", "on", "in", "at", "up", "out",
        "and", "but", "or", "absolutely", "astonished", "horrified",
        "lucky", "founder", "recruiter", "counselor", "calling",
    }

    transcript_lower = transcript.lower()

    # Pattern 1: "my name is {Name}" - most reliable
    match = re.search(r"my name is\s+([a-z]+)", transcript_lower)
    if match:
        name = match.group(1).capitalize()
        if name.lower() not in not_names and len(name) > 1:
            return name

    # Pattern 2: "name is {Name}" at start or after punctuation
    match = re.search(r"(?:^|[.!?]\s*)name is\s+([a-z]+)", transcript_lower)
    if match:
        name = match.group(1).capitalize()
        if name.lower() not in not_names and len(name) > 1:
            return name

    # Pattern 3: "I'm {Name}" or "I am {Name}" - only when followed by punctuation
    match = re.search(r"(?:i'm|i am)\s+([a-z]+)[.,!?]", transcript_lower)
    if match:
        name = match.group(1).capitalize()
        if name.lower() not in not_names and len(name) > 1:
            return name

    # Pattern 4: "call me {Name}" or "they call me {Name}"
    match = re.search(r"call me\s+([a-z]+)", transcript_lower)
    if match:
        name = match.group(1).capitalize()
        if name.lower() not in not_names and len(name) > 1:
            return name

    # Pattern 5: "this is {Name}" - when introducing themselves
    match = re.search(r"this is\s+([a-z]+)[.,!?]", transcript_lower)
    if match:
        name = match.group(1).capitalize()
        if name.lower() not in not_names and len(name) > 1:
            return name

    return None


# =============================================================================
# Legacy Functions (kept for backward compatibility)
# =============================================================================


def _parse_user_summary(summary_response: dict[str, Any]) -> dict[str, Any]:
    """Parse OpenMemory /users/:id/summary response.

    Input format:
    {
        "user_id": "+16125082017",
        "summary": "1 memories, 1 patterns | low | avg_sal=0.40 | top: semantic(1, sal=0.36): \"Participant Details: founder of Arbez...\"",
        "reflection_count": 0,
        "updated_at": 1764853457629
    }

    Returns:
        Parsed summary data with memory_count, activity_level, top_content, has_memories.
    """
    import re

    result = {
        "memory_count": 0,
        "activity_level": "none",
        "top_content": None,
        "has_memories": False,
    }

    summary_str = summary_response.get("summary", "")
    if not summary_str:
        return result

    # Parse memory count: "X memories" at the start
    memory_match = re.search(r"^(\d+)\s+memories?", summary_str)
    if memory_match:
        result["memory_count"] = int(memory_match.group(1))
        result["has_memories"] = result["memory_count"] > 0

    # Parse activity level: "| low |" or "| medium |" or "| high |"
    activity_match = re.search(r"\|\s*(low|medium|high)\s*\|", summary_str)
    if activity_match:
        result["activity_level"] = activity_match.group(1)

    # Parse top content: everything after the colon in quotes
    # Format: top: semantic(1, sal=0.36): "Participant Details: founder of Arbez..."
    content_match = re.search(r'top:.*?:\s*"([^"]+)"', summary_str)
    if content_match:
        top_content = content_match.group(1).strip()
        # Clean up the content - remove "Participant Details:" prefix if present
        if top_content.lower().startswith("participant details:"):
            top_content = top_content[20:].strip()
        if top_content and not _is_conversational_filler(top_content):
            result["top_content"] = top_content

    return result


async def get_user_profile(phone_number: str) -> Optional[dict[str, Any]]:
    """Query OpenMemory for user profile data via REST API.

    Uses the /users/:id/summary endpoint for efficient profile retrieval,
    then queries memories for name extraction if needed.

    Args:
        phone_number: The user's phone number in E.164 format (e.g., +16129782029).

    Returns:
        A dictionary containing user profile data, or None if no profile exists.
        Structure:
        {
            "name": str | None,
            "summary": str | None,
            "top_content": str | None,
            "memories": list[dict],
            "memory_count": int,
            "has_memories": bool
        }
    """
    from urllib.parse import quote

    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # First, get user summary via /users/:id/summary endpoint
        encoded_user_id = quote(phone_number, safe="")
        summary_url = f"{openmemory_url}/users/{encoded_user_id}/summary"

        async with httpx.AsyncClient(timeout=10.0) as client:
            summary_response = await client.get(summary_url, headers=headers)

            if summary_response.status_code == 404:
                logger.info(f"No profile found for user {phone_number}")
                return None

            if summary_response.status_code != 200:
                logger.warning(f"OpenMemory summary returned status {summary_response.status_code}: {summary_response.text}")
                return None

            summary_data = summary_response.json()

        # Parse the summary response
        parsed = _parse_user_summary(summary_data)

        # Check if summary is still initializing (OpenMemory hasn't processed yet)
        summary_str = summary_data.get("summary", "")
        is_initializing = "initializing" in summary_str.lower()

        if not parsed["has_memories"] and not is_initializing:
            logger.info(f"No memories found for user {phone_number}")
            return None

        # Query memories to extract name (need actual memory content for name extraction)
        memories = []
        name = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            query_payload = {
                "query": "user name first_name",
                "k": 10,
                "filters": {"user_id": phone_number}
            }
            mem_response = await client.post(
                f"{openmemory_url}/memory/query",
                json=query_payload,
                headers=headers
            )

            if mem_response.status_code == 200:
                results = mem_response.json()
                memories = results.get("matches", [])
                name = _extract_name_from_memories(memories)

        # If summary was initializing but we found memories, update the flags
        actual_has_memories = len(memories) > 0
        if is_initializing and actual_has_memories:
            logger.info(f"Summary initializing but found {len(memories)} memories for {phone_number}")

        # If no memories found at all, return None
        if not actual_has_memories and not parsed["has_memories"]:
            logger.info(f"No memories found for user {phone_number}")
            return None

        # Build summary from memories if top_content not available
        top_content = parsed.get("top_content")
        if not top_content and memories:
            top_content = _build_summary_from_memories(memories)

        return {
            "name": name,
            "summary": top_content,
            "top_content": top_content,
            "memories": memories,
            "memory_count": len(memories) if is_initializing else parsed["memory_count"],
            "has_memories": actual_has_memories or parsed["has_memories"],
            "activity_level": parsed.get("activity_level"),
            "phone_number": phone_number
        }

    except httpx.RequestError as e:
        logger.error(f"HTTP error querying OpenMemory for {phone_number}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving user profile for {phone_number}: {e}")
        return None


async def get_user_summary(phone_number: str) -> Optional[dict[str, Any]]:
    """Retrieve user summary from OpenMemory API.

    Calls the /users/{userId}/summary endpoint to get a comprehensive
    user summary generated by OpenMemory.

    Args:
        phone_number: The user's phone number in E.164 format.

    Returns:
        A dictionary containing the user summary, or None if unavailable.
        Structure:
        {
            "userId": str,
            "name": str | None,
            "summary": str | None,
            "memoryCount": int
        }
    """
    try:
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # URL encode the phone number for the path
        from urllib.parse import quote
        encoded_user_id = quote(phone_number, safe="")
        url = f"{openmemory_url}/users/{encoded_user_id}/summary"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info(f"No summary found for user {phone_number}")
                return None

            response.raise_for_status()
            return response.json()

    except httpx.RequestError as e:
        logger.error(f"Error fetching user summary for {phone_number}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching user summary: {e}")
        return None


def build_dynamic_variables(profile: Optional[dict[str, Any]]) -> DynamicVariables:
    """Format profile data for ElevenLabs response.

    Converts OpenMemory profile data into the DynamicVariables format
    expected by ElevenLabs for conversation personalization.

    Args:
        profile: User profile data from get_user_profile() or None for new callers.

    Returns:
        DynamicVariables object with user_name, user_profile_summary, last_call_summary.
        Returns empty/None values for new callers.
    """
    if profile is None:
        return DynamicVariables(
            user_name=None,
            user_profile_summary=None,
            last_call_summary=None
        )

    return DynamicVariables(
        user_name=profile.get("name"),
        user_profile_summary=profile.get("summary"),
        last_call_summary=_get_last_call_summary(profile.get("memories", []))
    )


def build_conversation_override(
    profile: Optional[dict[str, Any]]
) -> Optional[ConversationConfigOverride]:
    """Generate personalized firstMessage for ElevenLabs.

    Creates a conversation configuration override with a personalized
    greeting for returning callers. Uses top_content from OpenMemory summary
    for personalization and asks for name when not available.

    Decision logic:
    - First-time caller (no profile): Return None (use ElevenLabs default)
    - Has name + has content: Personalized greeting with name and content
    - Has name + no content: Simple greeting with name
    - No name + has content: Reference content + ask for name
    - No name + no content: Generic returning caller greeting + ask for name

    Args:
        profile: User profile data from get_user_profile() or None for new callers.

    Returns:
        ConversationConfigOverride with personalized firstMessage for returning callers,
        or None for new callers (to use ElevenLabs defaults).
    """
    if profile is None:
        # New caller - return None to use ElevenLabs defaults
        return None

    name = profile.get("name")
    top_content = profile.get("top_content")

    # Validate content is meaningful before using it
    has_content = (
        top_content
        and len(top_content) > 10
        and not _is_conversational_filler(top_content)
    )

    # Clean up content for natural speech if available
    if has_content:
        clean_content = _truncate_at_sentence(top_content, max_length=100) or top_content[:100]
    else:
        clean_content = None

    # Build a personalized greeting based on available context
    if name and has_content:
        # Case 1: Has name + has content - full personalization
        first_message = (
            f"Hello {name}, it's Margaret. Welcome back! "
            f"Last time you shared about {clean_content}. "
            "I'd love to continue that story - what feels right to explore today?"
        )
    elif name:
        # Case 2: Has name + no content - simple greeting with name
        first_message = (
            f"Hello {name}, it's Margaret again. So nice to have you back. "
            "What's on your mind today?"
        )
    elif has_content:
        # Case 3: No name + has content - reference content + ask for name
        first_message = (
            f"Hello, it's Margaret. Welcome back! "
            f"Last time you shared about {clean_content} - I'd love to hear more. "
            "By the way, I don't think I caught your name last time?"
        )
    else:
        # Case 4: No name + no content - generic returning caller + ask for name
        first_message = (
            "Hello, it's Margaret. Welcome back - it's lovely to hear from you again. "
            "Before we continue, I don't think I caught your name last time?"
        )

    return ConversationConfigOverride(
        agent=AgentConfig(first_message=first_message)
    )


def build_profile_data(profile: Optional[dict[str, Any]]) -> Optional[ProfileData]:
    """Build ProfileData response model from profile dictionary.

    Args:
        profile: User profile data from get_user_profile() or None.

    Returns:
        ProfileData object or None for new callers.
    """
    if profile is None:
        return None

    return ProfileData(
        name=profile.get("name"),
        summary=profile.get("summary"),
        phone_number=profile.get("phone_number")
    )


def _is_conversational_filler(content: str) -> bool:
    """Check if content is conversational filler that shouldn't be in summaries.

    Filters out raw transcript content, filler words, and meta-commentary
    that would make greetings sound awkward or incoherent.

    Args:
        content: The memory content to check.

    Returns:
        True if the content is conversational filler, False if it's meaningful.
    """
    if not content or len(content.strip()) < 10:
        return True

    content_lower = content.lower().strip()

    # Filler patterns that indicate raw transcript content
    filler_patterns = [
        # Conversational fillers
        "you know", "um", "uh", "okay", "ok", "great", "yeah", "yep",
        "right", "sure", "well", "so", "like", "actually",
        # Meta-commentary and session notes
        "session quality", "surface-level", "moderate", "rich",
        "chapters discussed", "stories shared", "emotional moments",
        "session date", "participant details",
        # Agent speech patterns (shouldn't be in user memories)
        "can you tell me", "tell me about", "what do you",
        "how did you", "that's wonderful", "thank you for sharing",
        # Short affirmations
        "yes", "no", "maybe", "i see", "i understand",
        # Name-only content (not useful for personalized greetings)
        "user name is", "user's name is", "name is",
    ]

    # Check if content starts with or is dominated by filler
    for pattern in filler_patterns:
        if content_lower.startswith(pattern) or content_lower == pattern:
            return True

    # Check if content is mostly filler (appears multiple times or is very short)
    filler_count = sum(1 for p in filler_patterns if p in content_lower)
    if filler_count >= 2 and len(content) < 50:
        return True

    # Filter out content that looks like questions (likely agent speech)
    question_starters = ["can you", "could you", "would you", "do you", "what", "how", "why", "where", "when"]
    if any(content_lower.startswith(q) for q in question_starters) and "?" in content:
        return True

    return False


def _extract_name_from_memories(memories: list[dict[str, Any]]) -> Optional[str]:
    """Extract user name from memories.

    Searches through memories for content that indicates the user's name.
    Uses strict patterns to avoid false positives from common phrases.

    Args:
        memories: List of memory objects from OpenMemory.

    Returns:
        The user's name if found, or None.
    """
    # Common words that are NOT names - filter these out
    not_names = {
        # Common verbs/adjectives after "I'm" / "I am"
        "a", "an", "the", "so", "just", "really", "very", "not", "also",
        "doing", "going", "trying", "looking", "working", "thinking",
        "sure", "glad", "happy", "sorry", "afraid", "excited", "worried",
        "here", "there", "back", "home", "now", "still", "always",
        # Common after "called"
        "me", "him", "her", "them", "us", "it", "that", "this",
        "for", "to", "by", "on", "in", "at", "up", "out",
        # Other common words
        "and", "but", "or", "the", "absolutely", "astonished", "horrified",
        "lucky", "founder", "recruiter", "counselor",
    }

    # More specific patterns that actually indicate a name introduction
    # Only match phrases that are explicitly introducing a name
    import re

    for memory in memories:
        content = memory.get("content", "")
        content_lower = content.lower()

        # Pattern 1: "my name is [Name]" - most reliable
        match = re.search(r"my name is\s+([a-z]+)", content_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in not_names and len(name) > 1:
                return name

        # Pattern 2: "name is [Name]" at start or after punctuation
        match = re.search(r"(?:^|[.!?]\s*)name is\s+([a-z]+)", content_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in not_names and len(name) > 1:
                return name

        # Pattern 3: "I'm [Name]" or "I am [Name]" - only when followed by punctuation
        # This filters out "I'm doing", "I'm just", etc.
        match = re.search(r"(?:i'm|i am)\s+([a-z]+)[.,!?]", content_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in not_names and len(name) > 1:
                return name

        # Pattern 4: "call me [Name]" or "they call me [Name]"
        match = re.search(r"call me\s+([a-z]+)", content_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in not_names and len(name) > 1:
                return name

    # Check for explicit name in metadata
    for memory in memories:
        metadata = memory.get("metadata", {})
        if isinstance(metadata, dict):
            if "name" in metadata:
                return metadata["name"]
            if "first_name" in metadata:
                return metadata["first_name"]

    return None


def _build_summary_from_memories(memories: list[dict[str, Any]]) -> Optional[str]:
    """Build a summary from user memories.

    Creates a concise summary based on stored memories, filtering for
    semantic (profile facts) memories with high salience. Excludes
    raw conversational content that would sound awkward in greetings.

    Args:
        memories: List of memory objects from OpenMemory.

    Returns:
        A summary string or None if no meaningful summary can be built.
    """
    if not memories:
        return None

    # Only use semantic memories (profile facts), not episodic (raw conversation)
    # Also filter for high-salience memories (>= 0.8)
    profile_memories = [
        m for m in memories
        if m.get("primary_sector") == "semantic"
        and m.get("salience", 0) >= 0.8
    ]

    # If no semantic memories, try high-salience memories of any type
    if not profile_memories:
        profile_memories = [
            m for m in memories
            if m.get("salience", 0) >= 0.85
        ]

    if not profile_memories:
        return None

    # Sort by salience and take top 3
    sorted_memories = sorted(
        profile_memories,
        key=lambda m: m.get("salience", 0.5),
        reverse=True
    )[:3]

    # Build summary from clean memories only
    summary_parts = []
    for memory in sorted_memories:
        content = memory.get("content", "").strip()
        # Filter out conversational filler and keep reasonable length
        if content and len(content) < 200 and not _is_conversational_filler(content):
            summary_parts.append(content)

    if summary_parts:
        return " ".join(summary_parts)

    return None


def _get_last_call_summary(memories: list[dict[str, Any]]) -> Optional[str]:
    """Get summary of the last call from memories.

    Extracts meaningful content from episodic memories, filtering out
    raw conversational filler and truncating at sentence boundaries.

    Args:
        memories: List of memory objects from OpenMemory.

    Returns:
        A summary of the last call or None if no meaningful content found.
    """
    if not memories:
        return None

    # Get episodic memories (conversation records)
    episodic_memories = [
        m for m in memories
        if m.get("primary_sector") == "episodic"
    ]

    if not episodic_memories:
        return None

    # Try to find a meaningful episodic memory (not just filler)
    for memory in episodic_memories:
        content = memory.get("content", "").strip()

        # Skip conversational filler
        if _is_conversational_filler(content):
            continue

        if content:
            # Truncate at sentence boundary instead of character count
            truncated = _truncate_at_sentence(content, max_length=150)
            if truncated and not _is_conversational_filler(truncated):
                return f"Last time we talked about: {truncated}"

    return None


def _truncate_at_sentence(text: str, max_length: int = 150) -> Optional[str]:
    """Truncate text at a sentence boundary.

    Args:
        text: The text to truncate.
        max_length: Maximum length of the result.

    Returns:
        Text truncated at a sentence boundary, or None if no valid content.
    """
    if not text or len(text.strip()) < 10:
        return None

    text = text.strip()

    # If text is already short enough, return it
    if len(text) <= max_length:
        return text

    # Find the last sentence boundary before max_length
    truncated = text[:max_length]

    # Look for sentence endings
    sentence_endings = [". ", "! ", "? "]
    last_boundary = -1
    for ending in sentence_endings:
        pos = truncated.rfind(ending)
        if pos > last_boundary:
            last_boundary = pos + 1  # Include the punctuation

    if last_boundary > 20:  # Ensure we have at least some content
        return truncated[:last_boundary].strip()

    # If no sentence boundary, try to break at a comma or natural pause
    comma_pos = truncated.rfind(", ")
    if comma_pos > 30:
        return truncated[:comma_pos].strip()

    # Last resort: truncate at word boundary
    space_pos = truncated.rfind(" ")
    if space_pos > 30:
        return truncated[:space_pos].strip() + "..."

    return None
