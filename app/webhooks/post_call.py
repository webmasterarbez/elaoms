"""Post-call webhook handler for processing call transcriptions and audio.

This module handles the POST /webhook/post-call endpoint:
- HMAC authentication REQUIRED (uses verify_hmac_signature dependency)
- Returns 200 immediately after HMAC verification
- Processes payload asynchronously in background task
- Handles three webhook types:
  - post_call_transcription: Process and save transcription
  - post_call_audio: Decode base64 and save audio
  - call_initiation_failure: Save failure log
- Implements payload storage with configurable directory
- Implements memory processing for OpenMemory integration
- TWO-TIER MEMORY ARCHITECTURE:
  - Tier 1: Updates universal user profile (name, interactions)
  - Tier 2: Generates and stores agent-specific next greeting via OpenAI
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.config import settings
from app.auth.hmac import verify_hmac_signature
from app.models.requests import PostCallWebhookRequest
from app.memory.extraction import (
    extract_user_info,
    extract_user_messages,
    create_profile_memories,
    store_conversation_memories,
)
from app.memory.profiles import (
    get_universal_user_profile,
    store_universal_user_profile,
    store_agent_conversation_state,
    extract_name_from_transcript,
)
from app.services.openai_service import generate_next_greeting, build_transcript_string
from app.services.agent_cache import get_agent_profile_cache

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_storage_path(conversation_id: str) -> Path:
    """Get the storage directory path for a conversation.

    Args:
        conversation_id: The unique conversation identifier.

    Returns:
        Path object for the conversation's storage directory.
    """
    base_path = Path(settings.PAYLOAD_STORAGE_PATH)
    return base_path / conversation_id


def _ensure_directory_exists(dir_path: Path) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        dir_path: Path to the directory.

    Raises:
        IOError: If directory creation fails.
    """
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        raise IOError(f"Failed to create directory: {e}")


def _save_transcription(
    conversation_id: str,
    payload: dict[str, Any]
) -> Path:
    """Save transcription payload to JSON file.

    Args:
        conversation_id: The unique conversation identifier.
        payload: The full webhook payload as a dictionary.

    Returns:
        Path to the saved file.

    Raises:
        IOError: If file writing fails.
    """
    storage_dir = _get_storage_path(conversation_id)
    _ensure_directory_exists(storage_dir)

    file_path = storage_dir / f"{conversation_id}_transcription.json"

    try:
        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Saved transcription to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save transcription: {e}")
        raise IOError(f"Failed to save transcription: {e}")


def _save_audio(
    conversation_id: str,
    audio_base64: str
) -> Path:
    """Decode base64 audio and save as MP3 file.

    Args:
        conversation_id: The unique conversation identifier.
        audio_base64: Base64 encoded audio data.

    Returns:
        Path to the saved file.

    Raises:
        IOError: If file writing fails.
        ValueError: If base64 decoding fails.
    """
    storage_dir = _get_storage_path(conversation_id)
    _ensure_directory_exists(storage_dir)

    file_path = storage_dir / f"{conversation_id}_audio.mp3"

    try:
        audio_bytes = base64.b64decode(audio_base64)
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"Saved audio to {file_path}")
        return file_path
    except base64.binascii.Error as e:
        logger.error(f"Failed to decode base64 audio: {e}")
        raise ValueError(f"Invalid base64 audio data: {e}")
    except Exception as e:
        logger.error(f"Failed to save audio: {e}")
        raise IOError(f"Failed to save audio: {e}")


def _save_failure(
    conversation_id: str,
    payload: dict[str, Any]
) -> Path:
    """Save failure payload to JSON file.

    Args:
        conversation_id: The unique conversation identifier.
        payload: The full webhook payload as a dictionary.

    Returns:
        Path to the saved file.

    Raises:
        IOError: If file writing fails.
    """
    storage_dir = _get_storage_path(conversation_id)
    _ensure_directory_exists(storage_dir)

    file_path = storage_dir / f"{conversation_id}_failure.json"

    try:
        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Saved failure log to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save failure log: {e}")
        raise IOError(f"Failed to save failure log: {e}")


def _extract_caller_phone(request_data: PostCallWebhookRequest) -> str | None:
    """Extract caller phone number from webhook data.

    The phone number is located at:
    data.conversation_initiation_client_data.dynamic_variables.system__caller_id

    Args:
        request_data: The parsed webhook request.

    Returns:
        The caller's phone number or None if not found.
    """
    try:
        client_data = request_data.data.conversation_initiation_client_data
        if client_data and client_data.dynamic_variables:
            return client_data.dynamic_variables.get("system__caller_id")
    except Exception as e:
        logger.warning(f"Failed to extract caller phone: {e}")
    return None


