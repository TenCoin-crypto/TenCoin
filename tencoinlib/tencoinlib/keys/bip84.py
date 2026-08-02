from typing import Tuple
from .bip32 import derive_path_from_seed
from .ec import privkey_to_pubkey
from ..utils import hash160, bech32_encode, convert_bits
from ..constants import MAINNET_HRP, DERIVATION_PATH

class BIP84Error(Exception):
    """BIP-84 related errors"""
    pass

def derive_bip84_address_from_seed(seed: bytes, account: int = 0, 
                                   change: int = 0, index: int = 0) -> Tuple[bytes, str]:
    """
    Derive BIP-84 SegWit native address from seed.
    
    Args:
        seed: 64-byte seed
        account: Account number (default: 0)
        change: 0 for external, 1 for change
        index: Address index
        
    Returns:
        (private_key, address)
    """
    # Build derivation path: m/84'/5353'/{account}'/{change}/{index}
    path = f"m/84'/5353'/{account}'/{change}/{index}"
    
    # Derive private key
    private_key, _ = derive_path_from_seed(seed, path)
    
    # Get compressed public key
    public_key = privkey_to_pubkey(private_key, compressed=True)
    
    # Create SegWit v0 address
    address = public_key_to_segwit_v0(public_key)
    
    return private_key, address

def public_key_to_segwit_v0(public_key: bytes) -> str:
    """
    Convert public key to SegWit v0 (P2WPKH) address.
    
    Args:
        public_key: 33-byte compressed public key
        
    Returns:
        bech32 address (tc1q...)
    """
    if len(public_key) != 33:
        raise BIP84Error(f"Invalid public key length: {len(public_key)}")
    
    # Hash160 of public key
    pubkey_hash = hash160(public_key)
    
    # Convert to bech32
    witness_program = list(pubkey_hash)
    
    # Convert 8-bit bytes to 5-bit array
    data_5bit = convert_bits(witness_program, 8, 5, True)
    
    # Prepend witness version (0 for P2WPKH)
    data_5bit_with_version = [0] + data_5bit
    
    # Encode as bech32
    address = bech32_encode(MAINNET_HRP, data_5bit_with_version)
    
    return address

def get_default_address_from_seed(seed: bytes) -> Tuple[bytes, str, str]:
    """
    Get default BIP-84 address (m/84'/5353'/0'/0/0).
    
    Args:
        seed: 64-byte seed
        
    Returns:
        (private_key, public_key, address)
    """
    private_key, address = derive_bip84_address_from_seed(
        seed, account=0, change=0, index=0
    )
    
    public_key = privkey_to_pubkey(private_key, compressed=True)
    
    return private_key, public_key.hex(), address