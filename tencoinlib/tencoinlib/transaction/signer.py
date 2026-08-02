import struct
from typing import List, Optional, Union
from ..utils import sha256d, hash160, encode_varint
from .core import Transaction, TxIn, TxOut
from .address import decode_address
from .script import build_p2pkh_script

class SigningError(Exception):
    pass

class SegWitSigner:
    
    @staticmethod
    def create_witness_signature(
        tx: Transaction,
        input_index: int,
        private_key: bytes,
        script_code: bytes,
        value: int,
        sighash_type: int = 1
    ) -> bytes:
        try:
            digest = SegWitSigner.bip143_digest(
                tx, input_index, script_code, value, sighash_type
            )
            from ..keys.ec import sign
            signature = sign(private_key, digest)
            return signature + bytes([sighash_type])
        except Exception as e:
            raise SigningError(f"Failed to create witness signature: {e}")
    
    @staticmethod
    def bip143_digest(
        tx: Transaction,
        input_index: int,
        script_code: bytes,
        value: int,
        sighash_type: int = 1
    ) -> bytes:
        prevouts = b''
        for txin in tx.vin:
            prevouts += bytes.fromhex(txin.prev_txid)[::-1] + struct.pack("<I", txin.vout)
        hashPrevouts = sha256d(prevouts)
        
        sequences = b''.join(struct.pack("<I", txin.sequence) for txin in tx.vin)
        hashSequence = sha256d(sequences)
        
        outputs = b''.join(txout.serialize() for txout in tx.vout)
        hashOutputs = sha256d(outputs)
        
        digest = struct.pack("<I", tx.version)
        digest += hashPrevouts
        digest += hashSequence
        
        txin = tx.vin[input_index]
        digest += bytes.fromhex(txin.prev_txid)[::-1]
        digest += struct.pack("<I", txin.vout)
        digest += encode_varint(len(script_code))
        digest += script_code
        digest += struct.pack("<Q", value)
        digest += struct.pack("<I", txin.sequence)
        digest += hashOutputs
        digest += struct.pack("<I", tx.locktime)
        digest += struct.pack("<I", sighash_type)
        
        return sha256d(digest)
    
    @staticmethod
    def sign_transaction(
        tx: Transaction,
        utxos: List[dict],
        private_keys: List[bytes]
    ) -> Transaction:
        if len(tx.vin) != len(utxos):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(utxos)} UTXOs provided")
        
        if len(tx.vin) != len(private_keys):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(private_keys)} private keys provided")
        
        for i, utxo in enumerate(utxos):
            addr_type, _ = decode_address(utxo["address"])
            if addr_type != "p2wpkh":
                raise SigningError(f"UTXO {i} is not P2WPKH: {utxo['address']}")
        
        signed_tx = Transaction(
            version=tx.version,
            vin=[TxIn(
                prev_txid=txin.prev_txid,
                vout=txin.vout,
                script_sig=txin.script_sig,
                sequence=txin.sequence
            ) for txin in tx.vin],
            vout=tx.vout[:],
            locktime=tx.locktime
        )
        
        signed_tx.has_witness = True
        
        for i in range(len(signed_tx.vin)):
            try:
                SegWitSigner.sign_input(
                    signed_tx, i, utxos[i], private_keys[i]
                )
            except Exception as e:
                raise SigningError(f"Failed to sign input {i}: {e}")
        
        return signed_tx
    
    @staticmethod
    def sign_input(
        tx: Transaction,
        input_index: int,
        utxo: dict,
        private_key: bytes
    ):
        from ..keys.ec import privkey_to_pubkey
        public_key = privkey_to_pubkey(private_key, compressed=True)
        
        pubkey_hash = hash160(public_key)
        script_code = bytes([0x76, 0xa9, 0x14]) + pubkey_hash + bytes([0x88, 0xac])
        
        signature = SegWitSigner.create_witness_signature(
            tx, input_index, private_key, script_code, utxo["value"]
        )
        
        tx.vin[input_index].witness = [signature, public_key]
        tx.vin[input_index].script_sig = b""
        tx.has_witness = True
    
    @staticmethod
    def verify_witness(
        tx: Transaction,
        input_index: int,
        public_key: bytes,
        script_code: bytes,
        value: int,
        witness: List[bytes]
    ) -> bool:
        if len(witness) < 2:
            return False
        
        signature = witness[0]
        witness_pubkey = witness[1]
        
        if witness_pubkey != public_key:
            return False
        
        if len(signature) < 1:
            return False
        
        sighash_type = signature[-1]
        signature_der = signature[:-1]
        
        digest = SegWitSigner.bip143_digest(
            tx, input_index, script_code, value, sighash_type
        )
        
        from ..keys.ec import verify
        return verify(public_key, digest, signature_der)


