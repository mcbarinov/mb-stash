"""Clipboard utility — copy text via system clipboard."""

import platform
import subprocess  # nosec B404


def _clipboard_cmd() -> list[str]:
    """Return the platform-specific clipboard command."""
    return ["pbcopy"] if platform.system() == "Darwin" else ["xclip", "-selection", "clipboard"]


def copy(text: str) -> None:
    """Copy text to the system clipboard.

    Uses pbcopy on macOS, xclip on Linux.
    """
    # S603: args are controlled literals — hardcoded clipboard commands
    subprocess.run(_clipboard_cmd(), input=text.encode(), check=True)  # noqa: S603  # nosec B603


def clear() -> None:
    """Clear the system clipboard."""
    # S603: args are controlled literals — hardcoded clipboard commands
    subprocess.run(_clipboard_cmd(), input=b"", check=True)  # noqa: S603  # nosec B603
