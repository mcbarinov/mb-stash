"""Clipboard utility — copy text via system clipboard."""

import platform
import subprocess  # nosec B404


def _copy_cmd() -> list[str]:
    """Return the platform-specific clipboard copy command."""
    return ["pbcopy"] if platform.system() == "Darwin" else ["xclip", "-selection", "clipboard"]


def _paste_cmd() -> list[str]:
    """Return the platform-specific clipboard paste command."""
    return ["pbpaste"] if platform.system() == "Darwin" else ["xclip", "-selection", "clipboard", "-o"]


def copy(text: str) -> None:
    """Copy text to the system clipboard.

    Uses pbcopy on macOS, xclip on Linux.
    """
    # S603: args are controlled literals — hardcoded clipboard commands
    subprocess.run(_copy_cmd(), input=text.encode(), check=True)  # noqa: S603  # nosec B603


def read() -> str:
    """Read current clipboard content."""
    # S603: args are controlled literals — hardcoded clipboard commands
    result = subprocess.run(_paste_cmd(), capture_output=True, check=True)  # noqa: S603  # nosec B603
    return result.stdout.decode()


def clear(*, expected: str | None = None) -> None:
    """Clear the system clipboard.

    If expected is provided, only clear when the clipboard still contains that value.
    """
    if expected is not None and read() != expected:
        return
    # S603: args are controlled literals — hardcoded clipboard commands
    subprocess.run(_copy_cmd(), input=b"", check=True)  # noqa: S603  # nosec B603
