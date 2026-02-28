"""Asyncio Unix socket server — the daemon loop.

Wraps a Stash instance and dispatches JSON-line requests from CLI clients.
"""

import asyncio
import contextlib
import logging
import os
import signal

from mm_clikit import write_pid_file

from mb_stash import clipboard
from mb_stash.config import Config
from mb_stash.daemon.protocol import Response, decode_request, encode_response
from mb_stash.stash import Stash, StashError

logger = logging.getLogger(__name__)


class DaemonServer:
    """Background daemon holding derived key + decrypted secrets in memory."""

    def __init__(self, cfg: Config) -> None:
        """Initialize the daemon server.

        Args:
            cfg: Application configuration.

        """
        self._cfg = cfg
        self._stash = Stash(cfg.stash_path)
        self._server: asyncio.AbstractServer | None = None
        self._inactivity_handle: asyncio.TimerHandle | None = None  # auto-lock timer, reset on every client request
        self._clipboard_handle: asyncio.TimerHandle | None = None  # clipboard auto-clear timer, reset on every get
        self._clipboard_value: str | None = None  # last copied secret, used for conditional clear
        # Strong references to background tasks to prevent GC
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        """Start the server and run until shutdown signal."""
        sock_path = self._cfg.daemon_sock_path
        # Remove stale socket
        with contextlib.suppress(OSError):
            sock_path.unlink()

        write_pid_file(self._cfg.daemon_pid_path)

        # Restrict umask before socket creation to prevent TOCTOU permission window
        old_umask = os.umask(0o077)
        try:
            self._server = await asyncio.start_unix_server(self._handle_client, path=str(sock_path))
        finally:
            os.umask(old_umask)
        sock_path.chmod(0o600)
        logger.info("Daemon listening on %s (pid %d)", sock_path, os.getpid())

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._schedule_shutdown)

        self._reset_inactivity_timer()

        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a single client connection: read request, dispatch, send response."""
        try:
            line = await reader.readline()
            if not line:
                return
            req = decode_request(line)
            logger.debug("Request: %s", req.command)
            resp = self._dispatch(req.command, req.params)
            writer.write(encode_response(resp))
            await writer.drain()
            self._reset_inactivity_timer()
        except Exception:
            logger.exception("Error handling client")
            writer.write(encode_response(Response.fail("internal", "Internal server error.")))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    def _dispatch(self, command: str, params: dict[str, str]) -> Response:
        """Route a command to the appropriate stash operation."""
        try:
            match command:
                case "unlock":
                    if "password" not in params:
                        return Response.fail("invalid_request", "Missing 'password' parameter.")
                    self._stash.unlock(params["password"])
                    return Response.success()
                case "lock":
                    self._cancel_clipboard_timer()
                    self._stash.lock()
                    return Response.success()
                case "get":
                    if "key" not in params:
                        return Response.fail("invalid_request", "Missing 'key' parameter.")
                    value = self._stash.get(params["key"])
                    if value is None:
                        return Response.fail("not_found", f"Key '{params['key']}' not found.")
                    return Response.success({"value": value})
                case "list":
                    keys = self._stash.list_keys(params.get("filter") or None)
                    return Response.success({"keys": keys})
                case "add":
                    if "key" not in params or "value" not in params:
                        return Response.fail("invalid_request", "Missing 'key' or 'value' parameter.")
                    self._stash.add(params["key"], params["value"])
                    return Response.success()
                case "delete":
                    if "key" not in params:
                        return Response.fail("invalid_request", "Missing 'key' parameter.")
                    if not self._stash.delete(params["key"]):
                        return Response.fail("not_found", f"Key '{params['key']}' not found.")
                    return Response.success()
                case "rename":
                    if "key" not in params or "new_key" not in params:
                        return Response.fail("invalid_request", "Missing 'key' or 'new_key' parameter.")
                    self._stash.rename(params["key"], params["new_key"])
                    return Response.success()
                case "health":
                    return Response.success({"unlocked": self._stash.is_unlocked})
                case "schedule_clipboard_clear":
                    self._clipboard_value = params.get("value")
                    self._reset_clipboard_timer()
                    return Response.success()
                case "stop":
                    self._schedule_shutdown()
                    return Response.success()
                case _:
                    return Response.fail("unknown_command", f"Unknown command: {command}")
        except StashError as e:
            return Response.fail(e.code, str(e))

    def _reset_inactivity_timer(self) -> None:
        """Reset the inactivity auto-lock timer."""
        if self._inactivity_handle is not None:
            self._inactivity_handle.cancel()
            self._inactivity_handle = None

        timeout = self._cfg.inactivity_timeout
        if timeout <= 0:
            return

        loop = asyncio.get_running_loop()
        self._inactivity_handle = loop.call_later(timeout, self._on_inactivity)

    def _on_inactivity(self) -> None:
        """Auto-lock the stash after inactivity timeout."""
        logger.info("Inactivity timeout — locking stash.")
        self._stash.lock()

    def _reset_clipboard_timer(self) -> None:
        """Reset the clipboard auto-clear timer."""
        self._cancel_clipboard_timer()
        timeout = self._cfg.clipboard_timeout
        if timeout <= 0:
            return
        loop = asyncio.get_running_loop()
        self._clipboard_handle = loop.call_later(timeout, self._on_clipboard_timeout)

    def _cancel_clipboard_timer(self) -> None:
        """Cancel the clipboard auto-clear timer if active."""
        if self._clipboard_handle is not None:
            self._clipboard_handle.cancel()
            self._clipboard_handle = None
        self._clipboard_value = None

    def _on_clipboard_timeout(self) -> None:
        """Clear clipboard after timeout, only if it still contains the copied secret."""
        logger.info("Clipboard timeout — clearing clipboard.")
        try:
            clipboard.clear(expected=self._clipboard_value)
        except Exception:
            logger.exception("Failed to clear clipboard")
        finally:
            self._clipboard_value = None

    def _schedule_shutdown(self) -> None:
        """Schedule a shutdown task with a strong reference to prevent GC."""
        task = asyncio.ensure_future(self._shutdown())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _shutdown(self) -> None:
        """Clean shutdown: stop server, remove socket and PID file."""
        logger.info("Shutting down daemon.")
        if self._inactivity_handle is not None:
            self._inactivity_handle.cancel()
        self._cancel_clipboard_timer()
        self._stash.lock()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove socket and PID files."""
        for path in (self._cfg.daemon_sock_path, self._cfg.daemon_pid_path):
            with contextlib.suppress(OSError):
                path.unlink()


def run_server(cfg: Config) -> None:
    """Entry point: create server and run the asyncio event loop."""
    server = DaemonServer(cfg)
    asyncio.run(server.run())
