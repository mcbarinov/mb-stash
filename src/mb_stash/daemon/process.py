"""Process liveness, PID file utilities, and daemon spawning."""

import contextlib
import socket
import time
from pathlib import Path

from mm_clikit import is_process_running, read_pid_file, spawn_detached, stop_process

from mb_stash.config import Config

# Polling parameters for ensure_daemon
_POLL_INTERVAL = 0.05
_POLL_TIMEOUT = 5.0


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


def stop_daemon(cfg: Config) -> bool:
    """Stop the daemon via SIGTERM, falling back to SIGKILL. Return True if a daemon was stopped."""
    pid = read_pid_file(cfg.daemon_pid_path)
    if pid is None:
        return False

    stopped = stop_process(pid)
    _cleanup_files(cfg)
    return stopped


def is_daemon_running(cfg: Config) -> bool:
    """Check whether the daemon is running via PID or socket."""
    return is_process_running(cfg.daemon_pid_path, command_contains="mb-stash") or is_connectable(cfg.daemon_sock_path)


def ensure_daemon(cfg: Config) -> None:
    """Ensure the daemon is running and accepting connections. Spawns if needed.

    Raises:
        RuntimeError: Daemon fails to start within timeout.

    """
    if is_connectable(cfg.daemon_sock_path):
        return

    # Socket not connectable — spawn a new daemon
    spawn_detached(["mb-stash", "--data-dir", str(cfg.data_dir), "daemon"])

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
