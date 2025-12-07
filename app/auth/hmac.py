"""HMAC authentication module for ElevenLabs webhook validation.

This module provides:
- HMAC signature verification using SHA256
- Timestamp validation with 30-minute tolerance window
- FastAPI dependency for protected endpoints

The signature format expected is: t=timestamp,v0=hash
where the hash is computed as SHA256 HMAC of {timestamp}.{request_body}
"""

import hmac
import time
from hashlib import sha256
from typing import Optional

from fastapi import Request, HTTPException, status

from app.config import settings


class HMACError(Exception):
    """Exception raised when HMAC validation fails.

    Attributes:
        message: A descriptive error message explaining the failure.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


# Tolerance window in seconds (30 minutes)
TIMESTAMP_TOLERANCE_SECONDS = 30 * 60  # 1800 seconds


def parse_signature_header(signature_header: str) -> tuple[int, str]:
    """Parse the ElevenLabs signature header format.

    Expected format: t=timestamp,v0=hash

    Args:
        signature_header: The raw signature header value.

    Returns:
        A tuple of (timestamp, hash_value).

    Raises:
        HMACError: If the header format is invalid or malformed.
    """
    if not signature_header or not signature_header.strip():
        raise HMACError("Malformed signature header: empty or missing")

    try:
        parts = signature_header.split(",")
        if len(parts) != 2:
            raise HMACError(
                "Malformed signature header: expected format t=timestamp,v0=hash"
            )

        timestamp_part = parts[0]
        hash_part = parts[1]

        # Parse timestamp
        if not timestamp_part.startswith("t="):
            raise HMACError(
                "Malformed signature header: timestamp must start with 't='"
            )
        timestamp_str = timestamp_part[2:]  # Remove 't=' prefix
        if not timestamp_str:
            raise HMACError("Malformed signature header: timestamp value is empty")

        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise HMACError(
                "Malformed signature header: timestamp must be a valid integer"
            )

        # Parse hash
        if not hash_part.startswith("v0="):
            raise HMACError("Malformed signature header: hash must start with 'v0='")
        hash_value = hash_part[3:]  # Remove 'v0=' prefix
        if not hash_value:
            raise HMACError("Malformed signature header: hash value is empty")

        return timestamp, hash_value

    except HMACError:
        raise
    except Exception as e:
        raise HMACError(f"Malformed signature header: failed to parse - {str(e)}")


def validate_timestamp(timestamp: int) -> None:
    """Validate that the timestamp is within the tolerance window.

    The tolerance window is 30 minutes (1800 seconds) from the current time.

    Args:
        timestamp: Unix timestamp from the signature header.

    Raises:
        HMACError: If the timestamp is expired (outside tolerance window).
    """
    current_time = int(time.time())
    tolerance_cutoff = current_time - TIMESTAMP_TOLERANCE_SECONDS

    if timestamp < tolerance_cutoff:
        raise HMACError(
            f"Timestamp expired: request timestamp {timestamp} is older than "
            f"30-minute tolerance window (cutoff: {tolerance_cutoff})"
        )


def compute_signature(timestamp: int, body: str, secret: str) -> str:
    """Compute the expected HMAC signature.

    The signature is computed as SHA256 HMAC of {timestamp}.{body}
    using the provided secret as the key.

    Args:
        timestamp: Unix timestamp from the signature header.
        body: The raw request body as a string.
        secret: The HMAC secret key.

    Returns:
        The computed signature hash as a hex string.
    """
    full_payload = f"{timestamp}.{body}"
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=full_payload.encode("utf-8"),
        digestmod=sha256,
    )
    return mac.hexdigest()


def verify_signature(
    signature_header: Optional[str],
    body: str,
    secret: str,
) -> bool:
    """Verify the HMAC signature from the request.

    This function:
    1. Validates the signature header is present
    2. Parses the timestamp and hash from the header
    3. Validates the timestamp is within tolerance
    4. Computes the expected signature
    5. Compares signatures using constant-time comparison

    Args:
        signature_header: The value of the 'elevenlabs-signature' header.
        body: The raw request body as a string.
        secret: The HMAC secret key (ELEVENLABS_POST_CALL_KEY).

    Returns:
        True if the signature is valid.

    Raises:
        HMACError: If validation fails for any reason.
    """
    # Check for missing header
    if signature_header is None:
        raise HMACError("Missing required 'elevenlabs-signature' header")

    # Parse the signature header
    timestamp, received_hash = parse_signature_header(signature_header)

    # Validate timestamp
    validate_timestamp(timestamp)

    # Compute expected signature
    expected_hash = compute_signature(timestamp, body, secret)

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HMACError("Invalid signature: computed hash does not match received hash")

    return True


async def verify_api_key(request: Request) -> None:
    """FastAPI dependency for X-Api-Key header verification.

    This dependency validates the X-Api-Key header against the configured
    ELEVENLABS_CLIENT_DATA_KEY. Used for the client-data webhook authentication.

    Usage:
        @app.post("/webhook/client-data")
        async def client_data_webhook(
            request: ClientDataRequest,
            _: None = Depends(verify_api_key)
        ):
            ...

    Args:
        request: The FastAPI Request object.

    Raises:
        HTTPException: 401 Unauthorized if API key validation fails.
    """
    api_key = request.headers.get("X-Api-Key")
    expected_key = settings.ELEVENLABS_CLIENT_DATA_KEY

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required 'X-Api-Key' header",
        )

    if not hmac.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


async def verify_hmac_signature(request: Request) -> None:
    """FastAPI dependency for HMAC signature verification.

    This dependency should be used on endpoints that require HMAC authentication,
    specifically the post-call webhook.

    Usage:
        @app.post("/webhook/post-call")
        async def post_call_webhook(
            request: Request,
            _: None = Depends(verify_hmac_signature)
        ):
            ...

    Args:
        request: The FastAPI Request object.

    Raises:
        HTTPException: 401 Unauthorized if signature validation fails.
    """
    # Get the signature header
    signature_header = request.headers.get("elevenlabs-signature")

    # Read the raw request body
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8")

    # Get the secret from settings
    secret = settings.ELEVENLABS_POST_CALL_KEY

    try:
        verify_signature(
            signature_header=signature_header,
            body=body,
            secret=secret,
        )
    except HMACError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"HMAC authentication failed: {e.message}",
        )