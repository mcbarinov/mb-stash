"""Change master password."""

import typer

from mb_stash.app_context import use_context
from mb_stash.daemon.process import stop_daemon
from mb_stash.stash import StashError


def change_password(ctx: typer.Context) -> None:
    """Change master password."""
    app = use_context(ctx)
    old_password: str = typer.prompt("Current password", hide_input=True)
    new_password: str = typer.prompt("New password", hide_input=True, confirmation_prompt=True)
    stop_daemon(app.cfg)
    try:
        app.stash.change_password(old_password, new_password)
    except StashError as e:
        app.out.print_error_and_exit(e.code, str(e))
    app.out.print_password_changed()
