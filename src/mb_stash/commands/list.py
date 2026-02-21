"""List stored keys."""

from typing import cast

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.client import DaemonClient
from mb_stash.daemon.process import ensure_daemon


def list_(ctx: typer.Context, filter_: str | None = typer.Argument(default=None, help="Filter keys by substring")) -> None:
    """List stored keys, optionally filter by substring."""
    app = use_context(ctx)
    ensure_daemon(app.cfg)
    client = DaemonClient(app.cfg)
    params: dict[str, str] = {}
    if filter_:
        params["filter"] = filter_
    resp = client.send_auto_unlock("list", params, password_prompt=lambda: typer.prompt("Enter master password", hide_input=True))
    if not resp.ok:
        app.out.print_error_and_exit(resp.error, resp.message)
    keys = cast(list[str], resp.data["keys"])
    app.out.print_list(keys)
