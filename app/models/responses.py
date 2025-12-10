"""Response models for ElevenLabs webhook responses.

This module contains Pydantic models for webhook response payloads:
- DynamicVariables: User profile information for dynamic variable injection
- ConversationConfigOverride: Agent configuration overrides
- ClientDataResponse: Response for client-data webhook
- MemoryItem: Individual memory item from OpenMemory
- ProfileData: User profile information
- SearchDataResponse: Response for search-data webhook
- NextGreetingData: Output from OpenAI greeting generation
- UniversalUserProfile: Tier 1 universal profile shared across agents
- AgentConversationState: Tier 2 agent-specific conversation state

All models use Pydantic v2 syntax with proper validation and documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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


# =============================================================================
# Two-Tier Memory Architecture Models
# =============================================================================


class NextGreetingData(BaseModel):
    """Output from OpenAI greeting generation.

    Contains the personalized greeting and conversation context
    generated by OpenAI for the next call.
    """

    next_greeting: Optional[str] = Field(
        default=None,
        description="Personalized greeting text for next call (null for first-time callers)",
        examples=["Welcome back, Sarah! Last time we discussed your garden project."],
    )
    key_topics: List[str] = Field(
        default_factory=list,
        description="3-5 key topics discussed in the conversation",
        examples=[["garden planning", "plant selection", "soil preparation"]],
    )
    sentiment: str = Field(
        default="neutral",
        description="Caller's sentiment: satisfied, neutral, frustrated, or confused",
        examples=["satisfied", "neutral", "frustrated", "confused"],
    )
    conversation_summary: str = Field(
        default="",
        description="One-sentence summary of what was discussed",
        examples=["Discussed garden layout and selected tomato varieties for spring planting."],
    )


class UniversalUserProfile(BaseModel):
    """Tier 1: Universal user profile shared across all agents.

    This profile is accessible by all agents and contains basic
    user information that should be consistent across interactions.
    """

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = Field(
        default=None,
        description="User's name extracted from any conversation",
        examples=["Sarah"],
    )
    phone_number: str = Field(
        ...,
        description="User's phone number in E.164 format",
        examples=["+16129782029"],
    )
    first_seen: Optional[str] = Field(
        default=None,
        description="ISO timestamp of first interaction with any agent",
        examples=["2024-01-15T10:30:00Z"],
    )
    total_interactions: int = Field(
        default=0,
        ge=0,
        description="Total count of interactions across all agents",
        examples=[5],
    )


class AgentConversationState(BaseModel):
    """Tier 2: Agent-specific conversation state.

    This state is unique to each agent-user pair and contains
    the pre-generated greeting and conversation context.
    """

    model_config = ConfigDict(extra="allow")

    next_greeting: Optional[str] = Field(
        default=None,
        description="Pre-generated personalized greeting for next call",
        examples=["Welcome back, Sarah! Ready to continue planning your garden?"],
    )
    key_topics: List[str] = Field(
        default_factory=list,
        description="Key topics from the last conversation",
        examples=[["tomatoes", "raised beds", "watering schedule"]],
    )
    sentiment: str = Field(
        default="neutral",
        description="Caller's sentiment from last interaction",
        examples=["satisfied"],
    )
    conversation_summary: str = Field(
        default="",
        description="Summary of last conversation with this agent",
        examples=["Discussed tomato varieties and raised bed construction."],
    )
    last_call_date: Optional[str] = Field(
        default=None,
        description="ISO timestamp of last call with this agent",
        examples=["2024-01-20T14:45:00Z"],
    )
    conversation_count: int = Field(
        default=0,
        ge=0,
        description="Number of calls with this specific agent",
        examples=[3],
    )


class ClientDataResponseV2(BaseModel):
    """Enhanced response model for client-data webhook (v2).

    Supports the two-tier memory architecture with optional
    conversation config override and enhanced dynamic variables.
    """

    dynamic_variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Variables injected into agent prompt",
    )
    conversation_config_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override agent's first message if provided",
    )
