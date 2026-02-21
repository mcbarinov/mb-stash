"""Cryptographic operations: key derivation, encryption, decryption."""

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# scrypt KDF parameters
SCRYPT_SALT_LENGTH = 16
SCRYPT_KEY_LENGTH = 32
SCRYPT_N = 1_048_576
SCRYPT_R = 8
SCRYPT_P = 1

# AES-256-GCM parameters
AES_GCM_NONCE_LENGTH = 12


@dataclass(frozen=True)
class EncryptResult:
    """Result of AES-256-GCM encryption."""

    nonce: bytes
    ciphertext: bytes


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from password and salt using scrypt."""
    kdf = Scrypt(salt=salt, length=SCRYPT_KEY_LENGTH, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(password.encode())


def encrypt(plaintext: bytes, key: bytes) -> EncryptResult:
    """Encrypt plaintext with AES-256-GCM."""
    nonce = os.urandom(AES_GCM_NONCE_LENGTH)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return EncryptResult(nonce=nonce, ciphertext=ciphertext)


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decrypt ciphertext with AES-256-GCM.

    Raises:
        InvalidTag: Wrong key or tampered ciphertext.

    """
    return AESGCM(key).decrypt(nonce, ciphertext, None)
