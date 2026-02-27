"""Rename a secret key."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def rename(ctx: typer.Context, key: str, new_key: str) -> None:
    """Rename a secret key without changing its value."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    client = DaemonClient(app.cfg)
    resp = client.send_auto_unlock(
        "rename", {"key": key, "new_key": new_key}, password_prompt=lambda: typer.prompt("Enter master password", hide_input=True)
    )
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_secret_renamed(key, new_key)
