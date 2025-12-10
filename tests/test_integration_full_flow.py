"""Integration tests for full two-tier memory flow.

These tests verify end-to-end scenarios across client-data and post-call webhooks,
ensuring the two-tier memory architecture works correctly for:
- First-time callers
- Returning callers to same agent
- Multi-agent scenarios
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFirstTimeCallerFlow:
    """Test complete flow for a first-time caller."""

    @pytest.mark.asyncio
    async def test_first_call_returns_empty_then_creates_profile(
        self,
        sample_post_call_payload,
        sample_greeting_data
    ):
        """
        Scenario: Brand new caller makes their first call

        Expected flow:
        1. Client-data: Returns empty (no profile, no agent state)
        2. Call happens with agent's default greeting
        3. Post-call: Creates Tier 1 profile + Tier 2 agent state
        """
        phone_number = "+16125559999"  # New number
        agent_id = "agent_test123"

        # --- Step 1: Client-data webhook (call initiation) ---
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_get_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_get_agent:

            # Simulate no existing data
            mock_get_universal.return_value = None
            mock_get_agent.return_value = None

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id=phone_number,
                agent_id=agent_id,
                called_number="+16125550000",
                call_sid="CA_new_caller"
            )

            response = await client_data_webhook(request, _=None)
            data = json.loads(response.body.decode())

            # Should return empty - agent uses defaults
            assert data["dynamic_variables"] == {}
            assert "conversation_config_override" not in data

        # --- Step 2: Post-call webhook (after call ends) ---
        # Modify payload to use our test phone number
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"]["system__caller_id"] = phone_number

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock) as mock_store_state, \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            # First call returns None (new user), second call returns the created profile
            mock_get_profile.side_effect = [None, {"name": "Sarah", "phone_number": phone_number, "total_interactions": 1}]
            mock_store_profile.return_value = True
            mock_store_state.return_value = True
            mock_generate.return_value = sample_greeting_data

            cache_instance = MagicMock()
            cache_instance.get_agent_profile = AsyncMock(return_value={
                "agent_id": agent_id,
                "agent_name": "Test Agent",
                "first_message": "Hello!",
                "system_prompt": "You are helpful."
            })
            mock_cache.return_value = cache_instance

            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**payload)
            await _process_memories(request)

            # Verify Tier 1 profile was stored
            mock_store_profile.assert_called()
            call_args = mock_store_profile.call_args
            assert call_args[1]["phone_number"] == phone_number

            # Verify Tier 2 agent state was stored
            mock_store_state.assert_called_once()
            state_call_args = mock_store_state.call_args
            assert state_call_args[1]["phone_number"] == phone_number
            assert state_call_args[1]["agent_id"] == agent_id


class TestReturningCallerSameAgentFlow:
    """Test complete flow for a returning caller to the same agent."""

    @pytest.mark.asyncio
    async def test_second_call_gets_personalized_greeting(
        self,
        sample_user_profile,
        sample_agent_state,
        sample_post_call_payload,
        sample_greeting_data
    ):
        """
        Scenario: Caller who has called this agent before calls again

        Expected flow:
        1. Client-data: Returns Tier 2 greeting + Tier 1 name
        2. Call uses personalized greeting
        3. Post-call: Updates both tiers with new data
        """
        phone_number = sample_user_profile["phone_number"]
        agent_id = "agent_test123"

        # --- Step 1: Client-data webhook ---
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_get_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_get_agent:

            mock_get_universal.return_value = sample_user_profile
            mock_get_agent.return_value = sample_agent_state

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id=phone_number,
                agent_id=agent_id,
                called_number="+16125550000",
                call_sid="CA_returning"
            )

            response = await client_data_webhook(request, _=None)
            data = json.loads(response.body.decode())

            # Should have personalized greeting from Tier 2
            assert "conversation_config_override" in data
            assert data["conversation_config_override"]["agent"]["first_message"] == sample_agent_state["next_greeting"]

            # Should have name and context in dynamic variables
            assert data["dynamic_variables"]["user_name"] == sample_user_profile["name"]
            assert "last_call_summary" in data["dynamic_variables"]
            assert "user_sentiment" in data["dynamic_variables"]

        # --- Step 2: Post-call webhook ---
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"]["system__caller_id"] = phone_number

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock) as mock_store_state, \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            # Existing profile with name
            mock_get_profile.return_value = sample_user_profile
            mock_store_profile.return_value = True
            mock_store_state.return_value = True

            # Generate new greeting for next call
            new_greeting = {
                "next_greeting": "Hi John! Ready to continue where we left off about your account?",
                "key_topics": ["account setup", "billing questions"],
                "sentiment": "satisfied",
                "conversation_summary": "Continued account setup discussion."
            }
            mock_generate.return_value = new_greeting

            cache_instance = MagicMock()
            cache_instance.get_agent_profile = AsyncMock(return_value={
                "agent_id": agent_id,
                "agent_name": "Test Agent",
                "first_message": "Hello!",
                "system_prompt": "You are helpful."
            })
            mock_cache.return_value = cache_instance

            from app.webhooks.post_call import _process_memories
            from app.models.requests import PostCallWebhookRequest

            request = PostCallWebhookRequest(**payload)
            await _process_memories(request)

            # Profile should be updated (increment interactions)
            mock_store_profile.assert_called()

            # New agent state should be stored
            mock_store_state.assert_called_once()
            state_call_args = mock_store_state.call_args
            assert state_call_args[1]["greeting_data"] == new_greeting


class TestMultiAgentFlow:
    """Test complete flow for a caller using multiple agents."""

    @pytest.mark.asyncio
    async def test_caller_recognized_by_second_agent_but_no_greeting(
        self,
        sample_user_profile
    ):
        """
        Scenario: Caller calls Agent A first, then Agent B

        Expected for Agent B:
        - Knows caller's name from Tier 1 (shared)
        - Has no Tier 2 state (first call to this agent)
        - Uses default greeting but can reference {{user_name}}
        """
        phone_number = sample_user_profile["phone_number"]
        agent_a_id = "agent_margaret"
        agent_b_id = "agent_sarah"

        # --- Call to Agent B (after having called Agent A) ---
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_get_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_get_agent:

            # Tier 1 exists (from Agent A call)
            mock_get_universal.return_value = sample_user_profile
            # Tier 2 does NOT exist for Agent B
            mock_get_agent.return_value = None

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id=phone_number,
                agent_id=agent_b_id,
                called_number="+16125550000",
                call_sid="CA_multi_agent"
            )

            response = await client_data_webhook(request, _=None)
            data = json.loads(response.body.decode())

            # Should have name (from Tier 1) but NO greeting override
            assert data["dynamic_variables"]["user_name"] == sample_user_profile["name"]
            assert "conversation_config_override" not in data

    @pytest.mark.asyncio
    async def test_both_agents_have_independent_greetings(
        self,
        sample_user_profile
    ):
        """
        Scenario: Caller has called both agents before

        Expected:
        - Each agent has its own Tier 2 state
        - Agent A's greeting references Agent A topics
        - Agent B's greeting references Agent B topics
        """
        phone_number = sample_user_profile["phone_number"]

        # Agent A's state (memoir topics)
        agent_a_state = {
            "next_greeting": "Hi John! Ready to continue your founding story?",
            "key_topics": ["founding story", "childhood memories"],
            "sentiment": "engaged",
            "conversation_summary": "Explored early life experiences.",
            "last_call_date": "2024-01-14T10:00:00Z",
            "conversation_count": 3
        }

        # Agent B's state (health topics)
        agent_b_state = {
            "next_greeting": "Welcome back John! How's your medication working?",
            "key_topics": ["medication review", "blood pressure"],
            "sentiment": "satisfied",
            "conversation_summary": "Discussed medication effectiveness.",
            "last_call_date": "2024-01-15T14:00:00Z",
            "conversation_count": 2
        }

        # --- Test Agent A ---
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_agent:

            mock_universal.return_value = sample_user_profile
            mock_agent.return_value = agent_a_state

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id=phone_number,
                agent_id="agent_margaret",
                called_number="+16125550000",
                call_sid="CA_agent_a"
            )

            response = await client_data_webhook(request, _=None)
            data_a = json.loads(response.body.decode())

            assert "founding story" in data_a["conversation_config_override"]["agent"]["first_message"]

        # --- Test Agent B ---
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal, \
             patch("app.webhooks.client_data.get_agent_conversation_state", new_callable=AsyncMock) as mock_agent:

            mock_universal.return_value = sample_user_profile
            mock_agent.return_value = agent_b_state

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id=phone_number,
                agent_id="agent_sarah",
                called_number="+16125550000",
                call_sid="CA_agent_b"
            )

            response = await client_data_webhook(request, _=None)
            data_b = json.loads(response.body.decode())

            assert "medication" in data_b["conversation_config_override"]["agent"]["first_message"]

        # Verify greetings are different (agent-specific)
        assert data_a["conversation_config_override"]["agent"]["first_message"] != \
               data_b["conversation_config_override"]["agent"]["first_message"]


class TestErrorHandlingFlow:
    """Test graceful degradation in error scenarios."""

    @pytest.mark.asyncio
    async def test_openai_failure_still_creates_profile(
        self,
        sample_post_call_payload
    ):
        """
        Scenario: OpenAI is unavailable during post-call

        Expected:
        - Tier 1 profile still created
        - Tier 2 state NOT created (no greeting)
        - No exception raised
        """
        phone_number = "+16125557777"
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"]["system__caller_id"] = phone_number

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock) as mock_store_state, \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            mock_get_profile.side_effect = [None, {"name": "Test", "phone_number": phone_number, "total_interactions": 1}]
            mock_store_profile.return_value = True
            mock_generate.return_value = None  # OpenAI failed

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

            request = PostCallWebhookRequest(**payload)

            # Should not raise exception
            await _process_memories(request)

            # Profile should still be stored
            mock_store_profile.assert_called()

            # Agent state should NOT be stored (no greeting data)
            mock_store_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier1_failure_still_returns_response(self):
        """
        Scenario: OpenMemory is unavailable during client-data

        Expected:
        - Return empty response (graceful degradation)
        - No exception raised
        - Agent uses default greeting
        """
        with patch("app.webhooks.client_data.get_universal_user_profile", new_callable=AsyncMock) as mock_universal:
            mock_universal.side_effect = Exception("OpenMemory connection failed")

            from app.webhooks.client_data import client_data_webhook
            from app.models.requests import ClientDataRequest

            request = ClientDataRequest(
                caller_id="+16125558888",
                agent_id="agent_test",
                called_number="+16125550000",
                call_sid="CA_error_test"
            )

            # Should not raise exception
            response = await client_data_webhook(request, _=None)
            data = json.loads(response.body.decode())

            # Should return valid empty response
            assert data == {"dynamic_variables": {}}


class TestNameExtractionFlow:
    """Test name extraction across the flow."""

    @pytest.mark.asyncio
    async def test_name_extracted_from_transcript_on_first_call(
        self,
        sample_post_call_payload,
        sample_greeting_data
    ):
        """
        Scenario: First-time caller mentions their name in transcript

        Expected:
        - Name extracted and stored in Tier 1
        - Name available for greeting generation
        """
        phone_number = "+16125556666"
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"]["system__caller_id"] = phone_number
        # Transcript contains "my name is Sarah"

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            # New user - no profile
            mock_get_profile.side_effect = [None, {"name": "Sarah", "phone_number": phone_number, "total_interactions": 1}]
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

            request = PostCallWebhookRequest(**payload)
            await _process_memories(request)

            # Verify store was called with extracted name
            store_calls = mock_store_profile.call_args_list
            # At least one call should have a name
            names_passed = [call[1].get("name") for call in store_calls if call[1].get("name")]
            assert len(names_passed) > 0 or any(
                "Sarah" in str(call) for call in store_calls
            )

    @pytest.mark.asyncio
    async def test_existing_name_not_overwritten(
        self,
        sample_user_profile,
        sample_post_call_payload,
        sample_greeting_data
    ):
        """
        Scenario: Returning caller with existing name mentions a different name

        Expected:
        - Original name preserved (not overwritten)
        """
        phone_number = sample_user_profile["phone_number"]
        payload = sample_post_call_payload.copy()
        payload["data"]["conversation_initiation_client_data"]["dynamic_variables"]["system__caller_id"] = phone_number

        with patch("app.webhooks.post_call.get_universal_user_profile", new_callable=AsyncMock) as mock_get_profile, \
             patch("app.webhooks.post_call.store_universal_user_profile", new_callable=AsyncMock) as mock_store_profile, \
             patch("app.webhooks.post_call.store_agent_conversation_state", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.generate_next_greeting", new_callable=AsyncMock) as mock_generate, \
             patch("app.webhooks.post_call.get_agent_profile_cache") as mock_cache, \
             patch("app.webhooks.post_call.create_profile_memories", new_callable=AsyncMock), \
             patch("app.webhooks.post_call.store_conversation_memories", new_callable=AsyncMock):

            # Existing profile with name "John"
            mock_get_profile.return_value = sample_user_profile
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

            request = PostCallWebhookRequest(**payload)
            await _process_memories(request)

            # The name should NOT be passed to store (it already exists)
            store_call = mock_store_profile.call_args
            assert store_call[1].get("name") is None
