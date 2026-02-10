import logging

import httpx
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from mealbot.config import settings

logger = logging.getLogger("mealbot")

ISSUER = f"https://{settings.auth0_domain}/"
AUDIENCE = settings.auth0_audience
JWKS_URL = f"https://{settings.auth0_domain}/.well-known/jwks.json"
ALGORITHMS = ["RS256"]

security = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


def _get_pem_certificate(token: str, jwks: dict) -> str | None:
    """Extract PEM certificate from JWKS using X5C, matching Go's getPEMCertificate.

    The Go code matches the token's kid header against JWKS keys and
    constructs a PEM certificate from the X5C field.
    """
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            x5c = key.get("x5c")
            if x5c and len(x5c) > 0:
                return (
                    "-----BEGIN CERTIFICATE-----\n"
                    + x5c[0]
                    + "\n-----END CERTIFICATE-----"
                )
    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Validate JWT from Authorization header. Returns claims dict or None.

    The Go implementation silently returns (no response written) on auth failure,
    causing the middleware to stop processing. In FastAPI, we return None and let
    routes decide how to handle unauthenticated requests, or raise via dependency.

    For OPTIONS preflight requests, authentication is skipped (matching Go behavior).
    """
    if request.method == "OPTIONS":
        return None

    if credentials is None:
        return None

    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        pem_cert = _get_pem_certificate(token, jwks)
        if pem_cert is None:
            logger.error("Unable to find appropriate key")
            return None

        payload = jwt.decode(
            token,
            pem_cert,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        return payload
    except JWTError as e:
        logger.error("JWT validation failed: %s", e)
        return None
    except Exception as e:
        logger.error("Auth error: %s", e)
        return None


def require_auth(user: dict | None = Depends(get_current_user)) -> dict:
    """Dependency that requires a valid authenticated user.

    Returns 401 with empty response if not authenticated (matching Go behavior
    where the middleware simply returns without writing a response body).
    """
    if user is None:
        raise _AuthError()
    return user


class _AuthError(Exception):
    pass


async def auth_error_handler(request: Request, exc: _AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content=None)
