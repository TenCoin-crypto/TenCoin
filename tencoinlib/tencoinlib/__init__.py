# tencoin/tencoinlib/__init__.py
"""
tencoinlib - Official Python library for Tencoin
"""

from .constants import (
    MAINNET_HRP,
    TENOS_PER_TEC,
    DUST_LIMIT,
    DEFAULT_RPC_PORT,
    COIN_TYPE,
    DERIVATION_PATH,
    DEFAULT_RPC_TOKEN,
    DEVELOPER_ADDRESS
)

from .wallet import Wallet, WalletError
from .rpc import RPCClient, RPCError
from .transaction import (
    Transaction, TxIn, TxOut, parse_transaction,
    TransactionBuilder, TransactionBuilderError,
    SegWitSigner, LegacySigner, TransactionSigner, SigningError,
    FeeCalculator,
    decode_address, address_to_script, is_valid_address,
    get_address_type, AddressError
)

from .message import (
    sign_message,
    verify_message,
    recover_address_from_signature,
    MessageSigningError,
)

from .integrity import compute_library_hash, get_file_manifest

# Version
__version__ = "0.1.4"

__all__ = [
    # Constants
    "MAINNET_HRP",
    "TENOS_PER_TEC",
    "DUST_LIMIT",
    "DEFAULT_RPC_PORT",
    "DEFAULT_RPC_TOKEN",
    "COIN_TYPE",
    "DERIVATION_PATH",
    
    # Wallet
    "Wallet",
    "WalletError",
    
    # RPC
    "RPCClient",
    "RPCError",
    
    # Transaction
    "Transaction",
    "TxIn",
    "TxOut",
    "parse_transaction",
    "TransactionBuilder",
    "TransactionBuilderError",
    "SegWitSigner",
    "LegacySigner",
    "TransactionSigner",
    "SigningError",
    "FeeCalculator",
    "decode_address",
    "address_to_script",
    "is_valid_address",
    "get_address_type",
    "AddressError",
    
    # Message Signing
    "sign_message",
    "verify_message",
    "recover_address_from_signature",
    "MessageSigningError",

    # Version
    "__version__",
]