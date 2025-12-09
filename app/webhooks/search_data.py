"""Search data webhook handler for mid-conversation memory retrieval.

This module handles the POST /webhook/search-data endpoint:
- No HMAC authentication required
- Parses SearchDataRequest from request body
- Extracts search query and user context
- Queries OpenMemory using om.query() with search query and userId
- Returns SearchDataResponse with profile and memories array
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models.requests import SearchDataRequest
from app.models.responses import (
    SearchDataResponse,
    ProfileData,
    MemoryItem,
)
from app.memory.extraction import search_memories

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search-data",
    response_model=SearchDataResponse,
    summary="Handle mid-conversation memory search",
    description=(
        "Webhook triggered when ElevenLabs agent invokes a server tool during "
        "conversation. Returns relevant memories and profile data for the caller."
    ),
)
async def search_data_webhook(request: SearchDataRequest) -> SearchDataResponse:
    """Handle search-data webhook for memory retrieval.

    This endpoint:
    1. Extracts the search query and user_id from the request
    2. Queries OpenMemory for relevant memories
    3. Returns profile data and matching memories

    Args:
        request: SearchDataRequest with query, user_id, agent_id, etc.

    Returns:
        SearchDataResponse with profile and memories array
    """
    query = request.query
    phone_number = request.user_id

    logger.info(f"Search-data webhook called for user {phone_number} with query: {query[:50]}...")

    try:
        # Query OpenMemory for relevant memories
        search_result = await search_memories(
            query=query,
            phone_number=phone_number,
        )

        # Build profile from search results
        profile = None
        profile_data = search_result.get("profile")
        if profile_data:
            profile = ProfileData(
                name=profile_data.get("name"),
                summary=profile_data.get("summary"),
                phone_number=profile_data.get("phone_number"),
            )

        # Build memory items from search results
        memories = []
        for memory in search_result.get("memories", []):
            memory_item = MemoryItem(
                content=memory.get("content", ""),
                sector=memory.get("sector", "semantic"),
                salience=memory.get("salience", 0.5),
                timestamp=None,  # Timestamp not always available from search
            )
            memories.append(memory_item)

        response = SearchDataResponse(
            profile=profile,
            memories=memories,
        )

        logger.info(f"Returning {len(memories)} memories for user {phone_number}")
        return response

    except Exception as e:
        logger.error(f"Error processing search-data webhook: {e}")
        # Return empty response on error
        return SearchDataResponse(
            profile=None,
            memories=[],
        )