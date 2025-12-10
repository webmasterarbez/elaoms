"""OpenAI service for generating personalized greetings.

This module provides functions for:
- Generating personalized next-call greetings using OpenAI
- Processing conversation transcripts for context extraction
- Error handling with graceful degradation
"""

import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


async def generate_next_greeting(
    agent_profile: dict[str, Any],
    user_profile: dict[str, Any],
    transcript: str,
    conversation_metadata: Optional[dict[str, Any]] = None
) -> Optional[dict[str, Any]]:
    """Generate personalized greeting for next call using OpenAI.

    Uses OpenAI's chat completions API to generate a natural, personalized
    greeting based on the agent's profile, user's profile, and the conversation
    transcript.

    Args:
        agent_profile: Agent configuration including:
            - agent_id: Unique identifier
            - agent_name: Display name
            - first_message: Default greeting
            - system_prompt: Agent's personality/instructions
        user_profile: User information including:
            - name: User's name (if known)
            - phone_number: E.164 formatted phone
            - total_interactions: Count across all agents
        transcript: Full conversation transcript as a string
        conversation_metadata: Optional metadata including:
            - duration: Call duration
            - topics_discussed: List of topics
            - data_collection: Extracted data

    Returns:
        Dictionary containing:
            - next_greeting: Personalized greeting text (str | None)
            - key_topics: List of conversation topics (List[str])
            - sentiment: Caller sentiment (str)
            - conversation_summary: One-sentence summary (str)
        Returns None if generation fails after retries.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured, skipping greeting generation")
        return None

    # Build the prompt
    prompt = _build_greeting_prompt(
        agent_profile=agent_profile,
        user_profile=user_profile,
        transcript=transcript,
        conversation_metadata=conversation_metadata
    )

    # Attempt generation with retries
    for attempt in range(MAX_RETRIES):
        try:
            result = await _call_openai_api(prompt)
            if result:
                return result
        except Exception as e:
            backoff = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning(
                f"OpenAI API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                f"Retrying in {backoff}s..."
            )
            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(backoff)

    logger.error("Failed to generate greeting after all retries")
    return None


def _build_greeting_prompt(
    agent_profile: dict[str, Any],
    user_profile: dict[str, Any],
    transcript: str,
    conversation_metadata: Optional[dict[str, Any]] = None
) -> str:
    """Build the OpenAI prompt for greeting generation.

    Args:
        agent_profile: Agent configuration dictionary
        user_profile: User profile dictionary
        transcript: Conversation transcript
        conversation_metadata: Optional conversation metadata

    Returns:
        Formatted prompt string for OpenAI
    """
    # Extract agent details
    agent_id = agent_profile.get("agent_id", "unknown")
    agent_name = agent_profile.get("agent_name", "AI Assistant")
    first_message = agent_profile.get("first_message", "Hello, how can I help you?")
    system_prompt = agent_profile.get("system_prompt", "")

    # Extract role from system prompt if available
    agent_role = "AI assistant"
    if system_prompt:
        # Try to extract a role description from the first sentence
        first_sentence = system_prompt.split(".")[0][:100]
        if first_sentence:
            agent_role = first_sentence

    # Extract user details
    user_name = user_profile.get("name", "Unknown")
    total_interactions = user_profile.get("total_interactions", 1)
    last_call_date = conversation_metadata.get("last_call_date") if conversation_metadata else None

    # Truncate transcript if too long (keep last 2000 chars for context)
    truncated_transcript = transcript
    if len(transcript) > 2000:
        truncated_transcript = f"[...earlier conversation omitted...]\n{transcript[-2000:]}"

    prompt = f"""You are generating a personalized greeting for a voice AI agent's next interaction with a caller.

Agent Profile:
- Agent ID: {agent_id}
- Agent Name: {agent_name}
- Agent Role: {agent_role}
- Default First Message: {first_message}

Caller Profile:
- Name: {user_name if user_name != "Unknown" else "Not yet known"}
- Total Interactions: {total_interactions}
- Last Call: {last_call_date or "This was their first call"}

Conversation Context:
{truncated_transcript}

Based on this conversation:
1. Write a natural, warm greeting (max 30 words) that:
   - Acknowledges the caller by name if known
   - References a specific topic from the conversation naturally
   - Maintains the agent's personality and tone
   - Creates continuity from where the last call ended

2. Identify 3-5 key topics discussed

3. Assess the caller's sentiment (satisfied/neutral/frustrated/confused)

4. Provide a 1-sentence conversation summary

Return ONLY valid JSON in this exact format:
{{
    "next_greeting": "Your personalized greeting here (or null if first call with no name)",
    "key_topics": ["topic1", "topic2", "topic3"],
    "sentiment": "satisfied",
    "conversation_summary": "One sentence summary of what was discussed."
}}

If this was the first call and no name was captured, return next_greeting as null.
Do not include any text outside the JSON object."""

    return prompt


async def _call_openai_api(prompt: str) -> Optional[dict[str, Any]]:
    """Call the OpenAI API to generate a greeting.

    Args:
        prompt: The formatted prompt for OpenAI

    Returns:
        Parsed JSON response or None on failure
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
    }

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that generates personalized greetings for voice AI agents. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "temperature": settings.OPENAI_TEMPERATURE,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return None

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                logger.error("Empty response from OpenAI API")
                return None

            # Parse the JSON response
            try:
                parsed = json.loads(content)

                # Validate expected fields
                return {
                    "next_greeting": parsed.get("next_greeting"),
                    "key_topics": parsed.get("key_topics", []),
                    "sentiment": parsed.get("sentiment", "neutral"),
                    "conversation_summary": parsed.get("conversation_summary", "")
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.debug(f"Raw response: {content}")
                return None

    except httpx.RequestError as e:
        logger.error(f"HTTP error calling OpenAI API: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI API: {e}")
        raise


def build_transcript_string(transcript_entries: list[dict[str, Any]]) -> str:
    """Build a string representation of the transcript.

    Converts a list of transcript entries into a readable string format
    suitable for the OpenAI prompt.

    Args:
        transcript_entries: List of transcript entry dictionaries with
            'role' and 'message' keys.

    Returns:
        Formatted transcript string.
    """
    lines = []
    for entry in transcript_entries:
        role = entry.get("role", "unknown").capitalize()
        message = entry.get("message", "")
        if message:
            lines.append(f"{role}: {message}")

    return "\n".join(lines)
