"""Delete a secret."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def delete(ctx: typer.Context, key: str) -> None:
    """Delete a secret."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    client = DaemonClient(app.cfg)
    resp = client.send_auto_unlock(
        "delete", {"key": key}, password_prompt=lambda: typer.prompt("Enter master password", hide_input=True)
    )
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_secret_deleted(key)
