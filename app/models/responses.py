"""Response models for ElevenLabs webhook responses.

This module contains Pydantic models for webhook response payloads:
- DynamicVariables: User profile information for dynamic variable injection
- ConversationConfigOverride: Agent configuration overrides
- ClientDataResponse: Response for client-data webhook
- MemoryItem: Individual memory item from OpenMemory
- ProfileData: User profile information
- SearchDataResponse: Response for search-data webhook

All models use Pydantic v2 syntax with proper validation and documentation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DynamicVariables(BaseModel):
    """Dynamic variables for personalized conversation.

    These variables are injected into the ElevenLabs agent's context
    to enable personalized greetings and context-aware responses.
    """

    model_config = ConfigDict(extra="allow")

    user_name: Optional[str] = Field(
        default=None,
        description="The user's name for personalized greetings",
        examples=["Stefan"],
    )
    user_profile_summary: Optional[str] = Field(
        default=None,
        description="Summary of the user's profile and preferences",
        examples=["Returning caller who previously discussed product inquiries."],
    )
    last_call_summary: Optional[str] = Field(
        default=None,
        description="Summary of the user's last conversation",
        examples=["Last call was about setting up an account on Nov 28, 2025."],
    )


class AgentConfig(BaseModel):
    """Agent configuration for conversation override.

    Contains settings that customize the agent's behavior for specific callers.
    """

    model_config = ConfigDict(populate_by_name=True)

    first_message: Optional[str] = Field(
        default=None,
        alias="firstMessage",
        description="Custom first message for the agent to use when greeting the caller",
        examples=["Welcome back, Stefan! How can I help you today?"],
    )


class ConversationConfigOverride(BaseModel):
    """Conversation configuration override for ElevenLabs.

    Allows customizing agent behavior based on caller profile.
    """

    agent: Optional[AgentConfig] = Field(
        default=None,
        description="Agent-specific configuration overrides",
    )


class ClientDataResponse(BaseModel):
    """Response model for client-data webhook.

    Returns profile information and configuration overrides to ElevenLabs
    for personalized conversation handling.
    """

    dynamic_variables: Optional[DynamicVariables] = Field(
        default=None,
        description="Dynamic variables for the conversation context",
    )
    conversation_config_override: Optional[ConversationConfigOverride] = Field(
        default=None,
        description="Configuration overrides for the conversation",
    )


class MemoryItem(BaseModel):
    """Individual memory item from OpenMemory.

    Represents a single piece of information stored about the caller.
    """

    content: str = Field(
        ...,
        description="The content of the memory",
        examples=["User mentioned they prefer email contact."],
    )
    sector: str = Field(
        ...,
        description="Memory sector classification: episodic, semantic, procedural, emotional, or reflective",
        examples=["semantic", "episodic"],
    )
    salience: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Salience/importance score from 0.0 to 1.0",
        examples=[0.8, 0.95],
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="When the memory was created",
    )


class ProfileData(BaseModel):
    """User profile data from OpenMemory.

    Contains summarized profile information about the caller.
    """

    name: Optional[str] = Field(
        default=None,
        description="The user's name",
        examples=["Stefan"],
    )
    summary: Optional[str] = Field(
        default=None,
        description="Summary of the user's profile",
        examples=["Regular caller interested in product support."],
    )
    phone_number: Optional[str] = Field(
        default=None,
        description="The user's phone number in E.164 format",
        examples=["+16129782029"],
    )


class SearchDataResponse(BaseModel):
    """Response model for search-data webhook.

    Returns profile information and relevant memories to ElevenLabs
    for context-aware conversation handling during the call.
    """

    profile: Optional[ProfileData] = Field(
        default=None,
        description="User profile information",
    )
    memories: list[MemoryItem] = Field(
        default_factory=list,
        description="List of relevant memories matching the search query",
    )
