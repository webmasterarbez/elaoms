"""Tests for authentication modules.

This module contains tests for:

HMAC Authentication (5 tests):
1. Test valid signature passes verification
2. Test invalid signature returns 401
3. Test expired timestamp (>30 min) returns 401
4. Test malformed signature header returns 401
5. Test missing signature header returns 401

X-Api-Key Authentication (3 tests):
1. Test valid API key passes verification
2. Test invalid API key returns 401
3. Test missing API key returns 401
"""

import hmac
import time
from hashlib import sha256
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient


class TestHMACAuthentication:
    """Test suite for HMAC authentication functionality."""

    def _generate_valid_signature(
        self, payload: str, secret: str, timestamp: int | None = None
    ) -> str:
        """Generate a valid HMAC signature for testing.

        Args:
            payload: The request body as a string.
            secret: The HMAC secret key.
            timestamp: Unix timestamp (defaults to current time).

        Returns:
            The formatted signature header value: t=timestamp,v0=hash
        """
        if timestamp is None:
            timestamp = int(time.time())

        full_payload = f"{timestamp}.{payload}"
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=sha256,
        )
        signature_hash = mac.hexdigest()
        return f"t={timestamp},v0={signature_hash}"

    def test_valid_signature_passes_verification(self) -> None:
        """Test that a valid HMAC signature passes verification."""
        from app.auth.hmac import verify_signature, HMACError

        secret = "test_secret_key_12345"
        payload = '{"type": "post_call_transcription", "data": {}}'
        timestamp = int(time.time())

        signature_header = self._generate_valid_signature(payload, secret, timestamp)

        # Should not raise an exception
        result = verify_signature(
            signature_header=signature_header,
            body=payload,
            secret=secret,
        )
        assert result is True

    def test_invalid_signature_returns_401(self) -> None:
        """Test that an invalid HMAC signature raises an error (results in 401)."""
        from app.auth.hmac import verify_signature, HMACError

        secret = "test_secret_key_12345"
        payload = '{"type": "post_call_transcription", "data": {}}'
        timestamp = int(time.time())

        # Generate signature with correct secret, then verify with wrong secret
        signature_header = self._generate_valid_signature(payload, secret, timestamp)

        # Use a different secret for verification - should fail
        wrong_secret = "wrong_secret_key"
        with pytest.raises(HMACError) as exc_info:
            verify_signature(
                signature_header=signature_header,
                body=payload,
                secret=wrong_secret,
            )

        assert "Invalid signature" in str(exc_info.value)

    def test_expired_timestamp_returns_401(self) -> None:
        """Test that an expired timestamp (>30 min) raises an error (results in 401)."""
        from app.auth.hmac import verify_signature, HMACError

        secret = "test_secret_key_12345"
        payload = '{"type": "post_call_transcription", "data": {}}'
        # Set timestamp to 31 minutes ago (beyond 30-minute tolerance)
        expired_timestamp = int(time.time()) - (31 * 60)

        signature_header = self._generate_valid_signature(
            payload, secret, expired_timestamp
        )

        with pytest.raises(HMACError) as exc_info:
            verify_signature(
                signature_header=signature_header,
                body=payload,
                secret=secret,
            )

        assert "expired" in str(exc_info.value).lower() or "timestamp" in str(
            exc_info.value
        ).lower()

    def test_malformed_signature_header_returns_401(self) -> None:
        """Test that a malformed signature header raises an error (results in 401)."""
        from app.auth.hmac import verify_signature, HMACError

        secret = "test_secret_key_12345"
        payload = '{"type": "post_call_transcription", "data": {}}'

        # Test various malformed headers
        malformed_headers = [
            "invalid_format",
            "t=,v0=hash",
            "t=timestamp,v0=",
            "t=not_a_number,v0=hash",
            "only_one_part",
            "v0=hash,t=123",  # Wrong order/format
            "",
        ]

        for malformed_header in malformed_headers:
            with pytest.raises(HMACError) as exc_info:
                verify_signature(
                    signature_header=malformed_header,
                    body=payload,
                    secret=secret,
                )
            # Error message should indicate malformed header
            error_msg = str(exc_info.value).lower()
            assert (
                "malformed" in error_msg
                or "invalid" in error_msg
                or "format" in error_msg
            ), f"Expected malformed error for header: {malformed_header}"

    def test_missing_signature_header_returns_401(self) -> None:
        """Test that a missing signature header raises an error (results in 401)."""
        from app.auth.hmac import verify_signature, HMACError

        secret = "test_secret_key_12345"
        payload = '{"type": "post_call_transcription", "data": {}}'

        # Test with None header (missing)
        with pytest.raises(HMACError) as exc_info:
            verify_signature(
                signature_header=None,
                body=payload,
                secret=secret,
            )

        error_msg = str(exc_info.value).lower()
        assert "missing" in error_msg or "required" in error_msg