def _extract_conversation_context(request_data: PostCallWebhookRequest) -> dict[str, Any]:
    """Extract conversation context including timestamp and conversation ID.

    Extracts temporal and identification data for grouping memories together:
    - conversation_id: Unique identifier for this conversation
    - event_timestamp: Unix timestamp when the event occurred
    - timestamp_utc: ISO 8601 UTC timestamp from dynamic_variables

    Args:
        request_data: The parsed webhook request.

    Returns:
        Dictionary with conversation_id, event_timestamp, and timestamp_utc.
    """
    context = {
        "conversation_id": request_data.data.conversation_id,
        "event_timestamp": request_data.event_timestamp,
        "timestamp_utc": None,
    }
    try:
        client_data = request_data.data.conversation_initiation_client_data
        if client_data and client_data.dynamic_variables:
            context["timestamp_utc"] = client_data.dynamic_variables.get("system__time_utc")
    except Exception as e:
        logger.warning(f"Failed to extract timestamp from conversation context: {e}")
    return context


async def _process_memories(request_data: PostCallWebhookRequest) -> None:
    """Process and store memories from post-call transcription.

    This function implements the two-tier memory architecture:

    TIER 1 (Universal Profile):
    1. Get/create universal user profile
    2. Extract name from transcript if not already set
    3. Increment interaction count

    TIER 2 (Agent-Specific State):
    1. Fetch agent profile (from cache or ElevenLabs API)
    2. Generate next greeting via OpenAI
    3. Store agent-specific conversation state

    LEGACY (backward compatible):
    - Store profile facts from data_collection_results
    - Store individual user messages

    Args:
        request_data: The parsed webhook request.
    """
    # Extract caller phone number
    phone_number = _extract_caller_phone(request_data)
    if not phone_number:
        logger.warning("No caller phone number found, skipping memory processing")
        return

    # Extract agent_id
    agent_id = request_data.data.agent_id

    logger.info(f"Processing memories for caller: {phone_number}, agent: {agent_id}")

    # Extract conversation context for memory grouping
    conversation_context = _extract_conversation_context(request_data)
    logger.debug(f"Conversation context: {conversation_context}")

    # Build transcript string for name extraction and greeting generation
    transcript_str = ""
    if request_data.data.transcript:
        transcript_entries = [
            {"role": entry.role, "message": entry.message}
            for entry in request_data.data.transcript
            if entry.message
        ]
        transcript_str = build_transcript_string(transcript_entries)

    # =========================================================================
    # TIER 1: Universal User Profile (Cross-Agent)
    # =========================================================================
    try:
        # Get existing universal profile
        universal_profile = await get_universal_user_profile(phone_number)

        # Extract name from transcript if not already known
        extracted_name = None
        if transcript_str:
            extracted_name = extract_name_from_transcript(transcript_str)
            if extracted_name:
                logger.info(f"Extracted name from transcript: {extracted_name}")

        # Also check data_collection_results for name
        if not extracted_name and request_data.data.analysis:
            data_results = request_data.data.analysis.data_collection_results or {}
            user_info = extract_user_info(data_results)
            extracted_name = user_info.get("first_name") or user_info.get("name")

        # Determine if we need to update name
        current_name = universal_profile.get("name") if universal_profile else None
        name_to_store = extracted_name if (extracted_name and not current_name) else None

        # Store/update universal profile (increments interaction count)
        await store_universal_user_profile(
            phone_number=phone_number,
            name=name_to_store,
            increment_interactions=True
        )
        logger.info(f"Updated universal profile for {phone_number}")

        # Refresh universal profile after update
        universal_profile = await get_universal_user_profile(phone_number)

    except Exception as e:
        logger.error(f"Failed to process Tier 1 (universal profile): {e}", exc_info=True)
        universal_profile = None

    # =========================================================================
    # TIER 2: Agent-Specific Conversation State (Per-Agent)
    # =========================================================================
    try:
        # Get agent profile from cache or ElevenLabs API
        agent_cache = get_agent_profile_cache()
        agent_profile = await agent_cache.get_agent_profile(agent_id)

        if not agent_profile:
            logger.warning(f"Could not fetch agent profile for {agent_id}, skipping greeting generation")
        elif transcript_str:
            # Generate next greeting via OpenAI
            logger.info(f"Generating next greeting for {phone_number} with agent {agent_id}")

            # Build conversation metadata
            conv_metadata = {
                "duration": None,
                "last_call_date": conversation_context.get("timestamp_utc"),
            }
            if request_data.data.metadata:
                conv_metadata["duration"] = request_data.data.metadata.call_duration_secs

            greeting_data = await generate_next_greeting(
                agent_profile=agent_profile,
                user_profile=universal_profile or {"name": None, "phone_number": phone_number, "total_interactions": 1},
                transcript=transcript_str,
                conversation_metadata=conv_metadata
            )

            if greeting_data:
                # Store agent-specific conversation state
                await store_agent_conversation_state(
                    phone_number=phone_number,
                    agent_id=agent_id,
                    greeting_data=greeting_data
                )
                logger.info(f"Stored agent-specific state for {phone_number} with agent {agent_id}")
            else:
                logger.warning(f"No greeting data generated for {phone_number}")

    except Exception as e:
        logger.error(f"Failed to process Tier 2 (agent state): {e}", exc_info=True)
        # Continue processing - greeting generation is optional

    # =========================================================================
    # LEGACY: Store additional memories (backward compatible)
    # =========================================================================

    # Extract user info from data collection results
    user_info = {}
    if request_data.data.analysis and request_data.data.analysis.data_collection_results:
        user_info = extract_user_info(request_data.data.analysis.data_collection_results)
        logger.debug(f"Extracted user info: {user_info}")

    # Store profile facts as memories
    if user_info:
        try:
            results = await create_profile_memories(user_info, phone_number, conversation_context)
            logger.info(f"Stored {len(results)} profile memories for {phone_number}")
        except Exception as e:
            logger.error(f"Failed to store profile memories: {e}")

    # Extract and store user messages
    if request_data.data.transcript:
        user_messages = extract_user_messages(request_data.data.transcript)
        if user_messages:
            try:
                results = await store_conversation_memories(user_messages, phone_number, conversation_context)
                logger.info(f"Stored {len(results)} conversation memories for {phone_number}")
            except Exception as e:
                logger.error(f"Failed to store conversation memories: {e}")


