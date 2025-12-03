"""Tests for Pydantic request and response models.

This module contains 6 focused tests for the Pydantic models:
1. Test ClientDataRequest validation with valid input
2. Test ClientDataResponse serialization with all fields
3. Test PostCallTranscriptionPayload parsing from sample JSON
4. Test SearchDataRequest validation
5. Test invalid phone number format rejection
6. Test optional field handling (null/missing values)
"""

import json
from pathlib import Path

import pytest

from app.models.requests import (
    ClientDataRequest,
    SearchDataRequest,
    PostCallWebhookRequest,
)
from app.models.responses import (
    ClientDataResponse,
    DynamicVariables,
    ConversationConfigOverride,
    AgentConfig,
    MemoryItem,
    ProfileData,
    SearchDataResponse,
)


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestPydanticModels:
    """Test suite for Pydantic request and response models."""

    def test_client_data_request_validation_with_valid_input(self) -> None:
        """Test ClientDataRequest validation with valid input."""
        # Load sample payload from fixtures
        with open(FIXTURES_DIR / "client_data_request.json") as f:
            payload = json.load(f)

        # Parse and validate the request
        request = ClientDataRequest(**payload)

        # Verify all fields are correctly parsed
        assert request.caller_id == "+16129782029"
        assert request.agent_id == "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
        assert request.called_number == "+16123241623"
        assert request.call_sid == "CA98d2b6a08ebed6b78880b61ffc0e3299"

    def test_client_data_response_serialization_with_all_fields(self) -> None:
        """Test ClientDataResponse serialization with all fields populated."""
        # Create dynamic variables
        dynamic_vars = DynamicVariables(
            user_name="Stefan",
            user_profile_summary="Returning caller who previously discussed product inquiries.",
            last_call_summary="Last call was about setting up an account on Nov 28, 2025."
        )

        # Create conversation config override
        agent_config = AgentConfig(
            first_message="Welcome back, Stefan! How can I help you today?"
        )
        config_override = ConversationConfigOverride(agent=agent_config)

        # Create the response
        response = ClientDataResponse(
            dynamic_variables=dynamic_vars,
            conversation_config_override=config_override
        )

        # Serialize to dict and verify structure
        response_dict = response.model_dump(by_alias=True)

        assert "dynamic_variables" in response_dict
        assert response_dict["dynamic_variables"]["user_name"] == "Stefan"
        assert response_dict["dynamic_variables"]["user_profile_summary"] is not None
        assert response_dict["dynamic_variables"]["last_call_summary"] is not None

        assert "conversation_config_override" in response_dict
        assert response_dict["conversation_config_override"]["agent"]["firstMessage"] == (
            "Welcome back, Stefan! How can I help you today?"
        )

    def test_post_call_transcription_payload_parsing_from_sample_json(self) -> None:
        """Test PostCallTranscriptionPayload parsing from sample JSON fixture."""
        # Load the actual ElevenLabs post-call transcription payload
        with open(FIXTURES_DIR / "post_call_transcription.json") as f:
            payload = json.load(f)

        # Parse and validate the request
        request = PostCallWebhookRequest(**payload)

        # Verify top-level fields
        assert request.type == "post_call_transcription"
        assert request.event_timestamp == 1764457176

        # Verify nested data fields
        assert request.data.agent_id == "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
        assert request.data.conversation_id == "conv_8701kb8xfaaney589jkc6pjesxrc"
        assert request.data.status == "done"

        # Verify transcript parsing
        assert len(request.data.transcript) == 3
        assert request.data.transcript[0].role == "agent"
        assert request.data.transcript[0].message == "Hello, how are you? What is your name?"
        assert request.data.transcript[1].role == "user"
        assert request.data.transcript[1].message == "Stefan."
        assert request.data.transcript[1].time_in_call_secs == 4
        assert request.data.transcript[1].source_medium == "audio"

        # Verify analysis data collection results
        assert "first_name" in request.data.analysis.data_collection_results
        first_name_result = request.data.analysis.data_collection_results["first_name"]
        assert first_name_result.data_collection_id == "first_name"
        assert first_name_result.value == "Stefan"

        # Verify conversation initiation client data
        assert request.data.conversation_initiation_client_data is not None
        dynamic_vars = request.data.conversation_initiation_client_data.dynamic_variables
        assert dynamic_vars["system__caller_id"] == "+16129782029"
        assert dynamic_vars["system__called_number"] == "+16123241623"

    def test_search_data_request_validation(self) -> None:
        """Test SearchDataRequest validation with valid input."""
        # Load sample payload from fixtures
        with open(FIXTURES_DIR / "search_data_request.json") as f:
            payload = json.load(f)

        # Parse and validate the request
        request = SearchDataRequest(**payload)

        # Verify all fields are correctly parsed
        assert request.query == "What is the user's name and preferences?"
        assert request.user_id == "+16129782029"
        assert request.agent_id == "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
        assert request.conversation_id == "conv_8701kb8xfaaney589jkc6pjesxrc"
        assert request.context is not None
        assert request.context["current_topic"] == "user inquiry"

    def test_invalid_phone_number_format_rejection(self) -> None:
        """Test that invalid phone number format is rejected."""
        # Test various invalid phone number formats
        invalid_numbers = [
            "12345",  # Too short, no country code
            "phone123",  # Contains letters
            "+1-612-978-2029",  # Contains dashes (not strict E.164)
            "1 612 978 2029",  # Contains spaces
        ]

        for invalid_number in invalid_numbers:
            with pytest.raises(ValueError) as exc_info:
                ClientDataRequest(
                    caller_id=invalid_number,
                    agent_id="agent_123",
                    called_number="+16123241623",
                    call_sid="CA123"
                )
            assert "phone number" in str(exc_info.value).lower() or "E.164" in str(exc_info.value)

    def test_optional_field_handling_null_and_missing_values(self) -> None:
        """Test optional field handling with null and missing values."""
        # Test ClientDataResponse with null/missing optional fields
        dynamic_vars = DynamicVariables(
            user_name=None,
            user_profile_summary=None,
            last_call_summary=None
        )

        response = ClientDataResponse(
            dynamic_variables=dynamic_vars,
            conversation_config_override=None
        )

        # Verify null values are handled correctly
        response_dict = response.model_dump(by_alias=True)
        assert response_dict["dynamic_variables"]["user_name"] is None
        assert response_dict["conversation_config_override"] is None

        # Test SearchDataResponse with empty memories list
        profile = ProfileData(
            name=None,
            summary=None,
            phone_number="+16129782029"
        )

        search_response = SearchDataResponse(
            profile=profile,
            memories=[]
        )

        search_dict = search_response.model_dump()
        assert search_dict["profile"]["name"] is None
        assert search_dict["memories"] == []

        # Test MemoryItem with optional fields
        memory = MemoryItem(
            content="User mentioned they prefer email contact.",
            sector="semantic",
            salience=0.8,
            timestamp=None  # Optional timestamp
        )

        memory_dict = memory.model_dump()
        assert memory_dict["timestamp"] is None
        assert memory_dict["content"] == "User mentioned they prefer email contact."
        assert memory_dict["sector"] == "semantic"
        assert memory_dict["salience"] == 0.8
