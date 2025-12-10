"""Tests for logging utilities with PII protection."""

import json
import logging
import pytest
from io import StringIO

from app.utils.logging import (
    hash_phone_number,
    mask_phone_number,
    StructuredLogFormatter,
    get_structured_logger,
    log_webhook_event,
    log_openai_event,
    log_memory_event,
)


class TestHashPhoneNumber:
    """Tests for phone number hashing."""

    def test_hashes_phone_number(self):
        """Should return consistent hash for same phone number."""
        phone = "+16125551234"
        hash1 = hash_phone_number(phone)
        hash2 = hash_phone_number(phone)
        assert hash1 == hash2
        assert hash1.startswith("ph_")

    def test_different_phones_different_hashes(self):
        """Should return different hashes for different numbers."""
        hash1 = hash_phone_number("+16125551234")
        hash2 = hash_phone_number("+16125559999")
        assert hash1 != hash2

    def test_handles_empty_phone(self):
        """Should handle empty phone number."""
        assert hash_phone_number("") == "ph_unknown"
        assert hash_phone_number(None) == "ph_unknown"

    def test_hash_length(self):
        """Should return hash with consistent length."""
        hash_result = hash_phone_number("+16125551234")
        # "ph_" prefix + 8 chars
        assert len(hash_result) == 11


class TestMaskPhoneNumber:
    """Tests for phone number masking."""

    def test_masks_phone_number(self):
        """Should mask middle digits."""
        result = mask_phone_number("+16125551234")
        assert result.endswith("1234")
        assert "612555" not in result

    def test_handles_short_number(self):
        """Should handle short phone numbers."""
        assert mask_phone_number("123") == "***"
        assert mask_phone_number("") == "***"

    def test_preserves_country_code(self):
        """Should preserve + prefix."""
        result = mask_phone_number("+16125551234")
        assert result.startswith("+")


class TestStructuredLogFormatter:
    """Tests for JSON log formatter."""

    def test_formats_as_json(self):
        """Should output valid JSON."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"

    def test_includes_timestamp(self):
        """Should include timestamp when enabled."""
        formatter = StructuredLogFormatter(include_timestamp=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "timestamp" in data

    def test_sanitizes_phone_numbers(self):
        """Should hash phone numbers in message."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing caller +16125551234",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        # Phone number should be hashed
        assert "+16125551234" not in data["message"]
        assert "ph_" in data["message"]

    def test_includes_extra_fields(self):
        """Should include extra fields from record."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.agent_id = "agent_xyz"
        record.caller_hash = "ph_abc123"
        record.scenario = "returning_caller"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["agent_id"] == "agent_xyz"
        assert data["caller_hash"] == "ph_abc123"
        assert data["scenario"] == "returning_caller"


class TestLogWebhookEvent:
    """Tests for webhook event logging."""

    def test_logs_webhook_event(self, caplog):
        """Should log webhook event with correct format."""
        logger = logging.getLogger("test_webhook")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_webhook_event(
                logger=logger,
                event_type="client_data_request",
                phone_number="+16125551234",
                agent_id="agent_test",
                scenario="returning_with_greeting",
                response_time_ms=45.5
            )

        assert len(caplog.records) == 1
        assert "client_data_request" in caplog.text
        assert "agent_test" in caplog.text
        # Phone should be hashed
        assert "+16125551234" not in caplog.text
        assert "ph_" in caplog.text

    def test_logs_with_cache_hit(self, caplog):
        """Should include cache hit info."""
        logger = logging.getLogger("test_cache")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_webhook_event(
                logger=logger,
                event_type="post_call_complete",
                phone_number="+16125551234",
                agent_id="agent_test",
                cache_hit=True
            )

        record = caplog.records[0]
        assert hasattr(record, "cache_hit")
        assert record.cache_hit is True


class TestLogOpenAIEvent:
    """Tests for OpenAI event logging."""

    def test_logs_successful_event(self, caplog):
        """Should log successful OpenAI event."""
        logger = logging.getLogger("test_openai")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_openai_event(
                logger=logger,
                event_type="greeting_generation",
                phone_number="+16125551234",
                agent_id="agent_test",
                success=True,
                tokens_used=142,
                latency_ms=3200.5
            )

        assert len(caplog.records) == 1
        assert "success=True" in caplog.text
        assert "tokens=142" in caplog.text
        # Phone should be hashed
        assert "+16125551234" not in caplog.text

    def test_logs_failed_event_as_error(self, caplog):
        """Should log failed event at error level."""
        logger = logging.getLogger("test_openai_error")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_openai_event(
                logger=logger,
                event_type="greeting_generation",
                phone_number="+16125551234",
                agent_id="agent_test",
                success=False,
                error="Rate limit exceeded"
            )

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.ERROR
        assert "error=Rate limit exceeded" in caplog.text


class TestLogMemoryEvent:
    """Tests for memory event logging."""

    def test_logs_tier1_event(self, caplog):
        """Should log Tier 1 memory event."""
        logger = logging.getLogger("test_memory")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_memory_event(
                logger=logger,
                event_type="query",
                phone_number="+16125551234",
                tier=1,
                success=True
            )

        assert "tier=1" in caplog.text
        assert "memory_event=query" in caplog.text

    def test_logs_tier2_event_with_agent(self, caplog):
        """Should log Tier 2 memory event with agent ID."""
        logger = logging.getLogger("test_memory_tier2")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_memory_event(
                logger=logger,
                event_type="store",
                phone_number="+16125551234",
                tier=2,
                agent_id="agent_xyz",
                success=True
            )

        assert "tier=2" in caplog.text
        assert "agent=agent_xyz" in caplog.text

    def test_logs_failed_event_as_error(self, caplog):
        """Should log failed memory event at error level."""
        logger = logging.getLogger("test_memory_error")
        logger.setLevel(logging.INFO)

        with caplog.at_level(logging.INFO):
            log_memory_event(
                logger=logger,
                event_type="query",
                phone_number="+16125551234",
                tier=1,
                success=False,
                error="Connection timeout"
            )

        assert caplog.records[0].levelno == logging.ERROR
        assert "error=Connection timeout" in caplog.text
