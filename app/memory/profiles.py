"""Caller profile management for OpenMemory integration.

This module provides functions for:
- Retrieving user profiles from OpenMemory via REST API
- Getting user summaries via the OpenMemory API
- Building dynamic variables for ElevenLabs response
- Generating personalized conversation overrides

All operations use the phone number as the userId for multi-tenant isolation.
"""

import logging
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

        if not parsed["has_memories"]:
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

        return {
            "name": name,
            "summary": parsed.get("top_content"),  # Use top_content as summary
            "top_content": parsed.get("top_content"),
            "memories": memories,
            "memory_count": parsed["memory_count"],
            "has_memories": parsed["has_memories"],
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
            f"Hello {name}, it's Margaret again. It's so good to hear your voice. "
            "I'm looking forward to continuing our journey through your life stories. "
            "What would you like to share today?"
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

    Args:
        memories: List of memory objects from OpenMemory.

    Returns:
        The user's name if found, or None.
    """
    name_keywords = ["name is", "my name is", "called", "i'm", "i am"]

    for memory in memories:
        content = memory.get("content", "").lower()
        for keyword in name_keywords:
            if keyword in content:
                # Try to extract the name after the keyword
                idx = content.find(keyword)
                after_keyword = content[idx + len(keyword):].strip()
                # Get the first word (likely the name)
                words = after_keyword.split()
                if words:
                    # Capitalize the name properly
                    name = words[0].strip(".,!?").capitalize()
                    if len(name) > 1:  # Valid name
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
