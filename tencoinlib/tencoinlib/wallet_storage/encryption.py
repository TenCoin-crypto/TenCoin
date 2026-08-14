# tencoinlib/wallet_storage/encryption.py
"""
AES-256-GCM authenticated encryption for TCW wallet payloads.

Algorithm:  AES-256-GCM  (NIST SP 800-38D)
Nonce:      96-bit (12 bytes), randomly generated per save
Tag:        128-bit (16 bytes), appended by the cryptography library
AAD:        TCW header bytes (magic + version + cipher_id + kdf_id + flags)

The `cryptography` library is used for the AES-GCM primitive; no
hand-rolled AES implementation is present anywhere in this module.

encrypt() output layout (on disk, after the header):
    [ ciphertext || 16-byte GCM authentication tag ]

The GCM tag is appended automatically by AESGCM.encrypt().
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NONCE_LEN  = 12   # 96-bit nonce — NIST recommended for interoperability
TAG_LEN    = 16   # 128-bit authentication tag
KEY_LEN    = 32   # 256-bit AES key

# Cipher ID byte used in the TCW header
CIPHER_ID_AES256_GCM = 0x01


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_nonce() -> bytes:
    """Return a fresh cryptographically-random 12-byte GCM nonce."""
    return os.urandom(NONCE_LEN)


def encrypt(
    key: bytes,
    nonce: bytes,
    plaintext: bytes,
    aad: bytes,
) -> bytes:
    """
    Encrypt *plaintext* with AES-256-GCM.

    Args:
        key:        32-byte AES-256 key (output of kdf.derive_key).
        nonce:      12-byte nonce (MUST be unique per (key, file-save).
        plaintext:  Raw bytes to encrypt (the serialised wallet payload).
        aad:        Additional Authenticated Data — authenticated but NOT
                    encrypted.  Pass the serialised TCW header so the
                    header cannot be tampered with without detection.

    Returns:
        ciphertext || 16-byte GCM tag  (concatenated by cryptography).

    Raises:
        ValueError: On key or nonce length mismatch.
    """
    _check_key(key)
    _check_nonce(nonce)

    aesgcm = AESGCM(key)
    # AESGCM.encrypt() appends the 16-byte tag automatically.
    return aesgcm.encrypt(nonce, plaintext, aad)


def decrypt(
    key: bytes,
    nonce: bytes,
    ciphertext_with_tag: bytes,
    aad: bytes,
) -> bytes:
    """
    Decrypt and authenticate *ciphertext_with_tag* with AES-256-GCM.

    Args:
        key:                  32-byte AES-256 key.
        nonce:                12-byte nonce read from the TCW header.
        ciphertext_with_tag:  Raw bytes from the TCW payload section
                              (ciphertext + 16-byte GCM tag).
        aad:                  Same AAD bytes that were passed to encrypt().

    Returns:
        Decrypted plaintext bytes.

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails due to
            wrong password, corrupted file, or tampered header/payload.
        ValueError: On key or nonce length mismatch.
    """
    _check_key(key)
    _check_nonce(nonce)

    if len(ciphertext_with_tag) < TAG_LEN:
        raise ValueError(
            f"Ciphertext too short: expected at least {TAG_LEN} bytes "
            f"for the GCM tag, got {len(ciphertext_with_tag)}"
        )

    aesgcm = AESGCM(key)
    # Raises cryptography.exceptions.InvalidTag on authentication failure.
    return aesgcm.decrypt(nonce, ciphertext_with_tag, aad)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_key(key: bytes) -> None:
    if len(key) != KEY_LEN:
        raise ValueError(f"AES-256 key must be {KEY_LEN} bytes, got {len(key)}")


def _check_nonce(nonce: bytes) -> None:
    if len(nonce) != NONCE_LEN:
        raise ValueError(f"GCM nonce must be {NONCE_LEN} bytes, got {len(nonce)}")