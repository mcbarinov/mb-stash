"""Tests for Config model validation and computed paths."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from mb_stash.config import Config

DATA_DIR = Path("/fake/data-dir")


class TestConfigPaths:
    """Computed path properties derive from data_dir."""

    def test_stash_path(self):
        """Stash file is data_dir / stash.json."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.stash_path == DATA_DIR / "stash.json"

    def test_config_path(self):
        """Config file is data_dir / config.toml."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.config_path == DATA_DIR / "config.toml"

    def test_daemon_sock_path(self):
        """Socket file is data_dir / daemon.sock."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.daemon_sock_path == DATA_DIR / "daemon.sock"

    def test_daemon_pid_path(self):
        """PID file is data_dir / daemon.pid."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.daemon_pid_path == DATA_DIR / "daemon.pid"

    def test_log_path(self):
        """Log file is data_dir / stash.log."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.log_path == DATA_DIR / "stash.log"


class TestConfigValidation:
    """Pydantic field constraints."""

    def test_defaults(self):
        """Default values for optional fields."""
        cfg = Config(data_dir=DATA_DIR)
        assert cfg.clipboard_timeout == 30
        assert cfg.inactivity_timeout == 0

    def test_clipboard_timeout_below_minimum(self):
        """clipboard_timeout < 1 is rejected."""
        with pytest.raises(ValidationError):
            Config(data_dir=DATA_DIR, clipboard_timeout=0)

    def test_inactivity_timeout_below_minimum(self):
        """inactivity_timeout < 0 is rejected."""
        with pytest.raises(ValidationError):
            Config(data_dir=DATA_DIR, inactivity_timeout=-1)
