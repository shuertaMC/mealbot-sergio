import pytest
from flask import Flask

from mealbot.utils import get_query_param, get_query_params


@pytest.fixture
def app():
    """Create a minimal Flask app for testing request context."""
    app = Flask(__name__)
    return app


class TestGetQueryParam:
    def test_single_value(self, app):
        with app.test_request_context("/?org=myorg"):
            from flask import request

            value, err = get_query_param(request, "org")
            assert value == "myorg"
            assert err is None

    def test_missing_key(self, app):
        with app.test_request_context("/?other=value"):
            from flask import request

            value, err = get_query_param(request, "org")
            assert value is None
            assert err == "Request query parameters must contain org"

    def test_multiple_values_for_key(self, app):
        with app.test_request_context("/?org=a&org=b"):
            from flask import request

            value, err = get_query_param(request, "org")
            assert value is None
            assert err == "Request query parameters must contain org"

    def test_empty_query_string(self, app):
        with app.test_request_context("/"):
            from flask import request

            value, err = get_query_param(request, "org")
            assert value is None
            assert err is not None

    def test_value_with_special_chars(self, app):
        with app.test_request_context("/?name=John%20Doe"):
            from flask import request

            value, err = get_query_param(request, "name")
            assert value == "John Doe"
            assert err is None


class TestGetQueryParams:
    def test_multiple_keys(self, app):
        with app.test_request_context("/?org=myorg&admin=user@test.com"):
            from flask import request

            values, err = get_query_params(request, ["org", "admin"])
            assert values == ["myorg", "user@test.com"]
            assert err is None

    def test_missing_one_key(self, app):
        with app.test_request_context("/?org=myorg"):
            from flask import request

            values, err = get_query_params(request, ["org", "admin"])
            assert values == []
            assert err == "Request query parameters does not contain admin"

    def test_all_keys_missing(self, app):
        with app.test_request_context("/"):
            from flask import request

            values, err = get_query_params(request, ["org", "admin"])
            assert values == []
            assert err is not None

    def test_duplicate_value_for_one_key(self, app):
        with app.test_request_context("/?org=a&org=b&admin=user"):
            from flask import request

            values, err = get_query_params(request, ["org", "admin"])
            assert values == []
            assert err == "Request query parameters does not contain org"

    def test_single_key_list(self, app):
        with app.test_request_context("/?org=myorg"):
            from flask import request

            values, err = get_query_params(request, ["org"])
            assert values == ["myorg"]
            assert err is None

    def test_empty_keys_list(self, app):
        with app.test_request_context("/?org=myorg"):
            from flask import request

            values, err = get_query_params(request, [])
            assert values == []
            assert err is None
