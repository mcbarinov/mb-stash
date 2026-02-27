"""CLI entry point for mb-stash."""

from pathlib import Path
from typing import Annotated

import typer
from mm_clikit import TyperPlus

from mb_stash.app_context import AppContext
from mb_stash.commands.add import add
from mb_stash.commands.change_password import change_password
from mb_stash.commands.daemon import daemon
from mb_stash.commands.delete import delete
from mb_stash.commands.get import get
from mb_stash.commands.health import health
from mb_stash.commands.init import init
from mb_stash.commands.list import list_
from mb_stash.commands.lock import lock
from mb_stash.commands.rename import rename
from mb_stash.commands.stop import stop
from mb_stash.commands.unlock import unlock
from mb_stash.config import Config
from mb_stash.log import setup_logging
from mb_stash.output import Output
from mb_stash.stash import Stash

app = TyperPlus(package_name="mb-stash")


@app.callback()
def callback(
    ctx: typer.Context,
    *,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON.")] = False,
    data_dir: Annotated[Path | None, typer.Option("--data-dir", help="Data directory path.")] = None,
) -> None:
    """Quick access to non-critical secrets from the terminal."""
    cfg = Config.build(data_dir)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(cfg.log_path)
    ctx.obj = AppContext(out=Output(json_mode=json_output), stash=Stash(cfg.stash_path), cfg=cfg)


# Setup
app.command()(init)
app.command("change-password")(change_password)

# Daemon
app.command(hidden=True)(daemon)
app.command()(stop)
app.command()(lock)
app.command()(unlock)
app.command(aliases=["h"])(health)

# Secrets
app.command(aliases=["g"])(get)
app.command("list", aliases=["l"])(list_)
app.command()(add)
app.command()(delete)
app.command()(rename)
