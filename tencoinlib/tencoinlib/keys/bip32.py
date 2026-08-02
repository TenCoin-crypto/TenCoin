import struct
from dataclasses import dataclass
from typing import List, Tuple

from .ec import (
    Gx,
    Gy,
    N,
    point_add,
    point_to_pubkey,
    privkey_to_pubkey,
    pubkey_to_point,
    scalar_mult,
)
from ..utils import (
    base58_decode,
    base58_encode,
    hash160,
    hmac_sha512,
    parse_256,
    ser_32,
    ser_256,
    sha256d,
)


class BIP32Error(Exception):
    """BIP-32 related errors"""

    pass


# BIP-32 constants
HARDENED_OFFSET = 0x80000000
MAINNET_VERSION = 0x0488B21E  # xpub
MAINNET_PRIVATE_VERSION = 0x0488ADE4  # xprv


def _b58check_encode(payload: bytes) -> str:
    """Encode data with Base58Check (checksum over full payload)."""
    checksum = sha256d(payload)[:4]
    return base58_encode(payload + checksum)


def _b58check_decode(s: str) -> bytes:
    """Decode Base58Check string and return raw payload (without checksum)."""
    data = base58_decode(s)
    if len(data) < 4:
        raise BIP32Error("Invalid extended key: too short")
    payload, checksum = data[:-4], data[-4:]
    if sha256d(payload)[:4] != checksum:
        raise BIP32Error("Invalid extended key checksum")
    return payload


def derive_child_key(
    parent_key: bytes, parent_chain_code: bytes, index: int, is_private: bool = True
) -> Tuple[bytes, bytes]:
    """
    Derive child key from parent key (CKDpriv / CKDpub).

    Args:
        parent_key: 33-byte public key or 32-byte private key
        parent_chain_code: 32-byte chain code
        index: Child index
        is_private: Whether parent_key is private

    Returns:
        (child_key, child_chain_code)
    """
    if is_private:
        if len(parent_key) != 32:
            raise BIP32Error(f"Invalid private key length: {len(parent_key)}")

        if index >= HARDENED_OFFSET:
            # Hardened derivation
            data = b"\x00" + parent_key + struct.pack(">I", index)
        else:
            # Normal derivation
            parent_pubkey = privkey_to_pubkey(parent_key, compressed=True)
            data = parent_pubkey + struct.pack(">I", index)
    else:
        if len(parent_key) != 33:
            raise BIP32Error(f"Invalid public key length: {len(parent_key)}")

        if index >= HARDENED_OFFSET:
            raise BIP32Error("Cannot derive hardened child from public key")

        data = parent_key + struct.pack(">I", index)

    # HMAC-SHA512
    hmac_result = hmac_sha512(parent_chain_code, data)
    left = hmac_result[:32]
    right = hmac_result[32:]

    il_int = parse_256(left)
    if il_int >= N or il_int == 0:
        raise BIP32Error("Invalid derived key (IL out of range)")

    if is_private:
        # Private key derivation (CKDpriv)
        parent_key_int = parse_256(parent_key)
        child_key_int = (il_int + parent_key_int) % N
        if child_key_int == 0:
            raise BIP32Error("Derived invalid private key")

        child_key = ser_256(child_key_int)
    else:
        # Public key derivation (CKDpub)
        gx, gy = Gx, Gy
        generator_point = (gx, gy)
        parent_point = pubkey_to_point(parent_key)
        derived_point = scalar_mult(il_int, generator_point)
        if derived_point is None:
            raise BIP32Error("Derived invalid public key (IL * G is infinity)")
        child_point = point_add(derived_point, parent_point)
        if child_point is None:
            raise BIP32Error("Derived invalid public key (point at infinity)")

        child_key = point_to_pubkey(child_point[0], child_point[1], compressed=True)

    return child_key, right


def create_master_key(seed: bytes) -> Tuple[bytes, bytes]:
    """
    Create master key and chain code from seed.

    Args:
        seed: 64-byte seed

    Returns:
        (master_private_key, master_chain_code)
    """
    # HMAC-SHA512 with key "Bitcoin seed"
    hmac_result = hmac_sha512(b"Bitcoin seed", seed)

    master_key = hmac_result[:32]
    master_chain_code = hmac_result[32:]

    # Validate key
    key_int = parse_256(master_key)
    if key_int == 0 or key_int >= N:
        raise BIP32Error("Invalid master key")

    return master_key, master_chain_code


