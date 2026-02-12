import time
from unittest.mock import patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import (
    CertificateBuilder,
    Name,
    NameAttribute,
)
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.hashes import SHA256
from flask import Flask

from mealbot.auth import (
    _check_jwt,
    _get_pem_certificate,
    _verify_audience,
    require_auth,
)

# --- Test helpers ---

def _generate_rsa_key_pair():
    """Generate an RSA private key for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key


def _generate_self_signed_cert(private_key):
    """Generate a self-signed X.509 certificate for testing."""
    import datetime
    subject = issuer = Name([
        NameAttribute(NameOID.COMMON_NAME, "test"),
    ])
    cert = (
        CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(1000)
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(private_key, SHA256())
    )
    return cert


def _cert_to_x5c_entry(cert):
    """Convert a certificate to a base64 DER string (x5c format)."""
    import base64
    der_bytes = cert.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der_bytes).decode("ascii")


def _cert_to_pem(cert):
    """Convert a certificate to PEM string."""
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


def _make_token(private_key, claims, kid="test-kid"):
    """Create a signed JWT for testing."""
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pyjwt.encode(
        claims,
        pem_bytes,
        algorithm="RS256",
        headers={"kid": kid},
    )


@pytest.fixture
def rsa_key():
    return _generate_rsa_key_pair()


@pytest.fixture
def self_signed_cert(rsa_key):
    return _generate_self_signed_cert(rsa_key)


@pytest.fixture
def auth_constants():
    return {
        "issuer": "https://mealbot.auth0.com/",
        "audience": "https://mealbot-2.herokuapp.com/",
        "jwks_url": "https://mealbot.auth0.com/.well-known/jwks.json",
    }


@pytest.fixture
def valid_claims(auth_constants):
    now = int(time.time())
    return {
        "aud": [auth_constants["audience"]],
        "iss": auth_constants["issuer"],
        "iat": now,
        "exp": now + 3600,
        "sub": "test-user",
    }


@pytest.fixture
def mock_jwks(self_signed_cert):
    """Create a mock JWKS response."""
    x5c = _cert_to_x5c_entry(self_signed_cert)
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "n": "test-n",
                "e": "test-e",
                "x5c": [x5c],
            }
        ]
    }


@pytest.fixture
def app():
    """Create a Flask test app."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected", methods=["GET", "OPTIONS"])
    @require_auth
    def protected():
        return "ok", 200

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# --- Tests for _verify_audience ---

class TestVerifyAudience:
    def test_audience_as_array_match(self):
        claims = {"aud": ["https://example.com/", "https://other.com/"]}
        _verify_audience(claims, "https://example.com/")

    def test_audience_as_array_no_match(self):
        claims = {"aud": ["https://other.com/"]}
        with pytest.raises(ValueError, match="Invalid audience"):
            _verify_audience(claims, "https://example.com/")

    def test_audience_as_string_match(self):
        claims = {"aud": "https://example.com/"}
        _verify_audience(claims, "https://example.com/")

    def test_audience_as_string_no_match(self):
        claims = {"aud": "https://other.com/"}
        with pytest.raises(ValueError, match="Invalid audience"):
            _verify_audience(claims, "https://example.com/")

    def test_audience_missing(self):
        claims = {}
        with pytest.raises(ValueError, match="No audience claim"):
            _verify_audience(claims, "https://example.com/")

    def test_audience_empty_array(self):
        claims = {"aud": []}
        with pytest.raises(ValueError, match="Invalid audience"):
            _verify_audience(claims, "https://example.com/")


# --- Tests for _get_pem_certificate ---

class TestGetPEMCertificate:
    @patch("mealbot.auth._fetch_jwks")
    def test_matching_kid(self, mock_fetch, mock_jwks):
        mock_fetch.return_value = mock_jwks
        headers = {"kid": "test-kid"}
        cert = _get_pem_certificate(headers, "https://fake-url")
        assert cert.startswith("-----BEGIN CERTIFICATE-----\n")
        assert cert.endswith("\n-----END CERTIFICATE-----")

    @patch("mealbot.auth._fetch_jwks")
    def test_no_matching_kid(self, mock_fetch, mock_jwks):
        mock_fetch.return_value = mock_jwks
        headers = {"kid": "nonexistent-kid"}
        with pytest.raises(ValueError, match="Unable to find appropriate key"):
            _get_pem_certificate(headers, "https://fake-url")

    @patch("mealbot.auth._fetch_jwks")
    def test_empty_jwks(self, mock_fetch):
        mock_fetch.return_value = {"keys": []}
        headers = {"kid": "test-kid"}
        with pytest.raises(ValueError, match="Unable to find appropriate key"):
            _get_pem_certificate(headers, "https://fake-url")


# --- Tests for _check_jwt ---

