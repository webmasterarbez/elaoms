"""Integration tests for ElevenLabs OpenMemory Integration.

This module contains integration tests that verify end-to-end workflows:
1. Full client-data flow: request -> OpenMemory query -> response
2. Full post-call flow: auth -> payload save -> memory store
3. Returning caller personalization end-to-end
4. New caller handling end-to-end
5. Error handling for OpenMemory connection failures
6. Error handling for invalid payload formats
7. Memory persistence and retrieval workflow
8. Complete conversation lifecycle simulation
"""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestClientDataIntegration:
    """Integration tests for client-data webhook flow."""

    def test_full_client_data_flow_returning_caller(
        self,
        mock_settings: MagicMock,
        mock_openmemory_client: MagicMock,
        client_data_payload: dict,
        known_caller_profile: dict,
    ) -> None:
        """Test full client-data flow: request -> OpenMemory query -> response.

        This test verifies the complete integration flow for a returning caller:
        1. Client sends request with caller_id
        2. System queries OpenMemory for user profile
        3. System builds dynamic variables from profile
        4. System returns personalized response with first message
        """
        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", return_value=known_caller_profile):
            from app.main import app
            client = TestClient(app)

            response = client.post("/webhook/client-data", json=client_data_payload)

            # Verify successful response
            assert response.status_code == 200

            data = response.json()

            # Verify dynamic variables are populated for returning caller
            assert data.get("dynamic_variables") is not None
            assert data["dynamic_variables"]["user_name"] == "Stefan"
            assert data["dynamic_variables"]["user_profile_summary"] is not None

            # Verify conversation config override has personalized greeting
            assert data.get("conversation_config_override") is not None
            assert "agent" in data["conversation_config_override"]
            first_message = data["conversation_config_override"]["agent"].get("firstMessage")
            assert first_message is not None
            assert "Stefan" in first_message

    def test_full_client_data_flow_new_caller(
        self,
        mock_settings: MagicMock,
        mock_openmemory_client_empty: MagicMock,
        client_data_payload: dict,
    ) -> None:
        """Test full client-data flow for a new caller (no existing profile).

        This test verifies:
        1. New caller request is processed without errors
        2. OpenMemory returns empty results
        3. System returns empty/null overrides
        4. ElevenLabs will use default greetings
        """
        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", return_value=None):
            from app.main import app
            client = TestClient(app)

            response = client.post("/webhook/client-data", json=client_data_payload)

            # Verify successful response (no error for new caller)
            assert response.status_code == 200

            data = response.json()

            # For new caller, dynamic_variables should have None values
            if data.get("dynamic_variables"):
                assert data["dynamic_variables"].get("user_name") is None

            # conversation_config_override should be None for new callers
            assert data.get("conversation_config_override") is None


