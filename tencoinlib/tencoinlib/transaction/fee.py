from typing import List
from .core import Transaction, TxIn, TxOut

class FeeCalculator:
    """Calculate transaction fees"""
    
    # Fee rates in Tenos per byte
    DEFAULT_FEE_RATE = 20  # 20 Tenos per byte
    PRIORITY_FEE_RATE = 50
    ECONOMY_FEE_RATE = 10
    
    @staticmethod
    def estimate_size(num_inputs: int, num_outputs: int, has_segwit: bool = True) -> int:
        """
        Estimate transaction size in bytes.
        
        Args:
            num_inputs: Number of inputs
            num_outputs: Number of outputs
            has_segwit: Whether inputs are SegWit
            
        Returns:
            Estimated size in bytes
        """
        if has_segwit:
            # SegWit inputs are smaller
            # Base: ~10.5 bytes, Input: ~68 bytes, Output: ~31 bytes
            base_size = 10
            input_size = 68  # SegWit input
            output_size = 31
        else:
            # Legacy inputs
            base_size = 10
            input_size = 148  # Legacy input
            output_size = 34
        
        return base_size + (num_inputs * input_size) + (num_outputs * output_size)
    
    @staticmethod
    def calculate_fee(
        num_inputs: int,
        num_outputs: int,
        fee_rate: int = None,
        has_segwit: bool = True
    ) -> int:
        """
        Calculate fee for transaction.
        
        Args:
            num_inputs: Number of inputs
            num_outputs: Number of outputs
            fee_rate: Fee rate in Tenos per byte
            has_segwit: Whether inputs are SegWit
            
        Returns:
            Fee in Tenos
        """
        if fee_rate is None:
            fee_rate = FeeCalculator.DEFAULT_FEE_RATE
        
        size = FeeCalculator.estimate_size(num_inputs, num_outputs, has_segwit)
        fee = size * fee_rate
        
        # Minimum fee
        min_fee = 1000  # 1000 Tenos minimum
        return max(fee, min_fee)
    
    @staticmethod
    def calculate_fee_for_transaction(tx: Transaction, fee_rate: int = None) -> int:
        """
        Calculate fee for a transaction object.
        
        Args:
            tx: Transaction object
            fee_rate: Fee rate in Tenos per byte
            
        Returns:
            Fee in Tenos
        """
        if fee_rate is None:
            fee_rate = FeeCalculator.DEFAULT_FEE_RATE
        
        # Check if any input uses SegWit
        has_segwit = tx.has_witness
        
        size = tx.calculate_vsize() if has_segwit else tx.calculate_size()
        fee = size * fee_rate
        
        # Minimum fee
        min_fee = 1000
        return max(fee, min_fee)
    
    @staticmethod
    def get_recommended_fee_rates() -> dict:
        """
        Get recommended fee rates.
        
        Returns:
            Dictionary of fee rates
        """
        return {
            "priority": FeeCalculator.PRIORITY_FEE_RATE,
            "normal": FeeCalculator.DEFAULT_FEE_RATE,
            "economy": FeeCalculator.ECONOMY_FEE_RATE,
        }