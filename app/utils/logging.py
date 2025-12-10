"""Structured logging utilities with PII protection.

This module provides:
- Phone number hashing for PII protection in logs
- Structured JSON logging formatter
- Helper functions for consistent log formatting
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional


def hash_phone_number(phone_number: str) -> str:
    """Hash a phone number for safe logging.

    Creates a consistent 8-character hash of the phone number
    that can be used to correlate logs without exposing PII.

    Args:
        phone_number: The phone number to hash (E.164 format)

    Returns:
        8-character hash string prefixed with 'ph_'
    """
    if not phone_number:
        return "ph_unknown"

    # Use SHA-256 and take first 8 chars for brevity
    hash_bytes = hashlib.sha256(phone_number.encode()).hexdigest()[:8]
    return f"ph_{hash_bytes}"


def mask_phone_number(phone_number: str) -> str:
    """Mask a phone number showing only last 4 digits.

    Args:
        phone_number: The phone number to mask

    Returns:
        Masked phone number like "+1***5551234"
    """
    if not phone_number or len(phone_number) < 4:
        return "***"

    # Keep country code and last 4 digits
    if phone_number.startswith("+"):
        return f"+{'*' * (len(phone_number) - 5)}{phone_number[-4:]}"
    return f"{'*' * (len(phone_number) - 4)}{phone_number[-4:]}"


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs logs in JSON format suitable for log aggregation tools
    like CloudWatch, Datadog, or Grafana Loki.

    Automatically hashes phone numbers found in log messages.
    """

    # Regex to find phone numbers in E.164 format
    PHONE_PATTERN = re.compile(r'\+\d{10,15}')

    def __init__(self, include_timestamp: bool = True):
        """Initialize the formatter.

        Args:
            include_timestamp: Whether to include ISO timestamp in output
        """
        super().__init__()
        self.include_timestamp = include_timestamp

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": self._sanitize_message(record.getMessage()),
        }

        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add extra fields if present
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        if hasattr(record, "caller_hash"):
            log_data["caller_hash"] = record.caller_hash
        if hasattr(record, "scenario"):
            log_data["scenario"] = record.scenario
        if hasattr(record, "response_time_ms"):
            log_data["response_time_ms"] = record.response_time_ms
        if hasattr(record, "cache_hit"):
            log_data["cache_hit"] = record.cache_hit

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def _sanitize_message(self, message: str) -> str:
        """Sanitize log message by hashing phone numbers.

        Args:
            message: Original log message

        Returns:
            Sanitized message with hashed phone numbers
        """
        def replace_phone(match):
            return hash_phone_number(match.group(0))

        return self.PHONE_PATTERN.sub(replace_phone, message)


def get_structured_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger configured for structured JSON output.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(handler)

    return logger


def log_webhook_event(
    logger: logging.Logger,
    event_type: str,
    phone_number: str,
    agent_id: str,
    scenario: Optional[str] = None,
    response_time_ms: Optional[float] = None,
    cache_hit: Optional[bool] = None,
    extra: Optional[dict[str, Any]] = None
) -> None:
    """Log a webhook event with structured data.

    Provides a consistent format for webhook-related logs
    with automatic PII hashing.

    Args:
        logger: Logger instance
        event_type: Type of event (e.g., "client_data_request", "post_call_complete")
        phone_number: Caller's phone number (will be hashed)
        agent_id: Agent ID
        scenario: Decision scenario (e.g., "returning_with_greeting")
        response_time_ms: Response time in milliseconds
        cache_hit: Whether agent cache was hit
        extra: Additional data to include
    """
    caller_hash = hash_phone_number(phone_number)

    # Build log record with extra fields
    log_extra = {
        "agent_id": agent_id,
        "caller_hash": caller_hash,
    }

    if scenario:
        log_extra["scenario"] = scenario
    if response_time_ms is not None:
        log_extra["response_time_ms"] = response_time_ms
    if cache_hit is not None:
        log_extra["cache_hit"] = cache_hit

    if extra:
        log_extra.update(extra)

    # Create log message
    message_parts = [f"event={event_type}", f"agent={agent_id}", f"caller={caller_hash}"]
    if scenario:
        message_parts.append(f"scenario={scenario}")
    if response_time_ms is not None:
        message_parts.append(f"time={response_time_ms:.1f}ms")

    message = " ".join(message_parts)

    # Log with extra fields
    logger.info(message, extra=log_extra)


def log_openai_event(
    logger: logging.Logger,
    event_type: str,
    phone_number: str,
    agent_id: str,
    success: bool,
    tokens_used: Optional[int] = None,
    latency_ms: Optional[float] = None,
    error: Optional[str] = None
) -> None:
    """Log an OpenAI API event.

    Args:
        logger: Logger instance
        event_type: Event type (e.g., "greeting_generation")
        phone_number: Caller's phone number (will be hashed)
        agent_id: Agent ID
        success: Whether the API call succeeded
        tokens_used: Number of tokens used
        latency_ms: API latency in milliseconds
        error: Error message if failed
    """
    caller_hash = hash_phone_number(phone_number)

    message_parts = [
        f"openai_event={event_type}",
        f"agent={agent_id}",
        f"caller={caller_hash}",
        f"success={success}"
    ]

    if tokens_used is not None:
        message_parts.append(f"tokens={tokens_used}")
    if latency_ms is not None:
        message_parts.append(f"latency={latency_ms:.1f}ms")
    if error:
        message_parts.append(f"error={error}")

    message = " ".join(message_parts)

    if success:
        logger.info(message)
    else:
        logger.error(message)


def log_memory_event(
    logger: logging.Logger,
    event_type: str,
    phone_number: str,
    tier: int,
    agent_id: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """Log a memory operation event.

    Args:
        logger: Logger instance
        event_type: Event type (e.g., "query", "store")
        phone_number: Caller's phone number (will be hashed)
        tier: Memory tier (1 or 2)
        agent_id: Agent ID (required for Tier 2)
        success: Whether the operation succeeded
        error: Error message if failed
    """
    caller_hash = hash_phone_number(phone_number)

    message_parts = [
        f"memory_event={event_type}",
        f"tier={tier}",
        f"caller={caller_hash}",
        f"success={success}"
    ]

    if agent_id:
        message_parts.append(f"agent={agent_id}")
    if error:
        message_parts.append(f"error={error}")

    message = " ".join(message_parts)

    if success:
        logger.info(message)
    else:
        logger.error(message)
