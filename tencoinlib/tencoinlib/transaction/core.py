import struct
from typing import List, Optional, Tuple
from ..utils import encode_varint, decode_varint, sha256d

class TxIn:
    """Transaction input"""
    
    def __init__(
        self, 
        prev_txid: str, 
        vout: int, 
        script_sig: bytes = b"", 
        sequence: int = 0xffffffff,
        witness: Optional[List[bytes]] = None
    ):
        """
        Args:
            prev_txid: Previous transaction ID (hex, big-endian)
            vout: Output index
            script_sig: Script signature
            sequence: Sequence number
            witness: Witness data for SegWit
        """
        self.prev_txid = prev_txid  # hex string, big-endian
        self.vout = vout
        self.script_sig = script_sig
        self.sequence = sequence
        self.witness = witness or []
    
    def serialize(self, for_witness: bool = False) -> bytes:
        """
        Serialize transaction input.
        
        Args:
            for_witness: If True, don't include witness data
            
        Returns:
            Serialized bytes
        """
        # Reverse txid for serialization (little-endian)
        prev_txid_bytes = bytes.fromhex(self.prev_txid)[::-1]
        
        data = prev_txid_bytes
        data += struct.pack("<I", self.vout)
        data += encode_varint(len(self.script_sig))
        data += self.script_sig
        data += struct.pack("<I", self.sequence)
        
        return data
    
    def __repr__(self) -> str:
        return f"TxIn({self.prev_txid[:16]}..., vout={self.vout})"

class TxOut:
    """Transaction output"""
    
    def __init__(self, value: int, script_pubkey: bytes):
        """
        Args:
            value: Amount in Tenos
            script_pubkey: Script public key
        """
        self.value = value
        self.script_pubkey = script_pubkey
    
    def serialize(self) -> bytes:
        """Serialize transaction output"""
        data = struct.pack("<Q", self.value)
        data += encode_varint(len(self.script_pubkey))
        data += self.script_pubkey
        return data
    
    def __repr__(self) -> str:
        return f"TxOut({self.value} Tenos, script={self.script_pubkey[:20].hex()}...)"

class Transaction:
    """Tencoin transaction"""
    
    def __init__(
        self, 
        version: int = 1,
        vin: Optional[List[TxIn]] = None,
        vout: Optional[List[TxOut]] = None,
        locktime: int = 0
    ):
        """
        Args:
            version: Transaction version
            vin: Inputs
            vout: Outputs
            locktime: Lock time
        """
        self.version = version
        self.vin = vin or []
        self.vout = vout or []
        self.locktime = locktime
        
        # Check if any input has witness data
        self.has_witness = any(len(txin.witness) > 0 for txin in self.vin)
    
    def serialize(self, include_witness: bool = True) -> bytes:
        """
        Serialize transaction.
        
        Args:
            include_witness: Include witness data if available
            
        Returns:
            Serialized transaction
        """
        data = struct.pack("<I", self.version)
        
        # SegWit marker and flag
        if self.has_witness and include_witness:
            data += b'\x00\x01'  # Marker and flag
        
        # Inputs
        data += encode_varint(len(self.vin))
        for txin in self.vin:
            data += txin.serialize()
        
        # Outputs
        data += encode_varint(len(self.vout))
        for txout in self.vout:
            data += txout.serialize()
        
        # Witness data
        if self.has_witness and include_witness:
            for txin in self.vin:
                data += encode_varint(len(txin.witness))
                for item in txin.witness:
                    data += encode_varint(len(item))
                    data += item
        
        # Locktime
        data += struct.pack("<I", self.locktime)
        
        return data
    
    def txid(self) -> str:
        """
        Calculate transaction ID (double SHA256 of serialized transaction without witness).
        
        Returns:
            Transaction ID as hex string
        """
        # For txid, exclude witness data
        serialized = self.serialize(include_witness=False)
        txid_bytes = sha256d(serialized)[::-1]  # Reverse for little-endian
        return txid_bytes.hex()
    
    def wtxid(self) -> str:
        """
        Calculate witness transaction ID (includes witness data).
        
        Returns:
            Witness TXID as hex string
        """
        serialized = self.serialize(include_witness=True)
        wtxid_bytes = sha256d(serialized)[::-1]
        return wtxid_bytes.hex()
    
    def is_coinbase(self) -> bool:
        """Check if transaction is coinbase"""
        return len(self.vin) == 1 and self.vin[0].prev_txid == "0" * 64
    
    def calculate_size(self) -> int:
        """Calculate transaction size in bytes"""
        return len(self.serialize(include_witness=True))
    
    def calculate_vsize(self) -> int:
        """
        Calculate virtual size (weight/4).
        SegWit transactions have lower virtual size.
        """
        if not self.has_witness:
            return self.calculate_size()
        
        # Calculate weight
        base_size = len(self.serialize(include_witness=False))
        total_size = len(self.serialize(include_witness=True))
        witness_size = total_size - base_size
        
        # Weight = base * 3 + total
        weight = base_size * 3 + total_size
        
        # Virtual size = weight / 4 (rounded up)
        vsize = (weight + 3) // 4
        
        return vsize
    
    def __repr__(self) -> str:
        txid = self.txid()
        return f"Transaction({txid[:16]}..., {len(self.vin)} in, {len(self.vout)} out)"

def parse_transaction(raw_hex: str) -> Transaction:
    """
    Parse raw transaction hex.
    
    Args:
        raw_hex: Raw transaction in hex
        
    Returns:
        Transaction object
    """
    data = bytes.fromhex(raw_hex)
    offset = 0
    
    # Version
    version = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    
    # Check for SegWit marker
    has_witness = False
    if offset + 2 <= len(data) and data[offset:offset+2] == b'\x00\x01':
        has_witness = True
        offset += 2
    
    # Inputs
    vin_count, offset = decode_varint(data, offset)
    vin = []
    
    for _ in range(vin_count):
        prev_txid = data[offset:offset+32][::-1].hex()
        offset += 32
        
        vout = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        
        script_len, offset = decode_varint(data, offset)
        script_sig = data[offset:offset+script_len]
        offset += script_len
        
        sequence = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        
        vin.append(TxIn(prev_txid, vout, script_sig, sequence))
    
    # Outputs
    vout_count, offset = decode_varint(data, offset)
    vout = []
    
    for _ in range(vout_count):
        value = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        
        script_len, offset = decode_varint(data, offset)
        script_pubkey = data[offset:offset+script_len]
        offset += script_len
        
        vout.append(TxOut(value, script_pubkey))
    
    # Witness data
    if has_witness:
        for txin in vin:
            witness_count, offset = decode_varint(data, offset)
            witness = []
            
            for _ in range(witness_count):
                item_len, offset = decode_varint(data, offset)
                item = data[offset:offset+item_len]
                offset += item_len
                witness.append(item)
            
            txin.witness = witness
    
    # Locktime
    locktime = struct.unpack_from("<I", data, offset)[0]
    
    return Transaction(version, vin, vout, locktime)