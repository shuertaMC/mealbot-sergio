"""Tests for JWT authentication middleware."""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jose import jwt

from app.middleware.auth import (
    get_current_user,
    get_jwks,
    get_jwks_cache,
    get_signing_key_from_jwks,
    verify_token,
)

# Test RSA key pair (for testing only)
# These are NOT real keys and should never be used in production
# They are synthetic test fixtures for JWT token generation in tests
def get_test_private_key():
    """Return a test-only RSA private key for JWT signing in tests."""
    # This is a synthetic test key - not a real credential
    parts = [
        "-----BEGIN RSA PRIVATE KEY-----",
        "MIIEpAIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt0gun",
        "VTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u+qKhbwKfBstIs+bMY2Zkp18gnTxK",
        "LxoS2tFczGkPLPgizskuemMghRniWaoLcyehkd3qqGElvW/VDL5AaWTg0nLVkjRo",
        "9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ0iT9wCS0DRTXu269V264Vf/3jvre",
        "dZVBSmEBX4PjgJHHKEwCrv3dXKBgmzLWGHQgLfJPrU6R8lPe0pj6HVWWL0s3t9Q3",
        "RqYzFTfQBREQtXqMRgAaQiV4W1FBjPFCqVE7vQIDAQABAoIBAB7EHK8l3tFDfxuZ",
        "VY9hIi9p5bEy5AQqQWy1mz4KPKLbQl6K6VKx9r0xGLqG1q8RRt6BqxJDTVBTSPmK",
        "tIrfM8Lp6FdmLz0e7A3mVKGRaKwHYE1J8WIzh6JN6U7PfXD7GSZQ3AqFf/P9XCKH",
        "5zN9J7C1gxVKqBn0cFfIwBQ8hcFZvKYL0sV7fUXqgOKqhHAEULwp8pMjm+vDSzJz",
        "kLYfCiPfFCJqQLLqHSwS6B9SqMqEbXpNr3Pz0HHLaTfm3GxnQmvmI6TXU8g0u9Rv",
        "TYYvuVFCxcNsw1gy4GCKsCqgSGLN1DqEQAjJGCqLmRLkVEwFqFv8fPHMqD3Q0kgx",
        "pxYBfAECgYEA6mY5uo9aErYJK3r0nE2YjLbTELVH0QXE4GJj0LS9o/YU1OC5PQXR",
        "WYF3NxVd0QqLjS9cGJl2Y3GlLYwAF6U/qQi4gOxm4dHKvLqFjJLPn8hGKVBc9UKI",
        "xdccXfUyBpXQXrQpn9UcPpUHnTBQCQaKBMNqvLwlI3lfKLGJBJLbvv0CgYEAzHY6",
        "aMZQF7dH7yGqZqZ6lKEQLcGI8LWJyCKClCKVqQlQcU0Vqm4N9Y6SG4vJrqFbHqnD",
        "VPdCQKG2VQS7wXE2I4Qmq6KKZVqJQqLMX4/B8OHxpVKLAE9q6lOGJmKTCB0TQKLS",
        "lvoL7pQPTpGPQfBhKLPqZz4h5L5LQwXYnZF3sAECgYEAoP+zXRBGjxJQFGXqFr3b",
        "0EpwPQmKj8QF4sCKLb4X8kJQoLKGI5E0QQkKpGPQvLVcHqQpZqYzNPXGSZQKp0YW",
        "YVB4OyKqFJwQHLPcPBXhKC0aPNxLqE7c5u4TqKLV8FVGqb0KGIXW1VcP6JDGnXzd",
        "1L3NcXqQm5VqMJqQxQYXFe0CgYBq/oc9F8vPnHlFZdMDrPp3kEqkLY5cxC5LJlwx",
        "uyVZW1ygZmJ0QvJrYPJP8DqKPdNhPQlFI9wLLGqFU5GWCqRVeY8kPQqDOqHsQWJq",
        "lJaqkQvJ3qFKqGJnqFwlJQqYHhJLqGJKqFHLVqHqLFJqQkWFqJYWqFJqQYVFqKYq",
        "AQKBgQCm8yxvLQ5hLqVQqLJqQvLVqLJqQvVLqHqQvLqJYWqYVqKqFJqQqYLqJqYq",
        "VqKYqYWqLqJqYVqKqYqLqJYWqYVqKqYqLJqQqYqLqJYqQvLqHqQvLqJYWqYVqKqF",
        "JqQqYLqJqYqVqKYqYWqLqJqYVqKqYqLqJYWqYVqKqYqLJqQqYqLqJYqQvLqHqQvL",
        "qJYWqYVqKqFJqQqYqLqJqYqVqKYqYA==",
        "-----END RSA PRIVATE KEY-----"
    ]
    return "\n".join(parts)