def derive_path_from_seed(seed: bytes, path: str) -> Tuple[bytes, bytes]:
    """
    Derive key at specified path from seed.

    Args:
        seed: 64-byte seed
        path: Derivation path like "m/84'/5353'/0'/0/0"

    Returns:
        (private_key, chain_code)
    """
    indices = path_to_indices(path)

    # Create master key
    private_key, chain_code = create_master_key(seed)

    # Derive through each level
    for index in indices:
        private_key, chain_code = derive_child_key(
            private_key, chain_code, index, is_private=True
        )

    return private_key, chain_code


def path_to_indices(path: str) -> List[int]:
    """
    Convert absolute derivation path string to list of indices.

    Args:
        path: Like "m/84'/5353'/0'/0/0"

    Returns:
        List of indices
    """
    if not path.startswith("m/"):
        raise BIP32Error(f"Invalid path: {path}")

    parts = path[2:].split("/")
    if not parts or any(p == "" for p in parts):
        raise BIP32Error(f"Invalid path: {path}")

    indices: List[int] = []
    for part in parts:
        if part.endswith("'"):
            indices.append(int(part[:-1]) + HARDENED_OFFSET)
        else:
            indices.append(int(part))

    return indices


def relative_path_to_indices(path: str) -> List[int]:
    """
    Convert relative path string (no leading 'm/') to list of indices.

    Args:
        path: Like "0/0" or "1/5'"

    Returns:
        List of indices
    """
    path = path.strip()
    if not path:
        return []

    parts = path.split("/")
    if any(p == "" for p in parts):
        raise BIP32Error(f"Invalid relative path: {path}")

    indices: List[int] = []
    for part in parts:
        if part.endswith("'"):
            indices.append(int(part[:-1]) + HARDENED_OFFSET)
        else:
            indices.append(int(part))

    return indices


@dataclass
class ExtendedKey:
    """Base class for BIP32 extended keys (metadata only)."""

    depth: int
    parent_fingerprint: bytes
    child_number: int
    chain_code: bytes


@dataclass
class ExtendedPrivateKey(ExtendedKey):
    """BIP32 extended private key (xprv)."""

    key: bytes

    @classmethod
    def from_seed(cls, seed: bytes) -> "ExtendedPrivateKey":
        priv, chain = create_master_key(seed)
        return cls(
            depth=0,
            parent_fingerprint=b"\x00\x00\x00\x00",
            child_number=0,
            chain_code=chain,
            key=priv,
        )

    @classmethod
    def from_xprv(cls, xprv: str) -> "ExtendedPrivateKey":
        payload = _b58check_decode(xprv)
        if len(payload) != 78:
            raise BIP32Error("Invalid extended private key length")

        version = int.from_bytes(payload[0:4], "big")
        if version != MAINNET_PRIVATE_VERSION:
            raise BIP32Error("Invalid extended private key version")

        depth = payload[4]
        parent_fingerprint = payload[5:9]
        child_number = int.from_bytes(payload[9:13], "big")
        chain_code = payload[13:45]
        key_data = payload[45:78]

        if key_data[0] != 0:
            raise BIP32Error("Invalid extended private key data")

        key = key_data[1:33]
        if len(key) != 32:
            raise BIP32Error("Invalid private key length in xprv")

        return cls(
            depth=depth,
            parent_fingerprint=parent_fingerprint,
            child_number=child_number,
            chain_code=chain_code,
            key=key,
        )

    def to_xprv(self) -> str:
        if len(self.chain_code) != 32:
            raise BIP32Error("Invalid chain code length")
        if len(self.key) != 32:
            raise BIP32Error("Invalid private key length")

        version = ser_32(MAINNET_PRIVATE_VERSION)
        depth_byte = bytes([self.depth])
        child_bytes = self.child_number.to_bytes(4, "big")
        key_data = b"\x00" + self.key
        payload = (
            version
            + depth_byte
            + self.parent_fingerprint
            + child_bytes
            + self.chain_code
            + key_data
        )
        return _b58check_encode(payload)

    def to_public(self) -> "ExtendedPublicKey":
        pub = privkey_to_pubkey(self.key, compressed=True)
        return ExtendedPublicKey(
            depth=self.depth,
            parent_fingerprint=self.parent_fingerprint,
            child_number=self.child_number,
            chain_code=self.chain_code,
            key=pub,
        )

    def fingerprint(self) -> bytes:
        """Fingerprint of *this* node (first 4 bytes of HASH160(pubkey))."""
        pub = privkey_to_pubkey(self.key, compressed=True)
        return hash160(pub)[:4]

    def child(self, index: int) -> "ExtendedPrivateKey":
        child_key, child_chain = derive_child_key(
            self.key, self.chain_code, index, is_private=True
        )
        return ExtendedPrivateKey(
            depth=self.depth + 1,
            parent_fingerprint=self.fingerprint(),
            child_number=index,
            chain_code=child_chain,
            key=child_key,
        )

    def derive_path(self, path: str) -> "ExtendedPrivateKey":
        """
        Derive along an absolute ("m/...") or relative ("0/0") path.
        """
        if path.startswith("m/"):
            indices = path_to_indices(path)
        elif path == "m":
            return self
        else:
            indices = relative_path_to_indices(path)

        node: ExtendedPrivateKey = self
        for index in indices:
            node = node.child(index)
        return node


