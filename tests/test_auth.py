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
# They are valid test fixtures for JWT token generation in tests
def get_test_private_key():
    """Return a test-only RSA private key for JWT signing in tests."""
    # This is a valid test key generated for testing purposes only
    parts = [
        "-----BEGIN RSA PRIVATE KEY-----",
        "MIIEowIBAAKCAQEAzIzdfPQeL9o/kJOOVvP6IsYfh8T5+t9gjCKhMYQ0H9z0yZ+d",
        "ebPGQlNc3i+x+tdmuSDGMhGYs+rGuuL+HwEhyY7HbzlMcAs+LDza7RkJsSYuyQzQ",
        "gC+Q2zrZpk5te+4QH8+l5NpXayXTnlPp5q3SHi3fuH9Sam3ZItK3q3sTKR7OVXs6",
        "8wySN+/Q3OOWmGkgrAYL8H1qrJ5JqS4CKDtq4C905ABq7abevIFA+wocuDyExFpT",
        "iNsnRrbFFjP2Ww5kuXAVlBlzm6hXKMDcy26f+BDnz/LvAHhu9SsGAPtuOjbdd3Yn",
        "yRaEVhsCXDsRVeisr8M/sgb2eFaZaAIpzBAJPQIDAQABAoIBAALHPaGBme2QKZGP",
        "y4Mw76dF9e4sz2Q1FGh63O66/k+mrn8Ux0Y8pwP5Tv2oLxYg4FqOqfQXcWTgmrmC",
        "aHpPB3o0UZwLYddaWiPhx+uoZ1o/K97O6Rl6OLdQx12FdOIiyhgtUUvFNaKoYh7+",
        "269M+GZkCZ6fWuUREzEW1+gam37d6Vj8QTZtJQQ2Hte3diI83JpU4YqcyRJiye5y",
        "h0qfBNWKZbfiUvMmg1MNPnRs6Ag1aTXWsgWutjBrLrXHcp/KR1sVDD1g3KCukLhE",
        "sqM9r5YH9l8v31i4y21V7LHSt6+Zq5K+sU6cqRFuu4SOlqHx6UKT+KNF90V3g52H",
        "MjFNNyECgYEA/upyibp3l2nVTflZm2n6dmrSPBIRqshUNZt6sKR4GzcIoWpoOTWO",
        "hksSA8wD+rb60ginYinYtWFrR9ApNmh3bGGR9JXzPUiOkreGFftMjt60JS1dpT7P",
        "Ne4Z8exLFYF4ipOT7m+RuevMKXlTKv/UeDmSUThSn0e1gTgJ344vj50CgYEAzWuU",
        "Z7BvEBIfcTwASDLge3clGFRayULYuA6LxxjGlpQE2+DFNP2aNwGdDO8/SiJRPLDx",
        "AIiZmNdehQkG8DHUks5ErYgMlgXMRnP054ejhL/SLunkqxCbiJ/VyFvHMXIjSmMy",
        "M+myqtb1x6Xy7pDvuPGsk8GO6XqEDYUbs3U4viECgYAy2HCgKCFSgjmZo/LLnQfo",
        "NsZYVQJRHkQtrSV7tlJ+myuNhrvjLVuQTcj6GOdySq0c170LR22CQDw1xr9xqsSn",
        "SY7jSkWKI77MZO7J06YhmSo1gCb9ntmV2Dg0mP0g/QIeIfGPzZEzlGTUoO6F1SF8",
        "GX+l06YnPxZk/9h4TtQNwQKBgHND2GROZiOYZ7g8ONRKaBgfhNsgCklAjybIUrqH",
        "Nner2wYeG8peOzh+WUe2v8azdu4dQz5PaBCRWOJBbHk/HM67m2HcI2PTIQqvak64",
        "l5KXqDLW3471pLCHL4hbp2whZZgKDVN/4NdoA0Xh4mznOvyF75aBV9W+/3YuqJqM",
        "PijBAoGBALJZCugd1APqWdnbyY7cvEUEWKuCbJp7sJ4+BgdMkwiqL7zMngJVL3ec",
        "gUPuEbVBmoIB5EtnKjgNe7cfgX7WedlG38uMuWwiWGoSfkTSMP8BTwpLM3/KzNji",
        "kBirs9kZEAiePGuWQRqU4PmB9UK3p/vDTDjc/MqaQsQ4pYI/6RvX",
        "-----END RSA PRIVATE KEY-----"
    ]
    return "\n".join(parts)

TEST_PRIVATE_KEY = get_test_private_key()


