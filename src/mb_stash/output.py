"""Structured output for CLI and JSON modes."""

from mm_clikit import DualModeOutput


class Output(DualModeOutput):
    """Handles all CLI output in JSON or human-readable format."""

    # --- Setup ---

    def print_init_done(self) -> None:
        """Print store creation confirmation."""
        self.output(json_data={}, display_data="Stash created.")

    def print_password_changed(self) -> None:
        """Print password change confirmation."""
        self.output(json_data={}, display_data="Password changed.")

    # --- Secrets ---

    def print_secret_copied(self, key: str) -> None:
        """Print secret copied to clipboard confirmation."""
        self.output(json_data={"key": key}, display_data=f"Copied '{key}' to clipboard.")

    def print_secret_stdout(self, key: str, value: str) -> None:
        """Print secret value to stdout."""
        self.output(json_data={"key": key, "value": value}, display_data=value)

    def print_list(self, keys: list[str]) -> None:
        """Print list of stored keys."""
        self.output(json_data={"keys": keys}, display_data="\n".join(keys))

    def print_secret_added(self, key: str) -> None:
        """Print secret add confirmation."""
        self.output(json_data={"key": key}, display_data=f"Secret '{key}' added.")

    def print_secret_deleted(self, key: str) -> None:
        """Print secret deletion confirmation."""
        self.output(json_data={"key": key}, display_data=f"Secret '{key}' deleted.")

    def print_secret_renamed(self, old_key: str, new_key: str) -> None:
        """Print secret rename confirmation."""
        self.output(
            json_data={"old_key": old_key, "new_key": new_key}, display_data=f"Secret '{old_key}' renamed to '{new_key}'."
        )

    # --- Daemon ---

    def print_locked(self) -> None:
        """Print stash locked confirmation."""
        self.output(json_data={}, display_data="Stash locked.")

    def print_unlocked(self) -> None:
        """Print stash unlocked confirmation."""
        self.output(json_data={}, display_data="Stash unlocked.")

    def print_stopped(self) -> None:
        """Print daemon stopped confirmation."""
        self.output(json_data={}, display_data="Daemon stopped.")

    def print_health(self, *, running: bool, locked: bool) -> None:
        """Print daemon health status."""
        self.output(
            json_data={"running": running, "locked": locked},
            display_data=f"Daemon: {'running' if running else 'stopped'}, stash: {'locked' if locked else 'unlocked'}.",
        )
