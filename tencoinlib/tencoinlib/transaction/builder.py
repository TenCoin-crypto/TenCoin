from typing import List, Tuple, Dict, Any, Optional
from ..constants import DUST_LIMIT
from .core import Transaction, TxIn, TxOut
from .fee import FeeCalculator
from .address import address_to_script, is_valid_address

class TransactionBuilderError(Exception):
    """Transaction builder errors"""
    pass

class TransactionBuilder:
    """
    Build Tencoin transactions with support for all address types.
    
    Features:
    - Support for P2WPKH, P2PKH, P2SH addresses
    - Automatic fee calculation
    - Change address handling
    - Dust limit enforcement
    - SegWit and Legacy input support
    
    Example:
        >>> builder = TransactionBuilder()
        >>> builder.add_input(txid="...", vout=0, value=1000000, script_pubkey=b"...")
        >>> builder.add_output("tc1q...", 500000)
        >>> builder.set_change_address("tc1q...")
        >>> tx, fee = builder.build()
    """
    
    def __init__(self):
        """Initialize transaction builder"""
        self.inputs: List[Dict[str, Any]] = []
        self.outputs: List[Tuple[str, int]] = []
        self.change_address: Optional[str] = None
        self.fee_rate: int = FeeCalculator.DEFAULT_FEE_RATE
        self.has_segwit: bool = True  # Default to SegWit inputs
        self.locktime: int = 0
        self.version: int = 1
        
    def add_input(
        self, 
        txid: str, 
        vout: int, 
        value: int, 
        script_pubkey: bytes,
        sequence: int = 0xffffffff
    ) -> 'TransactionBuilder':
        """
        Add a transaction input (UTXO).
        
        Args:
            txid: Previous transaction ID (hex, big-endian)
            vout: Output index in previous transaction
            value: Amount in Tenos
            script_pubkey: Script public key of the UTXO
            sequence: Sequence number (default: 0xffffffff)
            
        Returns:
            Self for method chaining
            
        Raises:
            TransactionBuilderError: If input data is invalid
        """
        if not txid or len(txid) != 64:
            raise TransactionBuilderError(f"Invalid txid: {txid}")
        
        if vout < 0:
            raise TransactionBuilderError(f"Invalid vout: {vout}")
        
        if value <= 0:
            raise TransactionBuilderError(f"Invalid value: {value}")
        
        if not script_pubkey:
            raise TransactionBuilderError("Script pubkey cannot be empty")
        
        self.inputs.append({
            "txid": txid,
            "vout": vout,
            "value": value,
            "script_pubkey": script_pubkey,
            "sequence": sequence
        })
        
        return self
    
    def add_output(self, address: str, amount: int) -> 'TransactionBuilder':
        """
        Add a transaction output.
        
        Args:
            address: Recipient address (P2WPKH, P2PKH, or P2SH)
            amount: Amount in Tenos
            
        Returns:
            Self for method chaining
            
        Raises:
            TransactionBuilderError: If amount is below dust limit or address is invalid
        """
        if amount < DUST_LIMIT:
            raise TransactionBuilderError(
                f"Amount {amount} below dust limit {DUST_LIMIT}"
            )
        
        if not is_valid_address(address):
            raise TransactionBuilderError(f"Invalid address: {address}")
        
        self.outputs.append((address, amount))
        
        return self
    
    def set_change_address(self, address: str) -> 'TransactionBuilder':
        """
        Set the change address.
        
        Args:
            address: Change address (any valid address type)
            
        Returns:
            Self for method chaining
            
        Raises:
            TransactionBuilderError: If address is invalid
        """
        if not is_valid_address(address):
            raise TransactionBuilderError(f"Invalid change address: {address}")
        
        self.change_address = address
        return self
    
    def set_fee_rate(self, fee_rate: int) -> 'TransactionBuilder':
        """
        Set custom fee rate.
        
        Args:
            fee_rate: Fee rate in Tenos per byte
            
        Returns:
            Self for method chaining
        """
        if fee_rate <= 0:
            raise TransactionBuilderError(f"Invalid fee rate: {fee_rate}")
        
        self.fee_rate = fee_rate
        return self
    
    def set_segwit(self, use_segwit: bool) -> 'TransactionBuilder':
        """
        Set whether to use SegWit inputs.
        
        Args:
            use_segwit: True for SegWit, False for Legacy
            
        Returns:
            Self for method chaining
        """
        self.has_segwit = use_segwit
        return self
    
    def set_locktime(self, locktime: int) -> 'TransactionBuilder':
        """
        Set transaction locktime.
        
        Args:
            locktime: Locktime value
            
        Returns:
            Self for method chaining
        """
        if locktime < 0:
            raise TransactionBuilderError(f"Invalid locktime: {locktime}")
        
        self.locktime = locktime
        return self
    
    def set_version(self, version: int) -> 'TransactionBuilder':
        """
        Set transaction version.
        
        Args:
            version: Transaction version
            
        Returns:
            Self for method chaining
        """
        if version < 1:
            raise TransactionBuilderError(f"Invalid version: {version}")
        
        self.version = version
        return self
    
    def calculate_total_input(self) -> int:
        """
        Calculate total input amount.
        
        Returns:
            Total input amount in Tenos
        """
        return sum(inp["value"] for inp in self.inputs)
    
    def calculate_total_output(self, include_change: bool = False) -> int:
        """
        Calculate total output amount.
        
        Args:
            include_change: Whether to include change in calculation
            
        Returns:
            Total output amount in Tenos
        """
        total = sum(amount for _, amount in self.outputs)
        
        if include_change and self.change_address:
            # We don't know change amount yet, so return base total
            pass
            
        return total
    
    def calculate_fee(self, include_change: bool = True) -> int:
        """
        Calculate estimated fee.
        
        Args:
            include_change: Whether to include change output in size calculation
            
        Returns:
            Estimated fee in Tenos
        """
        num_inputs = len(self.inputs)
        num_outputs = len(self.outputs)
        
        if include_change and self.change_address:
            num_outputs += 1
        
        return FeeCalculator.calculate_fee(
            num_inputs, num_outputs, self.fee_rate, self.has_segwit
        )
    
    def calculate_change(self) -> Tuple[int, bool]:
        """
        Calculate change amount.
        
        Returns:
            (change_amount, has_change)
            change_amount: Change amount in Tenos (0 if no change)
            has_change: Whether change should be included
        """
        total_input = self.calculate_total_input()
        total_output = self.calculate_total_output()
        fee = self.calculate_fee(include_change=False)
        
        required = total_output + fee
        change = total_input - required
        
        if change < 0:
            raise TransactionBuilderError(
                f"Insufficient funds: have {total_input}, need {required}"
            )
        
        # Only add change if it's above dust limit
        if change >= DUST_LIMIT and self.change_address:
            return change, True
        elif change > 0 and change < DUST_LIMIT:
            # Change is dust, add it to fee
            return 0, False
        else:
            # No change address or exact amount
            return 0, False
    
    def build(self) -> Tuple[Transaction, int]:
        """
        Build the transaction.
        
        Returns:
            (transaction, actual_fee)
            
        Raises:
            TransactionBuilderError: If transaction cannot be built
        """
        # Validation
        if not self.inputs:
            raise TransactionBuilderError("No inputs added")
        
        if not self.outputs:
            raise TransactionBuilderError("No outputs added")
        
        total_input = self.calculate_total_input()
        total_output = self.calculate_total_output()
        
        # Create transaction inputs
        tx_inputs = []
        for inp in self.inputs:
            txin = TxIn(
                prev_txid=inp["txid"],
                vout=inp["vout"],
                script_sig=b"",  # Will be filled during signing
                sequence=inp["sequence"]
            )
            tx_inputs.append(txin)
        
        # First, build transaction without change to get accurate size
        tx_outputs = []
        for address, amount in self.outputs:
            script_pubkey = address_to_script(address)
            txout = TxOut(amount, script_pubkey)
            tx_outputs.append(txout)
        
        # Create temporary transaction without change
        temp_tx = Transaction(
            version=self.version,
            vin=tx_inputs,
            vout=tx_outputs,
            locktime=self.locktime
        )
        
        # Calculate actual fee based on real transaction size (without change)
        if self.has_segwit:
            # For SegWit, calculate virtual size including witness
            # Base size (without witness)
            base_size = len(temp_tx.serialize(include_witness=False))
            # Witness size for P2WPKH: ~108 bytes per input
            # 1 byte (witness item count) + 1 byte (sig len) + ~72 bytes (sig) + 1 byte (pubkey len) + 33 bytes (pubkey)
            witness_size_per_input = 108
            total_witness_size = len(tx_inputs) * witness_size_per_input
            total_size = base_size + total_witness_size
            # Weight = base * 3 + total
            weight = base_size * 3 + total_size
            # Virtual size = weight / 4 (rounded up)
            temp_size = (weight + 3) // 4
        else:
            temp_size = temp_tx.calculate_size()
        
        fee_without_change = temp_size * self.fee_rate
        min_fee = 1000
        fee_without_change = max(fee_without_change, min_fee)
        
        # Calculate change
        remaining = total_input - total_output - fee_without_change
        
        # Check if we need change output
        has_change = False
        change_amount = 0
        
        if remaining >= DUST_LIMIT and self.change_address:
            # Add change output and recalculate fee
            change_script = address_to_script(self.change_address)
            change_output = TxOut(remaining, change_script)
            
            # Create transaction with change to get accurate size
            tx_with_change = Transaction(
                version=self.version,
                vin=tx_inputs,
                vout=tx_outputs + [change_output],
                locktime=self.locktime
            )
            
            # Calculate fee with change
            if self.has_segwit:
                # For SegWit, calculate virtual size including witness
                base_size = len(tx_with_change.serialize(include_witness=False))
                witness_size_per_input = 108
                total_witness_size = len(tx_inputs) * witness_size_per_input
                total_size = base_size + total_witness_size
                weight = base_size * 3 + total_size
                size_with_change = (weight + 3) // 4
            else:
                size_with_change = tx_with_change.calculate_size()
            
            fee_with_change = size_with_change * self.fee_rate
            fee_with_change = max(fee_with_change, min_fee)
            
            # Recalculate change with accurate fee
            change_amount = total_input - total_output - fee_with_change
            
            # If change is still above dust limit, use it
            if change_amount >= DUST_LIMIT:
                has_change = True
                fee = fee_with_change
            else:
                # Change is dust, add it to fee
                has_change = False
                change_amount = 0
                fee = fee_without_change + remaining
        else:
            # No change or change is dust
            has_change = False
            change_amount = 0
            fee = fee_without_change
        
        # Final verification
        required = total_output + fee + (change_amount if has_change else 0)
        if total_input < required:
            raise TransactionBuilderError(
                f"Insufficient funds: have {total_input}, need {required}"
            )
        
        # Build final transaction
        final_outputs = tx_outputs.copy()
        
        if has_change and self.change_address:
            change_script = address_to_script(self.change_address)
            change_output = TxOut(change_amount, change_script)
            final_outputs.append(change_output)
        
        # Create final transaction
        tx = Transaction(
            version=self.version,
            vin=tx_inputs,
            vout=final_outputs,
            locktime=self.locktime
        )
        
        # Calculate actual fee (may differ slightly due to rounding)
        actual_total_output = sum(out.value for out in final_outputs)
        actual_fee = total_input - actual_total_output
        
        return tx, actual_fee
    
    def build_raw(self) -> Tuple[str, int]:
        """
        Build transaction and return raw hex.
        
        Returns:
            (raw_transaction_hex, fee_amount)
        """
        tx, fee = self.build()
        return tx.serialize().hex(), fee
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get transaction summary.
        
        Returns:
            Dictionary with transaction details
        """
        total_input = self.calculate_total_input()
        total_output = self.calculate_total_output()
        
        try:
            change_amount, has_change = self.calculate_change()
            fee = self.calculate_fee(include_change=has_change)
        except TransactionBuilderError:
            change_amount = 0
            has_change = False
            fee = self.calculate_fee(include_change=False)
        
        return {
            "inputs_count": len(self.inputs),
            "outputs_count": len(self.outputs) + (1 if has_change else 0),
            "total_input": total_input,
            "total_output": total_output,
            "change_amount": change_amount,
            "has_change": has_change,
            "fee": fee,
            "fee_rate": self.fee_rate,
            "uses_segwit": self.has_segwit,
            "locktime": self.locktime,
            "version": self.version,
            "change_address": self.change_address if has_change else None
        }
    
    def clear(self) -> 'TransactionBuilder':
        """
        Clear all inputs and outputs.
        
        Returns:
            Self for method chaining
        """
        self.inputs.clear()
        self.outputs.clear()
        self.change_address = None
        self.fee_rate = FeeCalculator.DEFAULT_FEE_RATE
        self.has_segwit = True
        self.locktime = 0
        self.version = 1
        
        return self
    
    def copy(self) -> 'TransactionBuilder':
        """
        Create a copy of this builder.
        
        Returns:
            New TransactionBuilder instance with same data
        """
        import copy
        new_builder = TransactionBuilder()
        
        # Deep copy inputs
        new_builder.inputs = copy.deepcopy(self.inputs)
        
        # Shallow copy outputs (tuples are immutable)
        new_builder.outputs = self.outputs.copy()
        
        # Copy other attributes
        new_builder.change_address = self.change_address
        new_builder.fee_rate = self.fee_rate
        new_builder.has_segwit = self.has_segwit
        new_builder.locktime = self.locktime
        new_builder.version = self.version
        
        return new_builder
    
    def __repr__(self) -> str:
        """String representation"""
        summary = self.get_summary()
        return (
            f"TransactionBuilder("
            f"inputs={summary['inputs_count']}, "
            f"outputs={summary['outputs_count']}, "
            f"total={summary['total_input']} Tenos)"
        )