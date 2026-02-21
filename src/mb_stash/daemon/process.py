"""Process liveness, PID file utilities, and daemon spawning."""

import contextlib
import os
import signal
import socket
import subprocess  # nosec B404
import tempfile
import time
from pathlib import Path

from mb_stash.config import Config

# Polling parameters for ensure_daemon
_POLL_INTERVAL = 0.05
_POLL_TIMEOUT = 5.0


def read_pid(pid_path: Path) -> int | None:
    """Read PID from file, returning None if missing or invalid."""
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text().strip())
    except ValueError, OSError:
        return None


def is_alive(pid_path: Path) -> bool:
    """Check whether a process is running by PID file and process liveness."""
    pid = read_pid(pid_path)
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass

    # Verify process is a Python process
    try:
        # S603/S607: args are controlled literals, "ps" is a standard system utility
        result = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, check=False)  # noqa: S603, S607  # nosec B603, B607
        return "python" in result.stdout.lower()
    except OSError:
        return False


def write_pid_file(pid_path: Path) -> None:
    """Write current PID to a PID file atomically."""
    fd, tmp_path = tempfile.mkstemp(dir=pid_path.parent, prefix=".daemon.pid.")
    tmp = Path(tmp_path)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        tmp.replace(pid_path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def is_connectable(sock_path: Path) -> bool:
    """Check if the daemon socket is accepting connections."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(str(sock_path))
    except ConnectionRefusedError, FileNotFoundError, OSError:
        return False
    else:
        return True


def spawn_daemon(cfg: Config) -> None:
    """Launch the daemon as a detached background process."""
    # S603/S607: args are controlled literals, "mb-stash" is our own CLI entry point
    subprocess.Popen(  # noqa: S603  # nosec B603, B607
        ["mb-stash", "--data-dir", str(cfg.data_dir), "daemon"],  # noqa: S607
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def stop_daemon(cfg: Config) -> bool:
    """Stop the daemon via SIGTERM, falling back to SIGKILL. Return True if a daemon was stopped."""
    pid = read_pid(cfg.daemon_pid_path)
    if pid is None:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        # Already dead — clean up stale files
        _cleanup_files(cfg)
        return False

    # Poll for process exit
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            _cleanup_files(cfg)
            return True
        time.sleep(0.1)

    # Force kill
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    _cleanup_files(cfg)
    return True


def is_daemon_running(cfg: Config) -> bool:
    """Check whether the daemon is running via PID or socket."""
    return is_alive(cfg.daemon_pid_path) or is_connectable(cfg.daemon_sock_path)


def ensure_daemon(cfg: Config) -> None:
    """Ensure the daemon is running and accepting connections. Spawns if needed.

    Raises:
        RuntimeError: Daemon fails to start within timeout.

    """
    if is_connectable(cfg.daemon_sock_path):
        return

    # Socket not connectable — spawn a new daemon
    spawn_daemon(cfg)

    # Poll until socket is ready
    deadline = time.monotonic() + _POLL_TIMEOUT
    while time.monotonic() < deadline:
        if is_connectable(cfg.daemon_sock_path):
            return
        time.sleep(_POLL_INTERVAL)

    msg = f"Daemon failed to start within {_POLL_TIMEOUT}s."
    raise RuntimeError(msg)


def _cleanup_files(cfg: Config) -> None:
    """Remove stale PID and socket files."""
    with contextlib.suppress(OSError):
        cfg.daemon_pid_path.unlink()
    with contextlib.suppress(OSError):
        cfg.daemon_sock_path.unlink()
