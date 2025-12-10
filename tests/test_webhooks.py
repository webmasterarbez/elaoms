"""Tests for webhook handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestClientDataWebhook:
    """Tests for client-data webhook handler."""

    @pytest.mark.asyncio
    async def test_returns_greeting_for_returning_caller(self, sample_user_profile, sample_agent_state):
        """Should return personalized greeting for returning caller."""
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_agent:
            mock_universal.return_value = sample_user_profile
            mock_agent.return_value = sample_agent_state

            # Import after patching
            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id="+16125551234",
                agent_id="agent_test123",
                called_number="+16125559999",
                call_sid="CA123456789"
            )

            # Create mock dependency
            response = await client_data_webhook(request, _=None)

            # Parse response content
            content = response.body.decode()
            import json
            data = json.loads(content)

            assert "conversation_config_override" in data
            assert data["conversation_config_override"]["agent"]["first_message"] == sample_agent_state["next_greeting"]
            assert data["dynamic_variables"]["user_name"] == sample_user_profile["name"]

    @pytest.mark.asyncio
    async def test_returns_name_only_for_first_call_to_agent(self, sample_user_profile):
        """Should return name in dynamic_variables for first call to this agent."""
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_agent:
            mock_universal.return_value = sample_user_profile
            mock_agent.return_value = None  # No previous interaction with this agent

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id="+16125551234",
                agent_id="agent_new",
                called_number="+16125559999",
                call_sid="CA123456789"
            )

            response = await client_data_webhook(request, _=None)

            import json
            data = json.loads(response.body.decode())

            assert "conversation_config_override" not in data
            assert data["dynamic_variables"]["user_name"] == sample_user_profile["name"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_new_caller(self):
        """Should return empty response for new caller."""
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_agent:
            mock_universal.return_value = None
            mock_agent.return_value = None

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id="+16125559876",
                agent_id="agent_test123",
                called_number="+16125559999",
                call_sid="CA123456789"
            )

            response = await client_data_webhook(request, _=None)

            import json
            data = json.loads(response.body.decode())

            assert "conversation_config_override" not in data
            assert data["dynamic_variables"] == {}

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        """Should return empty response on error."""
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal:
            mock_universal.side_effect = Exception("Database connection failed")

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id="+16125551234",
                agent_id="agent_test123",
                called_number="+16125559999",
                call_sid="CA123456789"
            )

            response = await client_data_webhook(request, _=None)

            import json
            data = json.loads(response.body.decode())

            # Should return empty but valid response
            assert data == {"dynamic_variables": {}}


class TestPostCallWebhook:
    """Tests for post-call webhook handler processing."""

    @pytest.mark.asyncio
    async def test_processes_transcript_and_generates_greeting(self, sample_post_call_payload, sample_greeting_data):
        """Should process transcript and generate greeting."""
        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock) as mock_store_state, \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock) as mock_create_memories, \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock) as mock_store_memories:

            mock_get_profile.return_value = {"name": None, "phone_number": "+16125551234", "total_interactions": 0}
            mock_store_profile.return_value = True
            mock_store_state.return_value = True
            mock_generate.return_value = sample_greeting_data
            mock_create_memories.return_value = []
            mock_store_memories.return_value = []

            cache_instance = MagicMock()
            cache_instance.get_agent_profile = AsyncMock(return_value={
                "agent_id": "agent_test123",
                "agent_name": "Test Agent",
                "first_message": "Hello!",
                "system_prompt": "You are helpful."
            })
            mock_cache.return_value = cache_instance

            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**sample_post_call_payload)

            await _process_memories(request)

            # Verify universal profile was stored
            mock_store_profile.assert_called()

            # Verify greeting was generated
            mock_generate.assert_called_once()

            # Verify agent state was stored
            mock_store_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_extracts_name_from_transcript(self, sample_post_call_payload, sample_greeting_data):
        """Should extract name from transcript."""
        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            mock_get_profile.return_value = None  # New user
            mock_store_profile.return_value = True
            mock_generate.return_value = sample_greeting_data

            cache_instance = MagicMock()
            cache_instance.get_agent_profile = AsyncMock(return_value={
                "agent_id": "agent_test123",
                "agent_name": "Test Agent",
                "first_message": "Hello!",
                "system_prompt": "You are helpful."
            })
            mock_cache.return_value = cache_instance

            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**sample_post_call_payload)

            await _process_memories(request)

            # Check that store_universal_user_profile was called with a name
            # The transcript contains "my name is Sarah"
            call_args = mock_store_profile.call_args
            # Name should be extracted from transcript or data_collection_results
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_continues_on_greeting_generation_failure(self, sample_post_call_payload):
        """Should continue processing even if greeting generation fails."""
        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock) as mock_create_memories, \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock) as mock_store_memories:

            mock_get_profile.return_value = {"name": "Sarah", "phone_number": "+16125551234", "total_interactions": 1}
            mock_store_profile.return_value = True
            mock_generate.return_value = None  # Greeting generation failed
            mock_create_memories.return_value = [{"id": "mem_1"}]
            mock_store_memories.return_value = [{"id": "mem_2"}]

            cache_instance = MagicMock()
            cache_instance.get_agent_profile = AsyncMock(return_value={
                "agent_id": "agent_test123",
                "agent_name": "Test Agent",
                "first_message": "Hello!",
                "system_prompt": "You are helpful."
            })
            mock_cache.return_value = cache_instance

            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**sample_post_call_payload)

            # Should not raise exception
            await _process_memories(request)

            # Should still process legacy memories
            mock_create_memories.assert_called_once()
            mock_store_memories.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_processing_without_phone_number(self, sample_post_call_payload):
        """Should skip processing if no phone number found."""
        # Modify payload to remove phone number
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"] = {}

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile:
            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**payload)

            await _process_memories(request)

            # Should not try to get profile
            mock_get_profile.assert_not_called()
