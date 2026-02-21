"""Application context shared across CLI commands."""

from dataclasses import dataclass

import typer

from mb_stash.config import Config
from mb_stash.output import Output
from mb_stash.stash import Stash


@dataclass(frozen=True, slots=True)
class AppContext:
    """Shared application state passed through Typer context."""

    out: Output
    stash: Stash
    cfg: Config


def use_context(ctx: typer.Context) -> AppContext:
    """Extract application context from Typer context."""
    result: AppContext = ctx.obj
    return result
