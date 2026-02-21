"""Lock the stash and clear clipboard."""

import contextlib

import typer

from mb_stash import clipboard
from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import is_daemon_running


def lock(ctx: typer.Context) -> None:
    """Lock the stash and clear clipboard."""
    app = use_context(ctx)

    # Best-effort clipboard clear regardless of daemon state
    with contextlib.suppress(Exception):
        clipboard.clear()

    # Daemon not running — stash is already locked
    if not is_daemon_running(app.cfg):
        app.out.print_locked()
        return

    resp = DaemonClient(app.cfg).lock()
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    app.out.print_locked()
