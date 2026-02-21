"""Add a new secret."""

import sys

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def add(ctx: typer.Context, key: str) -> None:
    """Add a new secret (value entered interactively)."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    client = DaemonClient(app.cfg)
    # Unlock before prompting for value — better UX (password first, then secret)
    health = client.health()
    if health.ok and not health.data.get("unlocked") and sys.stdin.isatty():
        password = typer.prompt("Enter master password", hide_input=True)
        unlock_resp = client.unlock(password)
        if not unlock_resp.ok:
            app.out.print_error_and_exit(unlock_resp.error, unlock_resp.message)
    value = typer.prompt("Enter value", hide_input=True)
    resp = client.add(key, value)
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_secret_added(key)
