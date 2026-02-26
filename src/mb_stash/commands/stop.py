"""Stop the daemon."""

import time

import typer
from mm_clikit import is_process_running

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import is_connectable, is_daemon_available, stop_daemon


def stop(ctx: typer.Context) -> None:
    """Stop the daemon."""
    app = use_context(ctx)

    pid_alive = is_process_running(app.cfg.daemon_pid_path, command_contains="mb-stash")
    reachable = is_connectable(app.cfg.daemon_sock_path)

    if pid_alive:
        stop_daemon(app.cfg)
    elif reachable:
        DaemonClient(app.cfg).stop()

    # Give socket-based stop a moment to complete
    if not pid_alive and reachable:
        time.sleep(0.5)

    if is_daemon_available(app.cfg):
        app.out.print_error_and_exit("stop_failed", "Daemon is still running after stop attempt.")

    app.out.print_stopped()
