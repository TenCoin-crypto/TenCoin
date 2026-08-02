import hashlib
import hmac
import secrets
from typing import List, Optional
from .wordlist import BIP39_ENGLISH_WORDS
from ..utils import sha256

class BIP39Error(Exception):
    """BIP-39 related errors"""
    pass

def generate_entropy(bits: int = 128) -> bytes:
    """
    Generate cryptographically secure entropy.
    
    Args:
        bits: 128, 160, 192, 224, or 256
        
    Returns:
        Entropy bytes
    """
    if bits not in [128, 160, 192, 224, 256]:
        raise BIP39Error(f"Invalid entropy size: {bits}")
    
    # 1 byte = 8 bits
    byte_count = bits // 8
    return secrets.token_bytes(byte_count)

def entropy_to_mnemonic(entropy: bytes) -> str:
    """
    Convert entropy to mnemonic words.
    
    Args:
        entropy: 16-32 bytes
        
    Returns:
        Space-separated mnemonic words
    """
    if len(entropy) not in [16, 20, 24, 28, 32]:
        raise BIP39Error(f"Invalid entropy length: {len(entropy)}")
    
    # Calculate checksum
    checksum_length_bits = len(entropy) // 4  # bits
    hash_bytes = sha256(entropy)
    
    # Get first byte of hash and shift to get checksum bits
    hash_bits = int.from_bytes(hash_bytes, 'big')
    checksum = (hash_bits >> (256 - checksum_length_bits)) & ((1 << checksum_length_bits) - 1)
    
    # Combine entropy and checksum
    entropy_bits = int.from_bytes(entropy, 'big')
    combined_bits = (entropy_bits << checksum_length_bits) | checksum
    
    # Convert to words
    word_count = (len(entropy) * 8 + checksum_length_bits) // 11
    words = []
    
    for i in range(word_count):
        # Get 11 bits
        index = (combined_bits >> ((word_count - i - 1) * 11)) & 0x7FF
        words.append(BIP39_ENGLISH_WORDS[index])
    
    return " ".join(words)

def mnemonic_to_entropy(mnemonic: str) -> bytes:
    """
    Convert mnemonic words back to entropy.
    
    Args:
        mnemonic: Space-separated words
        
    Returns:
        Entropy bytes
    """
    words = mnemonic.strip().split()
    
    # Validate word count
    if len(words) not in [12, 15, 18, 21, 24]:
        raise BIP39Error(f"Invalid word count: {len(words)}")
    
    # Convert words to indices
    indices = []
    for word in words:
        try:
            index = BIP39_ENGLISH_WORDS.index(word)
            indices.append(index)
        except ValueError:
            raise BIP39Error(f"Invalid word: {word}")
    
    # Calculate combined integer
    combined_bits = 0
    for index in indices:
        combined_bits = (combined_bits << 11) | index
    
    # Extract entropy and checksum
    checksum_length_bits = len(words) // 3  # bits
    entropy_length_bits = len(words) * 11 - checksum_length_bits
    entropy_bits = combined_bits >> checksum_length_bits
    
    # Convert back to bytes
    entropy_bytes = entropy_bits.to_bytes(entropy_length_bits // 8, 'big')
    
    # Verify checksum
    hash_bytes = sha256(entropy_bytes)
    hash_bits = int.from_bytes(hash_bytes, 'big')
    calculated_checksum = (hash_bits >> (256 - checksum_length_bits)) & ((1 << checksum_length_bits) - 1)
    extracted_checksum = combined_bits & ((1 << checksum_length_bits) - 1)
    
    if calculated_checksum != extracted_checksum:
        raise BIP39Error("Invalid checksum")
    
    return entropy_bytes

def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """
    Convert mnemonic to seed using PBKDF2.
    
    Args:
        mnemonic: Space-separated words
        passphrase: Optional passphrase
        
    Returns:
        64-byte seed
    """
    # BIP-39 specification: "mnemonic" + passphrase
    salt = f"mnemonic{passphrase}".encode('utf-8')
    
    # PBKDF2 with HMAC-SHA512, 2048 iterations
    seed = hashlib.pbkdf2_hmac(
        'sha512',
        mnemonic.encode('utf-8'),
        salt,
        iterations=2048,
        dklen=64
    )
    
    return seed

def validate_mnemonic(mnemonic: str) -> bool:
    """
    Validate mnemonic words and checksum.
    
    Args:
        mnemonic: Space-separated words
        
    Returns:
        True if valid
    """
    try:
        mnemonic_to_entropy(mnemonic)
        return True
    except BIP39Error:
        return False

def generate_mnemonic(strength: int = 128) -> str:
    """
    Generate a new mnemonic phrase.
    
    Args:
        strength: 128, 160, 192, 224, or 256 bits
        
    Returns:
        Mnemonic phrase
    """
    entropy = generate_entropy(strength)
    return entropy_to_mnemonic(entropy)