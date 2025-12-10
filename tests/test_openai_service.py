"""Tests for OpenAI service greeting generation."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.openai_service import (
    generate_next_greeting,
    build_transcript_string,
    _build_greeting_prompt,
    _call_openai_api,
)


class TestBuildTranscriptString:
    """Tests for build_transcript_string function."""

    def test_builds_transcript_from_entries(self):
        """Should format transcript entries as readable string."""
        entries = [
            {"role": "agent", "message": "Hello!"},
            {"role": "user", "message": "Hi there."},
            {"role": "agent", "message": "How can I help?"},
        ]
        result = build_transcript_string(entries)
        assert "Agent: Hello!" in result
        assert "User: Hi there." in result
        assert "Agent: How can I help?" in result

    def test_handles_empty_entries(self):
        """Should return empty string for empty list."""
        result = build_transcript_string([])
        assert result == ""

    def test_skips_entries_without_message(self):
        """Should skip entries with no message."""
        entries = [
            {"role": "agent", "message": "Hello!"},
            {"role": "user", "message": ""},
            {"role": "agent", "message": "Bye!"},
        ]
        result = build_transcript_string(entries)
        assert "Agent: Hello!" in result
        assert "Agent: Bye!" in result
        # Empty message should not create a line
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 2


class TestBuildGreetingPrompt:
    """Tests for _build_greeting_prompt function."""

    def test_includes_agent_profile_details(self, sample_agent_profile, sample_user_profile, sample_transcript):
        """Should include agent details in prompt."""
        prompt = _build_greeting_prompt(
            agent_profile=sample_agent_profile,
            user_profile=sample_user_profile,
            transcript=sample_transcript
        )
        assert "agent_test123" in prompt
        assert "Test Assistant" in prompt

    def test_includes_user_profile_details(self, sample_agent_profile, sample_user_profile, sample_transcript):
        """Should include user details in prompt."""
        prompt = _build_greeting_prompt(
            agent_profile=sample_agent_profile,
            user_profile=sample_user_profile,
            transcript=sample_transcript
        )
        assert "John" in prompt
        assert "5" in prompt  # total_interactions

    def test_truncates_long_transcript(self, sample_agent_profile, sample_user_profile):
        """Should truncate transcripts longer than 2000 chars."""
        long_transcript = "A" * 3000
        prompt = _build_greeting_prompt(
            agent_profile=sample_agent_profile,
            user_profile=sample_user_profile,
            transcript=long_transcript
        )
        assert "[...earlier conversation omitted...]" in prompt

    def test_handles_missing_user_name(self, sample_agent_profile, sample_transcript):
        """Should handle user profile without name."""
        user_profile = {"name": None, "phone_number": "+1234", "total_interactions": 1}
        prompt = _build_greeting_prompt(
            agent_profile=sample_agent_profile,
            user_profile=user_profile,
            transcript=sample_transcript
        )
        # When name is None, it should show "None" or similar indication in the prompt
        assert "Name: None" in prompt or "Not yet known" in prompt


class TestGenerateNextGreeting:
    """Tests for generate_next_greeting function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_api_key(self, sample_agent_profile, sample_user_profile, sample_transcript):
        """Should return None if OPENAI_API_KEY is not set."""
        with patch("app.services.openai_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = await generate_next_greeting(
                agent_profile=sample_agent_profile,
                user_profile=sample_user_profile,
                transcript=sample_transcript
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_successful_greeting_generation(self, sample_agent_profile, sample_user_profile, sample_transcript, sample_greeting_data):
        """Should return greeting data on successful API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(sample_greeting_data)
                }
            }]
        }

        with patch("app.services.openai_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client:
            mock_settings.OPENAI_API_KEY = "test_key"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.OPENAI_MAX_TOKENS = 150
            mock_settings.OPENAI_TEMPERATURE = 0.7

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await generate_next_greeting(
                agent_profile=sample_agent_profile,
                user_profile=sample_user_profile,
                transcript=sample_transcript
            )

            assert result is not None
            assert "next_greeting" in result
            assert "key_topics" in result
            assert "sentiment" in result

    @pytest.mark.asyncio
    async def test_handles_api_error_with_retry(self, sample_agent_profile, sample_user_profile, sample_transcript):
        """Should retry on API error."""
        with patch("app.services.openai_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client, \
             patch("asyncio.sleep", new_callable=AsyncMock):

            mock_settings.OPENAI_API_KEY = "test_key"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.OPENAI_MAX_TOKENS = 150
            mock_settings.OPENAI_TEMPERATURE = 0.7

            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("API Error")
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await generate_next_greeting(
                agent_profile=sample_agent_profile,
                user_profile=sample_user_profile,
                transcript=sample_transcript
            )

            # Should return None after retries exhausted
            assert result is None
            # Should have attempted 3 times
            assert mock_instance.post.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self, sample_agent_profile, sample_user_profile, sample_transcript):
        """Should handle invalid JSON in API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Not valid JSON"
                }
            }]
        }

        with patch("app.services.openai_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client:
            mock_settings.OPENAI_API_KEY = "test_key"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.OPENAI_MAX_TOKENS = 150
            mock_settings.OPENAI_TEMPERATURE = 0.7

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await generate_next_greeting(
                agent_profile=sample_agent_profile,
                user_profile=sample_user_profile,
                transcript=sample_transcript
            )

            # Should return None for invalid JSON
            assert result is None