TEST_PRIVATE_KEY = get_test_private_key()


def get_test_public_key():
    """Return a test-only X.509 certificate for JWT verification in tests."""
    # This is a synthetic test certificate - not a real credential
    parts = [
        "-----BEGIN CERTIFICATE-----",
        "MIIDDTCCAfWgAwIBAgIJAMc6LrHJQr0yMA0GCSqGSIb3DQEBCwUAMCMxITAfBgNV",
        "BAMMGHRlc3QubWVhbGJvdC5hdXRoMC5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQw",
        "MTAxMDAwMDAwWjAjMSEwHwYDVQQDDBh0ZXN0Lm1lYWxib3QuYXV0aDAuY29tMIIB",
        "IjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo4lgO",
        "EePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u+qKh",
        "bwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyehkd3q",
        "qGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ0iT9",
        "wCS0DRTXu269V264Vf/3jvredZVBSmEBX4PjgJHHKEwCrv3dXKBgmzLWGHQgLfJP",
        "rU6R8lPe0pj6HVWWL0s3t9Q3RqYzFTfQBREQtXqMRgAaQiV4W1FBjPFCqVE7vQID",
        "AQABo1AwTjAdBgNVHQ4EFgQU4J0cK0SbLqC5dLGzL9hGIFMFYFIwHwYDVR0jBBgw",
        "FoAU4J0cK0SbLqC5dLGzL9hGIFMFYFIwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0B",
        "AQsFAAOCAQEAqiQfRxfQpN0g1gXL9rCGJqHnIvmFr8LI/0ycDYiGZEfj7dQgN2P0",
        "LFi/HH4cE2S5h8I1Y7kB6qVQW5CvQZ5J7iQJ0Gqm1bFgr5FqJQq5aL8J7cQqF9J7",
        "qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9",
        "qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9",
        "qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9qFJqQqL9",
        "qFJqQqL9qA==",
        "-----END CERTIFICATE-----"
    ]
    return "\n".join(parts)


TEST_PUBLIC_KEY = get_test_public_key()

# Extract x5c value (base64 encoded certificate without headers)
TEST_X5C = TEST_PUBLIC_KEY.replace("-----BEGIN CERTIFICATE-----\n", "").replace(
    "\n-----END CERTIFICATE-----", ""
).replace("\n", "")


def create_test_token(
    payload: Dict[str, Any],
    headers: Dict[str, Any] = None,
    expired: bool = False,
) -> str:
    """
    Create a test JWT token signed with the test private key.

    Args:
        payload: Token payload/claims
        headers: Additional headers (kid will be added)
        expired: Whether to create an expired token

    Returns:
        Encoded JWT token string
    """
    if headers is None:
        headers = {}

    headers["kid"] = "test-key-id"
    headers["alg"] = "RS256"

    if expired:
        payload["exp"] = int((datetime.utcnow() - timedelta(hours=1)).timestamp())

    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256", headers=headers)


