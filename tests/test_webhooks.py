"""Tests for webhook endpoint handlers.

This module contains 8 focused tests for webhook endpoints:
1. Test POST /webhook/client-data returns profile for known caller
2. Test POST /webhook/client-data returns empty for new caller
3. Test POST /webhook/search-data returns relevant memories
4. Test POST /webhook/post-call accepts valid HMAC signature
5. Test POST /webhook/post-call rejects invalid signature
6. Test POST /webhook/post-call saves transcription payload
7. Test POST /webhook/post-call saves audio payload (base64 decode)
8. Test GET /health returns healthy status
"""

import base64
import hmac
import json
import os
import tempfile
import time
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestWebhookEndpoints:
    """Test suite for webhook endpoints."""

    def _generate_valid_signature(
        self, payload: str, secret: str, timestamp: int | None = None
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
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=sha256,
        )
        signature_hash = mac.hexdigest()
        return f"t={timestamp},v0={signature_hash}"

    def _get_mock_settings(self, temp_dir: str) -> MagicMock:
        """Create mock settings for testing.

        Args:
            temp_dir: Temporary directory for payload storage.

        Returns:
            MagicMock object with all required settings.
        """
        mock = MagicMock()
        mock.ELEVENLABS_API_KEY = "test_api_key"
        mock.ELEVENLABS_POST_CALL_KEY = "test_post_call_secret"
        mock.ELEVENLABS_CLIENT_DATA_KEY = "test_client_data_key"
        mock.ELEVENLABS_SEARCH_DATA_KEY = "test_search_data_key"
        mock.OPENMEMORY_KEY = "test_openmemory_key"
        mock.OPENMEMORY_PORT = "8080"
        mock.OPENMEMORY_DB_PATH = "/tmp/test_db"
        mock.PAYLOAD_STORAGE_PATH = temp_dir
        mock.openmemory_url = "http://localhost:8080"
        return mock

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for payload storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_settings(self, temp_storage_dir):
        """Create mock settings with temporary storage directory."""
        return self._get_mock_settings(temp_storage_dir)

    @pytest.fixture
    def client(self, mock_settings):
        """Create a test client with mocked dependencies."""
        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.settings", mock_settings), \
             patch("app.webhooks.search_data.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings):
            from app.main import app
            yield TestClient(app)

    def test_health_endpoint_returns_healthy_status(self, client) -> None:
        """Test GET /health returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_client_data_returns_profile_for_known_caller(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/client-data returns profile for known caller."""
        # Mock the profile retrieval to return a known caller
        mock_profile = {
            "name": "Stefan",
            "summary": "Returning caller interested in support.",
            "memories": [{"content": "User's name is Stefan", "salience": 0.9}],
            "memory_count": 1,
            "phone_number": "+16129782029"
        }

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", return_value=mock_profile):
            from app.main import app
            client = TestClient(app)

            request_data = {
                "caller_id": "+16129782029",
                "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
                "called_number": "+16123241623",
                "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
            }

            response = client.post(
                "/webhook/client-data",
                json=request_data,
                headers={"X-Api-Key": mock_settings.ELEVENLABS_CLIENT_DATA_KEY}
            )

            assert response.status_code == 200
            data = response.json()

            # Should have dynamic variables for known caller
            assert data.get("dynamic_variables") is not None
            assert data["dynamic_variables"]["user_name"] == "Stefan"

            # Should have conversation config override
            assert data.get("conversation_config_override") is not None
            assert "agent" in data["conversation_config_override"]

    def test_client_data_returns_empty_for_new_caller(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/client-data returns empty for new caller."""
        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", return_value=None):
            from app.main import app
            client = TestClient(app)

            request_data = {
                "caller_id": "+19998887777",
                "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
                "called_number": "+16123241623",
                "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
            }

            response = client.post(
                "/webhook/client-data",
                json=request_data,
                headers={"X-Api-Key": mock_settings.ELEVENLABS_CLIENT_DATA_KEY}
            )

            assert response.status_code == 200
            data = response.json()

            # For new caller, dynamic_variables should have None values
            if data.get("dynamic_variables"):
                assert data["dynamic_variables"].get("user_name") is None

            # conversation_config_override should be None for new callers
            assert data.get("conversation_config_override") is None

    def test_search_data_returns_relevant_memories(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/search-data returns relevant memories."""
        mock_search_result = {
            "profile": {
                "name": "Stefan",
                "summary": "Regular caller",
                "phone_number": "+16129782029"
            },
            "memories": [
                {"content": "User prefers email contact", "sector": "semantic", "salience": 0.8},
                {"content": "Previous call about account setup", "sector": "episodic", "salience": 0.7}
            ]
        }

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.search_data.settings", mock_settings), \
             patch("app.webhooks.search_data.search_memories", return_value=mock_search_result):
            from app.main import app
            client = TestClient(app)

            request_data = {
                "query": "What are the user's preferences?",
                "user_id": "+16129782029",
                "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
            }

            response = client.post("/webhook/search-data", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Should have profile data
            assert data.get("profile") is not None
            assert data["profile"]["name"] == "Stefan"

            # Should have memories array
            assert "memories" in data
            assert len(data["memories"]) == 2

    def test_post_call_accepts_valid_hmac_signature(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/post-call accepts valid HMAC signature."""
        # Load sample transcription payload
        fixtures_path = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
        with open(fixtures_path) as f:
            payload = f.read()

        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = self._generate_valid_signature(payload, secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings), \
             patch("app.webhooks.post_call.extract_user_info", return_value={"first_name": "Stefan"}), \
             patch("app.webhooks.post_call.extract_user_messages", return_value=["Stefan."]), \
             patch("app.webhooks.post_call.create_profile_memories", return_value=[]), \
             patch("app.webhooks.post_call.store_conversation_memories", return_value=[]):
            from app.main import app
            client = TestClient(app)

            response = client.post(
                "/webhook/post-call",
                content=payload,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )

            assert response.status_code == 200

    def test_post_call_rejects_invalid_signature(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/post-call rejects invalid signature."""
        fixtures_path = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
        with open(fixtures_path) as f:
            payload = f.read()

        # Use wrong secret to generate invalid signature
        wrong_secret = "wrong_secret_key"
        signature = self._generate_valid_signature(payload, wrong_secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings):
            from app.main import app
            client = TestClient(app)

            response = client.post(
                "/webhook/post-call",
                content=payload,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )

            assert response.status_code == 401

    def test_post_call_saves_transcription_payload(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/post-call saves transcription payload."""
        fixtures_path = Path(__file__).parent / "fixtures" / "post_call_transcription.json"
        with open(fixtures_path) as f:
            payload = f.read()

        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = self._generate_valid_signature(payload, secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings), \
             patch("app.webhooks.post_call.extract_user_info", return_value={"first_name": "Stefan"}), \
             patch("app.webhooks.post_call.extract_user_messages", return_value=["Stefan."]), \
             patch("app.webhooks.post_call.create_profile_memories", return_value=[]), \
             patch("app.webhooks.post_call.store_conversation_memories", return_value=[]):
            from app.main import app
            client = TestClient(app)

            response = client.post(
                "/webhook/post-call",
                content=payload,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )

            assert response.status_code == 200

            # Verify file was saved
            conversation_id = "conv_8701kb8xfaaney589jkc6pjesxrc"
            expected_dir = Path(temp_storage_dir) / conversation_id
            expected_file = expected_dir / f"{conversation_id}_transcription.json"

            assert expected_dir.exists(), f"Directory {expected_dir} should exist"
            assert expected_file.exists(), f"File {expected_file} should exist"

            # Verify content
            with open(expected_file) as f:
                saved_data = json.load(f)
            assert saved_data["data"]["conversation_id"] == conversation_id

    def test_post_call_saves_audio_payload_base64_decode(
        self, mock_settings, temp_storage_dir
    ) -> None:
        """Test POST /webhook/post-call saves audio payload (base64 decode)."""
        # Create a mock audio payload with base64 encoded data
        audio_content = b"fake audio content for testing"
        audio_base64 = base64.b64encode(audio_content).decode("utf-8")

        audio_payload = {
            "type": "post_call_audio",
            "event_timestamp": 1764457176,
            "data": {
                "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
                "conversation_id": "conv_audio_test_123",
                "status": "done",
                "user_id": None,
                "branch_id": None,
                "transcript": [],
                "metadata": None,
                "analysis": None,
                "conversation_initiation_client_data": {
                    "dynamic_variables": {
                        "system__caller_id": "+16129782029"
                    }
                },
                "has_audio": True,
                "has_user_audio": False,
                "has_response_audio": False,
                "audio_base64": audio_base64
            }
        }

        payload_str = json.dumps(audio_payload)
        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = self._generate_valid_signature(payload_str, secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings):
            from app.main import app
            client = TestClient(app)

            response = client.post(
                "/webhook/post-call",
                content=payload_str,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )

            assert response.status_code == 200

            # Verify audio file was saved
            conversation_id = "conv_audio_test_123"
            expected_dir = Path(temp_storage_dir) / conversation_id
            expected_file = expected_dir / f"{conversation_id}_audio.mp3"

            assert expected_dir.exists(), f"Directory {expected_dir} should exist"
            assert expected_file.exists(), f"File {expected_file} should exist"

            # Verify content was base64 decoded
            with open(expected_file, "rb") as f:
                saved_audio = f.read()
            assert saved_audio == audio_content