"""Tests for agent profile caching service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.agent_cache import AgentProfileCache, get_agent_profile_cache


class TestAgentProfileCache:
    """Tests for AgentProfileCache class."""

    def test_initialization_with_default_ttl(self):
        """Should initialize with 24-hour TTL by default."""
        cache = AgentProfileCache()
        assert cache._ttl == timedelta(hours=24)

    def test_initialization_with_custom_ttl(self):
        """Should accept custom TTL."""
        cache = AgentProfileCache(ttl_hours=12)
        assert cache._ttl == timedelta(hours=12)

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_profile(self, sample_agent_profile):
        """Should return cached profile if not expired."""
        cache = AgentProfileCache()

        # Manually add to cache with recent timestamp
        from datetime import datetime
        profile_with_recent_timestamp = {**sample_agent_profile, "cached_at": datetime.utcnow().isoformat()}
        cache._cache["agent_test123"] = profile_with_recent_timestamp

        result = await cache.get_agent_profile("agent_test123")
        assert result == profile_with_recent_timestamp

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_api(self, sample_agent_profile):
        """Should fetch from ElevenLabs API on cache miss."""
        cache = AgentProfileCache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Test Assistant",
            "conversation_config": {
                "agent": {
                    "first_message": "Hello!",
                    "prompt": {"prompt": "You are helpful."}
                }
            }
        }

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.services.agent_cache.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await cache.get_agent_profile("agent_new")

            assert result is not None
            assert result["agent_id"] == "agent_new"
            assert result["agent_name"] == "Test Assistant"
            # Should now be in cache
            assert "agent_new" in cache._cache

    @pytest.mark.asyncio
    async def test_expired_cache_refetches(self, sample_agent_profile):
        """Should refetch when cached entry is expired."""
        cache = AgentProfileCache(ttl_hours=1)

        # Add expired entry
        expired_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        cache._cache["agent_test123"] = {**sample_agent_profile, "cached_at": expired_time}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Updated Assistant",
            "conversation_config": {
                "agent": {
                    "first_message": "Hello updated!",
                    "prompt": {"prompt": "You are updated."}
                }
            }
        }

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.services.agent_cache.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await cache.get_agent_profile("agent_test123")

            # Should have updated name from fresh fetch
            assert result["agent_name"] == "Updated Assistant"

    @pytest.mark.asyncio
    async def test_api_404_returns_none(self):
        """Should return None for non-existent agent."""
        cache = AgentProfileCache()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client, \
             patch("app.services.agent_cache.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_key"

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await cache.get_agent_profile("nonexistent_agent")

            assert result is None

    def test_invalidate_removes_entry(self, sample_agent_profile):
        """Should remove specific entry from cache."""
        cache = AgentProfileCache()
        cache._cache["agent_test123"] = sample_agent_profile
        cache._cache["agent_other"] = {"agent_id": "agent_other"}

        cache.invalidate("agent_test123")

        assert "agent_test123" not in cache._cache
        assert "agent_other" in cache._cache

    def test_invalidate_all_clears_cache(self, sample_agent_profile):
        """Should clear all entries from cache."""
        cache = AgentProfileCache()
        cache._cache["agent_1"] = sample_agent_profile
        cache._cache["agent_2"] = {"agent_id": "agent_2"}
        cache._cache["agent_3"] = {"agent_id": "agent_3"}

        cache.invalidate_all()

        assert len(cache._cache) == 0

    def test_get_cache_stats(self, sample_agent_profile):
        """Should return cache statistics."""
        cache = AgentProfileCache()
        cache._cache["agent_1"] = sample_agent_profile
        cache._cache["agent_2"] = {"agent_id": "agent_2"}

        stats = cache.get_cache_stats()

        assert stats["total_entries"] == 2
        assert "agent_1" in stats["agent_ids"]
        assert "agent_2" in stats["agent_ids"]


class TestGetAgentProfileCache:
    """Tests for singleton cache accessor."""

    def test_returns_singleton_instance(self):
        """Should return same instance on multiple calls."""
        # Reset singleton for test
        import app.services.agent_cache as module
        module._cache_instance = None

        cache1 = get_agent_profile_cache()
        cache2 = get_agent_profile_cache()

        assert cache1 is cache2

    def test_creates_instance_on_first_call(self):
        """Should create instance if none exists."""
        import app.services.agent_cache as module
        module._cache_instance = None

        cache = get_agent_profile_cache()

        assert cache is not None
        assert isinstance(cache, AgentProfileCache)