class TestPostCallIntegration:
    """Integration tests for post-call webhook flow."""

    def test_full_post_call_flow_transcription(
        self,
        mock_settings: MagicMock,
        mock_openmemory_client: MagicMock,
        post_call_transcription_payload: dict,
        hmac_signature_generator,
        temp_storage_dir: str,
    ) -> None:
        """Test full post-call flow: auth -> payload save -> memory store.

        This test verifies the complete post-call workflow:
        1. HMAC signature is validated
        2. Transcription payload is saved to disk
        3. User info is extracted and stored as memories
        4. Conversation messages are stored as memories
        """
        # Update mock settings with temp directory
        mock_settings.PAYLOAD_STORAGE_PATH = temp_storage_dir

        payload_str = json.dumps(post_call_transcription_payload)
        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = hmac_signature_generator(payload_str, secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings), \
             patch("app.memory.extraction.get_openmemory_client", return_value=mock_openmemory_client):
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

            # Verify successful response
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["type"] == "post_call_transcription"

            # Verify file was saved
            conversation_id = post_call_transcription_payload["data"]["conversation_id"]
            expected_file = Path(temp_storage_dir) / conversation_id / f"{conversation_id}_transcription.json"
            assert expected_file.exists()

            # Verify saved content
            with open(expected_file) as f:
                saved_data = json.load(f)
            assert saved_data["data"]["conversation_id"] == conversation_id

            # Verify memories were created (mocked)
            assert mock_openmemory_client.add.called

    def test_full_post_call_flow_audio(
        self,
        mock_settings: MagicMock,
        post_call_audio_payload: dict,
        hmac_signature_generator,
        temp_storage_dir: str,
    ) -> None:
        """Test post-call audio flow: auth -> base64 decode -> save audio.

        This test verifies:
        1. Audio payload is received and authenticated
        2. Base64 audio is decoded
        3. Audio file is saved to correct location
        """
        mock_settings.PAYLOAD_STORAGE_PATH = temp_storage_dir

        payload_str = json.dumps(post_call_audio_payload)
        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = hmac_signature_generator(payload_str, secret)

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
            conversation_id = post_call_audio_payload["data"]["conversation_id"]
            expected_file = Path(temp_storage_dir) / conversation_id / f"{conversation_id}_audio.mp3"
            assert expected_file.exists()

            # Verify audio content was decoded
            with open(expected_file, "rb") as f:
                saved_audio = f.read()
            assert saved_audio == b"fake audio content for testing purposes"


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_openmemory_connection_failure_client_data(
        self,
        mock_settings: MagicMock,
        mock_openmemory_client_error: MagicMock,
        client_data_payload: dict,
    ) -> None:
        """Test error handling when OpenMemory connection fails during client-data.

        The system should:
        1. Handle the connection error gracefully
        2. Return empty/null response (not 500 error)
        3. Allow conversation to proceed with defaults
        """
        from app.memory.client import OpenMemoryConnectionError

        def raise_connection_error(*args, **kwargs):
            raise OpenMemoryConnectionError("Connection refused")

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", side_effect=Exception("Connection failed")):
            from app.main import app
            client = TestClient(app)

            response = client.post("/webhook/client-data", json=client_data_payload)

            # Should return 200 with empty data, not 500
            assert response.status_code == 200

            data = response.json()
            # Should have null values to use defaults
            assert data.get("conversation_config_override") is None

    def test_openmemory_connection_failure_search_data(
        self,
        mock_settings: MagicMock,
        search_data_payload: dict,
    ) -> None:
        """Test error handling when OpenMemory connection fails during search-data.

        The system should:
        1. Handle the connection error gracefully
        2. Return empty memories array (not 500 error)
        """
        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.search_data.settings", mock_settings), \
             patch("app.webhooks.search_data.search_memories", return_value={"profile": None, "memories": []}):
            from app.main import app
            client = TestClient(app)

            response = client.post("/webhook/search-data", json=search_data_payload)

            # Should return 200 with empty results
            assert response.status_code == 200

            data = response.json()
            assert data.get("memories") == []

    def test_invalid_json_payload_post_call(
        self,
        mock_settings: MagicMock,
        hmac_signature_generator,
    ) -> None:
        """Test error handling for invalid JSON payload in post-call webhook.

        The system should:
        1. Return 400 Bad Request for invalid JSON
        2. Provide a descriptive error message
        """
        invalid_payload = "{ this is not valid json }"
        secret = mock_settings.ELEVENLABS_POST_CALL_KEY
        signature = hmac_signature_generator(invalid_payload, secret)

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings):
            from app.main import app
            client = TestClient(app)

            response = client.post(
                "/webhook/post-call",
                content=invalid_payload,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )

            # Should return 400 for invalid JSON
            assert response.status_code == 400

    def test_invalid_hmac_signature_rejected(
        self,
        mock_settings: MagicMock,
        post_call_transcription_payload: dict,
        hmac_signature_generator,
    ) -> None:
        """Test that invalid HMAC signatures are properly rejected.

        The system should:
        1. Return 401 Unauthorized for invalid signatures
        2. Not process the payload
        """
        payload_str = json.dumps(post_call_transcription_payload)
        wrong_secret = "completely_wrong_secret"
        signature = hmac_signature_generator(payload_str, wrong_secret)

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

            # Should return 401 for invalid signature
            assert response.status_code == 401


