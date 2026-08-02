from typing import Optional, Tuple
from ..utils import (
    bech32_decode, convert_bits, 
    b58decode, sha256d, hash160
)
from ..constants import MAINNET_HRP, P2PKH_VERSION, P2SH_VERSION

class AddressError(Exception):
    """Address related errors"""
    pass

def decode_address(address: str) -> Tuple[str, bytes]:
    """
    Decode address and return (type, hash).
    
    Args:
        address: Tencoin address
        
    Returns:
        (type, hash) where type is "p2wpkh", "p2wsh", "p2pkh", "p2sh"
    
    Raises:
        AddressError: If address is invalid
    """
    # 1. Check for Bech32 (SegWit) - tc1q...
    if address.startswith(MAINNET_HRP + "1"):
        hrp, data_5bit = bech32_decode(address)
        if hrp != MAINNET_HRP or not data_5bit:
            raise AddressError(f"Invalid bech32 address: {address}")
        
        # Convert from 5-bit to 8-bit bytes
        # First byte is witness version (should be 0)
        if not data_5bit:
            raise AddressError(f"Invalid bech32 address: {address}")
        
        witness_version = data_5bit[0]
        if witness_version != 0:
            raise AddressError(f"Unsupported witness version: {witness_version}")
        
        # Convert remaining 5-bit data to bytes
        data_8bit = convert_bits(data_5bit[1:], 5, 8, False)
        data_bytes = bytes(data_8bit)
        
        # Check witness program length
        if len(data_bytes) == 20:  # 20 bytes = P2WPKH
            return "p2wpkh", data_bytes
        elif len(data_bytes) == 32:  # 32 bytes = P2WSH
            return "p2wsh", data_bytes
        else:
            raise AddressError(f"Unsupported witness program length: {len(data_bytes)}")
    
    # 2. Check for Base58 (P2PKH or P2SH)
    try:
        decoded = b58decode(address)
        
        if len(decoded) != 25:
            raise AddressError(f"Invalid Base58 address length: {len(decoded)}")
        
        version_byte = decoded[0:1]
        version = decoded[0]
        payload = decoded[1:21]
        checksum = decoded[21:25]
        
        # Verify checksum
        expected_checksum = sha256d(version_byte + payload)[:4]
        if checksum != expected_checksum:
            raise AddressError("Invalid Base58 checksum")
        
        # Check version
        if version == P2PKH_VERSION:  # 0x41
            return "p2pkh", payload
        elif version == P2SH_VERSION:  # 0x32
            return "p2sh", payload
        else:
            raise AddressError(f"Unknown address version: {version:02x}")
    
    except AddressError:
        raise
    except Exception as e:
        raise AddressError(f"Invalid Base58 address: {e}")

def address_to_script(address: str) -> bytes:
    """
    Convert address to scriptPubKey.
    
    Args:
        address: Tencoin address
        
    Returns:
        scriptPubKey bytes
    
    Raises:
        AddressError: If address is invalid
    """
    addr_type, data = decode_address(address)
    
    if addr_type == "p2wpkh":
        # P2WPKH: OP_0 <20-byte-pubkey-hash>
        return bytes([0x00, 0x14]) + data
    
    elif addr_type == "p2pkh":
        # P2PKH: OP_DUP OP_HASH160 <20-byte-pubkey-hash> OP_EQUALVERIFY OP_CHECKSIG
        return bytes([0x76, 0xa9, 0x14]) + data + bytes([0x88, 0xac])
    
    elif addr_type == "p2sh":
        # P2SH: OP_HASH160 <20-byte-script-hash> OP_EQUAL
        return bytes([0xa9, 0x14]) + data + bytes([0x87])
    
    elif addr_type == "p2wsh":
        # P2WSH: OP_0 <32-byte-script-hash>
        return bytes([0x00, 0x20]) + data
    
    else:
        raise AddressError(f"Unsupported address type: {addr_type}")

def is_valid_address(address: str) -> bool:
    """
    Check if address is valid.
    
    Args:
        address: Tencoin address
        
    Returns:
        True if valid
    """
    try:
        decode_address(address)
        return True
    except AddressError:
        return False

def get_address_type(address: str) -> Optional[str]:
    """
    Get address type.
    
    Args:
        address: Tencoin address
        
    Returns:
        Address type or None if invalid
    """
    try:
        addr_type, _ = decode_address(address)
        return addr_type
    except AddressError:
        return None