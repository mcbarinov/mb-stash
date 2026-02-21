"""Data access layer for the encrypted secret store."""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag

from mb_stash.crypto import SCRYPT_N, SCRYPT_P, SCRYPT_R, SCRYPT_SALT_LENGTH, decrypt, derive_key, encrypt


@dataclass(frozen=True)
class StoreData:
    """Decoded contents of the encrypted store file."""

    salt: bytes
    nonce: bytes
    ciphertext: bytes


class StashError(Exception):
    """Application-level error raised by Stash operations."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize with a machine-readable code and a human-readable message.

        Args:
            code: Machine-readable error code (e.g. "already_initialized").
            message: Human-readable error description.

        """
        super().__init__(message)
        self.code = code


class Stash:
    """High-level API for stash operations, wrapping crypto and store I/O."""

    def __init__(self, stash_path: Path) -> None:
        """Initialize the stash data access layer.

        Args:
            stash_path: Path to the encrypted store file.

        """
        self._stash_path = stash_path
        # In-memory state (populated by unlock, wiped by lock).
        # _key and _salt are cached because _persist() needs them to re-encrypt on every add/delete.
        # The password is not stored, so the key cannot be re-derived; the salt must match the key it was derived with.
        self._key: bytes | None = None
        self._salt: bytes | None = None
        self._secrets: dict[str, str] | None = None

    @property
    def store_exists(self) -> bool:
        """Check if the encrypted store file exists."""
        return self._stash_path.exists()

    # --- Password operations ---

    def init(self, password: str) -> None:
        """Create a new encrypted store with an empty secret dict.

        Raises:
            StashError: Already exists (code: ``already_initialized``) or empty password (code: ``empty_password``).

        """
        if self.store_exists:
            raise StashError("already_initialized", "Stash already exists.")
        if not password:
            raise StashError("empty_password", "Password cannot be empty.")
        self._stash_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._stash_path.parent.chmod(0o700)
        salt = os.urandom(SCRYPT_SALT_LENGTH)
        key = derive_key(password, salt)
        result = encrypt(b"{}", key)
        self._write_store(StoreData(salt=salt, nonce=result.nonce, ciphertext=result.ciphertext))

    def change_password(self, old_password: str, new_password: str) -> None:
        """Re-encrypt the store with a new password.

        Raises:
            StashError: Not initialized (code: ``not_initialized``), wrong password
                (code: ``wrong_password``), or empty password (code: ``empty_password``).

        """
        self._require_store()
        if not new_password:
            raise StashError("empty_password", "New password cannot be empty.")
        store_data = self._read_store()
        old_key = derive_key(old_password, store_data.salt)
        try:
            plaintext = decrypt(store_data.ciphertext, old_key, store_data.nonce)
        except InvalidTag:
            raise StashError("wrong_password", "Wrong password.") from None
        new_salt = os.urandom(SCRYPT_SALT_LENGTH)
        new_key = derive_key(new_password, new_salt)
        result = encrypt(plaintext, new_key)
        self._write_store(StoreData(salt=new_salt, nonce=result.nonce, ciphertext=result.ciphertext))

    # --- Lock / unlock ---

    def unlock(self, password: str) -> None:
        """Derive key, decrypt store, and hold secrets in memory.

        Raises:
            StashError: Not initialized (code: ``not_initialized``) or wrong password (code: ``wrong_password``).

        """
        self._require_store()
        store_data = self._read_store()
        key = derive_key(password, store_data.salt)
        try:
            plaintext = decrypt(store_data.ciphertext, key, store_data.nonce)
        except InvalidTag:
            raise StashError("wrong_password", "Wrong password.") from None
        try:
            secrets = json.loads(plaintext)
        except json.JSONDecodeError:
            raise StashError("corrupted", "Decrypted store is not valid JSON — store may be corrupted.") from None
        self._key = key
        self._salt = store_data.salt
        self._secrets = secrets

    def lock(self) -> None:
        """Wipe key, salt, and secrets from memory."""
        self._key = None
        self._salt = None
        self._secrets = None

    @property
    def is_unlocked(self) -> bool:
        """Check if the stash is currently unlocked."""
        return self._key is not None and self._secrets is not None

    # --- CRUD (requires unlocked state) ---

    def get(self, key: str) -> str | None:
        """Get a secret by key, or None if not found.

        Raises:
            StashError: Stash is locked (code: ``locked``).

        """
        return self._require_unlocked().get(key)

    def list_keys(self, filter_: str | None = None) -> list[str]:
        """List stored keys, optionally filtered by substring.

        Raises:
            StashError: Stash is locked (code: ``locked``).

        """
        keys = sorted(self._require_unlocked())
        if filter_:
            keys = [k for k in keys if filter_ in k]
        return keys

    def add(self, key: str, value: str) -> None:
        """Add or update a secret and re-encrypt the store.

        Raises:
            StashError: Stash is locked (code: ``locked``), empty key (code: ``empty_key``),
                or empty value (code: ``empty_value``).

        """
        if not key:
            raise StashError("empty_key", "Key cannot be empty.")
        if not value:
            raise StashError("empty_value", "Value cannot be empty.")
        self._require_unlocked()[key] = value
        self._persist()

    def delete(self, key: str) -> bool:
        """Delete a secret and re-encrypt the store. Return True if key existed.

        Raises:
            StashError: Stash is locked (code: ``locked``).

        """
        secrets = self._require_unlocked()
        if key not in secrets:
            return False
        del secrets[key]
        self._persist()
        return True

    # --- Private helpers ---

    def _require_store(self) -> None:
        """Raise if the store file does not exist.

        Raises:
            StashError: Not initialized (code: ``not_initialized``).

        """
        if not self.store_exists:
            raise StashError("not_initialized", "Stash is not initialized. Run 'mb-stash init' first.")

    def _require_unlocked(self) -> dict[str, str]:
        """Return secrets dict or raise if locked.

        Raises:
            StashError: Stash is locked (code: ``locked``).

        """
        if self._secrets is None or self._key is None:
            raise StashError("locked", "Stash is locked. Unlock it first.")
        return self._secrets

    def _persist(self) -> None:
        """Re-encrypt and write secrets to disk.

        Raises:
            StashError: Stash is locked (code: ``locked``).

        """
        if self._key is None or self._salt is None or self._secrets is None:
            raise StashError("locked", "Stash is locked. Unlock it first.")
        plaintext = json.dumps(self._secrets).encode()
        result = encrypt(plaintext, self._key)
        self._write_store(StoreData(salt=self._salt, nonce=result.nonce, ciphertext=result.ciphertext))

    # --- Store I/O ---

    def _read_store(self) -> StoreData:
        """Read the encrypted store and return decoded data."""
        store = json.loads(self._stash_path.read_text())
        return StoreData(
            salt=base64.b64decode(store["kdf"]["salt"]),
            nonce=base64.b64decode(store["encryption"]["nonce"]),
            ciphertext=base64.b64decode(store["encryption"]["ciphertext"]),
        )

    def _write_store(self, store_data: StoreData) -> None:
        """Write the encrypted store atomically."""
        store = {
            "kdf": {
                "algorithm": "scrypt",
                "salt": base64.b64encode(store_data.salt).decode(),
                "n": SCRYPT_N,
                "r": SCRYPT_R,
                "p": SCRYPT_P,
            },
            "encryption": {
                "algorithm": "aes-256-gcm",
                "nonce": base64.b64encode(store_data.nonce).decode(),
                "ciphertext": base64.b64encode(store_data.ciphertext).decode(),
            },
        }
        tmp_path = self._stash_path.with_suffix(".tmp")
        data = (json.dumps(store, indent=2) + "\n").encode()
        # os.open with explicit 0o600: ensures owner-only perms regardless of umask,
        # preventing other users from copying the encrypted blob for offline brute-force.
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        tmp_path.replace(self._stash_path)
