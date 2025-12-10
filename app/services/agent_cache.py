"""Agent profile caching service for ElevenLabs agents.

This module provides:
- In-memory cache for ElevenLabs agent profiles
- Automatic cache invalidation with TTL
- Async fetching from ElevenLabs API
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AgentProfileCache:
    """In-memory cache for ElevenLabs agent profiles.

    Caches agent profiles to reduce API calls to ElevenLabs.
    Each cache entry has a TTL after which it will be refreshed.

    Note: For production deployments with multiple instances,
    consider using Redis or similar distributed cache.

    Attributes:
        _cache: Internal cache dictionary
        _ttl: Time-to-live for cache entries
    """

    def __init__(self, ttl_hours: int = 24):
        """Initialize the cache with specified TTL.

        Args:
            ttl_hours: Hours before cache entries expire. Default: 24
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._ttl = timedelta(hours=ttl_hours)

    async def get_agent_profile(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get agent profile from cache or fetch from ElevenLabs.

        Checks the cache first. If the entry exists and is not expired,
        returns the cached profile. Otherwise, fetches from ElevenLabs API
        and caches the result.

        Args:
            agent_id: The unique identifier of the ElevenLabs agent.

        Returns:
            Agent profile dictionary containing:
                - agent_id: str
                - agent_name: str
                - first_message: str
                - system_prompt: str
                - cached_at: str (ISO timestamp)
            Returns None if fetching fails.
        """
        # Check cache first
        if agent_id in self._cache:
            cached_entry = self._cache[agent_id]
            cached_at = datetime.fromisoformat(cached_entry["cached_at"])

            if datetime.utcnow() - cached_at < self._ttl:
                logger.debug(f"Cache hit for agent {agent_id}")
                return cached_entry

            logger.debug(f"Cache expired for agent {agent_id}")

        # Fetch from ElevenLabs API
        logger.info(f"Fetching agent profile from ElevenLabs: {agent_id}")
        profile = await self._fetch_from_elevenlabs(agent_id)

        if profile:
            # Add timestamp and cache
            profile["cached_at"] = datetime.utcnow().isoformat()
            self._cache[agent_id] = profile
            logger.info(f"Cached agent profile for {agent_id}")

        return profile

    async def _fetch_from_elevenlabs(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Fetch agent configuration from ElevenLabs API.

        Calls the ElevenLabs Conversational AI API to retrieve
        the agent's configuration.

        Args:
            agent_id: The unique identifier of the agent.

        Returns:
            Parsed agent profile or None on failure.
        """
        url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"

        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    logger.warning(f"Agent not found: {agent_id}")
                    return None

                if response.status_code != 200:
                    logger.error(
                        f"ElevenLabs API error: {response.status_code} - {response.text}"
                    )
                    return None

                data = response.json()

                # Extract relevant fields from the API response
                # The ElevenLabs API response structure may vary - adapt as needed
                agent_config = data.get("conversation_config", {}).get("agent", {})

                return {
                    "agent_id": agent_id,
                    "agent_name": data.get("name", "AI Assistant"),
                    "first_message": agent_config.get("first_message", "Hello, how can I help you?"),
                    "system_prompt": agent_config.get("prompt", {}).get("prompt", ""),
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP error fetching agent profile: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching agent profile: {e}")
            return None

    def invalidate(self, agent_id: str) -> None:
        """Manually invalidate cache for an agent.

        Removes the cached entry for the specified agent, forcing
        a fresh fetch on the next access.

        Args:
            agent_id: The unique identifier of the agent to invalidate.
        """
        if agent_id in self._cache:
            del self._cache[agent_id]
            logger.info(f"Invalidated cache for agent {agent_id}")

    def invalidate_all(self) -> None:
        """Invalidate all cached entries.

        Clears the entire cache, useful for forced refresh scenarios.
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Invalidated all {count} cached agent profiles")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics including:
                - total_entries: Number of cached entries
                - agent_ids: List of cached agent IDs
        """
        return {
            "total_entries": len(self._cache),
            "agent_ids": list(self._cache.keys())
        }


# Module-level singleton instance
_cache_instance: Optional[AgentProfileCache] = None


def get_agent_profile_cache() -> AgentProfileCache:
    """Get the singleton AgentProfileCache instance.

    Creates the instance on first call (lazy initialization).

    Returns:
        The singleton AgentProfileCache instance.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AgentProfileCache()
    return _cache_instance
