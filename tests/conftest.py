"""Shared test fixtures for ElevenLabs OpenMemory Integration.

This module provides common test fixtures for use across all test modules:
- Mock OpenMemory client fixture
- Sample request payload fixtures
- Test client fixture for FastAPI
- Environment variable fixtures
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Path to test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============================================================================
# Environment Variable Fixtures
# ============================================================================


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide a complete set of mock environment variables.

    Returns:
        Dictionary of all required environment variables with test values.
    """
    return {
        "ELEVENLABS_API_KEY": "test_elevenlabs_api_key",
        "ELEVENLABS_POST_CALL_KEY": "test_post_call_secret_key",
        "ELEVENLABS_CLIENT_DATA_KEY": "test_client_data_key",
        "ELEVENLABS_SEARCH_DATA_KEY": "test_search_data_key",
        "OPENMEMORY_KEY": "test_openmemory_key",
        "OPENMEMORY_PORT": "8080",
        "OPENMEMORY_DB_PATH": "/tmp/test_openmemory.db",
        "PAYLOAD_STORAGE_PATH": "/tmp/test_payloads",
    }


@pytest.fixture
def temp_storage_dir() -> Generator[str, None, None]:
    """Create a temporary directory for payload storage.

    Yields:
        Path to the temporary directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_settings(temp_storage_dir: str) -> MagicMock:
    """Create mock settings object with all required configuration.

    Args:
        temp_storage_dir: Temporary directory for payload storage.

    Returns:
        MagicMock object simulating the settings module.
    """
    mock = MagicMock()
    mock.ELEVENLABS_API_KEY = "test_api_key"
    mock.ELEVENLABS_POST_CALL_KEY = "test_post_call_secret"
    mock.ELEVENLABS_CLIENT_DATA_KEY = "test_client_data_key"
    mock.ELEVENLABS_SEARCH_DATA_KEY = "test_search_data_key"
    mock.OPENMEMORY_KEY = "test_openmemory_key"
    mock.OPENMEMORY_PORT = "8080"
    mock.OPENMEMORY_DB_PATH = "/tmp/test_db"
    mock.PAYLOAD_STORAGE_PATH = temp_storage_dir
    mock.openmemory_url = "http://localhost:8080"
    return mock


# ============================================================================
# Mock OpenMemory Client Fixture
# ============================================================================


@pytest.fixture
def mock_openmemory_client() -> MagicMock:
    """Create a mock OpenMemory client with default responses.

    Returns:
        MagicMock object simulating the OpenMemory client.
    """
    client = MagicMock()

    # Default add response
    client.add.return_value = {
        "id": "mem_test_123",
        "primarySector": "episodic",
        "sectors": ["episodic"]
    }

    # Default query response
    client.query.return_value = {
        "results": [
            {
                "id": "mem_1",
                "content": "User's name is Stefan",
                "sector": "semantic",
                "salience": 0.9,
                "score": 0.95,
                "metadata": {"field": "first_name", "value": "Stefan"}
            }
        ]
    }

    # Default close behavior
    client.close.return_value = None

    return client


@pytest.fixture
def mock_openmemory_client_empty() -> MagicMock:
    """Create a mock OpenMemory client that returns empty results.

    Returns:
        MagicMock object simulating an empty OpenMemory response (new user).
    """
    client = MagicMock()
    client.add.return_value = {
        "id": "mem_test_new",
        "primarySector": "episodic",
        "sectors": ["episodic"]
    }
    client.query.return_value = {"results": []}
    client.close.return_value = None
    return client


@pytest.fixture
def mock_openmemory_client_error() -> MagicMock:
    """Create a mock OpenMemory client that raises errors.

    Returns:
        MagicMock object that simulates connection errors.
    """
    client = MagicMock()
    client.add.side_effect = Exception("OpenMemory connection failed")
    client.query.side_effect = Exception("OpenMemory connection failed")
    client.close.return_value = None
    return client


# ============================================================================
# Sample Request Payload Fixtures
# ============================================================================


@pytest.fixture
def client_data_payload() -> dict[str, Any]:
    """Load sample client-data request payload.

    Returns:
        Dictionary containing a valid client-data request payload.
    """
    fixture_path = FIXTURES_DIR / "client_data_request.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {
        "caller_id": "+16129782029",
        "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
        "called_number": "+16123241623",
        "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
    }


@pytest.fixture
def search_data_payload() -> dict[str, Any]:
    """Load sample search-data request payload.

    Returns:
        Dictionary containing a valid search-data request payload.
    """
    fixture_path = FIXTURES_DIR / "search_data_request.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {
        "query": "What is the user's name and preferences?",
        "user_id": "+16129782029",
        "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
        "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
        "context": {"current_topic": "user inquiry"}
    }


@pytest.fixture
def post_call_transcription_payload() -> dict[str, Any]:
    """Load sample post-call transcription payload.

    Returns:
        Dictionary containing a valid post-call transcription payload.
    """
    fixture_path = FIXTURES_DIR / "post_call_transcription.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {
        "type": "post_call_transcription",
        "event_timestamp": 1764457176,
        "data": {
            "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
            "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
            "status": "done",
            "transcript": [
                {"role": "agent", "message": "Hello, what is your name?", "time_in_call_secs": 0},
                {"role": "user", "message": "Stefan.", "time_in_call_secs": 4}
            ],
            "analysis": {
                "data_collection_results": {
                    "first_name": {
                        "data_collection_id": "first_name",
                        "value": "Stefan"
                    }
                }
            },
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "system__caller_id": "+16129782029"
                }
            }
        }
    }


@pytest.fixture
def post_call_audio_payload() -> dict[str, Any]:
    """Generate sample post-call audio payload with base64 encoded data.

    Returns:
        Dictionary containing a valid post-call audio payload.
    """
    import base64

    # Generate simple test audio bytes
    test_audio = b"fake audio content for testing purposes"
    audio_base64 = base64.b64encode(test_audio).decode("utf-8")

    return {
        "type": "post_call_audio",
        "event_timestamp": 1764457176,
        "data": {
            "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
            "conversation_id": "conv_audio_test_456",
            "status": "done",
            "transcript": [],
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "system__caller_id": "+16129782029"
                }
            },
            "audio_base64": audio_base64
        }
    }


@pytest.fixture
def known_caller_profile() -> dict[str, Any]:
    """Create a mock profile for a known/returning caller.

    Returns:
        Dictionary containing profile data for a returning caller.
    """
    return {
        "name": "Stefan",
        "summary": "Returning caller who previously discussed product inquiries.",
        "memories": [
            {"content": "User's name is Stefan", "salience": 0.9, "sector": "semantic"},
            {"content": "User prefers email contact", "salience": 0.8, "sector": "semantic"}
        ],
        "memory_count": 2,
        "phone_number": "+16129782029"
    }


# ============================================================================
# FastAPI Test Client Fixture
# ============================================================================


@pytest.fixture
def test_client(mock_settings: MagicMock) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with mocked dependencies.

    Args:
        mock_settings: Mock settings object.

    Yields:
        TestClient instance for making requests to the API.
    """
    with patch("app.config.settings", mock_settings), \
         patch("app.auth.hmac.settings", mock_settings), \
         patch("app.webhooks.client_data.settings", mock_settings), \
         patch("app.webhooks.search_data.settings", mock_settings), \
         patch("app.webhooks.post_call.settings", mock_settings):
        from app.main import app
        yield TestClient(app)


# ============================================================================
# HMAC Signature Helper Fixture
# ============================================================================


@pytest.fixture
def hmac_signature_generator():
    """Provide a function to generate valid HMAC signatures for testing.

    Returns:
        A callable that generates HMAC signatures.
    """
    import hmac as hmac_module
    import time
    from hashlib import sha256

    def generate_signature(
        payload: str,
        secret: str,
        timestamp: int | None = None
    ) -> str:
        """Generate a valid HMAC signature for testing.

        Args:
            payload: The request body as a string.
            secret: The HMAC secret key.
            timestamp: Unix timestamp (defaults to current time).

        Returns:
            The formatted signature header value: t=timestamp,v0=hash
        """
        if timestamp is None:
            timestamp = int(time.time())

        full_payload = f"{timestamp}.{payload}"
        mac = hmac_module.new(
            key=secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=sha256,
        )
        signature_hash = mac.hexdigest()
        return f"t={timestamp},v0={signature_hash}"

    return generate_signature