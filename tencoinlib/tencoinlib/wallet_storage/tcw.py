# tencoinlib/wallet_storage/tcw.py
"""
TCW v1 — TenCoin Wallet binary container format.

On-disk layout:
┌──────────────────────────────────────────────────────────────┐
│ FIXED HEADER  (20 bytes)                                     │
│   magic        3 bytes   b"TCW"                              │
│   version      1 byte    0x01                                │
│   kdf_id       1 byte    0x01 = Argon2id                     │
│   cipher_id    1 byte    0x01 = AES-256-GCM                  │
│   flags        1 byte    reserved, must be 0x00              │
│   salt_len     1 byte    always 32                           │
│   nonce_len    1 byte    always 12                           │
│   kdf_params_len 2 bytes always 4  (big-endian)              │
│   payload_len  8 bytes   big-endian uint64                   │
├──────────────────────────────────────────────────────────────┤
│ SALT           32 bytes                                      │
├──────────────────────────────────────────────────────────────┤
│ KDF PARAMETERS  4 bytes                                      │
├──────────────────────────────────────────────────────────────┤
│ NONCE          12 bytes                                      │
├──────────────────────────────────────────────────────────────┤
│ ENCRYPTED PAYLOAD  (payload_len bytes)                       │
│   [ ciphertext || 16-byte GCM tag ]                         │
└──────────────────────────────────────────────────────────────┘

AAD (authenticated but not encrypted) = the 20-byte fixed header.
This means any change to magic, version, kdf_id, cipher_id, flags,
or length fields causes authentication to fail at decrypt time.

The payload is a UTF-8 encoded JSON document containing all wallet
secrets.  It is never written to disk in plaintext.
"""

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

from cryptography.exceptions import InvalidTag

from .kdf import KDFParams, KDF_ID_ARGON2ID, derive_key, generate_salt
from .encryption import (
    CIPHER_ID_AES256_GCM,
    NONCE_LEN,
    encrypt,
    decrypt,
    generate_nonce,
)

# ---------------------------------------------------------------------------
# Format constants
# ---------------------------------------------------------------------------
MAGIC              = b"TCW"
FORMAT_VERSION     = 0x01
FIXED_HEADER_LEN   = 20    # bytes
SALT_LEN           = 32
KDF_PARAMS_LEN     = 4


# ---------------------------------------------------------------------------
# Header dataclass
# ---------------------------------------------------------------------------

