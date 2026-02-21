"""Tests for the Stash data access layer."""

from pathlib import Path

import pytest

from mb_stash.stash import Stash, StashError

PASSWORD = "test-password"
OTHER_PASSWORD = "other-password"


@pytest.fixture
def stash(tmp_path: Path) -> Stash:
    """Stash instance with a temporary store path."""
    return Stash(tmp_path / "stash.json")


@pytest.fixture
def ready_stash(stash: Stash) -> Stash:
    """Create an initialized and unlocked stash with two secrets."""
    stash.init(PASSWORD)
    stash.unlock(PASSWORD)
    stash.add("alpha", "value-a")
    stash.add("beta", "value-b")
    return stash


class TestInit:
    """Store creation."""

    def test_creates_store_file(self, stash: Stash) -> None:
        """Store file exists on disk after init."""
        stash.init(PASSWORD)
        assert stash.store_exists

    def test_parent_directory_permissions(self, tmp_path: Path) -> None:
        """Parent directory has 0o700 permissions."""
        stash_path = tmp_path / "sub" / "stash.json"
        Stash(stash_path).init(PASSWORD)
        mode = stash_path.parent.stat().st_mode & 0o777
        assert mode == 0o700

    def test_store_file_permissions(self, tmp_path: Path) -> None:
        """Store file has 0o600 permissions."""
        stash_path = tmp_path / "sub" / "stash.json"
        Stash(stash_path).init(PASSWORD)
        mode = stash_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_empty_password(self, stash: Stash) -> None:
        """Empty password raises StashError."""
        with pytest.raises(StashError) as exc_info:
            stash.init("")
        assert exc_info.value.code == "empty_password"

    def test_already_initialized(self, stash: Stash) -> None:
        """Double init raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.init(PASSWORD)
        assert exc_info.value.code == "already_initialized"


class TestChangePassword:
    """Re-encryption with a new password."""

    def test_secrets_accessible_with_new_password(self, ready_stash: Stash) -> None:
        """Secrets are readable after changing password."""
        ready_stash.change_password(PASSWORD, OTHER_PASSWORD)
        ready_stash.lock()
        ready_stash.unlock(OTHER_PASSWORD)
        assert ready_stash.get("alpha") == "value-a"

    def test_wrong_old_password(self, ready_stash: Stash) -> None:
        """Wrong old password raises StashError."""
        with pytest.raises(StashError) as exc_info:
            ready_stash.change_password("wrong", OTHER_PASSWORD)
        assert exc_info.value.code == "wrong_password"

    def test_empty_new_password(self, ready_stash: Stash) -> None:
        """Empty new password raises StashError."""
        with pytest.raises(StashError) as exc_info:
            ready_stash.change_password(PASSWORD, "")
        assert exc_info.value.code == "empty_password"

    def test_not_initialized(self, stash: Stash) -> None:
        """Uninitialized store raises StashError."""
        with pytest.raises(StashError) as exc_info:
            stash.change_password(PASSWORD, OTHER_PASSWORD)
        assert exc_info.value.code == "not_initialized"


class TestUnlockLock:
    """Lock/unlock state transitions."""

    def test_unlock_enables_access(self, stash: Stash) -> None:
        """Unlock decrypts and enables secret access."""
        stash.init(PASSWORD)
        stash.unlock(PASSWORD)
        assert stash.is_unlocked

    def test_lock_wipes_memory(self, ready_stash: Stash) -> None:
        """Lock clears in-memory state."""
        ready_stash.lock()
        assert not ready_stash.is_unlocked

    def test_wrong_password(self, stash: Stash) -> None:
        """Wrong password raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.unlock("wrong")
        assert exc_info.value.code == "wrong_password"

    def test_not_initialized(self, stash: Stash) -> None:
        """Uninitialized store raises StashError."""
        with pytest.raises(StashError) as exc_info:
            stash.unlock(PASSWORD)
        assert exc_info.value.code == "not_initialized"

    def test_is_unlocked_reflects_transitions(self, stash: Stash) -> None:
        """is_unlocked tracks lock/unlock cycle."""
        stash.init(PASSWORD)
        assert not stash.is_unlocked
        stash.unlock(PASSWORD)
        assert stash.is_unlocked
        stash.lock()
        assert not stash.is_unlocked

    def test_store_exists_before_and_after_init(self, stash: Stash) -> None:
        """store_exists is False before init, True after."""
        assert not stash.store_exists
        stash.init(PASSWORD)
        assert stash.store_exists


