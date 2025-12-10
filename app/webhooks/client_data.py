"""Client data webhook handler for conversation initiation.

This module handles the POST /webhook/client-data endpoint with the new
two-tier memory architecture:

Flow:
1. Query Tier 1: Universal user profile (name only)
2. Query Tier 2: Agent-specific conversation state (greeting + context)
3. Return appropriate response based on available data

Response Cases:
- Case 1: Has agent-specific greeting → Return personalized greeting override
- Case 2: Has name but no greeting → Return name in dynamic variables
- Case 3: New caller → Return empty (agent uses defaults)

Authentication:
- X-Api-Key authentication required (validated against ELEVENLABS_CLIENT_DATA_KEY)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth.hmac import verify_api_key
from app.models.requests import ClientDataRequest
from app.memory.profiles import (
    get_universal_user_profile,
    get_agent_conversation_state,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/client-data",
    summary="Handle conversation initiation client data",
    description=(
        "Webhook called by ElevenLabs when a conversation is initiated. "
        "Uses two-tier memory architecture: "
        "Tier 1 (universal profile) for name recognition across agents, "
        "Tier 2 (agent-specific state) for personalized greetings. "
        "Returns empty objects for new callers (let ElevenLabs use defaults)."
    ),
)
async def client_data_webhook(
    request: ClientDataRequest,
    _: None = Depends(verify_api_key),
) -> JSONResponse:
    """Handle client-data webhook for conversation initiation.

    This endpoint implements the two-tier memory retrieval:
    1. Queries Tier 1 (universal profile) for user name
    2. Queries Tier 2 (agent-specific state) for pre-generated greeting
    3. Returns appropriate response based on available data

    Response Logic:
    - If agent-specific greeting exists: Override first_message
    - If only name exists: Add to dynamic_variables (agent uses {{user_name}})
    - If new caller: Return empty (agent uses default greeting)

    Args:
        request: ClientDataRequest with caller_id, agent_id, called_number, call_sid

    Returns:
        JSON response with dynamic_variables and optional conversation_config_override
    """
    phone_number = request.caller_id
    agent_id = request.agent_id

    logger.info(f"Client-data webhook called for caller: {phone_number}, agent: {agent_id}")

    try:
        # Tier 1: Query universal user profile (cross-agent)
        universal_profile = await get_universal_user_profile(phone_number)

        # Tier 2: Query agent-specific conversation state
        agent_state = await get_agent_conversation_state(phone_number, agent_id)

        # Build response
        response_data: dict[str, Any] = {"dynamic_variables": {}}

        # Case 1: Has agent-specific greeting (returning caller to THIS agent)
        if agent_state and agent_state.get("next_greeting"):
            logger.info(f"Found agent-specific greeting for {phone_number}")

            # Override the first message with personalized greeting
            response_data["conversation_config_override"] = {
                "agent": {
                    "first_message": agent_state["next_greeting"]
                }
            }

            # Add dynamic variables for agent prompt context
            dv = response_data["dynamic_variables"]
            if universal_profile and universal_profile.get("name"):
                dv["user_name"] = universal_profile["name"]
            if agent_state.get("conversation_summary"):
                dv["last_call_summary"] = agent_state["conversation_summary"]
            if agent_state.get("sentiment"):
                dv["user_sentiment"] = agent_state["sentiment"]
            if agent_state.get("key_topics"):
                dv["key_topics"] = ", ".join(agent_state["key_topics"])

        # Case 2: Has name but no greeting (first call to THIS agent, but called others)
        elif universal_profile and universal_profile.get("name"):
            logger.info(f"Found universal profile for {phone_number} (first call to agent {agent_id})")

            # Only add name to dynamic variables
            # Agent uses its default first_message, but can reference {{user_name}}
            response_data["dynamic_variables"]["user_name"] = universal_profile["name"]

        # Case 3: New caller (no profile at all)
        else:
            logger.info(f"New caller {phone_number} - using agent defaults")
            # Return empty - agent uses pure default first_message

        logger.info(f"Returning client-data response: {_safe_log_response(response_data)}")
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error processing client-data webhook: {e}", exc_info=True)
        # Return empty response on error to allow conversation to proceed
        return JSONResponse(content={"dynamic_variables": {}})


def _safe_log_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """Create a safe-to-log version of the response.

    Truncates long greeting messages for cleaner logs.

    Args:
        response_data: The full response data

    Returns:
        Truncated version safe for logging
    """
    log_data = {"dynamic_variables": response_data.get("dynamic_variables", {})}

    if "conversation_config_override" in response_data:
        override = response_data["conversation_config_override"]
        if override.get("agent", {}).get("first_message"):
            first_msg = override["agent"]["first_message"]
            truncated = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
            log_data["conversation_config_override"] = {
                "agent": {"first_message": truncated}
            }

    return log_data