class TestHMACFastAPIDependency:
    """Test suite for FastAPI HMAC dependency integration."""

    def _generate_valid_signature(
        self, payload: str, secret: str, timestamp: int | None = None
    ) -> str:
        """Generate a valid HMAC signature for testing."""
        if timestamp is None:
            timestamp = int(time.time())

        full_payload = f"{timestamp}.{payload}"
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=sha256,
        )
        signature_hash = mac.hexdigest()
        return f"t={timestamp},v0={signature_hash}"

    def test_dependency_integration_valid_signature(self) -> None:
        """Test that the FastAPI dependency allows valid signatures."""
        from app.auth.hmac import verify_hmac_signature
        from app.config import Settings

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_hmac_signature)
        ):
            return {"status": "success"}

        # Mock the settings
        test_secret = "test_post_call_key_12345"
        payload = '{"test": "data"}'
        signature = self._generate_valid_signature(payload, test_secret)

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_POST_CALL_KEY = test_secret

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                content=payload,
                headers={"elevenlabs-signature": signature},
            )

            assert response.status_code == 200
            assert response.json() == {"status": "success"}

    def test_dependency_integration_invalid_signature(self) -> None:
        """Test that the FastAPI dependency rejects invalid signatures."""
        from app.auth.hmac import verify_hmac_signature

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_hmac_signature)
        ):
            return {"status": "success"}

        test_secret = "test_post_call_key_12345"
        wrong_secret = "wrong_secret"
        payload = '{"test": "data"}'
        # Generate signature with wrong secret
        signature = self._generate_valid_signature(payload, wrong_secret)

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_POST_CALL_KEY = test_secret

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                content=payload,
                headers={"elevenlabs-signature": signature},
            )

            assert response.status_code == 401

    def test_dependency_integration_missing_signature(self) -> None:
        """Test that the FastAPI dependency rejects missing signatures."""
        from app.auth.hmac import verify_hmac_signature

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_hmac_signature)
        ):
            return {"status": "success"}

        test_secret = "test_post_call_key_12345"
        payload = '{"test": "data"}'

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_POST_CALL_KEY = test_secret

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                content=payload,
                # No signature header
            )

            assert response.status_code == 401


class TestApiKeyAuthentication:
    """Test suite for X-Api-Key authentication functionality."""

    def test_valid_api_key_passes_verification(self) -> None:
        """Test that a valid X-Api-Key passes verification."""
        from app.auth.hmac import verify_api_key

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_api_key)
        ):
            return {"status": "success"}

        test_api_key = "test_api_key_12345"

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_CLIENT_DATA_KEY = test_api_key

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                json={"test": "data"},
                headers={"X-Api-Key": test_api_key},
            )

            assert response.status_code == 200
            assert response.json() == {"status": "success"}

    def test_invalid_api_key_returns_401(self) -> None:
        """Test that an invalid X-Api-Key returns 401."""
        from app.auth.hmac import verify_api_key

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_api_key)
        ):
            return {"status": "success"}

        test_api_key = "test_api_key_12345"
        wrong_api_key = "wrong_api_key"

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_CLIENT_DATA_KEY = test_api_key

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                json={"test": "data"},
                headers={"X-Api-Key": wrong_api_key},
            )

            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]

    def test_missing_api_key_returns_401(self) -> None:
        """Test that a missing X-Api-Key header returns 401."""
        from app.auth.hmac import verify_api_key

        # Create a test app with the dependency
        app = FastAPI()

        @app.post("/test-endpoint")
        async def test_endpoint(
            request: Request, _: None = Depends(verify_api_key)
        ):
            return {"status": "success"}

        test_api_key = "test_api_key_12345"

        with patch("app.auth.hmac.settings") as mock_settings:
            mock_settings.ELEVENLABS_CLIENT_DATA_KEY = test_api_key

            client = TestClient(app)
            response = client.post(
                "/test-endpoint",
                json={"test": "data"},
                # No X-Api-Key header
            )

            assert response.status_code == 401
            assert "Missing" in response.json()["detail"]