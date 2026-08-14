# tencoinlib/wallet_storage/kdf.py
"""
Password-Based Key Derivation for TCW wallet files.

Algorithm: Argon2id  (RFC 9106)
Output:    32 bytes  → AES-256 key

Argon2id combines the side-channel resistance of Argon2i with the
GPU-attack resistance of Argon2d.  OWASP recommends it as the first
choice for password hashing / KDF.

KDF parameter encoding (4 bytes, stored in the TCW header):
    Byte 0:  time_cost     (1–255 iterations)
    Byte 1:  memory_cost   (encoded as log2 of kilobytes, 1–31)
              e.g. 0x10 = 2^16 KiB = 64 MiB
    Byte 2:  parallelism   (1–255 threads)
    Byte 3:  reserved / 0x00
"""

import os
import struct
from dataclasses import dataclass

from argon2.low_level import hash_secret_raw, Type

# ---------------------------------------------------------------------------
# Default parameters
# ---------------------------------------------------------------------------
# OWASP 2023 recommends: time=1, mem=64 MiB, parallelism=4 as minimum.
# For a wallet that is rarely opened, slightly higher cost is acceptable.
_DEFAULT_TIME_COST    = 2       # iterations
_DEFAULT_MEM_LOG2_KIB = 16     # 2^16 KiB = 65536 KiB = 64 MiB
_DEFAULT_PARALLELISM  = 2
_KEY_LEN              = 32     # 256-bit AES key
_SALT_LEN             = 32     # 256-bit salt

# KDF ID byte used in the TCW header
KDF_ID_ARGON2ID = 0x01


@dataclass(frozen=True)
class KDFParams:
    """Argon2id parameters, both runtime and serialisable."""
    time_cost:    int   # iterations
    mem_log2_kib: int   # log2(memory in KiB); memory_kib = 2 ** mem_log2_kib
    parallelism:  int

    @property
    def memory_kib(self) -> int:
        return 2 ** self.mem_log2_kib

    def to_bytes(self) -> bytes:
        """Encode to 4 bytes for TCW header storage."""
        return struct.pack(
            "BBBB",
            self.time_cost,
            self.mem_log2_kib,
            self.parallelism,
            0x00,   # reserved
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "KDFParams":
        """Decode from 4 bytes read from a TCW header."""
        if len(data) != 4:
            raise ValueError(f"KDFParams requires exactly 4 bytes, got {len(data)}")
        time_cost, mem_log2_kib, parallelism, _reserved = struct.unpack("BBBB", data)
        return cls(
            time_cost=time_cost,
            mem_log2_kib=mem_log2_kib,
            parallelism=parallelism,
        )

    @classmethod
    def default(cls) -> "KDFParams":
        return cls(
            time_cost=_DEFAULT_TIME_COST,
            mem_log2_kib=_DEFAULT_MEM_LOG2_KIB,
            parallelism=_DEFAULT_PARALLELISM,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_salt() -> bytes:
    """Return a fresh cryptographically-random 32-byte salt."""
    return os.urandom(_SALT_LEN)


def derive_key(
    password: str,
    salt: bytes,
    params: KDFParams,
) -> bytes:
    """
    Derive a 32-byte AES-256 key from *password* using Argon2id.

    Args:
        password:  User-supplied passphrase (unicode string).
        salt:      Random bytes stored in the TCW header (32 bytes).
        params:    KDF tuning parameters.

    Returns:
        32-byte key suitable for AES-256-GCM.

    Raises:
        ValueError: If salt length is wrong.
    """
    if len(salt) != _SALT_LEN:
        raise ValueError(f"Salt must be {_SALT_LEN} bytes, got {len(salt)}")

    password_bytes = password.encode("utf-8")

    key = hash_secret_raw(
        secret=password_bytes,
        salt=salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_kib,
        parallelism=params.parallelism,
        hash_len=_KEY_LEN,
        type=Type.ID,
    )

    return key


def verify_password_strength(password: str) -> None:
    """
    Raise ValueError if the password is obviously weak.

    This is a basic sanity check, not a strength meter.
    """
    if len(password) < 8:
        raise ValueError("Wallet password must be at least 8 characters")