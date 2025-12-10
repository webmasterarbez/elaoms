"""Transcript processing and memory extraction for OpenMemory.

This module provides functions for:
- Extracting user info from data collection results
- Filtering transcript for user messages
- Creating profile memories with high salience
- Storing conversation memories
- Searching memories for search-data webhook

All memories are stored with:
- userId = phone_number (for multi-tenant isolation)
- decayLambda = 0 (permanent retention)
- Appropriate salience values
"""

import logging
from typing import Any, Optional

import httpx

from app.models.requests import TranscriptEntry, DataCollectionResult
from app.utils.http_client import get_openmemory_client

logger = logging.getLogger(__name__)

# Constants for memory storage
PERMANENT_DECAY = 0  # decayLambda=0 for permanent retention
HIGH_SALIENCE = 0.9  # High importance for profile facts
MEDIUM_SALIENCE = 0.7  # Medium importance for conversation messages


def extract_user_info(
    data_collection_results: dict[str, DataCollectionResult]
) -> dict[str, Any]:
    """Extract user information from analysis data collection results.

    Parses the data_collection_results from the post-call webhook to extract
    meaningful user information like name, preferences, etc.

    Args:
        data_collection_results: Dictionary of DataCollectionResult objects
            from the conversation analysis.

    Returns:
        A dictionary of extracted user information.
        Example: {"first_name": "Stefan", "preference": "email"}
    """
    extracted = {}

    for field_id, result in data_collection_results.items():
        if result.value is not None:
            # Clean up the field ID to use as key
            key = field_id.lower().replace("-", "_").replace(" ", "_")
            extracted[key] = result.value

            logger.debug(f"Extracted user info: {key}={result.value}")

    return extracted


def extract_user_messages(transcript: list[TranscriptEntry]) -> list[dict[str, Any]]:
    """Filter transcript for user messages with timing information.

    Extracts all messages where role="user" from the conversation transcript,
    including the time_in_call_secs for temporal ordering within the conversation.

    Args:
        transcript: List of TranscriptEntry objects from the post-call webhook.

    Returns:
        A list of dictionaries with 'message' and 'time_in_call_secs' keys.
    """
    user_messages = []

    for entry in transcript:
        if entry.role == "user" and entry.message:
            user_messages.append({
                "message": entry.message,
                "time_in_call_secs": entry.time_in_call_secs
            })

    logger.debug(f"Extracted {len(user_messages)} user messages from transcript")
    return user_messages