class TestCheckJWT:
    def test_missing_authorization_header(self, auth_constants):
        with pytest.raises(ValueError, match="No authorization header"):
            _check_jwt("", auth_constants)

    def test_malformed_authorization_header_no_bearer(self, auth_constants):
        with pytest.raises(ValueError, match="Authorization header format must be Bearer"):
            _check_jwt("Basic abc123", auth_constants)

    def test_malformed_authorization_header_too_many_parts(self, auth_constants):
        with pytest.raises(ValueError, match="Authorization header format must be Bearer"):
            _check_jwt("Bearer abc 123", auth_constants)

    def test_invalid_token_format(self, auth_constants):
        with pytest.raises(ValueError):
            _check_jwt("Bearer not-a-jwt", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_wrong_algorithm(self, mock_fetch, auth_constants):
        """Token signed with HS256 should be rejected."""
        now = int(time.time())
        token = pyjwt.encode(
            {
                "aud": [auth_constants["audience"]],
                "iss": auth_constants["issuer"],
                "exp": now + 3600,
            },
            "secret",
            algorithm="HS256",
        )
        with pytest.raises(ValueError, match="Token must use 'alg' signing method"):
            _check_jwt(f"Bearer {token}", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_invalid_audience(self, mock_fetch, rsa_key, mock_jwks, auth_constants):
        mock_fetch.return_value = mock_jwks
        now = int(time.time())
        token = _make_token(rsa_key, {
            "aud": ["https://wrong-audience.com/"],
            "iss": auth_constants["issuer"],
            "exp": now + 3600,
        })
        with pytest.raises(ValueError, match="Invalid audience"):
            _check_jwt(f"Bearer {token}", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_invalid_issuer(self, mock_fetch, rsa_key, mock_jwks, auth_constants):
        mock_fetch.return_value = mock_jwks
        now = int(time.time())
        token = _make_token(rsa_key, {
            "aud": [auth_constants["audience"]],
            "iss": "https://wrong-issuer.com/",
            "exp": now + 3600,
        })
        with pytest.raises(ValueError, match="Invalid issuer"):
            _check_jwt(f"Bearer {token}", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_valid_token(self, mock_fetch, rsa_key, self_signed_cert, mock_jwks,
                         valid_claims, auth_constants):
        mock_fetch.return_value = mock_jwks
        token = _make_token(rsa_key, valid_claims)
        # Should not raise
        _check_jwt(f"Bearer {token}", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_expired_token(self, mock_fetch, rsa_key, mock_jwks, auth_constants):
        mock_fetch.return_value = mock_jwks
        now = int(time.time())
        token = _make_token(rsa_key, {
            "aud": [auth_constants["audience"]],
            "iss": auth_constants["issuer"],
            "exp": now - 3600,  # expired 1 hour ago
        })
        with pytest.raises(ValueError):
            _check_jwt(f"Bearer {token}", auth_constants)

    @patch("mealbot.auth._fetch_jwks")
    def test_kid_not_in_jwks(self, mock_fetch, rsa_key, auth_constants):
        mock_fetch.return_value = {"keys": []}
        now = int(time.time())
        token = _make_token(rsa_key, {
            "aud": [auth_constants["audience"]],
            "iss": auth_constants["issuer"],
            "exp": now + 3600,
        })
        with pytest.raises(ValueError, match="Unable to find appropriate key"):
            _check_jwt(f"Bearer {token}", auth_constants)


# --- Tests for require_auth decorator ---

class TestRequireAuthDecorator:
    @patch("mealbot.auth._get_auth0_constants")
    @patch("mealbot.auth._check_jwt")
    def test_options_bypasses_auth(self, mock_check, mock_constants, client):
        """OPTIONS requests should bypass JWT validation entirely."""
        response = client.options("/protected")
        mock_check.assert_not_called()

    @patch("mealbot.auth._get_auth0_constants")
    @patch("mealbot.auth._check_jwt")
    def test_valid_auth_passes(self, mock_check, mock_constants, client):
        """Valid JWT should allow the request through."""
        mock_constants.return_value = {
            "issuer": "test",
            "audience": "test",
            "jwks_url": "test",
        }
        mock_check.return_value = None  # no exception = success
        response = client.get("/protected", headers={
            "Authorization": "Bearer valid-token"
        })
        assert response.status_code == 200
        assert response.data == b"ok"

    @patch("mealbot.auth._get_auth0_constants")
    @patch("mealbot.auth._check_jwt")
    def test_missing_auth_header_returns_empty(self, mock_check, mock_constants, client):
        """Missing auth header should return empty body (matching Go behavior)."""
        mock_constants.return_value = {
            "issuer": "test",
            "audience": "test",
            "jwks_url": "test",
        }
        mock_check.side_effect = ValueError("No authorization header")
        response = client.get("/protected")
        # Go returns without writing a response body
        assert response.data == b""

    @patch("mealbot.auth._get_auth0_constants")
    @patch("mealbot.auth._check_jwt")
    def test_invalid_token_returns_empty(self, mock_check, mock_constants, client):
        """Invalid JWT should return empty body (matching Go behavior)."""
        mock_constants.return_value = {
            "issuer": "test",
            "audience": "test",
            "jwks_url": "test",
        }
        mock_check.side_effect = ValueError("Token is invalid")
        response = client.get("/protected", headers={
            "Authorization": "Bearer bad-token"
        })
        assert response.data == b""
