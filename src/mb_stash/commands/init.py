"""First-time setup: create master password."""

import typer

from mb_stash.app_context import use_context
from mb_stash.stash import StashError


def init(ctx: typer.Context) -> None:
    """First-time setup: create master password."""
    app = use_context(ctx)
    password: str = typer.prompt("Create master password", hide_input=True, confirmation_prompt=True)
    try:
        app.stash.init(password)
    except StashError as e:
        app.out.print_error_and_exit(e.code, str(e))
    app.out.print_init_done()