def get_test_public_key():
    """Return a test-only X.509 certificate for JWT verification in tests."""
    # This is a valid test certificate generated for testing purposes only
    parts = [
        "-----BEGIN CERTIFICATE-----",
        "MIICzjCCAbagAwIBAgIUFoqY7ZNPm29JvjZsJjFugbtRpiQwDQYJKoZIhvcNAQEL",
        "BQAwITEfMB0GA1UEAwwWdGVzdC5tZWFsYm90LmF1dGgwLmNvbTAeFw0yNDAxMDEw",
        "MDAwMDBaFw0zNDAxMDEwMDAwMDBaMCExHzAdBgNVBAMMFnRlc3QubWVhbGJvdC5h",
        "dXRoMC5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMjN189B4v",
        "2j+Qk45W8/oixh+HxPn632CMIqExhDQf3PTJn515s8ZCU1zeL7H612a5IMYyEZiz",
        "6sa64v4fASHJjsdvOUxwCz4sPNrtGQmxJi7JDNCAL5DbOtmmTm177hAfz6Xk2ldr",
        "JdOeU+nmrdIeLd+4f1Jqbdki0rerexMpHs5VezrzDJI379Dc45aYaSCsBgvwfWqs",
        "nkmpLgIoO2rgL3TkAGrtpt68gUD7Chy4PITEWlOI2ydGtsUWM/ZbDmS5cBWUGXOb",
        "qFcowNzLbp/4EOfP8u8AeG71KwYA+246Nt13difJFoRWGwJcOxFV6Kyvwz+yBvZ4",
        "VploAinMEAk9AgMBAAEwDQYJKoZIhvcNAQELBQADggEBADaB0SYtobjdvKzEi+0s",
        "FgcEBLpZ38/0Jsv/pD9vc9XS8UHrMvPk8XwmPye8amfbfvWNKpx7i4LFBQfyoVsC",
        "Mpgm7w6opQZNcupHN6pZ46yN+BR3yi+qU6kKdQNG9bCeCgMA/ZkZYwHOPsIllF5X",
        "ulSyLnNEZpQCPmxnUQx6vW5NSNBeYOZWKjdF63K8QiqtYaT6sH/dLKXlh4qQbfk3",
        "PibN/nR/R0UgcVBsS7WVYytE1fTwQhjJZnuR4YpNciwoms5JJq6VAZ4FayrEVz2T",
        "NvQvYCn+goR3iNJJjNmlGKpWO8FUdUBSLIIW2lEohrJYcO+Qm1tuLEN+HEixw6xq",
        "sY8=",
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
        # Create token with different private key (valid test key for invalid signature test)
        def get_different_test_key():
            """Return a different valid test key to simulate signature mismatch."""
            parts = [
                "-----BEGIN RSA PRIVATE KEY-----",
                "MIIEpAIBAAKCAQEAnBd41ktLs1rQto2WGSCaaIxZvYpkw7xzhckUiPJLN6LmfSch",
                "OyCiK+H638E5wGQxCnbvMpHib3gGsN5cC3JI4b4/XwbK3Vt8+WmkXMWkQFA51ApT",
                "GfvJYEY9fSq+qgDSXdVhHF54z/rfrm8CfaT8v2jNc3V3xgB2+I1ntTf9p1+st0mB",
                "Dk7tMMYtc1hmpw0E0s92H+WXV4d+9ULzSLWoyAhmXG89TPCeMqndwfjEhMDn0nhD",
                "JpD/Yg4wQe/etjXUalMH7TwKM9tXReAhIble82w4JN3715FR8T0b0A4oM0/gIZI5",
                "XPcgPyb8Jlf6sgmkQbG0SYV86+mMMndKIFS3aQIDAQABAoIBABQt/KidB2Zilppj",
                "PO/MBT+q6sHUWH6YUx8NW02bysRLQnJqUqOAQ+GvJMM0tIX+Q1DPsNDgMglTLRpE",
                "mlsTJVT58YYULLnoEATL9ucqLg1FJz9rLknXrAskSY1wWeyZ5UMi85u6ovJ7GTFF",
                "7L6C9qIQUdoGv7tQvWYYxzroctnmaDjyiYwM76rws1hsUfaxwPvC/xcElRDVyIc6",
                "8M2fWjfK7FtaRYwfivNi4YWFC7QCwMXM631unyTkThq4wguZWlgYQeCvyR/sW0qy",
                "iu4JHHDOEHY5yHhSP9W7mN8GgwW3RRaa7PwEGUAJSyyNXVOhvs52ju7Wmn5PK8OW",
                "U1/nMTkCgYEAxK0Ti/A4zDuhPvoX1qb+zyERsGGg7HaAIsLASWU4K79sGip79JCw",
                "sOYY9oW6RcqO0MsJGcpJGFulKdQEKu72tFn/yka1oo0aiCD066iav2xiaVSk7m7/",
                "1+brrgDbBapPj3YcBXgeqaPXOu8E3sSQq9iYrBRQB0lbN/vOm4rn1GMCgYEAyyyN",
                "WAsOgMMtkHi9E3wLpCJNWP1YtRv2VpZGjieRzC6WFsmCSzifB+Z8P8r7XG6LTPnY",
                "yzh7py+PL8CaR8egmZWTDioheRWEJDKAFBQPVxhWDUnw27ZHd0LWQVB6Mt1Krf88",
                "pVUH15eWuRU535GRJitrF/U6VY8/sAsqwgPVUMMCgYEArvOvIZqNS8/3fggG0KE4",
                "pZQrIhWWiwJWtZU8a42oy/G5/gSwwzs6kgH9Tr5ilta6+CzEabayEwLjBzRciLyN",
                "pJ0ylwMTbAfNBC8c78zJ62JEoKH1HUyMNchq+hw0uPNpVpqgDpVt4UWnnfsk/+0n",
                "LFa+aMSg8/pjNIfAoEiONTUCgYAPLaThjvHmbK5avKpjakD0YhulKkgWP6CHl3Jt",
                "7EbYGiLcUPGK7Q/0ZyOhIGjm3ttJROENTYrvUn4/8wOTmTZGQwZZaIxXn2Pf0GYB",
                "Gf6LYyYKmBuGTnfIURXwizKV2jJaDVdagp+zW3/HE+7e5OETGOtHPuq8uZbob+0h",
                "0Wd+QQKBgQCjk2JCwllKhMHARLjQ26ezeaeVYy8ztEq2XeqVP9Lhv5DdrKQBLRZl",
                "NXltR5jBlFyHZ38vXv4jIYUPGreIDoNr7gNUEViYnCwZ4iJzuOBhWSwwV4atUZ8i",
                "S1BAwJN6w8pdlUWqzTj+EphhvvBiZZrNy90YpmKlT54eSilDa0hdvQ==",
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
