"""Tests for CLI-daemon protocol encoding/decoding."""

import json

from mb_stash.daemon.protocol import Request, Response, decode_request, decode_response, encode_request, encode_response


class TestResponseBuilders:
    """Response.success() and Response.fail() static methods."""

    def test_success_no_data(self):
        """Success response with no data."""
        resp = Response.success()
        assert resp.ok is True
        assert resp.data == {}

    def test_success_with_data(self):
        """Success response carries data."""
        resp = Response.success({"value": "secret"})
        assert resp.ok is True
        assert resp.data == {"value": "secret"}

    def test_fail(self):
        """Error response has ok=False plus error and message."""
        resp = Response.fail("locked", "Stash is locked.")
        assert resp.ok is False
        assert resp.error == "locked"
        assert resp.message == "Stash is locked."


class TestRequestEncoding:
    """encode_request / decode_request round-trip."""

    def test_round_trip(self):
        """Encode → decode preserves command and params."""
        req = Request(command="get", params={"key": "my-token"})
        decoded = decode_request(encode_request(req))
        assert decoded.command == req.command
        assert decoded.params == req.params

    def test_empty_params(self):
        """Request with no params round-trips correctly."""
        req = Request(command="lock")
        decoded = decode_request(encode_request(req))
        assert decoded.command == "lock"
        assert decoded.params == {}

    def test_newline_terminated(self):
        """Encoded bytes end with newline."""
        encoded = encode_request(Request(command="health"))
        assert encoded.endswith(b"\n")


class TestResponseEncoding:
    """encode_response / decode_response round-trip."""

    def test_success_round_trip(self):
        """Success response round-trips correctly."""
        resp = Response.success({"value": "abc"})
        decoded = decode_response(encode_response(resp))
        assert decoded.ok is True
        assert decoded.data == {"value": "abc"}

    def test_error_round_trip(self):
        """Error response round-trips correctly."""
        resp = Response.fail("not_found", "Key not found.")
        decoded = decode_response(encode_response(resp))
        assert decoded.ok is False
        assert decoded.error == "not_found"
        assert decoded.message == "Key not found."

    def test_success_json_excludes_error_fields(self):
        """Success response JSON omits error and message keys."""
        encoded = encode_response(Response.success())
        obj = json.loads(encoded)
        assert "error" not in obj
        assert "message" not in obj

    def test_error_json_includes_error_fields(self):
        """Error response JSON includes error and message keys."""
        encoded = encode_response(Response.fail("err", "msg"))
        obj = json.loads(encoded)
        assert obj["error"] == "err"
        assert obj["message"] == "msg"

    def test_newline_terminated(self):
        """Encoded bytes end with newline."""
        encoded = encode_response(Response.success())
        assert encoded.endswith(b"\n")


class TestDecodeEdgeCases:
    """Edge cases for decode functions."""

    def test_decode_request_missing_params(self):
        """Missing params key defaults to empty dict."""
        data = json.dumps({"command": "lock"}).encode()
        req = decode_request(data)
        assert req.params == {}

    def test_decode_response_missing_optional_fields(self):
        """Missing error/message default to empty strings."""
        data = json.dumps({"ok": True}).encode()
        resp = decode_response(data)
        assert resp.ok is True
        assert resp.data == {}
        assert resp.error == ""
        assert resp.message == ""
