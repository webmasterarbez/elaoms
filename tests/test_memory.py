"""Tests for OpenMemory client and memory operations.

This module contains 6 focused tests for memory operations:
1. Test OpenMemory client initialization in REMOTE mode
2. Test memory add operation with correct parameters
3. Test memory query operation returns structured results
4. Test user summary retrieval
5. Test userId isolation (phone number as user ID)
6. Test memory storage with decayLambda=0 (permanent retention)
"""

import os
import sys
from unittest.mock import MagicMock, patch, Mock, PropertyMock
from typing import Any

import pytest


# Clear any cached imports before tests
def clear_memory_module_cache():
    """Clear memory module from sys.modules to ensure fresh imports."""
    modules_to_remove = [
        key for key in list(sys.modules.keys())
        if key.startswith("app.memory")
    ]
    for module in modules_to_remove:
        del sys.modules[module]


class TestOpenMemoryClient:
    """Test suite for OpenMemory client and memory operations."""

    def setup_method(self):
        """Clear module cache before each test."""
        clear_memory_module_cache()

    def test_openmemory_client_initialization_in_remote_mode(self) -> None:
        """Test OpenMemory client initializes correctly in REMOTE mode."""
        # Patch the settings module to provide specific values
        mock_settings = MagicMock()
        mock_settings.openmemory_url = "http://localhost:8080"
        mock_settings.OPENMEMORY_KEY = "test_api_key"

        with patch("app.memory.client.settings", mock_settings):
            with patch("app.memory.client.OpenMemory") as mock_om_class:
                mock_client = MagicMock()
                mock_om_class.return_value = mock_client

                # Import fresh to pick up the mock
                from app.memory.client import get_openmemory_client, reset_client
                reset_client()  # Ensure fresh client

                client = get_openmemory_client()

                # Verify OpenMemory was initialized with correct parameters
                mock_om_class.assert_called_once_with(
                    mode="remote",
                    url="http://localhost:8080",
                    apiKey="test_api_key"
                )
                assert client is not None

    def test_memory_add_operation_with_correct_parameters(self) -> None:
        """Test memory add operation passes correct parameters to OpenMemory SDK."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.add.return_value = {
            "id": "mem_123",
            "primarySector": "episodic",
            "sectors": ["episodic"]
        }

        # Patch get_openmemory_client to return our mock
        with patch("app.memory.extraction.get_openmemory_client", return_value=mock_client):
            from app.memory.extraction import store_conversation_memories

            phone_number = "+16129782029"
            messages = ["Hello, my name is Stefan", "I need help with my account"]

            result = store_conversation_memories(messages, phone_number)

            # Verify add was called for each message
            assert mock_client.add.call_count == 2

            # Verify the parameters were correct for each call
            for call in mock_client.add.call_args_list:
                kwargs = call[1]
                assert kwargs["userId"] == phone_number
                assert kwargs["decayLambda"] == 0  # Permanent retention

    def test_memory_query_operation_returns_structured_results(self) -> None:
        """Test memory query operation returns properly structured results."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.query.return_value = {
            "results": [
                {
                    "id": "mem_1",
                    "content": "User prefers email contact",
                    "sector": "semantic",
                    "salience": 0.8,
                    "score": 0.95
                },
                {
                    "id": "mem_2",
                    "content": "User name is Stefan",
                    "sector": "episodic",
                    "salience": 0.9,
                    "score": 0.88
                }
            ]
        }

        # Patch get_openmemory_client to return our mock
        with patch("app.memory.extraction.get_openmemory_client", return_value=mock_client):
            from app.memory.extraction import search_memories

            phone_number = "+16129782029"
            query = "What are the user's preferences?"

            result = search_memories(query, phone_number)

            # Verify query was called
            mock_client.query.assert_called_once()

            # Verify result structure
            assert "profile" in result
            assert "memories" in result
            assert isinstance(result["memories"], list)
            assert len(result["memories"]) == 2

    def test_user_summary_retrieval(self) -> None:
        """Test user summary retrieval returns proper profile data."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openmemory_url = "http://localhost:8080"
        mock_settings.OPENMEMORY_KEY = "test_api_key"

        with patch("app.memory.profiles.settings", mock_settings):
            # Mock the requests.get for the summary endpoint
            with patch("app.memory.profiles.requests.get") as mock_get:
                # Mock the summary API response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "userId": "+16129782029",
                    "summary": "Stefan is a returning customer interested in account support.",
                    "name": "Stefan",
                    "memoryCount": 5
                }
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                from app.memory.profiles import get_user_summary

                phone_number = "+16129782029"
                summary = get_user_summary(phone_number)

                # Verify summary structure
                assert summary is not None
                assert summary.get("name") == "Stefan"
                assert "summary" in summary

    def test_userid_isolation_with_phone_number(self) -> None:
        """Test userId isolation ensures phone number is used correctly."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.add.return_value = {
            "id": "mem_123",
            "primarySector": "semantic",
            "sectors": ["semantic"]
        }

        # Patch get_openmemory_client to return our mock
        with patch("app.memory.extraction.get_openmemory_client", return_value=mock_client):
            from app.memory.extraction import create_profile_memories

            phone_number = "+16129782029"
            user_info = {"first_name": "Stefan", "preference": "email"}

            create_profile_memories(user_info, phone_number)

            # Verify all add calls use the phone number as userId
            assert mock_client.add.call_count == 2
            for call in mock_client.add.call_args_list:
                kwargs = call[1]
                assert kwargs["userId"] == phone_number, \
                    f"Expected userId={phone_number}, got userId={kwargs.get('userId')}"

    def test_memory_storage_with_decay_lambda_zero_permanent_retention(self) -> None:
        """Test memory storage uses decayLambda=0 for permanent retention."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.add.return_value = {
            "id": "mem_123",
            "primarySector": "semantic",
            "sectors": ["semantic"]
        }

        # Patch get_openmemory_client to return our mock
        with patch("app.memory.extraction.get_openmemory_client", return_value=mock_client):
            from app.memory.extraction import create_profile_memories, store_conversation_memories

            phone_number = "+16129782029"

            # Test profile memories
            user_info = {"first_name": "Stefan"}
            create_profile_memories(user_info, phone_number)

            # Test conversation memories
            messages = ["I need help with my account"]
            store_conversation_memories(messages, phone_number)

            # Verify ALL add calls use decayLambda=0 for permanent retention
            assert mock_client.add.call_count == 2  # 1 profile + 1 message
            for call in mock_client.add.call_args_list:
                kwargs = call[1]
                assert kwargs["decayLambda"] == 0, \
                    f"Expected decayLambda=0 for permanent retention, got {kwargs.get('decayLambda')}"
