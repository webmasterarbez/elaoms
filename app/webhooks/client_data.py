"""Client data webhook handler for conversation initiation.

This module handles the POST /webhook/client-data endpoint:
- No HMAC authentication required
- Parses ClientDataRequest from request body
- Extracts caller phone number from caller_id field
- Queries OpenMemory for user profile using phone number as userId
- Builds DynamicVariables with user_name, user_profile_summary, last_call_summary
- Builds ConversationConfigOverride with personalized firstMessage for returning callers
- Returns empty objects for new callers (let ElevenLabs use defaults)
"""

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.requests import ClientDataRequest
from app.memory.profiles import (
    get_user_profile,
    build_dynamic_variables,
    build_conversation_override,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/client-data",
    summary="Handle conversation initiation client data",
    description=(
        "Webhook called by ElevenLabs when a conversation is initiated. "
        "Returns personalized dynamic variables and conversation config overrides "
        "for known callers, or empty values for new callers."
    ),
)
async def client_data_webhook(request: ClientDataRequest) -> JSONResponse:
    """Handle client-data webhook for conversation initiation.

    This endpoint:
    1. Extracts the caller phone number from the request
    2. Queries OpenMemory for the user's profile
    3. Builds personalized dynamic variables for known callers
    4. Returns conversation config overrides for personalized greetings
    5. Returns empty objects for new callers

    Args:
        request: ClientDataRequest with caller_id, agent_id, called_number, call_sid

    Returns:
        JSON response with dynamic_variables and conversation_config_override
    """
    phone_number = request.caller_id
    logger.info(f"Client-data webhook called for caller: {phone_number}")

    try:
        # Query OpenMemory for user profile (async)
        profile = await get_user_profile(phone_number)

        if profile:
            logger.info(f"Found profile for caller {phone_number}: {profile.get('name', 'Unknown')}")
        else:
            logger.info(f"No profile found for new caller {phone_number}")

        # Build response - exclude None values
        response_data: dict[str, Any] = {}

        # Build dynamic variables (only include non-null values)
        dynamic_vars = build_dynamic_variables(profile)
        dv_dict = {}
        if dynamic_vars.user_name:
            dv_dict["user_name"] = dynamic_vars.user_name
        if dynamic_vars.user_profile_summary:
            dv_dict["user_profile_summary"] = dynamic_vars.user_profile_summary
        if dynamic_vars.last_call_summary:
            dv_dict["last_call_summary"] = dynamic_vars.last_call_summary

        response_data["dynamic_variables"] = dv_dict

        # Build conversation config override (only include if we have a profile)
        conversation_override = build_conversation_override(profile)
        if conversation_override and conversation_override.agent:
            response_data["conversation_config_override"] = {
                "agent": {
                    "first_message": conversation_override.agent.first_message
                }
            }

        logger.info(f"Returning client-data response: {response_data}")
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error processing client-data webhook: {e}", exc_info=True)
        # Return empty response on error to allow conversation to proceed
        return JSONResponse(content={"dynamic_variables": {}})