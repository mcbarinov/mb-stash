"""Hidden CLI command: run the daemon process."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.server import run_server


def daemon(ctx: typer.Context) -> None:
    """Run the daemon process. Not intended for manual use."""
    app_ctx = use_context(ctx)
    run_server(app_ctx.cfg)
