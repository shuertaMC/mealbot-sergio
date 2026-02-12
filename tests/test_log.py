import json

import pytest
from flask import Flask

from mealbot.log import (
    err_to_bytes,
    log_and_write,
    log_and_write_err,
    log_and_write_status_bad_request,
    log_and_write_status_internal_server_error,
    str_to_bytes,
)


@pytest.fixture
def app():
    """Create a minimal Flask app for testing response helpers."""
    app = Flask(__name__)
    return app


class TestStrToBytes:
    def test_basic_message(self):
        result = str_to_bytes("hello")
        parsed = json.loads(result)
        assert parsed == {"Message": "hello"}

    def test_empty_message(self):
        result = str_to_bytes("")
        parsed = json.loads(result)
        assert parsed == {"Message": ""}

    def test_message_with_special_chars(self):
        result = str_to_bytes('error: "bad input"')
        parsed = json.loads(result)
        assert parsed == {"Message": 'error: "bad input"'}

    def test_capital_m_key(self):
        """Verify the Message key uses capital M to match Go behavior."""
        result = str_to_bytes("test")
        parsed = json.loads(result)
        assert "Message" in parsed
        assert "message" not in parsed


class TestErrToBytes:
    def test_with_exception(self):
        err = Exception("something went wrong")
        result = err_to_bytes(err)
        parsed = json.loads(result)
        assert parsed == {"Message": "something went wrong"}

    def test_with_value_error(self):
        err = ValueError("invalid value")
        result = err_to_bytes(err)
        parsed = json.loads(result)
        assert parsed == {"Message": "invalid value"}

    def test_with_string(self):
        result = err_to_bytes("plain error string")
        parsed = json.loads(result)
        assert parsed == {"Message": "plain error string"}

    def test_capital_m_key(self):
        """Verify the Message key uses capital M to match Go behavior."""
        result = err_to_bytes(Exception("test"))
        parsed = json.loads(result)
        assert "Message" in parsed
        assert "message" not in parsed


class TestLogAndWriteErr:
    def test_returns_correct_status(self, app):
        with app.app_context():
            err = Exception("bad request")
            response = log_and_write_err(err, 400, "TestFunc")
            assert response.status_code == 400

    def test_returns_json_body(self, app):
        with app.app_context():
            err = Exception("not found")
            response = log_and_write_err(err, 404, "TestFunc")
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == {"Message": "not found"}

    def test_content_type(self, app):
        with app.app_context():
            err = Exception("error")
            response = log_and_write_err(err, 500, "TestFunc")
            assert response.content_type.startswith("application/json")


class TestLogAndWrite:
    def test_returns_dict_as_json(self, app):
        with app.app_context():
            data = {"key": "value"}
            response = log_and_write(data, 200, "TestFunc")
            assert response.status_code == 200
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == {"key": "value"}

    def test_returns_string_body(self, app):
        with app.app_context():
            data = json.dumps({"Message": "ok"})
            response = log_and_write(data, 200, "TestFunc")
            assert response.status_code == 200
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == {"Message": "ok"}

    def test_returns_list_as_json(self, app):
        with app.app_context():
            data = [{"id": 1}, {"id": 2}]
            response = log_and_write(data, 200, "TestFunc")
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == [{"id": 1}, {"id": 2}]


class TestLogAndWriteStatusBadRequest:
    def test_returns_400(self, app):
        with app.app_context():
            err = Exception("missing field")
            response = log_and_write_status_bad_request(err, "TestFunc")
            assert response.status_code == 400
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == {"Message": "missing field"}


class TestLogAndWriteStatusInternalServerError:
    def test_returns_500(self, app):
        with app.app_context():
            err = Exception("database error")
            response = log_and_write_status_internal_server_error(
                err, "TestFunc"
            )
            assert response.status_code == 500
            parsed = json.loads(response.get_data(as_text=True))
            assert parsed == {"Message": "database error"}