@dataclass
class TCWHeader:
    """Parsed representation of the 20-byte TCW fixed header."""
    version:         int
    kdf_id:          int
    cipher_id:       int
    flags:           int
    salt_len:        int
    nonce_len:       int
    kdf_params_len:  int
    payload_len:     int

    def to_bytes(self) -> bytes:
        """Serialise to the 20-byte wire format (also used as AAD)."""
        return (
            MAGIC
            + struct.pack(
                ">BBBBBBBHQ",
                self.version,
                self.kdf_id,
                self.cipher_id,
                self.flags,
                self.salt_len,
                self.nonce_len,
                0,                    # padding so struct aligns to 2-byte kdf_params_len
                self.kdf_params_len,
                self.payload_len,
            )
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "TCWHeader":
        """Parse the 20-byte fixed header from raw bytes."""
        if len(data) < FIXED_HEADER_LEN:
            raise TCWFormatError(
                f"File too short: expected at least {FIXED_HEADER_LEN} bytes, got {len(data)}"
            )

        magic = data[:3]
        if magic != MAGIC:
            raise TCWFormatError(
                f"Not a TCW file (magic={magic!r}, expected {MAGIC!r})"
            )

        (
            version,
            kdf_id,
            cipher_id,
            flags,
            salt_len,
            nonce_len,
            _pad,
            kdf_params_len,
            payload_len,
        ) = struct.unpack(">BBBBBBBHQ", data[3:FIXED_HEADER_LEN])

        return cls(
            version=version,
            kdf_id=kdf_id,
            cipher_id=cipher_id,
            flags=flags,
            salt_len=salt_len,
            nonce_len=nonce_len,
            kdf_params_len=kdf_params_len,
            payload_len=payload_len,
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TCWError(Exception):
    """Base exception for TCW format errors."""


class TCWFormatError(TCWError):
    """Raised when the file structure is invalid or unrecognised."""


class TCWAuthError(TCWError):
    """
    Raised when AES-GCM authentication fails — wrong password,
    corrupted file, or tampered header/payload.
    """


class TCWVersionError(TCWError):
    """Raised when the file version is not supported."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_wallet(filepath: str, payload: Dict[str, Any], password: str) -> None:
    """
    Encrypt *payload* with *password* and write a TCW v1 file to *filepath*.

    Args:
        filepath:   Destination path (e.g. "wallet.tcw").
        payload:    Dict with all wallet secrets.  Will be JSON-encoded
                    then encrypted.  Never written to disk in plaintext.
        password:   User passphrase.  Not stored anywhere.

    Raises:
        TCWError: On any serialisation or I/O problem.
    """
    # 1. Serialise payload → UTF-8 bytes
    plaintext: bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # 2. Generate fresh salt, nonce, and KDF params
    salt        = generate_salt()
    nonce       = generate_nonce()
    kdf_params  = KDFParams.default()

    # 3. Derive AES-256 key from password
    key = derive_key(password, salt, kdf_params)

    # 4. Build fixed header (needed for AAD before we know payload_len)
    #    We will patch payload_len after encryption.
    kdf_params_bytes  = kdf_params.to_bytes()

    # Placeholder header to compute AAD; payload_len will be updated below.
    # We encrypt first, then fix the length in the final header.
    #
    # Note: AAD must match exactly what is written; so we build the
    # definitive header after encryption when we know the exact length.
    #
    # To avoid a chicken-and-egg situation, we compute AAD twice:
    # once with payload_len=0 for building, and re-derive with the real
    # length for the actual encrypt call.  The definitive AAD is the
    # header that is physically written to the file.

    def _make_header(payload_len: int) -> TCWHeader:
        return TCWHeader(
            version=FORMAT_VERSION,
            kdf_id=KDF_ID_ARGON2ID,
            cipher_id=CIPHER_ID_AES256_GCM,
            flags=0x00,
            salt_len=SALT_LEN,
            nonce_len=NONCE_LEN,
            kdf_params_len=KDF_PARAMS_LEN,
            payload_len=payload_len,
        )

    # First pass: encrypt with payload_len=0 in AAD — this is intentional.
    # The real payload_len is only known after encryption (ciphertext length
    # = plaintext length + 16-byte GCM tag).  We set payload_len in the AAD
    # to the *ciphertext* length so decryption can validate it.
    ciphertext_len_estimate = len(plaintext) + 16  # tag is always 16 bytes

    header      = _make_header(ciphertext_len_estimate)
    aad         = header.to_bytes()
    ciphertext  = encrypt(key, nonce, plaintext, aad)

    # Sanity-check our estimate was exact.
    assert len(ciphertext) == ciphertext_len_estimate, (
        f"Ciphertext length mismatch: expected {ciphertext_len_estimate}, "
        f"got {len(ciphertext)}"
    )

    # 5. Write the file atomically (write to tmp, then rename)
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "wb") as fh:
            fh.write(aad)             # 20-byte fixed header (= AAD)
            fh.write(salt)            # 32 bytes
            fh.write(kdf_params_bytes)# 4 bytes
            fh.write(nonce)           # 12 bytes
            fh.write(ciphertext)      # plaintext + 16-byte GCM tag
        Path(tmp_path).replace(filepath)
    except Exception:
        # Clean up temp file on error
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise

    # 6. Zeroize the key in memory (best-effort in Python)
    _zeroize(key)


def load_wallet(filepath: str, password: str) -> Dict[str, Any]:
    """
    Read and decrypt a TCW v1 file, returning the wallet payload dict.

    Args:
        filepath:  Path to the .tcw file.
        password:  User passphrase.

    Returns:
        Dict with decrypted wallet secrets.

    Raises:
        TCWFormatError:  File is not a valid TCW container.
        TCWVersionError: File version is not supported.
        TCWAuthError:    Wrong password or file is corrupted/tampered.
        FileNotFoundError: File does not exist.
    """
    with open(filepath, "rb") as fh:
        raw = fh.read()

    # 1. Parse fixed header
    header = TCWHeader.from_bytes(raw[:FIXED_HEADER_LEN])
    aad    = raw[:FIXED_HEADER_LEN]   # AAD = the exact bytes written

    _validate_header(header)

    # 2. Parse variable sections
    offset = FIXED_HEADER_LEN
    salt           = _read_exact(raw, offset, header.salt_len,       "salt");        offset += header.salt_len
    kdf_params_raw = _read_exact(raw, offset, header.kdf_params_len, "kdf_params");  offset += header.kdf_params_len
    nonce          = _read_exact(raw, offset, header.nonce_len,       "nonce");       offset += header.nonce_len
    ciphertext     = _read_exact(raw, offset, header.payload_len,     "payload");     offset += header.payload_len

    if offset != len(raw):
        raise TCWFormatError(
            f"Unexpected trailing bytes: file is {len(raw)} bytes, "
            f"expected {offset}"
        )

    # 3. Parse KDF parameters
    kdf_params = KDFParams.from_bytes(kdf_params_raw)

    # 4. Derive AES key
    key = derive_key(password, salt, kdf_params)

    # 5. Decrypt + authenticate
    try:
        plaintext = decrypt(key, nonce, ciphertext, aad)
    except InvalidTag:
        raise TCWAuthError(
            "Wallet authentication failed: wrong password or corrupted file."
        )
    finally:
        _zeroize(key)

    # 6. Deserialise JSON payload
    try:
        payload = json.loads(plaintext.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TCWFormatError(f"Payload is not valid JSON: {exc}") from exc

    return payload


def read_header(filepath: str) -> TCWHeader:
    """
    Read and parse only the fixed header of a TCW file.

    Useful to determine format version and KDF parameters without
    supplying a password.

    Returns:
        TCWHeader dataclass.

    Raises:
        TCWFormatError: If the file is not a valid TCW container.
    """
    with open(filepath, "rb") as fh:
        raw = fh.read(FIXED_HEADER_LEN)
    return TCWHeader.from_bytes(raw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_header(header: TCWHeader) -> None:
    if header.version != FORMAT_VERSION:
        raise TCWVersionError(
            f"Unsupported TCW version: {header.version} "
            f"(only version {FORMAT_VERSION} is supported)"
        )
    if header.kdf_id != KDF_ID_ARGON2ID:
        raise TCWFormatError(f"Unknown KDF ID: {header.kdf_id:#04x}")
    if header.cipher_id != CIPHER_ID_AES256_GCM:
        raise TCWFormatError(f"Unknown cipher ID: {header.cipher_id:#04x}")
    if header.flags != 0x00:
        raise TCWFormatError(f"Unknown flags: {header.flags:#04x}")
    if header.salt_len != SALT_LEN:
        raise TCWFormatError(f"Unexpected salt length: {header.salt_len}")
    if header.nonce_len != NONCE_LEN:
        raise TCWFormatError(f"Unexpected nonce length: {header.nonce_len}")
    if header.kdf_params_len != KDF_PARAMS_LEN:
        raise TCWFormatError(f"Unexpected KDF params length: {header.kdf_params_len}")
    if header.payload_len == 0:
        raise TCWFormatError("Payload length is zero")


def _read_exact(data: bytes, offset: int, length: int, name: str) -> bytes:
    end = offset + length
    if end > len(data):
        raise TCWFormatError(
            f"File truncated while reading '{name}': "
            f"need {length} bytes at offset {offset}, file is {len(data)} bytes"
        )
    return data[offset:end]


def _zeroize(key: bytes) -> None:
    """
    Best-effort zeroization of a key in CPython.

    Python bytes are immutable and GC-managed, so we cannot guarantee
    that all copies in memory are erased.  This attempts to zeroize the
    underlying buffer of a bytearray if the key happens to be one;
    for plain bytes, deletion is the best we can do.

    Callers should not rely on this for hard security guarantees on
    untrusted machines; it is a defence-in-depth measure only.
    """
    if isinstance(key, bytearray):
        for i in range(len(key)):
            key[i] = 0
    del key