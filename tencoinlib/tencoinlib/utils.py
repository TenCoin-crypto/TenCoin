"""
Utility functions: hashing, encoding, varint, bech32, base58
"""
import hashlib
import hmac
import struct
from typing import List, Optional, Tuple, Union

# --- Hashing ---
def sha256(data: bytes) -> bytes:
    """SHA256"""
    return hashlib.sha256(data).digest()

def sha256d(data: bytes) -> bytes:
    """Double SHA256"""
    return sha256(sha256(data))

def ripemd160(data: bytes) -> bytes:
    """RIPEMD-160"""
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()

def hash160(data: bytes) -> bytes:
    """SHA256 followed by RIPEMD-160"""
    return ripemd160(sha256(data))

def hmac_sha512(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA512"""
    return hmac.new(key, data, hashlib.sha512).digest()

# --- Varint ---
def encode_varint(i: int) -> bytes:
    """Encode integer as variable-length integer"""
    if i < 0xfd:
        return struct.pack("<B", i)
    elif i <= 0xffff:
        return b'\xfd' + struct.pack("<H", i)
    elif i <= 0xffffffff:
        return b'\xfe' + struct.pack("<I", i)
    else:
        return b'\xff' + struct.pack("<Q", i)

def decode_varint(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """Decode variable-length integer from bytes"""
    if offset >= len(data):
        raise ValueError("varint offset out of range")
    
    fb = data[offset]
    if fb < 0xfd:
        return fb, offset + 1
    elif fb == 0xfd:
        if offset + 3 > len(data):
            raise ValueError("varint truncated")
        v = struct.unpack_from("<H", data, offset + 1)[0]
        return v, offset + 3
    elif fb == 0xfe:
        if offset + 5 > len(data):
            raise ValueError("varint truncated")
        v = struct.unpack_from("<I", data, offset + 1)[0]
        return v, offset + 5
    else:
        if offset + 9 > len(data):
            raise ValueError("varint truncated")
        v = struct.unpack_from("<Q", data, offset + 1)[0]
        return v, offset + 9

# --- Serialization ---
def ser_32(i: int) -> bytes:
    """Serialize 32-bit integer"""
    return struct.pack(">I", i)

def ser_256(v: Union[int, bytes]) -> bytes:
    """Serialize 256-bit integer (32 bytes)"""
    if isinstance(v, int):
        return v.to_bytes(32, 'big')
    elif isinstance(v, bytes):
        if len(v) != 32:
            raise ValueError("Input must be 32 bytes")
        return v
    else:
        raise ValueError(f"Invalid input type: {type(v)}")

def parse_256(v: bytes) -> int:
    """Parse 256-bit integer"""
    if len(v) != 32:
        raise ValueError("Input must be 32 bytes")
    return int.from_bytes(v, 'big')

# --- Bech32 ---
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def bech32_polymod(values: List[int]) -> int:
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= GEN[i]
    return chk

def bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_verify_checksum(hrp: str, data: List[int]) -> bool:
    """Verify Bech32 checksum"""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1

def bech32_create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def bech32_encode(hrp: str, data: List[int]) -> str:
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([BECH32_CHARSET[d] for d in combined])

def bech32_decode(bech: str) -> Tuple[Optional[str], Optional[List[int]]]:
    """
    Decode a Bech32 string and return HRP and data.
    Returns (None, None) on failure.
    """
    # Validate length
    if len(bech) < 8 or len(bech) > 90:
        return None, None
    
    # Check for separator '1'
    sep_pos = bech.rfind('1')
    if sep_pos < 1 or sep_pos + 7 > len(bech):
        return None, None
    
    # Extract HRP and data part
    hrp = bech[:sep_pos].lower()
    data_part = bech[sep_pos + 1:]
    
    # Validate characters
    if not all(c in BECH32_CHARSET for c in data_part):
        return None, None
    
    # Convert chars to values
    data = [BECH32_CHARSET.find(c) for c in data_part]
    
    # Verify checksum
    if not bech32_verify_checksum(hrp, data):
        return None, None
    
    # Strip checksum (last 6 chars)
    return hrp, data[:-6]

def convert_bits(data: List[int], frombits: int, tobits: int, pad: bool = True) -> List[int]:
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError("Invalid value")
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("Invalid padding")
    return ret

# --- Base58 ---
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(data: bytes) -> str:
    """Encode bytes to Base58 string"""
    # Count leading zeros
    leading_zeros = 0
    for b in data:
        if b == 0:
            leading_zeros += 1
        else:
            break
    
    # Convert bytes to integer
    num = int.from_bytes(data, 'big')
    
    # Encode to base58
    result = ''
    while num > 0:
        num, rem = divmod(num, 58)
        result = BASE58_ALPHABET[rem] + result
    
    # Add leading zeros
    return '1' * leading_zeros + result

def base58_decode(s: str) -> bytes:
    """Decode Base58 string to bytes"""
    # Count leading ones
    leading_ones = 0
    for c in s:
        if c == '1':
            leading_ones += 1
        else:
            break
    
    # Convert string to integer
    num = 0
    for c in s:
        num = num * 58 + BASE58_ALPHABET.index(c)
    
    # Convert integer to bytes
    result = num.to_bytes((num.bit_length() + 7) // 8, 'big')
    
    # Add leading zeros
    return b'\x00' * leading_ones + result

def base58check_encode(version: int, payload: bytes) -> str:
    """Base58Check encode with version byte"""
    data = bytes([version]) + payload
    checksum = sha256d(data)[:4]
    return base58_encode(data + checksum)

def base58check_decode(s: str) -> Tuple[int, bytes]:
    """Base58Check decode, return (version, payload)"""
    data = base58_decode(s)
    if len(data) < 5:
        raise ValueError("Invalid Base58Check: too short")
    
    payload = data[:-4]
    checksum = data[-4:]
    if sha256d(payload)[:4] != checksum:
        raise ValueError("Invalid Base58Check: checksum mismatch")
    
    return payload[0], payload[1:]

# --- Address helpers ---
def is_valid_address(address: str) -> bool:
    """
    Check if address is valid (Bech32 or Base58)
    """
    # Check Bech32 (SegWit)
    if address.startswith('tc1q'):
        hrp, data = bech32_decode(address)
        return hrp is not None and data is not None
    
    # Check Base58 (Legacy)
    try:
        version, payload = base58check_decode(address)
        return version in [0x41, 0x32]  # Mainnet P2PKH or P2SH
    except:
        return False

def hash_to_address(hash_bytes: bytes, bech32_hrp: str = "tc") -> str:
    """
    Convert hash to address
    """
    # For SegWit (P2WPKH)
    if len(hash_bytes) == 20:
        return bech32_encode(bech32_hrp, convert_bits(list(hash_bytes), 8, 5))
    
    # For P2PKH
    elif len(hash_bytes) == 20:
        return base58check_encode(0x41, hash_bytes)  # P2PKH
    
    # For P2SH
    elif len(hash_bytes) == 20:
        return base58check_encode(0x32, hash_bytes)  # P2SH
    
    else:
        raise ValueError(f"Invalid hash length: {len(hash_bytes)}")

# --- Compatibility aliases ---
def b58decode(s: str) -> bytes:
    """Alias for base58_decode for compatibility with existing code"""
    return base58_decode(s)

def b58encode(data: bytes) -> str:
    """Alias for base58_encode for compatibility with existing code"""
    return base58_encode(data)