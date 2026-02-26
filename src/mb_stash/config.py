"""Centralized application configuration."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

DEFAULT_DATA_DIR = Path.home() / ".local" / "mb-stash"


class Config(BaseModel):
    """Application-wide configuration."""

    model_config = ConfigDict(frozen=True)

    data_dir: Path = Field(description="Base directory for all application data")
    clipboard_timeout: int = Field(default=30, ge=1, description="Clipboard auto-clear timeout in seconds")
    inactivity_timeout: int = Field(default=0, ge=0, description="Auto-lock after inactivity in seconds (0 = disabled)")

    @computed_field(description="Encrypted store file")
    @property
    def stash_path(self) -> Path:
        """Encrypted store file."""
        return self.data_dir / "stash.json"

    @computed_field(description="Optional TOML configuration file")
    @property
    def config_path(self) -> Path:
        """Optional TOML configuration file."""
        return self.data_dir / "config.toml"

    @computed_field(description="Unix domain socket for daemon")
    @property
    def daemon_sock_path(self) -> Path:
        """Unix domain socket for daemon."""
        return self.data_dir / "daemon.sock"

    @computed_field(description="Daemon PID file")
    @property
    def daemon_pid_path(self) -> Path:
        """Daemon PID file."""
        return self.data_dir / "daemon.pid"

    @computed_field(description="Log file")
    @property
    def log_path(self) -> Path:
        """Log file."""
        return self.data_dir / "stash.log"

    def cli_base_args(self) -> list[str]:
        """Build CLI base args, including --data-dir only when non-default."""
        args: list[str] = ["mb-stash"]
        if self.data_dir != DEFAULT_DATA_DIR:
            args.extend(["--data-dir", str(self.data_dir)])
        return args

    @staticmethod
    def build(data_dir: Path | None = None) -> Config:
        """Build a Config from defaults and optional config.toml."""
        resolved_dir = data_dir if data_dir is not None else DEFAULT_DATA_DIR
        config_path = resolved_dir / "config.toml"

        kwargs: dict[str, Any] = {"data_dir": resolved_dir}
        if config_path.is_file():
            with config_path.open("rb") as f:
                toml_data = tomllib.load(f)
            if isinstance(toml_data.get("clipboard_timeout"), int):
                kwargs["clipboard_timeout"] = toml_data["clipboard_timeout"]
            if isinstance(toml_data.get("inactivity_timeout"), int):
                kwargs["inactivity_timeout"] = toml_data["inactivity_timeout"]

        return Config(**kwargs)
