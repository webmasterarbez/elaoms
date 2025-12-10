"""HTTP client utilities for external API communication.

This module provides configured httpx AsyncClient factories for consistent
HTTP communication across the application. Centralizing client configuration:

- Ensures consistent timeouts, headers, and error handling
- Reduces code duplication across memory, services, and webhook modules
- Makes it easier to add global features like retries or circuit breakers

Usage:
    async with get_openmemory_client() as client:
        response = await client.post("/memory/add", json=payload)

    async with get_openai_client() as client:
        response = await client.post("/v1/chat/completions", json=payload)
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import httpx

from app.config import settings


# Default timeout configuration (seconds)
DEFAULT_TIMEOUT = 10.0
OPENAI_TIMEOUT = 30.0
ELEVENLABS_TIMEOUT = 30.0


def _build_openmemory_headers(api_key: Optional[str] = None) -> dict[str, str]:
    """Build headers for OpenMemory API requests.

    Args:
        api_key: Optional API key override. Uses settings if not provided.

    Returns:
        Dictionary of HTTP headers.
    """
    headers = {"Content-Type": "application/json"}
    key = api_key or settings.OPENMEMORY_KEY
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _build_openai_headers(api_key: Optional[str] = None) -> dict[str, str]:
    """Build headers for OpenAI API requests.

    Args:
        api_key: Optional API key override. Uses settings if not provided.

    Returns:
        Dictionary of HTTP headers.
    """
    key = api_key or settings.OPENAI_API_KEY
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }


def _build_elevenlabs_headers(api_key: Optional[str] = None) -> dict[str, str]:
    """Build headers for ElevenLabs API requests.

    Args:
        api_key: Optional API key override. Uses settings if not provided.

    Returns:
        Dictionary of HTTP headers.
    """
    key = api_key or settings.ELEVENLABS_API_KEY
    return {
        "xi-api-key": key,
        "Content-Type": "application/json"
    }


@asynccontextmanager
async def get_openmemory_client(
    timeout: float = DEFAULT_TIMEOUT
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get a configured httpx client for OpenMemory API.

    Creates an AsyncClient with:
    - Base URL from settings.openmemory_url
    - Authorization header with OPENMEMORY_KEY
    - Configurable timeout (default: 10s)

    Usage:
        async with get_openmemory_client() as client:
            response = await client.post("/memory/add", json=payload)

    Args:
        timeout: Request timeout in seconds (default: 10.0)

    Yields:
        Configured httpx.AsyncClient instance.
    """
    async with httpx.AsyncClient(
        base_url=settings.openmemory_url,
        headers=_build_openmemory_headers(),
        timeout=timeout
    ) as client:
        yield client


@asynccontextmanager
async def get_openai_client(
    timeout: Optional[float] = None
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get a configured httpx client for OpenAI API.

    Creates an AsyncClient with:
    - Base URL: https://api.openai.com
    - Authorization header with OPENAI_API_KEY
    - Configurable timeout (default: from settings or 30s)

    Usage:
        async with get_openai_client() as client:
            response = await client.post("/v1/chat/completions", json=payload)

    Args:
        timeout: Request timeout in seconds (default: settings.OPENAI_TIMEOUT)

    Yields:
        Configured httpx.AsyncClient instance.
    """
    effective_timeout = timeout or float(settings.OPENAI_TIMEOUT)
    async with httpx.AsyncClient(
        base_url="https://api.openai.com",
        headers=_build_openai_headers(),
        timeout=effective_timeout
    ) as client:
        yield client


@asynccontextmanager
async def get_elevenlabs_client(
    timeout: float = ELEVENLABS_TIMEOUT
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get a configured httpx client for ElevenLabs API.

    Creates an AsyncClient with:
    - Base URL: https://api.elevenlabs.io
    - xi-api-key header with ELEVENLABS_API_KEY
    - Configurable timeout (default: 30s)

    Usage:
        async with get_elevenlabs_client() as client:
            response = await client.get(f"/v1/convai/agents/{agent_id}")

    Args:
        timeout: Request timeout in seconds (default: 30.0)

    Yields:
        Configured httpx.AsyncClient instance.
    """
    async with httpx.AsyncClient(
        base_url="https://api.elevenlabs.io",
        headers=_build_elevenlabs_headers(),
        timeout=timeout
    ) as client:
        yield client


@asynccontextmanager
async def get_raw_client(
    timeout: float = DEFAULT_TIMEOUT
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get a basic httpx client without preconfigured base URL or headers.

    Use this for one-off requests to arbitrary URLs where you need
    full control over the request configuration.

    Args:
        timeout: Request timeout in seconds (default: 10.0)

    Yields:
        Basic httpx.AsyncClient instance.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        yield client
