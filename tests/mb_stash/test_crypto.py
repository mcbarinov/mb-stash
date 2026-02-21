"""Tests for cryptographic operations."""

import base64

import pytest
from cryptography.exceptions import InvalidTag

from mb_stash.crypto import SCRYPT_KEY_LENGTH, decrypt, derive_key, encrypt

SALT_16 = b"0123456789abcdef"


class TestDeriveKey:
    """Key derivation with scrypt."""

    def test_deterministic(self):
        """Same password + salt produces identical key."""
        key1 = derive_key("password", SALT_16)
        key2 = derive_key("password", SALT_16)
        assert key1 == key2

    def test_key_length(self):
        """Key is exactly 32 bytes (AES-256)."""
        key = derive_key("password", SALT_16)
        assert len(key) == SCRYPT_KEY_LENGTH

    def test_different_passwords(self):
        """Different passwords produce different keys."""
        key1 = derive_key("password-a", SALT_16)
        key2 = derive_key("password-b", SALT_16)
        assert key1 != key2

    def test_different_salts(self):
        """Different salts produce different keys."""
        key1 = derive_key("password", b"salt-aaaaaaaaaa01")
        key2 = derive_key("password", b"salt-bbbbbbbbbb02")
        assert key1 != key2


class TestEncryptDecrypt:
    """Round-trip encryption/decryption."""

    def test_round_trip(self):
        """Encrypt → decrypt returns original plaintext."""
        key = derive_key("password", SALT_16)
        plaintext = b"hello, world"
        result = encrypt(plaintext, key)
        assert decrypt(result.ciphertext, key, result.nonce) == plaintext

    def test_wrong_key(self):
        """Wrong key raises InvalidTag."""
        key = derive_key("password", SALT_16)
        wrong_key = derive_key("wrong", SALT_16)
        result = encrypt(b"secret", key)
        with pytest.raises(InvalidTag):
            decrypt(result.ciphertext, wrong_key, result.nonce)

    def test_tampered_ciphertext(self):
        """Tampered ciphertext raises InvalidTag."""
        key = derive_key("password", SALT_16)
        result = encrypt(b"secret", key)
        tampered = bytearray(result.ciphertext)
        tampered[0] ^= 0xFF
        with pytest.raises(InvalidTag):
            decrypt(bytes(tampered), key, result.nonce)

    def test_tampered_nonce(self):
        """Tampered nonce raises InvalidTag."""
        key = derive_key("password", SALT_16)
        result = encrypt(b"secret", key)
        tampered = bytearray(result.nonce)
        tampered[0] ^= 0xFF
        with pytest.raises(InvalidTag):
            decrypt(result.ciphertext, key, bytes(tampered))


class TestDecryptKnownVector:
    """Regression test with a hardcoded encrypt output."""

    KNOWN_KEY = base64.b64decode("GIKHS4/BTgb8u3rM4VECH8dApZlcQfhcpm/UAzY3m0s=")
    KNOWN_NONCE = base64.b64decode("HO9U3SqTuiDfNFaP")
    KNOWN_CIPHERTEXT = base64.b64decode("YkabsB3Xkj7XwhjRC6DgrujBLXkXQc4gZi3BXRdwNRdvb2k9RH3j9eQ2Gqw=")
    KNOWN_PLAINTEXT = b'{"my-token": "secret-value"}'

    def test_known_vector(self):
        """Decrypt a known ciphertext to verify no algorithm regression."""
        result = decrypt(self.KNOWN_CIPHERTEXT, self.KNOWN_KEY, self.KNOWN_NONCE)
        assert result == self.KNOWN_PLAINTEXT
