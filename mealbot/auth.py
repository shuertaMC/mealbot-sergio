import functools
import logging

import jwt
import requests
from cryptography.x509 import load_pem_x509_certificate
from flask import request

from mealbot.config import get_auth0_settings

logger = logging.getLogger(__name__)

# Constants matching Go's auth.go
INVALID_ACCESS_TOKEN = "Invalid access token"


def _get_auth0_constants():
    """Retrieve Auth0 constants from configuration."""
    settings = get_auth0_settings()
    return {
        "issuer": settings["issuer"],
        "audience": settings["audience"],
        "jwks_url": settings["jwks_url"],
    }


def _fetch_jwks(jwks_url):
    """Fetch the JSON Web Key Set from the Auth0 endpoint.

    Mirrors Go's per-request fetch from JSONWebKeySet URL.
    """
    resp = requests.get(jwks_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_pem_certificate(token_headers, jwks_url):
    """Extract PEM certificate from JWKS matching the token's kid header.

    Mirrors Go's getPEMCertificate function.
    """
    jwks = _fetch_jwks(jwks_url)
    cert = ""

    kid = token_headers.get("kid", "")
    for key in jwks.get("keys", []):
        if kid == key.get("kid", ""):
            x5c = key.get("x5c", [])
            if x5c:
                cert = (
                    "-----BEGIN CERTIFICATE-----\n"
                    + x5c[0]
                    + "\n-----END CERTIFICATE-----"
                )

    if not cert:
        raise ValueError("Unable to find appropriate key")

    return cert


def _verify_audience(claims, audience):
    """Verify the audience claim, handling it as an array.

    Mirrors Go's verifyAudience function which handles the JWT aud claim
    as a JSON array ([]interface{}), iterating to find a match.
    This is needed because dgrijalva/jwt-go had a known quirk
    (issue #290) where aud could be a list.
    """
    aud = claims.get("aud")
    if aud is None:
        raise ValueError("No audience claim")

    # Handle aud as either a list or a single string
    if isinstance(aud, list):
        for item in aud:
            if item == audience:
                return
    elif isinstance(aud, str):
        if aud == audience:
            return

    raise ValueError("Invalid audience")


def _check_jwt(auth_header, auth_constants):
    """Validate the JWT from the Authorization header.

    Mirrors Go's CustomJWTMiddleware.CheckJWT method.
    """
    if not auth_header:
        raise ValueError("No authorization header")

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Authorization header format must be Bearer {token}")

    token_str = parts[1]

    # Decode without verification first to get the header (kid, alg)
    try:
        unverified_header = jwt.get_unverified_header(token_str)
    except jwt.exceptions.DecodeError as e:
        raise ValueError(str(e))

    # Validate signing method is RS256
    if unverified_header.get("alg") != "RS256":
        raise ValueError("Token must use 'alg' signing method")

    # Decode without verification to get claims for audience/issuer checks
    # (mirrors Go's flow where ValidationKeyGetter receives parsed claims)
    try:
        unverified_claims = jwt.decode(
            token_str, options={"verify_signature": False}
        )
    except Exception as e:
        raise ValueError(str(e))

    # Verify audience (as array, matching Go's verifyAudience)
    _verify_audience(unverified_claims, auth_constants["audience"])

    # Verify issuer
    token_issuer = unverified_claims.get("iss", "")
    if token_issuer != auth_constants["issuer"]:
        raise ValueError("Invalid issuer")

    # Get PEM certificate from JWKS
    cert_pem = _get_pem_certificate(unverified_header, auth_constants["jwks_url"])

    # Extract RSA public key from the PEM certificate.
    # Mirrors Go's jwt.ParseRSAPublicKeyFromPEM([]byte(cert)).
    cert_obj = load_pem_x509_certificate(cert_pem.encode("utf-8"))
    public_key = cert_obj.public_key()

    # Fully verify the token signature with the RSA public key.
    try:
        jwt.decode(
            token_str,
            public_key,
            algorithms=["RS256"],
            audience=auth_constants["audience"],
            issuer=auth_constants["issuer"],
        )
    except jwt.exceptions.InvalidTokenError as e:
        raise ValueError(str(e))


def require_auth(f):
    """Flask route decorator that enforces JWT authentication.

    Mirrors Go's GetAuthHandler which wraps handlers with
    CustomJWTMiddleware. OPTIONS requests bypass authentication
    (preflight). On auth failure, the Go code returns without
    writing a response body — this is replicated by returning
    an empty response with a 200 status.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # OPTIONS requests bypass JWT validation (preflight)
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        auth_constants = _get_auth0_constants()

        try:
            _check_jwt(auth_header, auth_constants)
        except Exception as e:
            # Go middleware prints the error and returns without writing
            # a response body. We replicate this by returning empty body.
            logger.error("JWT validation failed: %s", str(e))
            return ("", 200)

        return f(*args, **kwargs)
    return decorated