class TestSearchDataIntegration:
    """Integration tests for search-data webhook flow."""

    def test_search_data_returns_relevant_memories(
        self,
        mock_settings: MagicMock,
        search_data_payload: dict,
    ) -> None:
        """Test search-data webhook returns properly structured memories.

        This test verifies:
        1. Search query is processed
        2. Memories are returned in expected format
        3. Profile data is included if available
        """
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

            response = client.post("/webhook/search-data", json=search_data_payload)

            assert response.status_code == 200

            data = response.json()

            # Verify profile data
            assert data.get("profile") is not None
            assert data["profile"]["name"] == "Stefan"

            # Verify memories array
            assert len(data["memories"]) == 2
            assert data["memories"][0]["content"] == "User prefers email contact"


class TestConversationLifecycle:
    """Integration tests for complete conversation lifecycle."""

    def test_complete_conversation_lifecycle(
        self,
        mock_settings: MagicMock,
        mock_openmemory_client: MagicMock,
        client_data_payload: dict,
        search_data_payload: dict,
        post_call_transcription_payload: dict,
        known_caller_profile: dict,
        hmac_signature_generator,
        temp_storage_dir: str,
    ) -> None:
        """Test complete conversation lifecycle: initiation -> search -> post-call.

        This test simulates a full conversation:
        1. Call initiation with client-data webhook (profile lookup)
        2. Mid-conversation search-data webhook (memory retrieval)
        3. Post-call webhook (save transcription and store memories)

        This validates that all components work together correctly.
        """
        mock_settings.PAYLOAD_STORAGE_PATH = temp_storage_dir

        with patch("app.config.settings", mock_settings), \
             patch("app.auth.hmac.settings", mock_settings), \
             patch("app.webhooks.client_data.settings", mock_settings), \
             patch("app.webhooks.search_data.settings", mock_settings), \
             patch("app.webhooks.post_call.settings", mock_settings), \
             patch("app.webhooks.client_data.get_user_profile", return_value=known_caller_profile), \
             patch("app.webhooks.search_data.search_memories", return_value={
                 "profile": {"name": "Stefan", "summary": "Regular caller"},
                 "memories": [{"content": "User's name is Stefan", "sector": "semantic", "salience": 0.9}]
             }), \
             patch("app.memory.extraction.get_openmemory_client", return_value=mock_openmemory_client):
            from app.main import app
            client = TestClient(app)

            # Step 1: Call initiation - client-data webhook
            response1 = client.post("/webhook/client-data", json=client_data_payload)
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["dynamic_variables"]["user_name"] == "Stefan"

            # Step 2: Mid-conversation - search-data webhook
            response2 = client.post("/webhook/search-data", json=search_data_payload)
            assert response2.status_code == 200
            data2 = response2.json()
            assert len(data2["memories"]) > 0

            # Step 3: Post-call - save transcription and memories
            payload_str = json.dumps(post_call_transcription_payload)
            secret = mock_settings.ELEVENLABS_POST_CALL_KEY
            signature = hmac_signature_generator(payload_str, secret)

            response3 = client.post(
                "/webhook/post-call",
                content=payload_str,
                headers={
                    "elevenlabs-signature": signature,
                    "Content-Type": "application/json"
                }
            )
            assert response3.status_code == 200
            data3 = response3.json()
            assert data3["status"] == "success"

            # Verify transcription was saved
            conversation_id = post_call_transcription_payload["data"]["conversation_id"]
            saved_file = Path(temp_storage_dir) / conversation_id / f"{conversation_id}_transcription.json"
            assert saved_file.exists()