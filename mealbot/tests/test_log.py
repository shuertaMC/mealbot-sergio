from mealbot.log import str_to_dict, err_to_dict, log_and_write_err, log_and_write, log_and_write_bad_request, log_and_write_internal_server_error


class TestStrToDict:
    def test_returns_message_format(self):
        result = str_to_dict("hello")
        assert result == {"Message": "hello"}

    def test_empty_string(self):
        result = str_to_dict("")
        assert result == {"Message": ""}


class TestErrToDict:
    def test_string_error(self):
        result = err_to_dict("something went wrong")
        assert result == {"Message": "something went wrong"}

    def test_exception_error(self):
        result = err_to_dict(ValueError("bad value"))
        assert result == {"Message": "bad value"}


class TestLogAndWriteErr:
    def test_returns_json_response_with_status(self):
        resp = log_and_write_err("error msg", 400, "TestFunc")
        assert resp.status_code == 400
        assert resp.body == b'{"Message":"error msg"}'

    def test_returns_500(self):
        resp = log_and_write_err("server error", 500, "TestFunc")
        assert resp.status_code == 500


class TestLogAndWrite:
    def test_returns_json_response(self):
        resp = log_and_write({"key": "value"}, 200, "TestFunc")
        assert resp.status_code == 200
        assert b'"key":"value"' in resp.body


class TestLogAndWriteBadRequest:
    def test_returns_400(self):
        resp = log_and_write_bad_request("bad request", "TestFunc")
        assert resp.status_code == 400


class TestLogAndWriteInternalServerError:
    def test_returns_500(self):
        resp = log_and_write_internal_server_error("internal error", "TestFunc")
        assert resp.status_code == 500
