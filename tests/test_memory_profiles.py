"""Tests for two-tier memory profile management."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.memory.profiles import (
    get_universal_user_profile,
    store_universal_user_profile,
    get_agent_conversation_state,
    store_agent_conversation_state,
    extract_name_from_transcript,
)


class TestExtractNameFromTranscript:
    """Tests for extract_name_from_transcript function."""

    def test_extracts_name_from_my_name_is(self):
        """Should extract name from 'my name is' pattern."""
        transcript = "User: Hi, my name is John. I need help."
        result = extract_name_from_transcript(transcript)
        assert result == "John"

    def test_extracts_name_from_im_pattern(self):
        """Should extract name from 'I'm' pattern with punctuation."""
        transcript = "User: Hi, I'm Sarah. How are you?"
        result = extract_name_from_transcript(transcript)
        assert result == "Sarah"

    def test_extracts_name_from_call_me(self):
        """Should extract name from 'call me' pattern."""
        transcript = "User: Please call me Mike, I prefer that."
        result = extract_name_from_transcript(transcript)
        assert result == "Mike"

    def test_extracts_name_from_this_is(self):
        """Should extract name from 'this is' pattern."""
        transcript = "User: Hello, this is David. I'm calling about..."
        result = extract_name_from_transcript(transcript)
        assert result == "David"

    def test_ignores_common_words(self):
        """Should not extract common words as names."""
        transcript = "User: I'm just calling to check on my order."
        result = extract_name_from_transcript(transcript)
        assert result is None

    def test_returns_none_for_no_name(self):
        """Should return None when no name pattern found."""
        transcript = "User: Hello, I have a question about billing."
        result = extract_name_from_transcript(transcript)
        assert result is None

    def test_handles_empty_transcript(self):
        """Should handle empty transcript."""
        result = extract_name_from_transcript("")
        assert result is None

    def test_capitalizes_extracted_name(self):
        """Should capitalize the extracted name."""
        transcript = "User: my name is jennifer."
        result = extract_name_from_transcript(transcript)
        assert result == "Jennifer"


class TestGetUniversalUserProfile:
    """Tests for get_universal_user_profile function."""

    @pytest.mark.asyncio
    async def test_returns_none_for_new_user(self):
        """Should return None for user with no profile."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await get_universal_user_profile("+16125551234")

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_profile_for_existing_user(self, sample_user_profile):
        """Should return profile for existing user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {"metadata": {"field": "name", "value": "John"}},
                {"metadata": {"field": "first_seen", "value": "2024-01-10T09:00:00"}},
                {"metadata": {"field": "total_interactions", "value": "5"}}
            ]
        }

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await get_universal_user_profile("+16125551234")

            assert result is not None
            assert result["name"] == "John"
            assert result["total_interactions"] == 5

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        """Should return None on API error."""
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("Connection failed")
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await get_universal_user_profile("+16125551234")

            assert result is None


class TestStoreUniversalUserProfile:
    """Tests for store_universal_user_profile function."""

    @pytest.mark.asyncio
    async def test_stores_new_profile(self):
        """Should store new profile successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "memory_123"}

        # Mock get_universal_user_profile to return None (new user)
        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings, \
             patch("app.memory.profiles.get_universal_user_profile", new_callable=AsyncMock) as mock_get:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"
            mock_get.return_value = None

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await store_universal_user_profile("+16125551234", name="John")

            assert result is True
            # Should have made POST calls for each field
            assert mock_instance.post.call_count >= 2

    @pytest.mark.asyncio
    async def test_increments_interactions(self, sample_user_profile):
        """Should increment interaction count for existing user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "memory_123"}

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings, \
             patch("app.memory.profiles.get_universal_user_profile", new_callable=AsyncMock) as mock_get:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"
            mock_get.return_value = sample_user_profile

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await store_universal_user_profile(
                "+16125551234",
                name=None,
                increment_interactions=True
            )

            assert result is True


class TestGetAgentConversationState:
    """Tests for get_agent_conversation_state function."""

    @pytest.mark.asyncio
    async def test_returns_none_for_new_agent_relationship(self):
        """Should return None for first call to this agent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await get_agent_conversation_state("+16125551234", "agent_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_state_for_returning_caller(self, sample_agent_state):
        """Should return state for returning caller."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {
                    "metadata": {
                        "next_greeting": sample_agent_state["next_greeting"],
                        "key_topics": sample_agent_state["key_topics"],
                        "sentiment": sample_agent_state["sentiment"],
                        "conversation_summary": sample_agent_state["conversation_summary"],
                        "last_call_date": sample_agent_state["last_call_date"],
                        "conversation_count": sample_agent_state["conversation_count"]
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await get_agent_conversation_state("+16125551234", "agent_123")

            assert result is not None
            assert result["next_greeting"] == sample_agent_state["next_greeting"]
            assert result["sentiment"] == "satisfied"


class TestStoreAgentConversationState:
    """Tests for store_agent_conversation_state function."""

    @pytest.mark.asyncio
    async def test_stores_greeting_data(self, sample_greeting_data):
        """Should store greeting data successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "memory_456"}

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings, \
             patch("app.memory.profiles.get_agent_conversation_state", new_callable=AsyncMock) as mock_get:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"
            mock_get.return_value = None

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await store_agent_conversation_state(
                phone_number="+16125551234",
                agent_id="agent_123",
                greeting_data=sample_greeting_data
            )

            assert result is True
            mock_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_increments_conversation_count(self, sample_greeting_data, sample_agent_state):
        """Should increment conversation count for existing relationship."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "memory_456"}

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.memory.profiles.settings") as mock_settings, \
             patch("app.memory.profiles.get_agent_conversation_state", new_callable=AsyncMock) as mock_get:
            mock_settings.openmemory_url = "http://localhost:8080"
            mock_settings.OPENMEMORY_KEY = "test_key"
            mock_get.return_value = sample_agent_state

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await store_agent_conversation_state(
                phone_number="+16125551234",
                agent_id="agent_123",
                greeting_data=sample_greeting_data
            )

            assert result is True
            # Check that conversation_count was incremented
            call_args = mock_instance.post.call_args
            payload = call_args[1]["json"]
            assert payload["metadata"]["conversation_count"] == 4  # 3 + 1
