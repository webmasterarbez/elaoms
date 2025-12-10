"""Utility modules for ELAOMS.

This package provides shared utilities:
- logging: Structured logging with PII protection
- http_client: Configured httpx clients for external APIs
"""

from app.utils.logging import (
    hash_phone_number,
    mask_phone_number,
    StructuredLogFormatter,
    get_structured_logger,
    log_webhook_event,
    log_openai_event,
    log_memory_event,
)
from app.utils.http_client import (
    get_openmemory_client,
    get_openai_client,
    get_elevenlabs_client,
    get_raw_client,
)

__all__ = [
    # Logging utilities
    "hash_phone_number",
    "mask_phone_number",
    "StructuredLogFormatter",
    "get_structured_logger",
    "log_webhook_event",
    "log_openai_event",
    "log_memory_event",
    # HTTP client utilities
    "get_openmemory_client",
    "get_openai_client",
    "get_elevenlabs_client",
    "get_raw_client",
]
