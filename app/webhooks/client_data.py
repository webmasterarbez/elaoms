"""Client data webhook handler for conversation initiation.

This module handles the POST /webhook/client-data endpoint:
- No HMAC authentication required
- Parses ClientDataRequest from request body
- Extracts caller phone number from caller_id field
- Queries OpenMemory for user profile using phone number as userId
- Builds DynamicVariables with user_name, user_profile_summary, last_call_summary
- Builds ConversationConfigOverride with personalized firstMessage for returning callers
- Returns empty/null values for new callers (let ElevenLabs use defaults)
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models.requests import ClientDataRequest
from app.models.responses import ClientDataResponse
from app.memory.profiles import (
    get_user_profile,
    build_dynamic_variables,
    build_conversation_override,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/client-data",
    response_model=ClientDataResponse,
    summary="Handle conversation initiation client data",
    description=(
        "Webhook called by ElevenLabs when a conversation is initiated. "
        "Returns personalized dynamic variables and conversation config overrides "
        "for known callers, or empty values for new callers."
    ),
)
async def client_data_webhook(request: ClientDataRequest) -> ClientDataResponse:
    """Handle client-data webhook for conversation initiation.

    This endpoint:
    1. Extracts the caller phone number from the request
    2. Queries OpenMemory for the user's profile
    3. Builds personalized dynamic variables for known callers
    4. Returns conversation config overrides for personalized greetings
    5. Returns empty/null values for new callers

    Args:
        request: ClientDataRequest with caller_id, agent_id, called_number, call_sid

    Returns:
        ClientDataResponse with dynamic_variables and conversation_config_override
    """
    phone_number = request.caller_id
    logger.info(f"Client-data webhook called for caller: {phone_number}")

    try:
        # Query OpenMemory for user profile
        profile = get_user_profile(phone_number)

        if profile:
            logger.info(f"Found profile for caller {phone_number}: {profile.get('name', 'Unknown')}")
        else:
            logger.info(f"No profile found for new caller {phone_number}")

        # Build response components
        dynamic_variables = build_dynamic_variables(profile)
        conversation_override = build_conversation_override(profile)

        response = ClientDataResponse(
            dynamic_variables=dynamic_variables,
            conversation_config_override=conversation_override,
        )

        logger.debug(f"Returning client-data response: {response.model_dump_json()}")
        return response

    except Exception as e:
        logger.error(f"Error processing client-data webhook: {e}")
        # Return empty response on error to allow conversation to proceed
        return ClientDataResponse(
            dynamic_variables=None,
            conversation_config_override=None,
        )