"""Tests for the configuration module.

This module contains 4 focused tests for the configuration system:
1. Test environment variable loading with all required vars present
2. Test validation fails when required vars are missing
3. Test config object properly exposes all settings
4. Test .env file loading via python-dotenv
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _clear_config_module_cache():
    """Clear config module from sys.modules to ensure fresh imports."""
    modules_to_remove = [
        key for key in list(sys.modules.keys())
        if key.startswith("app.config") or key == "app"
    ]
    for module in modules_to_remove:
        del sys.modules[module]


class TestConfigurationLoading:
    """Test suite for configuration loading functionality."""

    def setup_method(self):
        """Clear module cache before each test to ensure fresh imports."""
        _clear_config_module_cache()

    def test_environment_variable_loading_with_all_required_vars(self) -> None:
        """Test that all required environment variables are loaded correctly."""
        env_vars = {
            "ELEVENLABS_API_KEY": "test_elevenlabs_key",
            "ELEVENLABS_POST_CALL_KEY": "test_post_call_key",
            "ELEVENLABS_CLIENT_DATA_KEY": "test_client_data_key",
            "ELEVENLABS_SEARCH_DATA_KEY": "test_search_data_key",
            "OPENMEMORY_KEY": "test_openmemory_key",
            "OPENMEMORY_PORT": "8000",
            "OPENMEMORY_DB_PATH": "/tmp/test_openmemory.db",
            "PAYLOAD_STORAGE_PATH": "/tmp/test_payloads",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Import fresh module to pick up new environment
            from app.config import Settings

            settings = Settings()

            assert settings.ELEVENLABS_API_KEY == "test_elevenlabs_key"
            assert settings.ELEVENLABS_POST_CALL_KEY == "test_post_call_key"
            assert settings.ELEVENLABS_CLIENT_DATA_KEY == "test_client_data_key"
            assert settings.ELEVENLABS_SEARCH_DATA_KEY == "test_search_data_key"
            assert settings.OPENMEMORY_KEY == "test_openmemory_key"
            assert settings.OPENMEMORY_PORT == "8000"
            assert settings.OPENMEMORY_DB_PATH == "/tmp/test_openmemory.db"
            assert settings.PAYLOAD_STORAGE_PATH == "/tmp/test_payloads"

    def test_validation_fails_when_required_vars_missing(self) -> None:
        """Test that validation fails with descriptive error when required vars are missing."""
        # We need to mock load_dotenv to prevent it from loading the .env file
        # and clear the environment to ensure no variables are set
        with patch("dotenv.load_dotenv"):
            with patch.dict(os.environ, {}, clear=True):
                from app.config import Settings, ConfigurationError

                # Create settings (this doesn't raise, values will be empty strings)
                settings = Settings()

                # Validation should raise ConfigurationError since all values are empty
                with pytest.raises(ConfigurationError) as exc_info:
                    settings.validate()

                # Check that error message is descriptive
                error_message = str(exc_info.value)
                assert "ELEVENLABS_API_KEY" in error_message or "required" in error_message.lower()

    def test_config_object_exposes_all_settings(self) -> None:
        """Test that the config object properly exposes all settings as attributes."""
        env_vars = {
            "ELEVENLABS_API_KEY": "api_key_test",
            "ELEVENLABS_POST_CALL_KEY": "post_call_key_test",
            "ELEVENLABS_CLIENT_DATA_KEY": "client_data_key_test",
            "ELEVENLABS_SEARCH_DATA_KEY": "search_data_key_test",
            "OPENMEMORY_KEY": "openmemory_key_test",
            "OPENMEMORY_PORT": "9000",
            "OPENMEMORY_DB_PATH": "/data/memory.db",
            "PAYLOAD_STORAGE_PATH": "/data/payloads",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            from app.config import Settings

            settings = Settings()

            # Verify all expected attributes exist and are accessible
            expected_attrs = [
                "ELEVENLABS_API_KEY",
                "ELEVENLABS_POST_CALL_KEY",
                "ELEVENLABS_CLIENT_DATA_KEY",
                "ELEVENLABS_SEARCH_DATA_KEY",
                "OPENMEMORY_KEY",
                "OPENMEMORY_PORT",
                "OPENMEMORY_DB_PATH",
                "PAYLOAD_STORAGE_PATH",
            ]

            for attr in expected_attrs:
                assert hasattr(settings, attr), f"Settings missing attribute: {attr}"
                assert getattr(settings, attr) is not None, f"Attribute {attr} is None"

    def test_dotenv_file_loading(self) -> None:
        """Test that .env file is loaded via python-dotenv."""
        # Create a temporary .env file
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file_path = Path(tmpdir) / ".env"
            env_content = """
ELEVENLABS_API_KEY=from_dotenv_file
ELEVENLABS_POST_CALL_KEY=post_call_from_file
ELEVENLABS_CLIENT_DATA_KEY=client_data_from_file
ELEVENLABS_SEARCH_DATA_KEY=search_data_from_file
OPENMEMORY_KEY=openmemory_from_file
OPENMEMORY_PORT=7000
OPENMEMORY_DB_PATH=/from/dotenv/path.db
PAYLOAD_STORAGE_PATH=/from/dotenv/payloads
"""
            env_file_path.write_text(env_content)

            # Clear environment and load from file
            with patch.dict(os.environ, {}, clear=True):
                from dotenv import load_dotenv

                # Load the .env file
                load_dotenv(env_file_path)

                from app.config import Settings

                settings = Settings()

                # Verify values came from .env file
                assert settings.ELEVENLABS_API_KEY == "from_dotenv_file"
                assert settings.OPENMEMORY_PORT == "7000"
                assert settings.PAYLOAD_STORAGE_PATH == "/from/dotenv/payloads"