class TestGet:
    """Read secrets."""

    def test_existing_key(self, ready_stash: Stash) -> None:
        """Returns value for existing key."""
        assert ready_stash.get("alpha") == "value-a"

    def test_missing_key(self, ready_stash: Stash) -> None:
        """Returns None for non-existing key."""
        assert ready_stash.get("nonexistent") is None

    def test_locked(self, stash: Stash) -> None:
        """Locked stash raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.get("alpha")
        assert exc_info.value.code == "locked"


class TestListKeys:
    """Key listing."""

    def test_sorted_keys(self, ready_stash: Stash) -> None:
        """Returns keys in sorted order."""
        assert ready_stash.list_keys() == ["alpha", "beta"]

    def test_filter(self, ready_stash: Stash) -> None:
        """Filter narrows results by substring."""
        assert ready_stash.list_keys("alp") == ["alpha"]

    def test_filter_no_match(self, ready_stash: Stash) -> None:
        """Filter with no match returns empty list."""
        assert ready_stash.list_keys("zzz") == []

    def test_locked(self, stash: Stash) -> None:
        """Locked stash raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.list_keys()
        assert exc_info.value.code == "locked"


class TestAdd:
    """Add/update secrets."""

    def test_persists_to_disk(self, stash: Stash) -> None:
        """New key survives lock → unlock cycle."""
        stash.init(PASSWORD)
        stash.unlock(PASSWORD)
        stash.add("key1", "val1")
        stash.lock()
        stash.unlock(PASSWORD)
        assert stash.get("key1") == "val1"

    def test_update_existing(self, ready_stash: Stash) -> None:
        """Existing key gets updated."""
        ready_stash.add("alpha", "new-value")
        assert ready_stash.get("alpha") == "new-value"

    def test_empty_key(self, ready_stash: Stash) -> None:
        """Empty key raises StashError."""
        with pytest.raises(StashError) as exc_info:
            ready_stash.add("", "value")
        assert exc_info.value.code == "empty_key"

    def test_empty_value(self, ready_stash: Stash) -> None:
        """Empty value raises StashError."""
        with pytest.raises(StashError) as exc_info:
            ready_stash.add("key", "")
        assert exc_info.value.code == "empty_value"

    def test_locked(self, stash: Stash) -> None:
        """Locked stash raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.add("key", "value")
        assert exc_info.value.code == "locked"


class TestDelete:
    """Delete secrets."""

    def test_existing_key(self, ready_stash: Stash) -> None:
        """Existing key returns True and is removed."""
        assert ready_stash.delete("alpha") is True
        assert ready_stash.get("alpha") is None

    def test_missing_key(self, ready_stash: Stash) -> None:
        """Non-existing key returns False."""
        assert ready_stash.delete("nonexistent") is False

    def test_persists_to_disk(self, stash: Stash) -> None:
        """Delete survives lock → unlock cycle."""
        stash.init(PASSWORD)
        stash.unlock(PASSWORD)
        stash.add("key1", "val1")
        stash.delete("key1")
        stash.lock()
        stash.unlock(PASSWORD)
        assert stash.get("key1") is None

    def test_locked(self, stash: Stash) -> None:
        """Locked stash raises StashError."""
        stash.init(PASSWORD)
        with pytest.raises(StashError) as exc_info:
            stash.delete("key")
        assert exc_info.value.code == "locked"
