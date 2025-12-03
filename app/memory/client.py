"""OpenMemory client wrapper for memory operations.

This module provides:
- OpenMemory SDK initialization in REMOTE mode
- Configuration using environment variables (OPENMEMORY_PORT, OPENMEMORY_KEY)
- Singleton client instance for application-wide use
- Graceful error handling for connection issues

The client uses REMOTE mode to connect to an OpenMemory backend service,
with userId-based isolation using phone numbers as the primary identifier.
"""

import logging
from typing import Optional

from openmemory import OpenMemory

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level client instance (lazy initialization)
_client: Optional[OpenMemory] = None


class OpenMemoryConnectionError(Exception):
    """Raised when connection to OpenMemory service fails."""
    pass


def get_openmemory_client() -> OpenMemory:
    """Get or create the OpenMemory client instance.

    Initializes the OpenMemory SDK in REMOTE mode using configuration
    from environment variables:
    - OPENMEMORY_PORT: The URL or port of the OpenMemory service
    - OPENMEMORY_KEY: The API key for authentication

    Returns:
        OpenMemory: The initialized OpenMemory client instance.

    Raises:
        OpenMemoryConnectionError: If connection to OpenMemory service fails.
    """
    global _client

    if _client is not None:
        return _client

    try:
        # Get the OpenMemory URL from settings
        openmemory_url = settings.openmemory_url
        api_key = settings.OPENMEMORY_KEY

        logger.info(f"Initializing OpenMemory client in REMOTE mode at {openmemory_url}")

        _client = OpenMemory(
            mode="remote",
            url=openmemory_url,
            apiKey=api_key
        )

        logger.info("OpenMemory client initialized successfully")
        return _client

    except ValueError as e:
        logger.error(f"Invalid OpenMemory configuration: {e}")
        raise OpenMemoryConnectionError(f"Invalid OpenMemory configuration: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenMemory client: {e}")
        raise OpenMemoryConnectionError(f"Failed to connect to OpenMemory: {e}")


def reset_client() -> None:
    """Reset the client instance.

    This is primarily used for testing to ensure a fresh client
    instance is created with updated configuration.
    """
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception as e:
            logger.warning(f"Error closing OpenMemory client: {e}")
    _client = None


def close_client() -> None:
    """Close the OpenMemory client connection.

    Should be called during application shutdown to cleanly
    release resources.
    """
    global _client
    if _client is not None:
        try:
            _client.close()
            logger.info("OpenMemory client closed successfully")
        except Exception as e:
            logger.warning(f"Error closing OpenMemory client: {e}")
        finally:
            _client = None