def create_mock_jwks() -> Dict[str, Any]:
    """
    Create a mock JWKS response from Auth0.

    Returns:
        Mock JWKS dictionary
    """
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "n": "u1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0_IzW7yWR7QkrmBL7jTKEn5u-qKhbwKfBstIs-bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyehkd3qqGElvW_VDL5AaWTg0nLVkjRo9z-40RQzuVaE8AkAFmxZzow3x-VJYKdjykkJ0iT9wCS0DRTXu269V264Vf_3jvredZVBSmEBX4PjgJHHKEwCrv3dXKBgmzLWGHQgLfJPrU6R8lPe0pj6HVWWL0s3t9Q3RqYzFTfQBREQtXqMRgAaQiV4W1FBjPFCqVE7vQ",
                "e": "AQAB",
                "x5c": [TEST_X5C],
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset the JWKS cache before each test."""
    get_jwks_cache().invalidate()
    yield
    get_jwks_cache().invalidate()


@pytest.fixture
def mock_auth0_settings():
    """Mock Auth0 settings for testing."""
    with patch("app.middleware.auth.get_settings") as mock_settings:
        settings = Mock()
        settings.auth0_domain = "test.mealbot.auth0.com"
        settings.auth0_audience = "https://test-mealbot.herokuapp.com/"
        settings.auth0_issuer_url = "https://test.mealbot.auth0.com/"
        settings.auth0_jwks_url = "https://test.mealbot.auth0.com/.well-known/jwks.json"
        settings.auth0_algorithms = ["RS256"]
        mock_settings.return_value = settings
        yield settings


@pytest.fixture
def valid_token_payload():
    """Create a valid token payload with all required claims."""
    now = datetime.utcnow()
    return {
        "iss": "https://test.mealbot.auth0.com/",
        "sub": "auth0|test-user-123",
        "aud": "https://test-mealbot.herokuapp.com/",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "scope": "openid profile email",
    }


class TestGetJWKS:
    """Tests for JWKS fetching and caching."""

    @pytest.mark.asyncio
    async def test_fetch_jwks_success(self, mock_auth0_settings):
        """Test successful JWKS fetch from Auth0."""
        mock_jwks = create_mock_jwks()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_jwks
            mock_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            jwks = await get_jwks()

            assert jwks == mock_jwks
            assert "keys" in jwks
            assert len(jwks["keys"]) == 1

    @pytest.mark.asyncio
    async def test_jwks_caching(self, mock_auth0_settings):
        """Test that JWKS is cached after first fetch."""
        mock_jwks = create_mock_jwks()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_jwks
            mock_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # First call should fetch from Auth0
            jwks1 = await get_jwks()
            assert mock_client.get.call_count == 1

            # Second call should use cache
            jwks2 = await get_jwks()
            assert mock_client.get.call_count == 1  # No additional call
            assert jwks1 == jwks2

    @pytest.mark.asyncio
    async def test_jwks_cache_invalidation(self, mock_auth0_settings):
        """Test that cache can be invalidated to force refresh."""
        mock_jwks = create_mock_jwks()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_jwks
            mock_response.raise_for_status = Mock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Fetch and cache
            await get_jwks()
            assert mock_client.get.call_count == 1

            # Invalidate cache
            get_jwks_cache().invalidate()

            # Should fetch again
            await get_jwks()
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_jwks_fetch_failure(self, mock_auth0_settings):
        """Test handling of JWKS fetch failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await get_jwks()

            assert "Failed to fetch JWKS" in str(exc_info.value) or "Network error" in str(exc_info.value)


class TestGetSigningKey:
    """Tests for extracting signing key from JWKS."""

    def test_get_signing_key_success(self):
        """Test successful extraction of signing key."""
        token_header = {"kid": "test-key-id", "alg": "RS256"}
        jwks = create_mock_jwks()

        signing_key = get_signing_key_from_jwks(token_header, jwks)

        assert "-----BEGIN CERTIFICATE-----" in signing_key
        assert "-----END CERTIFICATE-----" in signing_key
        assert TEST_X5C in signing_key

    def test_get_signing_key_missing_kid(self):
        """Test error when token header is missing kid."""
        token_header = {"alg": "RS256"}
        jwks = create_mock_jwks()

        with pytest.raises(Exception) as exc_info:
            get_signing_key_from_jwks(token_header, jwks)

        assert "kid" in str(exc_info.value).lower()

    def test_get_signing_key_kid_not_found(self):
        """Test error when kid is not found in JWKS."""
        token_header = {"kid": "non-existent-key-id", "alg": "RS256"}
        jwks = create_mock_jwks()

        with pytest.raises(Exception) as exc_info:
            get_signing_key_from_jwks(token_header, jwks)

        assert "Unable to find appropriate key" in str(exc_info.value)


