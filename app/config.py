"""Configuration module for ElevenLabs OpenMemory Integration.

This module handles:
- Loading environment variables using python-dotenv
- Defining the Settings class with all required configuration
- Startup validation with descriptive error messages
- Exporting a singleton settings instance

Required environment variables:
- ELEVENLABS_API_KEY: Primary API key for ElevenLabs SDK
- ELEVENLABS_POST_CALL_KEY: HMAC secret for post-call webhook validation
- ELEVENLABS_CLIENT_DATA_KEY: HMAC secret for client-data webhook
- ELEVENLABS_SEARCH_DATA_KEY: HMAC secret for search-data webhook
- OPENMEMORY_KEY: OpenMemory API key for authentication
- OPENMEMORY_PORT: OpenMemory service port/URL
- OPENMEMORY_DB_PATH: Path to OpenMemory database file
- PAYLOAD_STORAGE_PATH: Directory for saving conversation payloads

Optional environment variables:
- OPENAI_API_KEY: OpenAI API key for greeting generation
- OPENAI_MODEL: Model for greeting generation (default: gpt-4o-mini)
- OPENAI_MAX_TOKENS: Max tokens for greeting response (default: 150)
- OPENAI_TEMPERATURE: Creativity level (default: 0.7)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


@dataclass
class Settings:
    """Application settings loaded from environment variables.

    All settings are loaded from environment variables, with support for
    .env file loading via python-dotenv.
    """

    # ElevenLabs Configuration
    ELEVENLABS_API_KEY: str = field(default="")
    ELEVENLABS_POST_CALL_KEY: str = field(default="")
    ELEVENLABS_CLIENT_DATA_KEY: str = field(default="")
    ELEVENLABS_SEARCH_DATA_KEY: str = field(default="")

    # OpenMemory Configuration
    OPENMEMORY_KEY: str = field(default="")
    OPENMEMORY_PORT: str = field(default="")
    OPENMEMORY_DB_PATH: str = field(default="")

    # Storage Configuration
    PAYLOAD_STORAGE_PATH: str = field(default="")

    # OpenAI Configuration (for greeting generation)
    OPENAI_API_KEY: str = field(default="")
    OPENAI_MODEL: str = field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = field(default=150)
    OPENAI_TEMPERATURE: float = field(default=0.7)
    OPENAI_TIMEOUT: int = field(default=30)  # seconds

    def __post_init__(self) -> None:
        """Load environment variables after initialization."""
        self._load_from_environment()

    def _validate_int_range(
        self, value: str, min_val: int, max_val: int, name: str, default: int
    ) -> int:
        """Validate an integer is within range.

        Args:
            value: String value to parse
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name of the setting for error messages
            default: Default value if parsing fails

        Returns:
            Validated integer within range
        """
        try:
            parsed = int(value)
            if parsed < min_val or parsed > max_val:
                import logging
                logging.warning(
                    f"{name}={parsed} out of range [{min_val}, {max_val}], using {default}"
                )
                return default
            return parsed
        except (ValueError, TypeError):
            return default

    def _validate_float_range(
        self, value: str, min_val: float, max_val: float, name: str, default: float
    ) -> float:
        """Validate a float is within range.

        Args:
            value: String value to parse
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name of the setting for error messages
            default: Default value if parsing fails

        Returns:
            Validated float within range
        """
        try:
            parsed = float(value)
            if parsed < min_val or parsed > max_val:
                import logging
                logging.warning(
                    f"{name}={parsed} out of range [{min_val}, {max_val}], using {default}"
                )
                return default
            return parsed
        except (ValueError, TypeError):
            return default

    def _load_from_environment(self) -> None:
        """Load all settings from environment variables."""
        # Load .env file if it exists (won't override existing env vars)
        load_dotenv()

        # ElevenLabs Configuration
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        self.ELEVENLABS_POST_CALL_KEY = os.getenv("ELEVENLABS_POST_CALL_KEY", "")
        self.ELEVENLABS_CLIENT_DATA_KEY = os.getenv("ELEVENLABS_CLIENT_DATA_KEY", "")
        self.ELEVENLABS_SEARCH_DATA_KEY = os.getenv("ELEVENLABS_SEARCH_DATA_KEY", "")

        # OpenMemory Configuration
        self.OPENMEMORY_KEY = os.getenv("OPENMEMORY_KEY", "")
        self.OPENMEMORY_PORT = os.getenv("OPENMEMORY_PORT", "")
        self.OPENMEMORY_DB_PATH = os.getenv("OPENMEMORY_DB_PATH", "")

        # Storage Configuration
        self.PAYLOAD_STORAGE_PATH = os.getenv("PAYLOAD_STORAGE_PATH", "")

        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.OPENAI_MAX_TOKENS = self._validate_int_range(
            os.getenv("OPENAI_MAX_TOKENS", "150"), 50, 500, "OPENAI_MAX_TOKENS", 150
        )
        self.OPENAI_TEMPERATURE = self._validate_float_range(
            os.getenv("OPENAI_TEMPERATURE", "0.7"), 0.0, 2.0, "OPENAI_TEMPERATURE", 0.7
        )
        self.OPENAI_TIMEOUT = self._validate_int_range(
            os.getenv("OPENAI_TIMEOUT", "30"), 5, 120, "OPENAI_TIMEOUT", 30
        )

    def validate(self) -> None:
        """Validate that all required environment variables are set.

        Raises:
            ConfigurationError: If any required environment variable is missing.
        """
        required_vars = [
            ("ELEVENLABS_API_KEY", self.ELEVENLABS_API_KEY),
            ("ELEVENLABS_POST_CALL_KEY", self.ELEVENLABS_POST_CALL_KEY),
            ("ELEVENLABS_CLIENT_DATA_KEY", self.ELEVENLABS_CLIENT_DATA_KEY),
            ("ELEVENLABS_SEARCH_DATA_KEY", self.ELEVENLABS_SEARCH_DATA_KEY),
            ("OPENMEMORY_KEY", self.OPENMEMORY_KEY),
            ("OPENMEMORY_PORT", self.OPENMEMORY_PORT),
            ("OPENMEMORY_DB_PATH", self.OPENMEMORY_DB_PATH),
            ("PAYLOAD_STORAGE_PATH", self.PAYLOAD_STORAGE_PATH),
        ]

        missing_vars = [name for name, value in required_vars if not value]

        if missing_vars:
            missing_list = ", ".join(missing_vars)
            raise ConfigurationError(
                f"Missing required environment variables: {missing_list}. "
                f"Please ensure all required variables are set in your .env file or environment. "
                f"See .env.example for reference."
            )

    def ensure_storage_paths_exist(self) -> None:
        """Ensure that required storage directories exist.

        Creates the PAYLOAD_STORAGE_PATH directory if it doesn't exist.
        """
        if self.PAYLOAD_STORAGE_PATH:
            Path(self.PAYLOAD_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    @property
    def openmemory_url(self) -> str:
        """Get the full OpenMemory URL from port configuration.

        Returns:
            The full URL for OpenMemory service.
        """
        port = self.OPENMEMORY_PORT
        if port.startswith("http://") or port.startswith("https://"):
            return port
        return f"http://localhost:{port}"


def get_settings() -> Settings:
    """Get the application settings instance.

    This function creates a new Settings instance each time it's called.
    For singleton behavior in the application, use the `settings` module-level
    variable instead.

    Returns:
        A Settings instance with values loaded from environment.
    """
    return Settings()


def validate_startup_configuration() -> Settings:
    """Validate configuration on application startup.

    This function should be called during application startup to ensure
    all required configuration is present before the application begins
    handling requests.

    Returns:
        A validated Settings instance.

    Raises:
        ConfigurationError: If any required configuration is missing.
    """
    settings = Settings()
    settings.validate()
    settings.ensure_storage_paths_exist()
    return settings


# Singleton settings instance for import
# Note: This is created on module import. For testing, create new Settings instances.
# The validate() method should be called explicitly during application startup.
settings = Settings()
