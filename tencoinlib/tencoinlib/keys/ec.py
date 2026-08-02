import hashlib
from typing import Optional, Tuple

# Try to import ecdsa library
try:
    from ecdsa import SigningKey, VerifyingKey, SECP256k1
    from ecdsa.util import sigencode_der, sigdecode_der
    ECDSA_AVAILABLE = True
except ImportError:
    ECDSA_AVAILABLE = False
    SECP256k1 = None

# Secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def bytes_to_int(b: bytes) -> int:
    """Convert bytes to integer (big-endian)"""
    return int.from_bytes(b, "big")


def int_to_bytes(i: int, length: int = 32) -> bytes:
    """Convert integer to bytes (big-endian)"""
    return i.to_bytes(length, "big")


def _modinv(a: int, n: int = P) -> int:
    """Modular inverse using Fermat's little theorem (since P is prime)."""
    return pow(a, n - 2, n)


def point_to_pubkey(x: int, y: int, compressed: bool = True) -> bytes:
    """Convert (x, y) point to public key bytes."""
    if compressed:
        prefix = b"\x02" if y % 2 == 0 else b"\x03"
        return prefix + int_to_bytes(x, 32)
    else:
        return b"\x04" + int_to_bytes(x, 32) + int_to_bytes(y, 32)


def pubkey_to_point(pubkey: bytes) -> Tuple[int, int]:
    """
    Convert a compressed or uncompressed public key to (x, y) point.

    Only compressed (33-byte, 0x02/0x03) and uncompressed (65-byte, 0x04) keys
    are supported.
    """
    if len(pubkey) == 33 and pubkey[0] in (2, 3):
        prefix = pubkey[0]
        x = bytes_to_int(pubkey[1:33])
        # y^2 = x^3 + 7 mod P
        y_sq = (pow(x, 3, P) + 7) % P
        # Since P % 4 == 3, sqrt is y = y_sq^((P+1)//4) mod P
        y = pow(y_sq, (P + 1) // 4, P)
        if (y % 2 == 0 and prefix == 3) or (y % 2 == 1 and prefix == 2):
            y = P - y
        return x, y
    elif len(pubkey) == 65 and pubkey[0] == 4:
        x = bytes_to_int(pubkey[1:33])
        y = bytes_to_int(pubkey[33:65])
        return x, y
    else:
        raise ValueError("Invalid public key format")


def point_add(p1: Optional[Tuple[int, int]], p2: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """Elliptic curve point addition on secp256k1."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 != y2:
        return None

    if x1 == x2 and y1 == y2:
        # Point doubling
        s = (3 * x1 * x1) * _modinv(2 * y1 % P, P) % P
    else:
        # General addition
        s = (y2 - y1) * _modinv((x2 - x1) % P, P) % P

    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return x3, y3


def scalar_mult(k: int, point: Tuple[int, int]) -> Optional[Tuple[int, int]]:
    """Scalar multiplication k * point using double-and-add."""
    if k % N == 0 or point is None:
        return None

    k = k % N
    result: Optional[Tuple[int, int]] = None
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


def privkey_to_pubkey(privkey: bytes, compressed: bool = True) -> bytes:
    """Convert private key to public key using ecdsa if available."""
    if not ECDSA_AVAILABLE:
        raise ImportError("ecdsa library is required. Install with: pip install ecdsa")

    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    vk = sk.get_verifying_key()

    if compressed:
        # Get compressed format
        point = vk.pubkey.point
        prefix = b"\x02" if point.y() % 2 == 0 else b"\x03"
        return prefix + int_to_bytes(point.x())
    else:
        return b"\x04" + vk.to_string()


def sign(privkey: bytes, msg_hash: bytes) -> bytes:
    """Sign message hash with private key."""
    if not ECDSA_AVAILABLE:
        raise ImportError("ecdsa library is required. Install with: pip install ecdsa")

    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    sig = sk.sign_digest(msg_hash, sigencode=sigencode_der)
    return sig


def verify(pubkey: bytes, msg_hash: bytes, sig: bytes) -> bool:
    """Verify signature."""
    if not ECDSA_AVAILABLE:
        raise ImportError("ecdsa library is required. Install with: pip install ecdsa")

    try:
        vk = VerifyingKey.from_string(pubkey, curve=SECP256k1)
        return vk.verify_digest(sig, msg_hash, sigdecode=sigdecode_der)
    except Exception:
        return False