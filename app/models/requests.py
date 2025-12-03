"""Request models for ElevenLabs webhook payloads.

This module contains Pydantic models for validating incoming webhook requests:
- ClientDataRequest: Conversation initiation client data request
- SearchDataRequest: Server tool search data request
- PostCallWebhookRequest: Post-call webhook request with nested data models

All models use Pydantic v2 syntax with proper validation and documentation.
"""

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def validate_e164_phone_number(phone_number: str) -> str:
    """Validate phone number is in E.164 format.

    E.164 format: + followed by country code and subscriber number (max 15 digits).
    Example: +16129782029

    Args:
        phone_number: The phone number to validate.

    Returns:
        The validated phone number.

    Raises:
        ValueError: If phone number is not in valid E.164 format.
    """
    # E.164 pattern: + followed by 1-15 digits
    e164_pattern = r"^\+[1-9]\d{1,14}$"
    if not re.match(e164_pattern, phone_number):
        raise ValueError(
            f"Invalid phone number format: '{phone_number}'. "
            f"Expected E.164 format (e.g., +16129782029). "
            f"Phone number must start with + followed by country code and digits only."
        )
    return phone_number


class ClientDataRequest(BaseModel):
    """Request model for client-data webhook.

    This webhook is called by ElevenLabs when a conversation is initiated.
    It provides caller information for profile lookup and personalization.
    """

    caller_id: str = Field(
        ...,
        description="The phone number of the caller in E.164 format (e.g., +16129782029)",
        examples=["+16129782029"],
    )
    agent_id: str = Field(
        ...,
        description="The unique identifier of the ElevenLabs agent receiving the call",
        examples=["agent_8501k9r8sbb5fjbbym8c9y1jqt9b"],
    )
    called_number: str = Field(
        ...,
        description="The Twilio phone number that was called in E.164 format",
        examples=["+16123241623"],
    )
    call_sid: str = Field(
        ...,
        description="Unique identifier for the Twilio call session",
        examples=["CA98d2b6a08ebed6b78880b61ffc0e3299"],
    )

    @field_validator("caller_id", "called_number")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone numbers are in E.164 format."""
        return validate_e164_phone_number(v)


class SearchDataRequest(BaseModel):
    """Request model for search-data webhook.

    This webhook is triggered when an ElevenLabs agent invokes a server tool
    during a conversation to search for relevant information.
    """

    query: str = Field(
        ...,
        description="The search query from the ElevenLabs agent",
        examples=["What is the user's name and preferences?"],
    )
    user_id: str = Field(
        ...,
        description="The user identifier (phone number) for memory isolation",
        examples=["+16129782029"],
    )
    agent_id: str = Field(
        ...,
        description="The unique identifier of the ElevenLabs agent",
        examples=["agent_8501k9r8sbb5fjbbym8c9y1jqt9b"],
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="The unique identifier for the current conversation",
        examples=["conv_8701kb8xfaaney589jkc6pjesxrc"],
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context information for the search query",
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id_phone_format(cls, v: str) -> str:
        """Validate user_id is in E.164 format."""
        return validate_e164_phone_number(v)


# --- Nested models for PostCallWebhookRequest ---


class AgentMetadata(BaseModel):
    """Metadata about the agent for a transcript entry."""

    agent_id: str = Field(
        ...,
        description="The unique identifier of the agent",
    )
    branch_id: Optional[str] = Field(
        default=None,
        description="Branch identifier for versioned agents",
    )
    workflow_node_id: Optional[str] = Field(
        default=None,
        description="Workflow node identifier if using workflows",
    )


class ConversationTurnMetrics(BaseModel):
    """Metrics for a conversation turn."""

    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of metric names to metric data",
    )


class TranscriptEntry(BaseModel):
    """A single entry in the conversation transcript.

    Represents either an agent or user turn in the conversation.
    """

    role: Literal["agent", "user"] = Field(
        ...,
        description="The role of the speaker: 'agent' or 'user'",
    )
    message: str = Field(
        ...,
        description="The content of the message spoken",
    )
    time_in_call_secs: int = Field(
        ...,
        description="Time in seconds from the start of the call when this message occurred",
    )
    tool_calls: list[Any] = Field(
        default_factory=list,
        description="List of tool calls made during this turn",
    )
    tool_results: list[Any] = Field(
        default_factory=list,
        description="Results from tool calls",
    )
    llm_usage: Optional[dict[str, Any]] = Field(
        default=None,
        description="LLM usage statistics for this turn",
    )
    conversation_turn_metrics: Optional[ConversationTurnMetrics] = Field(
        default=None,
        description="Performance metrics for this conversation turn",
    )
    interrupted: bool = Field(
        default=False,
        description="Whether this turn was interrupted",
    )
    original_message: Optional[str] = Field(
        default=None,
        description="Original message before any modifications",
    )
    source_medium: Optional[str] = Field(
        default=None,
        description="Source medium of the message (e.g., 'audio')",
    )
    feedback: Optional[Any] = Field(
        default=None,
        description="Feedback data for this turn",
    )
    agent_metadata: Optional[AgentMetadata] = Field(
        default=None,
        description="Metadata about the agent for this turn",
    )
    multivoice_message: Optional[Any] = Field(
        default=None,
        description="Multi-voice message data if applicable",
    )
    llm_override: Optional[Any] = Field(
        default=None,
        description="LLM override configuration",
    )
    rag_retrieval_info: Optional[Any] = Field(
        default=None,
        description="RAG retrieval information",
    )


class DataCollectionJsonSchema(BaseModel):
    """JSON schema for a data collection field."""

    type: str = Field(
        ...,
        description="The data type (e.g., 'string', 'number')",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the data field",
    )
    enum: Optional[list[str]] = Field(
        default=None,
        description="Enumerated allowed values",
    )
    is_system_provided: bool = Field(
        default=False,
        description="Whether this field is system-provided",
    )
    dynamic_variable: Optional[str] = Field(
        default=None,
        description="Dynamic variable name if applicable",
    )
    constant_value: Optional[str] = Field(
        default=None,
        description="Constant value if applicable",
    )


class DataCollectionResult(BaseModel):
    """Result of data collection from the conversation.

    Contains extracted information like user name, preferences, etc.
    """

    data_collection_id: str = Field(
        ...,
        description="Unique identifier for this data collection field",
    )
    value: Optional[Any] = Field(
        default=None,
        description="The extracted value (can be null if not collected)",
    )
    json_schema: Optional[DataCollectionJsonSchema] = Field(
        default=None,
        description="Schema definition for the collected data",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Explanation of why this value was extracted",
    )


class DeletionSettings(BaseModel):
    """Settings for data deletion policies."""

    deletion_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp for scheduled deletion",
    )
    deleted_logs_at_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp when logs were deleted",
    )
    deleted_audio_at_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp when audio was deleted",
    )
    deleted_transcript_at_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp when transcript was deleted",
    )
    delete_transcript_and_pii: bool = Field(
        default=False,
        description="Whether to delete transcript and PII",
    )
    delete_audio: bool = Field(
        default=False,
        description="Whether to delete audio",
    )


class MetadataFeedback(BaseModel):
    """Feedback data from the call."""

    type: Optional[str] = Field(default=None, description="Feedback type")
    overall_score: Optional[float] = Field(default=None, description="Overall score")
    likes: int = Field(default=0, description="Number of likes")
    dislikes: int = Field(default=0, description="Number of dislikes")
    rating: Optional[float] = Field(default=None, description="Rating value")
    comment: Optional[str] = Field(default=None, description="Feedback comment")


class PhoneCallInfo(BaseModel):
    """Information about the phone call."""

    type: str = Field(
        ...,
        description="Phone provider type (e.g., 'twilio')",
    )
    stream_sid: Optional[str] = Field(
        default=None,
        description="Stream SID for the call",
    )
    call_sid: Optional[str] = Field(
        default=None,
        description="Call SID for the call",
    )


class FeatureUsageItem(BaseModel):
    """Usage status for a feature."""

    enabled: bool = Field(default=False, description="Whether the feature is enabled")
    used: bool = Field(default=False, description="Whether the feature was used")


class WorkflowFeatures(BaseModel):
    """Workflow-related feature usage."""

    enabled: bool = Field(default=False, description="Whether workflows are enabled")
    tool_node: Optional[FeatureUsageItem] = Field(default=None)
    standalone_agent_node: Optional[FeatureUsageItem] = Field(default=None)
    phone_number_node: Optional[FeatureUsageItem] = Field(default=None)
    end_node: Optional[FeatureUsageItem] = Field(default=None)


class AgentTestingFeature(BaseModel):
    """Agent testing feature status."""

    enabled: bool = Field(default=False, description="Whether agent testing is enabled")
    tests_ran_after_last_modification: bool = Field(
        default=False, description="Whether tests ran after last modification"
    )
    tests_ran_in_last_7_days: bool = Field(
        default=False, description="Whether tests ran in last 7 days"
    )


class FeaturesUsage(BaseModel):
    """Usage information for various features."""

    language_detection: Optional[FeatureUsageItem] = Field(default=None)
    transfer_to_agent: Optional[FeatureUsageItem] = Field(default=None)
    transfer_to_number: Optional[FeatureUsageItem] = Field(default=None)
    multivoice: Optional[FeatureUsageItem] = Field(default=None)
    dtmf_tones: Optional[FeatureUsageItem] = Field(default=None)
    external_mcp_servers: Optional[FeatureUsageItem] = Field(default=None)
    pii_zrm_workspace: bool = Field(default=False)
    pii_zrm_agent: bool = Field(default=False)
    tool_dynamic_variable_updates: Optional[FeatureUsageItem] = Field(default=None)
    is_livekit: bool = Field(default=False)
    voicemail_detection: Optional[FeatureUsageItem] = Field(default=None)
    workflow: Optional[WorkflowFeatures] = Field(default=None)
    agent_testing: Optional[AgentTestingFeature] = Field(default=None)


class ElevenAssistant(BaseModel):
    """Eleven Assistant status."""

    is_eleven_assistant: bool = Field(
        default=False, description="Whether this is an Eleven Assistant"
    )


class InitiationTrigger(BaseModel):
    """Call initiation trigger information."""

    trigger_type: str = Field(
        default="default", description="Type of trigger that initiated the call"
    )


class CallMetadata(BaseModel):
    """Metadata about the call."""

    start_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp when the call started",
    )
    end_time_unix_secs: Optional[int] = Field(
        default=None,
        description="Unix timestamp when the call ended",
    )
    call_duration_secs: Optional[int] = Field(
        default=None,
        description="Duration of the call in seconds",
    )
    cost: Optional[float] = Field(
        default=None,
        description="Cost of the call",
    )
    deletion_settings: Optional[DeletionSettings] = Field(
        default=None,
        description="Data deletion settings",
    )
    feedback: Optional[MetadataFeedback] = Field(
        default=None,
        description="Call feedback data",
    )
    authorization_method: Optional[str] = Field(
        default=None,
        description="Method used for authorization",
    )
    phone_call: Optional[PhoneCallInfo] = Field(
        default=None,
        description="Phone call information",
    )
    batch_call: Optional[Any] = Field(
        default=None,
        description="Batch call information if applicable",
    )
    termination_reason: Optional[str] = Field(
        default=None,
        description="Reason the call was terminated",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the call failed",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warnings during the call",
    )
    main_language: Optional[str] = Field(
        default=None,
        description="Main language of the conversation",
    )
    rag_usage: Optional[Any] = Field(
        default=None,
        description="RAG usage information",
    )
    text_only: bool = Field(
        default=False,
        description="Whether the call was text-only",
    )
    features_usage: Optional[FeaturesUsage] = Field(
        default=None,
        description="Feature usage information",
    )
    eleven_assistant: Optional[ElevenAssistant] = Field(
        default=None,
        description="Eleven Assistant status",
    )
    initiator_id: Optional[str] = Field(
        default=None,
        description="ID of the call initiator",
    )
    conversation_initiation_source: Optional[str] = Field(
        default=None,
        description="Source of conversation initiation (e.g., 'twilio')",
    )
    conversation_initiation_source_version: Optional[str] = Field(
        default=None,
        description="Version of the initiation source",
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Timezone of the conversation",
    )
    initiation_trigger: Optional[InitiationTrigger] = Field(
        default=None,
        description="Trigger that initiated the call",
    )
    async_metadata: Optional[Any] = Field(
        default=None,
        description="Async metadata if applicable",
    )
    whatsapp: Optional[Any] = Field(
        default=None,
        description="WhatsApp information if applicable",
    )
    agent_created_from: Optional[str] = Field(
        default=None,
        description="Where the agent was created from (e.g., 'ui')",
    )
    agent_last_updated_from: Optional[str] = Field(
        default=None,
        description="Where the agent was last updated from",
    )


class Analysis(BaseModel):
    """Analysis results from the conversation."""

    evaluation_criteria_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Results of evaluation criteria",
    )
    data_collection_results: dict[str, DataCollectionResult] = Field(
        default_factory=dict,
        description="Collected data from the conversation",
    )
    call_successful: Optional[str] = Field(
        default=None,
        description="Whether the call was successful",
    )
    transcript_summary: Optional[str] = Field(
        default=None,
        description="Summary of the transcript",
    )
    call_summary_title: Optional[str] = Field(
        default=None,
        description="Title for the call summary",
    )


class SourceInfo(BaseModel):
    """Source information for conversation initiation."""

    source: Optional[str] = Field(default=None, description="Source identifier")
    version: Optional[str] = Field(default=None, description="Source version")


class ConversationConfigOverrideRequest(BaseModel):
    """Conversation configuration override from the request."""

    turn: Optional[Any] = Field(default=None, description="Turn configuration")
    tts: Optional[Any] = Field(default=None, description="TTS configuration")
    conversation: Optional[Any] = Field(
        default=None, description="Conversation configuration"
    )
    agent: Optional[Any] = Field(default=None, description="Agent configuration")


class ConversationInitiationClientData(BaseModel):
    """Client data provided at conversation initiation.

    Contains dynamic variables including system-provided caller information.
    """

    conversation_config_override: Optional[ConversationConfigOverrideRequest] = Field(
        default=None,
        description="Configuration overrides for the conversation",
    )
    custom_llm_extra_body: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom LLM extra body parameters",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID if provided",
    )
    source_info: Optional[SourceInfo] = Field(
        default=None,
        description="Source information",
    )
    dynamic_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic variables including system__caller_id, system__called_number, etc.",
    )


class PostCallData(BaseModel):
    """Data payload for post-call webhooks.

    Contains the full conversation data including transcript, metadata, and analysis.
    """

    agent_id: str = Field(
        ...,
        description="The unique identifier of the agent",
    )
    conversation_id: str = Field(
        ...,
        description="The unique identifier for the conversation",
    )
    status: str = Field(
        ...,
        description="Status of the conversation (e.g., 'done')",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID if provided",
    )
    branch_id: Optional[str] = Field(
        default=None,
        description="Branch ID for versioned agents",
    )
    transcript: list[TranscriptEntry] = Field(
        default_factory=list,
        description="List of transcript entries for the conversation",
    )
    metadata: Optional[CallMetadata] = Field(
        default=None,
        description="Call metadata",
    )
    analysis: Optional[Analysis] = Field(
        default=None,
        description="Analysis results from the conversation",
    )
    conversation_initiation_client_data: Optional[ConversationInitiationClientData] = (
        Field(
            default=None,
            description="Client data from conversation initiation",
        )
    )
    has_audio: bool = Field(
        default=False,
        description="Whether audio is available for this conversation",
    )
    has_user_audio: bool = Field(
        default=False,
        description="Whether user audio is available",
    )
    has_response_audio: bool = Field(
        default=False,
        description="Whether response audio is available",
    )


class PostCallWebhookRequest(BaseModel):
    """Request model for post-call webhook.

    This webhook is called by ElevenLabs after a call completes.
    It can contain transcription, audio, or failure data.
    """

    type: Literal[
        "post_call_transcription", "post_call_audio", "call_initiation_failure"
    ] = Field(
        ...,
        description="Type of post-call webhook: 'post_call_transcription', 'post_call_audio', or 'call_initiation_failure'",
    )
    event_timestamp: int = Field(
        ...,
        description="Unix timestamp when the event occurred",
    )
    data: PostCallData = Field(
        ...,
        description="The post-call data payload",
    )