async def create_profile_memories(
    user_info: dict[str, Any],
    phone_number: str,
    conversation_context: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Store profile facts as memories with high salience.

    Creates permanent memories for extracted user profile information.
    Each piece of information is stored as a separate memory for
    better retrieval and granularity.

    Args:
        user_info: Dictionary of user information (e.g., {"first_name": "Stefan"}).
        phone_number: The user's phone number for userId isolation.
        conversation_context: Optional dict with conversation_id, timestamp_utc,
            and event_timestamp for grouping memories together.

    Returns:
        A list of memory creation results from OpenMemory.
    """
    if not user_info:
        logger.info("No user info to store")
        return []

    results = []

    try:
        async with get_openmemory_client() as client:
            for key, value in user_info.items():
                if value is None:
                    continue

                # Create human-readable content
                content = _format_profile_content(key, value)

                if not content:
                    continue

                # Build metadata with conversation context for grouping
                metadata = {
                    "field": key,
                    "value": str(value),
                }
                if conversation_context:
                    metadata["conversation_id"] = conversation_context.get("conversation_id")
                    metadata["timestamp_utc"] = conversation_context.get("timestamp_utc")
                    metadata["event_timestamp"] = conversation_context.get("event_timestamp")

                payload = {
                    "content": content,
                    "tags": ["profile", key],
                    "metadata": metadata,
                    "user_id": phone_number,
                    "salience": HIGH_SALIENCE,
                    "decay_lambda": PERMANENT_DECAY
                }

                response = await client.post("/memory/add", json=payload)

                if response.status_code == 200:
                    results.append(response.json())
                    logger.info(f"Stored profile memory for {phone_number}: {key}={value}")
                else:
                    logger.warning(f"Failed to store profile memory: {response.status_code} - {response.text}")

        return results

    except httpx.RequestError as e:
        logger.error(f"HTTP error storing profile memories: {e}")
        return results
    except Exception as e:
        logger.error(f"Error storing profile memories: {e}")
        return results


async def store_conversation_memories(
    messages: list[dict[str, Any]],
    phone_number: str,
    conversation_context: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Store each user message as an individual memory.

    Creates permanent memories for each user message from the conversation.
    This enables detailed conversation recall and context building.

    Args:
        messages: List of dicts with 'message' and 'time_in_call_secs' keys.
        phone_number: The user's phone number for userId isolation.
        conversation_context: Optional dict with conversation_id, timestamp_utc,
            and event_timestamp for grouping memories together.

    Returns:
        A list of memory creation results from OpenMemory.
    """
    if not messages:
        logger.info("No messages to store")
        return []

    results = []

    try:
        async with get_openmemory_client() as client:
            for idx, msg_data in enumerate(messages):
                message = msg_data.get("message", "")
                time_in_call_secs = msg_data.get("time_in_call_secs")

                if not message or len(message.strip()) < 3:
                    continue

                # Build metadata with conversation context for grouping
                metadata = {
                    "message_index": idx,
                    "type": "user_utterance",
                    "time_in_call_secs": time_in_call_secs,
                }
                if conversation_context:
                    metadata["conversation_id"] = conversation_context.get("conversation_id")
                    metadata["timestamp_utc"] = conversation_context.get("timestamp_utc")
                    metadata["event_timestamp"] = conversation_context.get("event_timestamp")

                payload = {
                    "content": message,
                    "tags": ["conversation", "user_message"],
                    "metadata": metadata,
                    "user_id": phone_number,
                    "salience": MEDIUM_SALIENCE,
                    "decay_lambda": PERMANENT_DECAY
                }

                response = await client.post("/memory/add", json=payload)

                if response.status_code == 200:
                    results.append(response.json())
                    logger.debug(f"Stored conversation memory {idx} for {phone_number}")
                else:
                    logger.warning(f"Failed to store conversation memory: {response.status_code}")

        logger.info(f"Stored {len(results)} conversation memories for {phone_number}")
        return results

    except httpx.RequestError as e:
        logger.error(f"HTTP error storing conversation memories: {e}")
        return results
    except Exception as e:
        logger.error(f"Error storing conversation memories: {e}")
        return results


async def search_memories(
    query: str,
    phone_number: str,
    limit: int = 10
) -> dict[str, Any]:
    """Query OpenMemory for relevant memories.

    Searches for memories matching the query, filtered by userId.
    Returns structured results with profile and memories array.

    Args:
        query: The search query string.
        phone_number: The user's phone number for userId isolation.
        limit: Maximum number of memories to return (default: 10).

    Returns:
        A dictionary with 'profile' and 'memories' keys.
        Handles empty results gracefully.
    """
    try:
        async with get_openmemory_client() as client:
            payload = {
                "query": query,
                "k": limit,
                "filters": {"user_id": phone_number}
            }

            response = await client.post("/memory/query", json=payload)

            if response.status_code != 200:
                logger.warning(f"OpenMemory query failed: {response.status_code}")
                return {"profile": None, "memories": []}

            results = response.json()

        # Parse results into structured format
        memories = []
        name = None
        summary_parts = []

        raw_results = results.get("matches", []) if results else []

        for memory in raw_results:
            memory_item = {
                "content": memory.get("content", ""),
                "sector": memory.get("primary_sector", "semantic"),
                "salience": memory.get("salience", 0.5),
            }
            memories.append(memory_item)

            # Extract name if found
            metadata = memory.get("metadata", {})
            if isinstance(metadata, dict):
                if metadata.get("field") == "first_name":
                    name = metadata.get("value")

            # Collect for summary
            content = memory.get("content", "")
            if content and memory.get("salience", 0) > 0.7:
                summary_parts.append(content)

        # Build profile from memories
        profile = None
        if name or summary_parts:
            summary = " ".join(summary_parts[:3]) if summary_parts else None
            profile = {
                "name": name,
                "summary": summary,
                "phone_number": phone_number
            }

        return {
            "profile": profile,
            "memories": memories
        }

    except httpx.RequestError as e:
        logger.error(f"HTTP error searching memories: {e}")
        return {"profile": None, "memories": []}
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return {"profile": None, "memories": []}


def _format_profile_content(key: str, value: Any) -> Optional[str]:
    """Format a profile field into human-readable content.

    Args:
        key: The field key (e.g., "first_name").
        value: The field value.

    Returns:
        A human-readable string or None if value is empty.
    """
    if value is None or value == "":
        return None

    # Map common field names to readable formats
    field_formats = {
        "first_name": f"User's name is {value}",
        "name": f"User's name is {value}",
        "last_name": f"User's last name is {value}",
        "full_name": f"User's full name is {value}",
        "email": f"User prefers contact via email at {value}",
        "preference": f"User preference: {value}",
        "topic": f"User is interested in {value}",
        "issue": f"User reported issue: {value}",
        "request": f"User requested: {value}",
        "feedback": f"User feedback: {value}",
    }

    # Check for exact match
    if key in field_formats:
        return field_formats[key]

    # Default format
    readable_key = key.replace("_", " ").title()
    return f"{readable_key}: {value}"
