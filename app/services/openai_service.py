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
from app.utils.http_client import get_openai_client

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
    """Build the OpenAI prompt for greeting generation using XML structure.

    Uses XML formatting for structured data as per Sean Kochel's prompt
    engineering guidelines for better LLM comprehension.

    Args:
        agent_profile: Agent configuration dictionary
        user_profile: User profile dictionary
        transcript: Conversation transcript
        conversation_metadata: Optional conversation metadata

    Returns:
        Formatted prompt string for OpenAI with XML structure
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
    user_name = user_profile.get("name") or "Unknown"
    total_interactions = user_profile.get("total_interactions", 1)
    last_call_date = conversation_metadata.get("last_call_date") if conversation_metadata else None

    # Truncate transcript if too long (keep last 2000 chars for context)
    truncated_transcript = transcript
    if len(transcript) > 2000:
        truncated_transcript = f"[...earlier conversation omitted...]\n{transcript[-2000:]}"

    prompt = f"""<agent_profile>
<agent_id>{agent_id}</agent_id>
<agent_name>{agent_name}</agent_name>
<agent_role>{agent_role}</agent_role>
<default_first_message>{first_message}</default_first_message>
</agent_profile>

<caller_profile>
<name>{user_name if user_name != "Unknown" else "Not yet known"}</name>
<total_interactions>{total_interactions}</total_interactions>
<last_call_date>{last_call_date or "This was their first call"}</last_call_date>
</caller_profile>

<conversation_transcript>
{truncated_transcript}
</conversation_transcript>

<task>
Generate a personalized greeting for this agent's next call with this caller.
</task>

<explicit_instructions>
1. Write a natural, warm greeting (MAXIMUM 30 words, NO EXCEPTIONS)
2. If caller's name is known, acknowledge them by name naturally
3. Reference ONE specific topic from the conversation (be specific, not generic)
4. Maintain the agent's personality and tone from the system_prompt
5. Create continuity - pick up where this call ended
6. If this was first call AND no name captured, return next_greeting as null
7. Identify 3-5 key topics discussed (be specific, e.g., "Arbez founding story" not "business")
8. Assess sentiment based on caller's language and tone
9. Summarize conversation in ONE sentence focusing on the main outcome
</explicit_instructions>

<output_format>
Return ONLY valid JSON, no markdown formatting:
{{
    "next_greeting": "Your personalized greeting here or null",
    "key_topics": ["topic1", "topic2", "topic3"],
    "sentiment": "satisfied",
    "conversation_summary": "One sentence summary."
}}
</output_format>

<constraints>
- Do NOT use ellipses (...) as greetings will be read by text-to-speech
- Do NOT make assumptions about topics not explicitly discussed
- Do NOT create generic greetings like "welcome back" without specific context
- Do NOT exceed 30 words for next_greeting under any circumstances
</constraints>

<examples>
GOOD Example:
{{
  "next_greeting": "Hi Stefan! I've been thinking about your Arbez founding story - ready to continue where we left off?",
  "key_topics": ["Arbez founding details", "childhood memories", "business challenges"],
  "sentiment": "engaged",
  "conversation_summary": "Explored early entrepreneurial journey and formative childhood experiences."
}}

BAD Example (too generic):
{{
  "next_greeting": "Welcome back! How can I help you today?",
  "key_topics": ["general conversation", "small talk"],
  "sentiment": "neutral",
  "conversation_summary": "Had a conversation."
}}
</examples>"""

    return prompt


async def _call_openai_api(prompt: str) -> Optional[dict[str, Any]]:
    """Call the OpenAI API to generate a greeting.

    Args:
        prompt: The formatted prompt for OpenAI

    Returns:
        Parsed JSON response or None on failure
    """
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
        async with get_openai_client() as client:
            response = await client.post("/v1/chat/completions", json=payload)

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
