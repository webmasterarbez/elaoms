"""Pydantic models for request and response validation.

This module exports all request and response models for ElevenLabs webhooks:

Request Models:
- ClientDataRequest: Conversation initiation client data request
- SearchDataRequest: Server tool search data request
- PostCallWebhookRequest: Post-call webhook request
- TranscriptEntry: Individual transcript entry
- PostCallData: Post-call data payload
- DataCollectionResult: Collected data from conversation analysis
- ConversationInitiationClientData: Client data from conversation initiation

Response Models:
- DynamicVariables: Dynamic variables for personalization
- ConversationConfigOverride: Agent configuration overrides
- ClientDataResponse: Response for client-data webhook
- MemoryItem: Individual memory from OpenMemory
- ProfileData: User profile information
- SearchDataResponse: Response for search-data webhook
"""

from app.models.requests import (
    ClientDataRequest,
    SearchDataRequest,
    PostCallWebhookRequest,
    TranscriptEntry,
    PostCallData,
    DataCollectionResult,
    ConversationInitiationClientData,
    Analysis,
    CallMetadata,
    AgentMetadata,
    DataCollectionJsonSchema,
    validate_e164_phone_number,
)
from app.models.responses import (
    DynamicVariables,
    AgentConfig,
    ConversationConfigOverride,
    ClientDataResponse,
    MemoryItem,
    ProfileData,
    SearchDataResponse,
)

__all__ = [
    # Request models
    "ClientDataRequest",
    "SearchDataRequest",
    "PostCallWebhookRequest",
    "TranscriptEntry",
    "PostCallData",
    "DataCollectionResult",
    "ConversationInitiationClientData",
    "Analysis",
    "CallMetadata",
    "AgentMetadata",
    "DataCollectionJsonSchema",
    "validate_e164_phone_number",
    # Response models
    "DynamicVariables",
    "AgentConfig",
    "ConversationConfigOverride",
    "ClientDataResponse",
    "MemoryItem",
    "ProfileData",
    "SearchDataResponse",
]
