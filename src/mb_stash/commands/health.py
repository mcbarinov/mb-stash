"""Show daemon status."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import is_daemon_available


def health(ctx: typer.Context) -> None:
    """Show daemon status (running, locked/unlocked)."""
    app = use_context(ctx)

    if not is_daemon_available(app.cfg):
        app.out.print_health(running=False, locked=True)
        return

    resp = DaemonClient(app.cfg).health()
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_health(running=True, locked=not resp.data.get("unlocked", False))
