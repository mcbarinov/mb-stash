"""Structured output for CLI and JSON modes."""

# ruff: noqa: T201 — this module is the output layer; print() is its sole mechanism for producing CLI output.

import json
import sys
from typing import NoReturn

import typer


class Output:
    """Handles all CLI output in JSON or human-readable format."""

    def __init__(self, *, json_mode: bool) -> None:
        """Initialize output handler.

        Args:
            json_mode: If True, output JSON envelopes; otherwise human-readable text.

        """
        self._json_mode = json_mode

    def _success(self, data: dict[str, object], message: str) -> None:
        """Print a success result in JSON or human-readable format."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": data}))
        else:
            print(message)

    def print_error_and_exit(self, code: str, message: str) -> NoReturn:
        """Print an error in JSON or human-readable format and exit with code 1.

        Raises:
            typer.Exit: Always, with code 1.

        """
        if self._json_mode:
            print(json.dumps({"ok": False, "error": code, "message": message}))
        else:
            print(f"Error: {message}", file=sys.stderr)
        raise typer.Exit(code=1)

    # --- Setup ---

    def print_init_done(self) -> None:
        """Print store creation confirmation."""
        self._success({}, "Stash created.")

    def print_password_changed(self) -> None:
        """Print password change confirmation."""
        self._success({}, "Password changed.")

    # --- Secrets ---

    def print_secret_copied(self, key: str) -> None:
        """Print secret copied to clipboard confirmation."""
        self._success({"key": key}, f"Copied '{key}' to clipboard.")

    def print_secret_stdout(self, key: str, value: str) -> None:
        """Print secret value to stdout."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": {"key": key, "value": value}}))
        else:
            print(value)

    def print_list(self, keys: list[str]) -> None:
        """Print list of stored keys."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": {"keys": keys}}))
        else:
            for key in keys:
                print(key)

    def print_secret_added(self, key: str) -> None:
        """Print secret add confirmation."""
        self._success({"key": key}, f"Secret '{key}' added.")

    def print_secret_deleted(self, key: str) -> None:
        """Print secret deletion confirmation."""
        self._success({"key": key}, f"Secret '{key}' deleted.")

    # --- Daemon ---

    def print_locked(self) -> None:
        """Print stash locked confirmation."""
        self._success({}, "Stash locked.")

    def print_unlocked(self) -> None:
        """Print stash unlocked confirmation."""
        self._success({}, "Stash unlocked.")

    def print_stopped(self) -> None:
        """Print daemon stopped confirmation."""
        self._success({}, "Daemon stopped.")

    def print_health(self, *, running: bool, locked: bool) -> None:
        """Print daemon health status."""
        self._success(
            {"running": running, "locked": locked},
            f"Daemon: {'running' if running else 'stopped'}, stash: {'locked' if locked else 'unlocked'}.",
        )