class LegacySigner:
    
    @staticmethod
    def legacy_digest(
        tx: Transaction,
        input_index: int,
        script_code: bytes,
        sighash_type: int = 1
    ) -> bytes:
        if sighash_type != 1:
            raise SigningError(f"Only SIGHASH_ALL (1) is supported, got {sighash_type}")
        
        def le32(v: int) -> bytes:
            return struct.pack("<I", v)
        
        digest = b""
        
        digest += le32(tx.version)
        digest += encode_varint(len(tx.vin))
        
        for i, txin in enumerate(tx.vin):
            prev_txid_bytes = bytes.fromhex(txin.prev_txid)[::-1]
            digest += prev_txid_bytes
            digest += le32(txin.vout)
            
            if i == input_index:
                digest += encode_varint(len(script_code))
                digest += script_code
            else:
                digest += encode_varint(0)
            
            digest += le32(txin.sequence)
        
        digest += encode_varint(len(tx.vout))
        
        for txout in tx.vout:
            digest += txout.serialize()
        
        digest += le32(tx.locktime)
        digest += le32(sighash_type)
        
        return sha256d(digest)
    
    @staticmethod
    def sign_p2pkh_input(
        tx: Transaction,
        input_index: int,
        private_key: bytes,
        script_pubkey: bytes,
        sighash_type: int = 1
    ):
        from ..keys.ec import privkey_to_pubkey
        public_key = privkey_to_pubkey(private_key, compressed=True)
        
        script_code = script_pubkey
        
        digest = LegacySigner.legacy_digest(tx, input_index, script_code, sighash_type)
        
        from ..keys.ec import sign
        signature = sign(private_key, digest)
        signature_with_sighash = signature + bytes([sighash_type])
        
        script_sig = encode_varint(len(signature_with_sighash))
        script_sig += signature_with_sighash
        script_sig += encode_varint(len(public_key))
        script_sig += public_key
        
        tx.vin[input_index].script_sig = script_sig
    
    @staticmethod
    def sign_p2sh_input(
        tx: Transaction,
        input_index: int,
        private_key: bytes,
        redeem_script: bytes,
        script_pubkey: bytes,
        sighash_type: int = 1
    ):
        from ..keys.ec import privkey_to_pubkey
        public_key = privkey_to_pubkey(private_key, compressed=True)
        
        script_code = redeem_script
        
        digest = LegacySigner.legacy_digest(tx, input_index, script_code, sighash_type)
        
        from ..keys.ec import sign
        signature = sign(private_key, digest)
        signature_with_sighash = signature + bytes([sighash_type])
        
        script_sig = encode_varint(len(signature_with_sighash))
        script_sig += signature_with_sighash
        script_sig += encode_varint(len(public_key))
        script_sig += public_key
        script_sig += encode_varint(len(redeem_script))
        script_sig += redeem_script
        
        tx.vin[input_index].script_sig = script_sig
    
    @staticmethod
    def sign_transaction(
        tx: Transaction,
        utxos: List[dict],
        private_keys: List[bytes]
    ) -> Transaction:
        if len(tx.vin) != len(utxos):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(utxos)} UTXOs provided")
        
        if len(tx.vin) != len(private_keys):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(private_keys)} private keys provided")
        
        signed_tx = Transaction(
            version=tx.version,
            vin=[TxIn(
                prev_txid=txin.prev_txid,
                vout=txin.vout,
                script_sig=txin.script_sig,
                sequence=txin.sequence
            ) for txin in tx.vin],
            vout=tx.vout[:],
            locktime=tx.locktime
        )
        
        for i in range(len(signed_tx.vin)):
            try:
                utxo = utxos[i]
                addr_type, _ = decode_address(utxo["address"])
                
                if addr_type == "p2pkh":
                    LegacySigner.sign_p2pkh_input(
                        signed_tx, i, private_keys[i], utxo["script_pubkey"]
                    )
                elif addr_type == "p2sh":
                    if "redeem_script" not in utxo:
                        from ..keys.ec import privkey_to_pubkey
                        pubkey = privkey_to_pubkey(private_keys[i], compressed=True)
                        redeem_script = build_p2pkh_script(pubkey)
                    else:
                        redeem_script = utxo["redeem_script"]
                    
                    LegacySigner.sign_p2sh_input(
                        signed_tx, i, private_keys[i], redeem_script, utxo["script_pubkey"]
                    )
                else:
                    raise SigningError(f"Unsupported address type for Legacy signing: {addr_type}")
            except Exception as e:
                raise SigningError(f"Failed to sign input {i}: {e}")
        
        return signed_tx


class TransactionSigner:
    
    @staticmethod
    def sign_transaction(
        tx: Transaction,
        utxos: List[dict],
        private_keys: List[bytes]
    ) -> Transaction:
        if len(tx.vin) != len(utxos):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(utxos)} UTXOs provided")
        
        if len(tx.vin) != len(private_keys):
            raise SigningError(f"Transaction has {len(tx.vin)} inputs but {len(private_keys)} private keys provided")
        
        signed_tx = Transaction(
            version=tx.version,
            vin=[TxIn(
                prev_txid=txin.prev_txid,
                vout=txin.vout,
                script_sig=txin.script_sig,
                sequence=txin.sequence
            ) for txin in tx.vin],
            vout=tx.vout[:],
            locktime=tx.locktime
        )
        
        has_segwit = False
        
        for i in range(len(signed_tx.vin)):
            try:
                utxo = utxos[i]
                addr_type, _ = decode_address(utxo["address"])
                
                if addr_type == "p2wpkh":
                    SegWitSigner.sign_input(signed_tx, i, utxo, private_keys[i])
                    has_segwit = True
                elif addr_type == "p2pkh":
                    LegacySigner.sign_p2pkh_input(
                        signed_tx, i, private_keys[i], utxo["script_pubkey"]
                    )
                elif addr_type == "p2sh":
                    if "redeem_script" not in utxo:
                        from ..keys.ec import privkey_to_pubkey
                        pubkey = privkey_to_pubkey(private_keys[i], compressed=True)
                        redeem_script = build_p2pkh_script(pubkey)
                    else:
                        redeem_script = utxo["redeem_script"]
                    
                    LegacySigner.sign_p2sh_input(
                        signed_tx, i, private_keys[i], redeem_script, utxo["script_pubkey"]
                    )
                else:
                    raise SigningError(f"Unsupported address type: {addr_type}")
            except Exception as e:
                raise SigningError(f"Failed to sign input {i}: {e}")
        
        if has_segwit:
            signed_tx.has_witness = True
        
        return signed_tx