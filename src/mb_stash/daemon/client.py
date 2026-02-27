"""Synchronous client for CLI → daemon communication."""

import socket
import sys
from collections.abc import Callable

from mb_stash.config import Config
from mb_stash.daemon.protocol import Request, Response, decode_response, encode_request

# Read buffer size
_BUFSIZE = 65536


def _recv_line(s: socket.socket) -> bytes:
    """Read from socket until newline (protocol framing delimiter) or connection close."""
    chunks: list[bytes] = []
    while True:
        chunk = s.recv(_BUFSIZE)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    return b"".join(chunks)


class DaemonClient:
    """Synchronous client that talks to the daemon over a Unix socket."""

    def __init__(self, cfg: Config) -> None:
        """Initialize client with configuration.

        Args:
            cfg: Application configuration (provides socket path).

        """
        self._cfg = cfg

    def send(self, command: str, params: dict[str, str] | None = None) -> Response:
        """Send a request to the daemon and return the response."""
        req = Request(command=command, params=params or {})
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(10.0)
            s.connect(str(self._cfg.daemon_sock_path))
            s.sendall(encode_request(req))
            data = _recv_line(s)
        return decode_response(data)

    def send_auto_unlock(
        self, command: str, params: dict[str, str] | None = None, *, password_prompt: Callable[[], str]
    ) -> Response:
        """Send a request, auto-unlocking if the stash is locked.

        If the daemon responds with "locked" and stdin is a TTY, prompts for
        password, unlocks, and retries once. Non-interactive callers get the
        locked error as-is.

        Args:
            command: Daemon command name.
            params: Optional command parameters.
            password_prompt: Callable that prompts the user for a password.

        """
        resp = self.send(command, params)
        if resp.ok or resp.error != "locked" or not sys.stdin.isatty():
            return resp
        password = password_prompt()
        unlock_resp = self.unlock(password)
        if not unlock_resp.ok:
            return unlock_resp
        return self.send(command, params)

    # --- Convenience methods ---

    def health(self) -> Response:
        """Query daemon health status."""
        return self.send("health")

    def unlock(self, password: str) -> Response:
        """Unlock the stash with a password."""
        return self.send("unlock", {"password": password})

    def lock(self) -> Response:
        """Lock the stash."""
        return self.send("lock")

    def stop(self) -> Response:
        """Stop the daemon."""
        return self.send("stop")

    def get(self, key: str) -> Response:
        """Get a secret by key."""
        return self.send("get", {"key": key})

    def list_keys(self, filter_: str | None = None) -> Response:
        """List stored keys, optionally filtered."""
        params: dict[str, str] = {}
        if filter_:
            params["filter"] = filter_
        return self.send("list", params)

    def add(self, key: str, value: str) -> Response:
        """Add or update a secret."""
        return self.send("add", {"key": key, "value": value})

    def delete(self, key: str) -> Response:
        """Delete a secret."""
        return self.send("delete", {"key": key})

    def rename(self, key: str, new_key: str) -> Response:
        """Rename a secret key."""
        return self.send("rename", {"key": key, "new_key": new_key})
