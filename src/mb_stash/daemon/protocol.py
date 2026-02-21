"""Request/Response protocol for CLI-daemon communication.

JSON-over-Unix-socket with newline framing. Each message is one JSON line.

Request:  {"command": "get", "params": {"key": "my-token"}}
Response: {"ok": true, "data": {"value": "xxx"}}
Error:    {"ok": false, "data": {}, "error": "locked", "message": "Stash is locked."}
"""

import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Request:
    """Daemon request: a command name with optional parameters."""

    command: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Response:
    """Daemon response: success/error envelope with data."""

    ok: bool
    data: dict[str, object] = field(default_factory=dict)
    error: str = ""
    message: str = ""

    @staticmethod
    def success(data: dict[str, object] | None = None) -> Response:
        """Build a success response."""
        return Response(ok=True, data=data or {})

    @staticmethod
    def fail(error: str, message: str) -> Response:
        """Build an error response."""
        return Response(ok=False, error=error, message=message)


def encode_request(req: Request) -> bytes:
    """Serialize a Request to a newline-terminated JSON bytes line."""
    return json.dumps({"command": req.command, "params": req.params}).encode() + b"\n"


def decode_request(data: bytes) -> Request:
    """Deserialize a JSON bytes line into a Request."""
    obj = json.loads(data)
    return Request(command=obj["command"], params=obj.get("params", {}))


def encode_response(resp: Response) -> bytes:
    """Serialize a Response to a newline-terminated JSON bytes line."""
    payload: dict[str, object] = {"ok": resp.ok, "data": resp.data}
    if not resp.ok:
        payload["error"] = resp.error
        payload["message"] = resp.message
    return json.dumps(payload).encode() + b"\n"


def decode_response(data: bytes) -> Response:
    """Deserialize a JSON bytes line into a Response."""
    obj = json.loads(data)
    return Response(ok=obj["ok"], data=obj.get("data", {}), error=obj.get("error", ""), message=obj.get("message", ""))
