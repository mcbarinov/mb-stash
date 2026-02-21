"""Unlock with master password."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def unlock(ctx: typer.Context) -> None:
    """Unlock with master password."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    password = typer.prompt("Enter master password", hide_input=True)
    resp = DaemonClient(app.cfg).unlock(password)
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_unlocked()
