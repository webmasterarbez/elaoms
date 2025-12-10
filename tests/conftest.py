"""Pytest configuration and fixtures for ELAOMS tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables before importing app modules
os.environ.setdefault("ELEVENLABS_API_KEY", "test_elevenlabs_key")
os.environ.setdefault("ELEVENLABS_POST_CALL_KEY", "test_post_call_key")
os.environ.setdefault("ELEVENLABS_CLIENT_DATA_KEY", "test_client_data_key")
os.environ.setdefault("ELEVENLABS_SEARCH_DATA_KEY", "test_search_data_key")
os.environ.setdefault("OPENMEMORY_KEY", "test_openmemory_key")
os.environ.setdefault("OPENMEMORY_PORT", "8080")
os.environ.setdefault("OPENMEMORY_DB_PATH", "./test_data/openmemory.db")
os.environ.setdefault("PAYLOAD_STORAGE_PATH", "./test_payloads")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_MAX_TOKENS", "150")
os.environ.setdefault("OPENAI_TEMPERATURE", "0.7")


@pytest.fixture
def sample_agent_profile():
    """Sample agent profile for testing."""
    return {
        "agent_id": "agent_test123",
        "agent_name": "Test Assistant",
        "first_message": "Hello! How can I help you today?",
        "system_prompt": "You are a helpful assistant for customer support.",
        "cached_at": "2024-01-15T10:00:00"
    }


@pytest.fixture
def sample_user_profile():
    """Sample universal user profile for testing."""
    return {
        "name": "John",
        "phone_number": "+16125551234",
        "first_seen": "2024-01-10T09:00:00",
        "total_interactions": 5
    }


@pytest.fixture
def sample_agent_state():
    """Sample agent-specific conversation state for testing."""
    return {
        "next_greeting": "Welcome back, John! Last time we discussed your account settings.",
        "key_topics": ["account settings", "password reset", "notifications"],
        "sentiment": "satisfied",
        "conversation_summary": "Helped user reset password and update notification preferences.",
        "last_call_date": "2024-01-14T15:30:00",
        "conversation_count": 3
    }


@pytest.fixture
def sample_transcript():
    """Sample conversation transcript for testing."""
    return """Agent: Hello! How can I help you today?
User: Hi, my name is John. I need help with my account.
Agent: Of course, John! What specifically do you need help with?
User: I forgot my password and can't log in.
Agent: I can help you reset that. Let me send you a reset link.
User: That would be great, thanks!
Agent: Done! You should receive an email shortly. Is there anything else?
User: No, that's all. Thank you!
Agent: You're welcome! Have a great day!"""


@pytest.fixture
def sample_greeting_data():
    """Sample OpenAI greeting generation output."""
    return {
        "next_greeting": "Welcome back, John! Ready to continue with your account setup?",
        "key_topics": ["password reset", "account access", "email verification"],
        "sentiment": "satisfied",
        "conversation_summary": "User needed help resetting their password after being locked out."
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing HTTP calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_client.return_value.__aexit__.return_value = None
        yield mock_instance


@pytest.fixture
def sample_client_data_request():
    """Sample client-data webhook request."""
    return {
        "caller_id": "+16125551234",
        "agent_id": "agent_test123",
        "called_number": "+16125559999",
        "call_sid": "CA123456789"
    }


@pytest.fixture
def sample_post_call_payload():
    """Sample post-call webhook payload."""
    return {
        "type": "post_call_transcription",
        "event_timestamp": 1705326000,
        "data": {
            "agent_id": "agent_test123",
            "conversation_id": "conv_test456",
            "status": "done",
            "transcript": [
                {
                    "role": "agent",
                    "message": "Hello! How can I help you today?",
                    "time_in_call_secs": 0,
                    "tool_calls": [],
                    "tool_results": [],
                    "interrupted": False
                },
                {
                    "role": "user",
                    "message": "Hi, my name is Sarah. I have a question about my order.",
                    "time_in_call_secs": 3,
                    "tool_calls": [],
                    "tool_results": [],
                    "interrupted": False
                }
            ],
            "metadata": {
                "call_duration_secs": 120
            },
            "analysis": {
                "data_collection_results": {
                    "first_name": {
                        "data_collection_id": "first_name",
                        "value": "Sarah"
                    }
                }
            },
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "system__caller_id": "+16125551234",
                    "system__time_utc": "2024-01-15T10:00:00Z"
                }
            }
        }
    }