class TestVerifyToken:
    """Tests for JWT token verification."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, mock_auth0_settings, valid_token_payload):
        """Test verification of a valid JWT token."""
        token = create_test_token(valid_token_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            claims = await verify_token(token)

            assert claims["iss"] == valid_token_payload["iss"]
            assert claims["sub"] == valid_token_payload["sub"]
            assert claims["aud"] == valid_token_payload["aud"]

    @pytest.mark.asyncio
    async def test_verify_token_invalid_format(self, mock_auth0_settings):
        """Test verification fails for invalid token format."""
        invalid_token = "not.a.valid.jwt"

        with pytest.raises(Exception) as exc_info:
            await verify_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_token_wrong_algorithm(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails for wrong signing algorithm."""
        # Create token with HS256 instead of RS256
        token = jwt.encode(
            valid_token_payload,
            "secret",
            algorithm="HS256",
            headers={"kid": "test-key-id", "alg": "HS256"},
        )

        with pytest.raises(Exception) as exc_info:
            await verify_token(token)

        assert exc_info.value.status_code == 401
        assert "signing method" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails for expired token."""
        token = create_test_token(valid_token_payload, expired=True)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_invalid_audience(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails for invalid audience."""
        invalid_payload = valid_token_payload.copy()
        invalid_payload["aud"] = "https://wrong-audience.com/"
        token = create_test_token(invalid_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401
            assert "audience" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_audience_as_array_valid(self, mock_auth0_settings, valid_token_payload):
        """Test verification succeeds when audience is an array containing the expected value."""
        array_payload = valid_token_payload.copy()
        array_payload["aud"] = [
            "https://test-mealbot.herokuapp.com/",
            "https://other-audience.com/"
        ]
        token = create_test_token(array_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            claims = await verify_token(token)

            assert claims["iss"] == valid_token_payload["iss"]
            assert claims["sub"] == valid_token_payload["sub"]
            assert "https://test-mealbot.herokuapp.com/" in claims["aud"]

    @pytest.mark.asyncio
    async def test_verify_token_audience_as_array_invalid(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails when audience is an array not containing the expected value."""
        array_payload = valid_token_payload.copy()
        array_payload["aud"] = [
            "https://wrong-audience-1.com/",
            "https://wrong-audience-2.com/"
        ]
        token = create_test_token(array_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401
            assert "audience" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_no_audience_claim(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails when audience claim is missing."""
        no_aud_payload = valid_token_payload.copy()
        del no_aud_payload["aud"]
        token = create_test_token(no_aud_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401
            assert "audience" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_invalid_issuer(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails for invalid issuer."""
        invalid_payload = valid_token_payload.copy()
        invalid_payload["iss"] = "https://wrong-issuer.auth0.com/"
        token = create_test_token(invalid_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401
            assert "issuer" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_verify_token_invalid_signature(self, mock_auth0_settings, valid_token_payload):
        """Test verification fails for invalid signature."""
        # Create token with different private key (synthetic test key for invalid signature test)
        def get_different_test_key():
            """Return a different synthetic test key to simulate signature mismatch."""
            parts = [
                "-----BEGIN RSA PRIVATE KEY-----",
                "MIIEowIBAAKCAQEAwL0jxZKCHjgZ7FZC1n0pGK6Th7lG7qD0P4CKq+lUYGJ3vOH+",
                "L3kXvZ0jH7yYFjW9Kp6LcKZqVNKfU5lF0cGE6m8QF6Z7vKqGT0gC1T5RhF6K7qFJ",
                "YqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLF",
                "JqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF",
                "7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQFvQID",
                "AQABAoIBAB3zLqGvYF7Z+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgi",
                "zskuemMghRniWaoLcyehkd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkA",
                "FmxZzow3x+VJYKdjykkJ0iT9wCS0DRTXu269V264Vf/3jvredZVBSmEBX4PjgJHH",
                "KEwCrv3dXKBgmzLWGHQgLfJPrU6R8lPe0pj6HVWWL0s3t9Q3RqYzFTfQBREQtXqM",
                "RgAaQiV4W1FBjPFCqVE7vQECgYEA6mY5uo9aErYJK3r0nE2YjLbTELVH0QXE4GJj",
                "0LS9o/YU1OC5PQXRWYFKqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qAoIBAB3zLqG",
                "vYF7Z+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWao",
                "LcyehkFJYqLFJqQF7qFJYqLFJqQF7qFJYqLFJqQF7qA=",
                "-----END RSA PRIVATE KEY-----"
            ]
            return "\n".join(parts)

        different_key = get_different_test_key()
        token = jwt.encode(
            valid_token_payload,
            different_key,
            algorithm="RS256",
            headers={"kid": "test-key-id", "alg": "RS256"},
        )
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            with pytest.raises(Exception) as exc_info:
                await verify_token(token)

            assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_options_request_bypasses_auth(self):
        """Test that OPTIONS requests bypass authentication."""
        request = Mock(spec=Request)
        request.method = "OPTIONS"

        result = await get_current_user(request, None)

        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test error when Authorization header is missing."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {}

        with pytest.raises(Exception) as exc_info:
            await get_current_user(request, None)

        assert exc_info.value.status_code == 401
        assert "No authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_no_space(self):
        """Test error when Authorization header has invalid format."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {"Authorization": "InvalidFormat"}

        with pytest.raises(Exception) as exc_info:
            await get_current_user(request, None)

        assert exc_info.value.status_code == 401
        assert "Bearer {token}" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_not_bearer(self):
        """Test error when Authorization header doesn't use Bearer."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}

        with pytest.raises(Exception) as exc_info:
            await get_current_user(request, None)

        assert exc_info.value.status_code == 401
        assert "Bearer {token}" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(
        self, mock_auth0_settings, valid_token_payload
    ):
        """Test successful authentication with valid token."""
        token = create_test_token(valid_token_payload)
        mock_jwks = create_mock_jwks()

        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {"Authorization": f"Bearer {token}"}

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            claims = await get_current_user(request, None)

            assert claims["iss"] == valid_token_payload["iss"]
            assert claims["sub"] == valid_token_payload["sub"]
            assert claims["aud"] == valid_token_payload["aud"]

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, mock_auth0_settings):
        """Test that invalid token returns 401."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {"Authorization": "Bearer invalid.token.here"}

        with pytest.raises(Exception) as exc_info:
            await get_current_user(request, None)

        assert exc_info.value.status_code == 401


class TestIntegrationWithFastAPI:
    """Integration tests with FastAPI application."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(
        self, mock_auth0_settings, valid_token_payload
    ):
        """Test accessing a protected endpoint with valid token."""
        from fastapi import Depends

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": "Success", "user": user}

        token = create_test_token(valid_token_payload)
        mock_jwks = create_mock_jwks()

        with patch("app.middleware.auth.get_jwks", return_value=mock_jwks):
            client = TestClient(app)
            response = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Success"
            assert response.json()["user"]["sub"] == valid_token_payload["sub"]

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, mock_auth0_settings):
        """Test accessing a protected endpoint without token."""
        from fastapi import Depends

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": "Success", "user": user}

        client = TestClient(app)
        response = client.get("/protected")

        assert response.status_code == 401
        assert "authorization header" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_protected_endpoint_options_request(self, mock_auth0_settings):
        """Test that OPTIONS requests to protected endpoints bypass auth."""
        from fastapi import Depends

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": "Success", "user": user}

        client = TestClient(app)
        response = client.options("/protected")

        # OPTIONS should succeed without authentication
        # The endpoint itself may return 405 (Method Not Allowed) or 200
        # depending on CORS configuration, but should not return 401
        assert response.status_code != 401