async def _process_webhook_payload(payload_dict: dict[str, Any]) -> None:
    """Process webhook payload in background.

    This function handles all webhook types asynchronously after
    the immediate 200 response has been sent to ElevenLabs.

    Args:
        payload_dict: The raw webhook payload as a dictionary.
    """
    try:
        # Parse the request
        request_data = PostCallWebhookRequest(**payload_dict)
        webhook_type = request_data.type
        conversation_id = request_data.data.conversation_id

        logger.info(f"Background processing webhook: type={webhook_type}, conversation_id={conversation_id}")

        if webhook_type == "post_call_transcription":
            # Save transcription
            _save_transcription(conversation_id, payload_dict)
            # Process memories
            await _process_memories(request_data)
            logger.info(f"Completed transcription processing for {conversation_id}")

        elif webhook_type == "post_call_audio":
            # Extract and save audio
            audio_base64 = payload_dict.get("data", {}).get("full_audio")
            if audio_base64:
                _save_audio(conversation_id, audio_base64)
                logger.info(f"Completed audio processing for {conversation_id}")
            else:
                logger.warning(f"No full_audio found in post_call_audio webhook for {conversation_id}")

        elif webhook_type == "call_initiation_failure":
            # Save failure log
            _save_failure(conversation_id, payload_dict)
            logger.info(f"Saved failure log for {conversation_id}")

        else:
            logger.warning(f"Unknown webhook type: {webhook_type}")

    except Exception as e:
        logger.error(f"Error in background webhook processing: {e}", exc_info=True)
        # Save raw payload for debugging
        try:
            conversation_id = payload_dict.get("data", {}).get("conversation_id", "unknown")
            storage_dir = _get_storage_path(conversation_id)
            _ensure_directory_exists(storage_dir)
            error_file = storage_dir / f"{conversation_id}_error.json"
            with open(error_file, "w") as f:
                json.dump({
                    "error": str(e),
                    "payload": payload_dict
                }, f, indent=2)
            logger.info(f"Saved error payload to {error_file}")
        except Exception as save_error:
            logger.error(f"Failed to save error payload: {save_error}")


@router.post(
    "/post-call",
    summary="Handle post-call webhook",
    description=(
        "Webhook called by ElevenLabs after a call completes. "
        "Handles transcription, audio, and failure payloads. "
        "HMAC authentication is required. "
        "Returns 200 immediately after HMAC verification; processing happens in background."
    ),
    responses={
        200: {"description": "Webhook received and queued for processing"},
        401: {"description": "HMAC authentication failed"},
    },
)
async def post_call_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_hmac_signature),
) -> dict[str, Any]:
    """Handle post-call webhook for transcription, audio, and failure processing.

    This endpoint:
    1. Validates HMAC signature (via dependency)
    2. Returns 200 immediately to acknowledge receipt
    3. Processes payload asynchronously in background task

    This design ensures ElevenLabs always receives a timely response,
    preventing webhook timeouts regardless of processing complexity.

    Args:
        request: FastAPI Request object
        background_tasks: FastAPI BackgroundTasks for async processing
        _: HMAC signature verification dependency

    Returns:
        Immediate success response acknowledging webhook receipt
    """
    # Parse JSON body - minimal validation here for fast response
    try:
        body = await request.body()
        payload_dict = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        # Still return 200 but log the error - don't block ElevenLabs
        return {
            "status": "error",
            "message": f"Invalid JSON payload: {e}"
        }

    # Extract basic info for logging (without full Pydantic validation)
    webhook_type = payload_dict.get("type", "unknown")
    conversation_id = payload_dict.get("data", {}).get("conversation_id", "unknown")

    logger.info(f"Post-call webhook received: type={webhook_type}, conversation_id={conversation_id}")

    # Queue background processing - this runs after response is sent
    background_tasks.add_task(_process_webhook_payload, payload_dict)

    # Return immediately - processing continues in background
    return {
        "status": "received",
        "type": webhook_type,
        "conversation_id": conversation_id,
        "message": "Webhook received and queued for processing"
    }