"""JWT authentication middleware using Auth0."""

import json
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from app.config import get_settings

# HTTP Bearer security scheme for extracting token from Authorization header
security = HTTPBearer(auto_error=False)


class JWKSCache:
    """Cache for Auth0 JWKS (JSON Web Key Set) to reduce API calls."""

    def __init__(self):
        self._jwks: Optional[Dict[str, Any]] = None

    async def get_jwks(self) -> Dict[str, Any]:
        """
        Fetch JWKS from Auth0, using cached value if available.

        Returns:
            Dict containing the JWKS data with public keys

        Raises:
            HTTPException: If JWKS cannot be fetched from Auth0
        """
        if self._jwks is not None:
            return self._jwks

        settings = get_settings()
        jwks_url = settings.auth0_jwks_url

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url, timeout=10.0)
                response.raise_for_status()
                self._jwks = response.json()
                return self._jwks
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to fetch JWKS from Auth0",
            ) from e

    def invalidate(self):
        """Invalidate the cached JWKS, forcing a refresh on next request."""
        self._jwks = None


# Global JWKS cache instance
_jwks_cache = JWKSCache()


async def get_jwks() -> Dict[str, Any]:
    """
    Get the cached JWKS or fetch from Auth0.

    Returns:
        Dict containing the JWKS data
    """
    return await _jwks_cache.get_jwks()


def get_jwks_cache() -> JWKSCache:
    """
    Get the global JWKS cache instance (useful for testing).

    Returns:
        The global JWKSCache instance
    """
    return _jwks_cache


def get_signing_key_from_jwks(token_header: Dict[str, Any], jwks: Dict[str, Any]) -> str:
    """
    Extract the signing key from JWKS based on the token's kid (key ID).

    Args:
        token_header: The JWT header containing the kid
        jwks: The JWKS data containing public keys

    Returns:
        PEM-formatted certificate string

    Raises:
        HTTPException: If the key cannot be found in JWKS
    """
    kid = token_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token header missing 'kid' field",
        )

    # Find the key with matching kid
    keys = jwks.get("keys", [])
    for key in keys:
        if key.get("kid") == kid:
            # Extract the x5c certificate if available
            x5c = key.get("x5c")
            if x5c and len(x5c) > 0:
                # Return PEM-formatted certificate
                cert = (
                    "-----BEGIN CERTIFICATE-----\n"
                    + x5c[0]
                    + "\n-----END CERTIFICATE-----"
                )
                return cert

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find appropriate key",
    )


async def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token from Auth0.

    This function:
    1. Fetches JWKS from Auth0 (or uses cached version)
    2. Extracts the unverified token header to get the kid
    3. Finds the matching public key in JWKS
    4. Verifies the token signature using the public key
    5. Validates token claims (audience, issuer, expiration)

    Args:
        token: The JWT token string to verify

    Returns:
        Dict containing the decoded token claims

    Raises:
        HTTPException: For any validation failure (401 Unauthorized)
    """
    settings = get_settings()

    try:
        # Get the unverified header to extract the kid
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        ) from e

    # Verify algorithm matches expected (RS256)
    alg = unverified_header.get("alg")
    if alg not in settings.auth0_algorithms:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token must use 'alg' signing method",
        )

    # Fetch JWKS and get the signing key
    try:
        jwks = await get_jwks()
        signing_key = get_signing_key_from_jwks(unverified_header, jwks)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PEM Certificate failed",
        ) from e

    # Verify and decode the token
    try:
        # Decode and verify token with all validations except audience
        # Note: We disable automatic audience verification because python-jose
        # expects audience to be a string, but Auth0 can send it as an array.
        # We'll verify audience manually below (matching Go's verifyAudience function).
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=settings.auth0_algorithms,
            issuer=settings.auth0_issuer_url,
            options={
                "verify_signature": True,
                "verify_aud": False,  # We'll verify audience manually
                "verify_iat": True,
                "verify_exp": True,
                "verify_iss": True,
            },
        )

        # Manually verify audience to handle both string and array cases
        # (matching Go implementation's verifyAudience function at lines 169-185)
        aud_claim = payload.get("aud")
        if aud_claim is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No audience claim",
            )

        # Handle audience as either string or array
        audience_valid = False
        if isinstance(aud_claim, str):
            audience_valid = aud_claim == settings.auth0_audience
        elif isinstance(aud_claim, list):
            audience_valid = settings.auth0_audience in aud_claim

        if not audience_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid audience",
            )

        return payload

    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from e

    except JWTClaimsError as e:
        # This covers issuer validation errors and other claim issues
        error_msg = str(e)
        if "audience" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid audience",
            ) from e
        elif "issuer" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer",
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
            ) from e

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid",
        ) from e


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI dependency for protecting endpoints with JWT authentication.

    This dependency:
    1. Skips authentication for OPTIONS requests (CORS preflight)
    2. Extracts the Authorization header
    3. Validates the Bearer token format
    4. Verifies the JWT token and returns decoded claims

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}

    Args:
        request: The FastAPI request object
        credentials: Optional credentials extracted by HTTPBearer

    Returns:
        Dict containing the decoded JWT claims (user info)

    Raises:
        HTTPException: 401 for any authentication failure
    """
    # Skip authentication for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return {}

    # Check if Authorization header is present
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authorization header",
        )

    # Parse Bearer token format
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header format must be Bearer {token}",
        )

    token = parts[1]

    # Verify the token and return claims
    return await verify_token(token)
