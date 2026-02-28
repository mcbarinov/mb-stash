"""Copy secret to clipboard."""

import contextlib

import typer

from mb_stash import clipboard
from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def get(
    ctx: typer.Context,
    key: str,
    *,
    stdout: bool = typer.Option(default=False, help="Print to stdout instead of copying to clipboard"),
) -> None:
    """Copy secret to clipboard (or --stdout for stdout)."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    client = DaemonClient(app.cfg)
    resp = client.send_auto_unlock(
        "get", {"key": key}, password_prompt=lambda: typer.prompt("Enter master password", hide_input=True)
    )
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    value = str(resp.data["value"])
    if stdout:
        app.out.print_secret_stdout(key, value)
    else:
        clipboard.copy(value)
        app.out.print_secret_copied(key)
        # Schedule clipboard auto-clear via daemon (best-effort)
        with contextlib.suppress(Exception):
            client.send("schedule_clipboard_clear", {"value": value})
