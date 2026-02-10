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


def _get_rsa_key(token: str, jwks: dict) -> dict | None:
    unverified_header = jwt.get_unverified_header(token)
    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
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
        rsa_key = _get_rsa_key(token, jwks)
        if rsa_key is None:
            logger.error("Unable to find appropriate key")
            return None

        payload = jwt.decode(
            token,
            rsa_key,
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
