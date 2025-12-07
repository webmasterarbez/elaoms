"""Authentication utilities including HMAC validation.

This module provides authentication functionality for webhook endpoints:
- HMAC signature verification for ElevenLabs webhooks
- FastAPI dependencies for protected endpoints
"""

from app.auth.hmac import (
    HMACError,
    verify_signature,
    verify_hmac_signature,
    verify_api_key,
    parse_signature_header,
    validate_timestamp,
    compute_signature,
    TIMESTAMP_TOLERANCE_SECONDS,
)

__all__ = [
    "HMACError",
    "verify_signature",
    "verify_hmac_signature",
    "verify_api_key",
    "parse_signature_header",
    "validate_timestamp",
    "compute_signature",
    "TIMESTAMP_TOLERANCE_SECONDS",
]