@dataclass
class ExtendedPublicKey(ExtendedKey):
    """BIP32 extended public key (xpub)."""

    key: bytes

    @classmethod
    def from_xpub(cls, xpub: str) -> "ExtendedPublicKey":
        payload = _b58check_decode(xpub)
        if len(payload) != 78:
            raise BIP32Error("Invalid extended public key length")

        version = int.from_bytes(payload[0:4], "big")
        if version != MAINNET_VERSION:
            raise BIP32Error("Invalid extended public key version")

        depth = payload[4]
        parent_fingerprint = payload[5:9]
        child_number = int.from_bytes(payload[9:13], "big")
        chain_code = payload[13:45]
        key = payload[45:78]

        if len(key) != 33:
            raise BIP32Error("Invalid public key length in xpub")

        return cls(
            depth=depth,
            parent_fingerprint=parent_fingerprint,
            child_number=child_number,
            chain_code=chain_code,
            key=key,
        )

    def to_xpub(self) -> str:
        if len(self.chain_code) != 32:
            raise BIP32Error("Invalid chain code length")
        if len(self.key) != 33:
            raise BIP32Error("Invalid public key length")

        version = ser_32(MAINNET_VERSION)
        depth_byte = bytes([self.depth])
        child_bytes = self.child_number.to_bytes(4, "big")
        payload = (
            version
            + depth_byte
            + self.parent_fingerprint
            + child_bytes
            + self.chain_code
            + self.key
        )
        return _b58check_encode(payload)

    def fingerprint(self) -> bytes:
        """Fingerprint of *this* node (first 4 bytes of HASH160(pubkey))."""
        return hash160(self.key)[:4]

    def child(self, index: int) -> "ExtendedPublicKey":
        child_key, child_chain = derive_child_key(
            self.key, self.chain_code, index, is_private=False
        )
        return ExtendedPublicKey(
            depth=self.depth + 1,
            parent_fingerprint=self.fingerprint(),
            child_number=index,
            chain_code=child_chain,
            key=child_key,
        )

    def derive_path(self, path: str) -> "ExtendedPublicKey":
        """
        Derive along a relative path ("0/0") from this xpub.
        Absolute hardened paths are not supported from public keys.
        """
        if path.startswith("m/"):
            # From a pure xpub we cannot move through hardened steps,
            # so only allow non-hardened absolute paths if they match depth.
            indices = path_to_indices(path)
        elif path == "m":
            return self
        else:
            indices = relative_path_to_indices(path)

        node: ExtendedPublicKey = self
        for index in indices:
            if index >= HARDENED_OFFSET:
                raise BIP32Error("Cannot derive hardened child from public key")
            node = node.child(index)
        return node