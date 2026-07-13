# Tencoinlib Documentation

Complete and comprehensive documentation for the Tencoinlib Python library.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Wallet](#wallet)
5. [Transactions](#transactions)
6. [RPC Client](#rpc-client)
7. [Address Utilities](#address-utilities)
8. [Fee Management](#fee-management)
9. [Key Management](#key-management)
10. [Transaction Signing](#transaction-signing)
11. [Complete Examples](#complete-examples)
12. [API Reference](#api-reference)
13. [Error Handling](#error-handling)
14. [Constants and Configuration](#constants-and-configuration)
15. [Best Practices](#best-practices)

---

## Introduction

**Tencoinlib** is the official Python library for working with the Tencoin cryptocurrency. It provides a comprehensive set of tools for creating HD wallets, building and signing transactions, and interacting with Tencoin nodes via RPC.

### Key Features

- ✅ **HD Wallets**: Full support for BIP-39 (mnemonic phrases) + BIP-84 (SegWit addresses)
- ✅ **BIP-32 Extended Keys**: Master/account-level xprv/xpub with standard serialization
- ✅ **Watch-Only Wallets**: Create wallets from xpub only (no seed/private keys)
- ✅ **Multiple Address Types**: 
  - **SegWit v0** (P2WPKH): Native SegWit addresses (`tc1q...`)
  - **Legacy P2PKH**: Pay-to-pubkey-hash addresses (`T...`)
  - **Legacy P2SH**: Pay-to-script-hash addresses (`M...`)
  - **P2WSH**: SegWit script addresses (`tc1q...` with 32-byte program)
- ✅ **Custom Scripts**: Support for multisig and custom redeem/witness scripts
- ✅ **Transaction Signing**: Automatic detection and signing for SegWit (BIP-143) and Legacy (P2PKH/P2SH) inputs
- ✅ **Key Derivation**: Standard BIP-84 derivation path `m/84'/5353'/0'/0/0` + generic BIP-32 paths
- ✅ **Mnemonic Phrases**: 12, 15, 18, 21, or 24 word English mnemonics
- ✅ **Wallet Recovery**: Restore wallets from mnemonic phrases
- ✅ **Transaction Building**: Create and sign transactions with all address types
- ✅ **RPC Client**: Connect to Tencoin nodes via JSON-RPC
- ✅ **Fee Calculation**: Automatic fee estimation and management
- ✅ **Address Validation**: Support for multiple address types

### Supported Standards

- **BIP-39**: Mnemonic code for generating deterministic keys
- **BIP-32**: Hierarchical Deterministic Wallets
- **BIP-84**: Derivation scheme for P2WPKH (SegWit v0)
- **BIP-143**: Transaction signature verification for SegWit
- **BIP-13**: Pay-to-script-hash (P2SH)
- **BIP-141**: SegWit (P2WSH support)

---

## Installation

### Install from PyPI

```bash
pip install tencoinlib
```

### Install with Optional Dependencies

```bash
# For development tools (pytest, black, ruff)
pip install tencoinlib[dev]

# For async support (when available)
pip install tencoinlib[async]

# For enhanced mnemonic support
pip install tencoinlib[mnemonic]
```

### Requirements

- Python >= 3.8
- `ecdsa>=0.18.0` - For transaction signing
- `requests>=2.28.0` - For RPC client
- `bech32>=1.2.0` - For SegWit address encoding

---

## Quick Start

### Create a New Wallet

```python
from tencoinlib import Wallet

# Create a new wallet with 12-word mnemonic
wallet = Wallet.create()

print(f"Mnemonic: {wallet.get_mnemonic()}")
print(f"Address: {wallet.get_address()}")
print(f"Private Key: {wallet.get_private_key_hex()}")
```

### Recover a Wallet

```python
from tencoinlib import Wallet

# Recover wallet from mnemonic
mnemonic = "abandon ability able about above absent absorb abstract absurd abuse access accident"
wallet = Wallet.recover(mnemonic)

print(f"Recovered Address: {wallet.get_address()}")
```

### Send a Transaction

```python
from tencoinlib import Wallet, TransactionBuilder, TransactionSigner
from tencoinlib.rpc import RPCClient
from tencoinlib.transaction.address import address_to_script

# Setup
wallet = Wallet.recover("your mnemonic phrase")
rpc = RPCClient(host="127.0.0.1", port=10111, token="your-token")

# Get UTXOs
utxos = rpc.list_unspent(wallet.get_address())

# Build transaction
builder = TransactionBuilder()
for utxo in utxos:
    builder.add_input(
        txid=utxo["txid"],
        vout=utxo["vout"],
        value=utxo["amount"],
        script_pubkey=bytes.fromhex(utxo["scriptPubKey"])
    )
# Recipient can be SegWit (tc1q...), P2PKH (T...), or P2SH (M...)
builder.add_output("tc1q...", 1000000)
builder.set_change_address(wallet.get_address())

tx, fee = builder.build()

# Sign transaction (automatically detects address type)
utxo_data = [{
    "value": u["amount"],
    "script_pubkey": bytes.fromhex(u["scriptPubKey"]),
    "address": wallet.get_address()  # Can be any address type
} for u in utxos]
private_keys = [bytes.fromhex(wallet.get_private_key_hex())] * len(utxos)

# TransactionSigner automatically handles SegWit, P2PKH, and P2SH
signed_tx = TransactionSigner.sign_transaction(tx, utxo_data, private_keys)

# Broadcast
txid = rpc.send_raw_transaction(signed_tx.serialize().hex())
print(f"Transaction sent! TXID: {txid}")
```

---

## Wallet

The `Wallet` class provides high-level HD wallet functionality for Tencoin.

### Creating Wallets

#### Create New Wallet

```python
from tencoinlib import Wallet

# Create wallet with default 12-word mnemonic (128-bit entropy)
wallet = Wallet.create()

# Create wallet with different strengths
wallet_15 = Wallet.create(strength=160)   # 15 words
wallet_18 = Wallet.create(strength=192)   # 18 words
wallet_21 = Wallet.create(strength=224)   # 21 words
wallet_24 = Wallet.create(strength=256)   # 24 words

# Valid strength values: 128, 160, 192, 224, 256
```

#### Recover from Mnemonic

```python
from tencoinlib import Wallet

# Recover without passphrase
mnemonic = "word1 word2 word3 ... word12"
wallet = Wallet.recover(mnemonic)

# Recover with BIP-39 passphrase
wallet = Wallet.recover(mnemonic, passphrase="my-secret-passphrase")
```

**Note**: The mnemonic phrase must be valid BIP-39 format with correct checksum.

### Accessing Wallet Information

```python
# Get SegWit address (P2WPKH) — default
address = wallet.get_address()
print(f"Address: {address}")  # e.g., "tc1q..."

# Same key as other address types (P2PKH, P2SH)
print("SegWit:  ", wallet.get_address())              # tc1q...
print("P2PKH:   ", wallet.get_address("p2pkh"))       # T...
print("P2SH:    ", wallet.get_address("p2sh"))        # M... (single-sig P2SH)

# Get private key (hex format)
private_key = wallet.get_private_key_hex()
print(f"Private Key: {private_key}")

# Get public key (hex format, compressed)
public_key = wallet.get_public_key_hex()
print(f"Public Key: {public_key}")

# Get mnemonic phrase (only if wallet was created or recovered with mnemonic)
try:
    mnemonic = wallet.get_mnemonic()
    print(f"Mnemonic: {mnemonic}")
except WalletError:
    print("Mnemonic not available")
```

### Address Types and Custom Scripts

The `get_address()` method supports multiple address types and custom scripts (multisig, custom redeem scripts).

#### Standard Address Types

```python
wallet = Wallet.create()

# SegWit v0 native (P2WPKH) - default
segwit_addr = wallet.get_address()  # or wallet.get_address("p2wpkh")
print(f"SegWit: {segwit_addr}")  # tc1q...

# Legacy P2PKH
p2pkh_addr = wallet.get_address("p2pkh")
print(f"P2PKH: {p2pkh_addr}")  # T...

# Single-sig P2SH (P2SH-wrapped P2PKH)
p2sh_addr = wallet.get_address("p2sh")
print(f"P2SH: {p2sh_addr}")  # M...
```

#### Custom Scripts (P2SH and P2WSH)

You can create addresses from custom redeem/witness scripts (e.g., multisig, custom logic).

##### P2SH with Custom Redeem Script

```python
from tencoinlib.transaction import build_multisig_script, script_to_p2sh_address

# Build 2-of-3 multisig redeem script
pubkeys = [
    bytes.fromhex("02a1b2c3..."),  # Public key 1 (33 bytes)
    bytes.fromhex("03d4e5f6..."),  # Public key 2
    bytes.fromhex("0298a7b8..."),  # Public key 3
]

# Create multisig script (sorted for canonical form)
redeem_script = build_multisig_script(2, pubkeys, sort_pubkeys=True)

# Get P2SH address from redeem script
p2sh_multisig_addr = script_to_p2sh_address(redeem_script)
print(f"2-of-3 P2SH: {p2sh_multisig_addr}")  # M...

# Or use wallet.get_address() with script
p2sh_addr = wallet.get_address("p2sh", script=redeem_script)
```

##### P2WSH (SegWit Script) with Custom Witness Script

```python
from tencoinlib.transaction import build_multisig_script, script_to_p2wsh_address

# Build 2-of-3 multisig witness script
pubkeys = [
    bytes.fromhex("02a1b2c3..."),
    bytes.fromhex("03d4e5f6..."),
    bytes.fromhex("0298a7b8..."),
]

witness_script = build_multisig_script(2, pubkeys, sort_pubkeys=True)

# Get P2WSH address (SegWit v0 script)
p2wsh_addr = script_to_p2wsh_address(witness_script)
print(f"2-of-3 P2WSH: {p2wsh_addr}")  # tc1q...

# Or use wallet.get_address() with script
p2wsh_addr = wallet.get_address("p2wsh", script=witness_script)
```

##### Complete Example: 2-of-3 P2WSH Multisig Wallet

```python
from tencoinlib import Wallet
from tencoinlib.transaction import build_multisig_script
from tencoinlib.keys.bip32 import derive_path_from_seed
from tencoinlib.keys.ec import privkey_to_pubkey

# Generate master mnemonic
wallet = Wallet.create()
mnemonic = wallet.get_mnemonic()
seed = wallet.seed  # Access seed for derivation

# Derive three keys from different paths
paths = [
    "m/84'/5353'/0'/0/0",
    "m/84'/5353'/0'/0/1",
    "m/84'/5353'/0'/0/2"
]

pubkeys = []
for path in paths:
    priv, _ = derive_path_from_seed(seed, path)
    pub = privkey_to_pubkey(priv, compressed=True)
    pubkeys.append(pub)

# Build 2-of-3 multisig witness script
witness_script = build_multisig_script(2, pubkeys, sort_pubkeys=True)

# Get P2WSH address
multisig_address = wallet.get_address("p2wsh", script=witness_script)
print(f"2-of-3 P2WSH Address: {multisig_address}")
print(f"Witness Script: {witness_script.hex()}")
```

#### Using Wallet.build_multisig_script()

For convenience, you can use the static method on `Wallet`:

```python
# Build multisig script (pubkeys can be bytes or hex strings)
pubkeys_hex = ["02a1b2c3...", "03d4e5f6...", "0298a7b8..."]
script = Wallet.build_multisig_script(2, pubkeys_hex)

# Use with get_address
addr = wallet.get_address("p2wsh", script=script)
```

### Deriving Additional Addresses

#### Derive Specific Address

```python
# Derive address at specific path: m/84'/5353'/{account}'/{change}/{index}
private_key_hex, address = wallet.derive_address(
    account=0,   # Account number (typically 0)
    change=0,    # 0 for external (receiving), 1 for change
    index=1      # Address index
)

print(f"Address: {address}")
print(f"Private Key: {private_key_hex}")
```

#### Get Next Address

```python
# Get next external address (automatically increments index)
priv_key, next_address = wallet.get_next_address(change=0)
print(f"Next receiving address: {next_address}")

# Get next change address
priv_key, change_address = wallet.get_next_address(change=1)
print(f"Next change address: {change_address}")
```

#### Derive Multiple Addresses

```python
# Derive first 5 receiving addresses
print("Receiving Addresses:")
for i in range(5):
    priv, addr = wallet.derive_address(account=0, change=0, index=i)
    print(f"  {i}: {addr}")

# Derive first 3 change addresses
print("\nChange Addresses:")
for i in range(3):
    priv, addr = wallet.derive_address(account=0, change=1, index=i)
    print(f"  {i}: {addr}")
```

### Wallet Serialization

#### Export Wallet Information

```python
# Convert wallet to dictionary
wallet_dict = wallet.to_dict()
print(wallet_dict)
# {
#     "mnemonic": "word1 word2 ...",
#     "address": "tc1q...",
#     "public_key": "02...",
#     "private_key": "abc123...",
#     "derivation_path": "m/84'/5353'/0'/0/0",
#     "account_index": 0,
#     "change_index": 0,
#     "address_index": 0,
#     "seed_available": True
# }
```

#### Save and Load Wallet

```python
# Save wallet to file
wallet.save_to_file("my_wallet.json")

# Load wallet from file
wallet = Wallet.load_from_file("my_wallet.json")

# Note: Wallet encryption is not yet implemented
# The wallet file is stored in plain JSON format
# For production use, implement additional encryption
```

---

## Transactions

The transaction system allows you to create, build, and sign Tencoin transactions.

### TransactionBuilder

`TransactionBuilder` is the main class for constructing transactions.

#### Basic Transaction Building

```python
from tencoinlib import TransactionBuilder

# Initialize builder
builder = TransactionBuilder()

# Add input (UTXO)
builder.add_input(
    txid="abc123...",           # Previous transaction ID (hex, big-endian)
    vout=0,                     # Output index in previous transaction
    value=1000000,              # Amount in Tenos
    script_pubkey=b"..."        # ScriptPubKey of the UTXO
)

# Add output (recipient)
builder.add_output(
    address="tc1q...",          # Recipient address
    amount=500000               # Amount to send in Tenos
)

# Set change address
builder.set_change_address("tc1q...")

# Build transaction
transaction, fee = builder.build()
print(f"Fee: {fee} Tenos")
```

#### Advanced Transaction Configuration

```python
builder = TransactionBuilder()

# Set custom fee rate (Tenos per byte)
builder.set_fee_rate(50)  # Higher fee = faster confirmation

# Enable/disable SegWit (default: True)
builder.set_segwit(True)

# Set transaction locktime
builder.set_locktime(0)  # 0 = immediate

# Set transaction version
builder.set_version(1)  # Default is 1

# Build transaction
tx, fee = builder.build()
```

#### Multiple Inputs and Outputs

```python
builder = TransactionBuilder()

# Add multiple inputs
for utxo in utxos:
    builder.add_input(
        txid=utxo["txid"],
        vout=utxo["vout"],
        value=utxo["amount"],
        script_pubkey=bytes.fromhex(utxo["scriptPubKey"]),
        sequence=0xffffffff
    )

# Add multiple outputs
builder.add_output("tc1q...", 1000000)  # Payment 1 (tc1q... / T... / M...)
builder.add_output("tc1q...", 500000)   # Payment 2 (tc1q... / T... / M...)
builder.add_output("tc1q...", 200000)   # Payment 3 (tc1q... / T... / M...)

# Set change address
builder.set_change_address("tc1q...")

tx, fee = builder.build()
```

#### Transaction Summary

```python
# Get transaction summary before building
summary = builder.get_summary()
print(f"Inputs: {summary['inputs_count']}")
print(f"Outputs: {summary['outputs_count']}")
print(f"Total Input: {summary['total_input']} Tenos")
print(f"Total Output: {summary['total_output']} Tenos")
print(f"Estimated Fee: {summary['fee']} Tenos")
print(f"Change Amount: {summary['change_amount']} Tenos")
print(f"Has Change: {summary['has_change']}")
```

#### Helper Methods

```python
# Calculate total input amount
total_input = builder.calculate_total_input()

# Calculate total output amount
total_output = builder.calculate_total_output()

# Calculate estimated fee
estimated_fee = builder.calculate_fee()

# Calculate change amount
change_amount, has_change = builder.calculate_change()

# Build raw hex directly
raw_hex, fee = builder.build_raw()
```

#### Transaction Builder Methods

```python
# Clear all inputs and outputs
builder.clear()

# Create a copy of the builder
builder_copy = builder.copy()
```

### Transaction Object

The `Transaction` class represents a Tencoin transaction.

#### Transaction Properties

```python
from tencoinlib.transaction import Transaction, TxIn, TxOut

# Create transaction manually
tx = Transaction(
    version=1,
    vin=[TxIn(prev_txid="...", vout=0)],
    vout=[TxOut(value=1000000, script_pubkey=b"...")],
    locktime=0
)

# Access properties
print(f"Version: {tx.version}")
print(f"Inputs: {len(tx.vin)}")
print(f"Outputs: {len(tx.vout)}")
print(f"Locktime: {tx.locktime}")
print(f"Has Witness: {tx.has_witness}")
```

#### Transaction Serialization

```python
# Serialize transaction (include witness if available)
raw_bytes = tx.serialize(include_witness=True)
raw_hex = raw_bytes.hex()

# Serialize without witness (for txid calculation)
raw_bytes_no_witness = tx.serialize(include_witness=False)
```

#### Transaction Identifiers

```python
# Get transaction ID (hash without witness)
txid = tx.txid()
print(f"TXID: {txid}")

# Get witness transaction ID (includes witness)
wtxid = tx.wtxid()
print(f"WTXID: {wtxid}")
```

#### Transaction Size

```python
# Calculate transaction size in bytes
size = tx.calculate_size()
print(f"Size: {size} bytes")

# Calculate virtual size (for SegWit, weight/4)
vsize = tx.calculate_vsize()
print(f"Virtual Size: {vsize} bytes")
```

#### Parse Transaction

```python
from tencoinlib.transaction import parse_transaction

# Parse raw transaction hex
raw_hex = "0100000001..."
tx = parse_transaction(raw_hex)

# Access parsed transaction
print(f"TXID: {tx.txid()}")
print(f"Inputs: {len(tx.vin)}")
for i, txin in enumerate(tx.vin):
    print(f"  Input {i}: {txin.prev_txid[:16]}..., vout={txin.vout}")
    if txin.witness:
        print(f"    Witness: {len(txin.witness)} items")

print(f"Outputs: {len(tx.vout)}")
for i, txout in enumerate(tx.vout):
    print(f"  Output {i}: {txout.value} Tenos")
```

---

## Transaction Signing

The library provides comprehensive transaction signing support for all address types:
- **SegWit v0 (P2WPKH)**: Native SegWit addresses (`tc1q...`)
- **Legacy P2PKH**: Pay-to-pubkey-hash addresses (`T...`)
- **Legacy P2SH**: Pay-to-script-hash addresses (`M...`)
- **P2WSH**: SegWit script addresses (multisig, custom scripts)

### TransactionSigner (Universal Signer)

The `TransactionSigner` class automatically detects address types and uses the appropriate signing method. **This is the recommended approach** for most use cases.

#### Sign Transaction with Automatic Detection

```python
from tencoinlib import TransactionSigner, Wallet, TransactionBuilder
from tencoinlib.transaction.address import address_to_script

# Create wallet
wallet = Wallet.create()

# Build transaction with mixed address types
builder = TransactionBuilder()

# Add SegWit input
builder.add_input(
    txid="00" * 32,
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(wallet.get_address())
)

# Add P2PKH input
p2pkh_addr = wallet.get_address("p2pkh")
builder.add_input(
    txid="11" * 32,
    vout=0,
    value=1500000,
    script_pubkey=address_to_script(p2pkh_addr)
)

# Add P2SH input
p2sh_addr = wallet.get_address("p2sh")
builder.add_input(
    txid="22" * 32,
    vout=0,
    value=1000000,
    script_pubkey=address_to_script(p2sh_addr)
)

builder.add_output("tc1q...", 3000000)
builder.set_change_address(wallet.get_address())

tx, fee = builder.build()

# Prepare UTXOs (address type is automatically detected)
utxos = [
    {
        "value": 2000000,
        "script_pubkey": address_to_script(wallet.get_address()),
        "address": wallet.get_address()  # SegWit
    },
    {
        "value": 1500000,
        "script_pubkey": address_to_script(p2pkh_addr),
        "address": p2pkh_addr  # P2PKH
    },
    {
        "value": 1000000,
        "script_pubkey": address_to_script(p2sh_addr),
        "address": p2sh_addr  # P2SH
    }
]

private_keys = [
    bytes.fromhex(wallet.get_private_key_hex()),
    bytes.fromhex(wallet.get_private_key_hex()),
    bytes.fromhex(wallet.get_private_key_hex())
]

# Sign transaction (automatically handles all address types)
signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)

print(f"Transaction ID: {signed_tx.txid()}")
print(f"Has witness: {signed_tx.has_witness}")  # True (has SegWit inputs)
```

#### Sign P2PKH Transaction

```python
from tencoinlib import TransactionSigner, Wallet, TransactionBuilder
from tencoinlib.transaction.address import address_to_script

wallet = Wallet.create()
p2pkh_addr = wallet.get_address("p2pkh")

builder = TransactionBuilder()
builder.add_input(
    txid="abc123...",
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(p2pkh_addr)
)
builder.add_output("T...", 1000000)
builder.set_change_address(p2pkh_addr)

tx, fee = builder.build()

utxos = [{
    "value": 2000000,
    "script_pubkey": address_to_script(p2pkh_addr),
    "address": p2pkh_addr
}]

signed_tx = TransactionSigner.sign_transaction(
    tx, utxos, [bytes.fromhex(wallet.get_private_key_hex())]
)

# P2PKH uses scriptSig (not witness)
print(f"ScriptSig length: {len(signed_tx.vin[0].script_sig)} bytes")
```

#### Sign P2SH Transaction

```python
from tencoinlib import TransactionSigner, Wallet, TransactionBuilder
from tencoinlib.transaction.address import address_to_script

wallet = Wallet.create()
p2sh_addr = wallet.get_address("p2sh")

builder = TransactionBuilder()
builder.add_input(
    txid="def456...",
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(p2sh_addr)
)
builder.add_output("M...", 1000000)
builder.set_change_address(p2sh_addr)

tx, fee = builder.build()

utxos = [{
    "value": 2000000,
    "script_pubkey": address_to_script(p2sh_addr),
    "address": p2sh_addr
    # redeem_script is automatically derived for single-sig P2SH
}]

signed_tx = TransactionSigner.sign_transaction(
    tx, utxos, [bytes.fromhex(wallet.get_private_key_hex())]
)

# P2SH uses scriptSig with redeem script
print(f"ScriptSig length: {len(signed_tx.vin[0].script_sig)} bytes")
```

#### Sign Transaction with Custom P2SH Redeem Script

```python
from tencoinlib import TransactionSigner, TransactionBuilder, build_multisig_script
from tencoinlib.transaction.address import address_to_script, script_to_p2sh_address

# Build multisig redeem script (2-of-3)
pubkeys = [
    bytes.fromhex("02a1b2c3..."),
    bytes.fromhex("03d4e5f6..."),
    bytes.fromhex("0298a7b8...")
]
redeem_script = build_multisig_script(2, pubkeys)

# Get P2SH address
p2sh_addr = script_to_p2sh_address(redeem_script)

builder = TransactionBuilder()
builder.add_input(
    txid="ghi789...",
    vout=0,
    value=5000000,
    script_pubkey=address_to_script(p2sh_addr)
)
builder.add_output("M...", 3000000)
tx, fee = builder.build()

# Provide redeem script for P2SH
utxos = [{
    "value": 5000000,
    "script_pubkey": address_to_script(p2sh_addr),
    "address": p2sh_addr,
    "redeem_script": redeem_script  # Required for multisig P2SH
}]

# For multisig, provide private keys for required signatures
private_keys = [bytes.fromhex("key1..."), bytes.fromhex("key2...")]

signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)
```

### LegacySigner

The `LegacySigner` class handles signing for Legacy address types (P2PKH and P2SH).

#### Sign P2PKH Transaction

```python
from tencoinlib.transaction import LegacySigner, TransactionBuilder
from tencoinlib.transaction.address import address_to_script

wallet = Wallet.create()
p2pkh_addr = wallet.get_address("p2pkh")

builder = TransactionBuilder()
builder.add_input(
    txid="abc123...",
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(p2pkh_addr)
)
builder.add_output("T...", 1000000)
tx, fee = builder.build()

utxos = [{
    "value": 2000000,
    "script_pubkey": address_to_script(p2pkh_addr),
    "address": p2pkh_addr
}]

signed_tx = LegacySigner.sign_transaction(
    tx, utxos, [bytes.fromhex(wallet.get_private_key_hex())]
)
```

#### Sign P2SH Transaction with Redeem Script

```python
from tencoinlib.transaction import LegacySigner, build_p2pkh_script
from tencoinlib.keys.ec import privkey_to_pubkey

wallet = Wallet.create()
p2sh_addr = wallet.get_address("p2sh")
private_key = bytes.fromhex(wallet.get_private_key_hex())
pubkey = privkey_to_pubkey(private_key, compressed=True)

# Build redeem script (P2PKH script)
redeem_script = build_p2pkh_script(pubkey)

builder = TransactionBuilder()
builder.add_input(
    txid="def456...",
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(p2sh_addr)
)
tx, fee = builder.build()

utxos = [{
    "value": 2000000,
    "script_pubkey": address_to_script(p2sh_addr),
    "address": p2sh_addr,
    "redeem_script": redeem_script
}]

signed_tx = LegacySigner.sign_transaction(tx, utxos, [private_key])
```

### SegWitSigner

The `SegWitSigner` class handles signing for SegWit (P2WPKH) transactions using BIP-143.

#### Sign SegWit Transaction

```python
from tencoinlib import SegWitSigner, Wallet, TransactionBuilder
from tencoinlib.transaction.address import address_to_script

wallet = Wallet.create()

builder = TransactionBuilder()
builder.add_input(
    txid="abc123...",
    vout=0,
    value=2000000,
    script_pubkey=address_to_script(wallet.get_address())
)
builder.add_output("tc1q...", 1000000)
tx, fee = builder.build()

utxos = [{
    "value": 2000000,
    "script_pubkey": address_to_script(wallet.get_address()),
    "address": wallet.get_address()  # Must be P2WPKH
}]

signed_tx = SegWitSigner.sign_transaction(
    tx, utxos, [bytes.fromhex(wallet.get_private_key_hex())]
)

# SegWit uses witness (not scriptSig)
print(f"Has witness: {signed_tx.has_witness}")
print(f"Witness items: {len(signed_tx.vin[0].witness)}")
```

#### Sign Single SegWit Input

```python
# Sign a specific input
utxo = {
    "value": 1000000,
    "script_pubkey": bytes.fromhex("..."),
    "address": "tc1q..."
}
private_key = bytes.fromhex("abc123...")

SegWitSigner.sign_input(
    tx=transaction,
    input_index=0,
    utxo=utxo,
    private_key=private_key
)
```

#### Create Witness Signature

```python
# Create witness signature manually
script_code = b"..."  # P2PKH script for the public key hash
signature = SegWitSigner.create_witness_signature(
    tx=transaction,
    input_index=0,
    private_key=private_key,
    script_code=script_code,
    value=1000000,
    sighash_type=1  # SIGHASH_ALL
)
```

#### Verify Witness

```python
# Verify witness signature
is_valid = SegWitSigner.verify_witness(
    tx=transaction,
    input_index=0,
    public_key=b"...",           # 33-byte compressed public key
    script_code=b"...",
    value=1000000,
    witness=[signature, public_key]
)

print(f"Signature valid: {is_valid}")
```

---

## RPC Client

The `RPCClient` class provides methods to interact with Tencoin nodes via JSON-RPC.

### Connection Setup

```python
from tencoinlib.rpc import RPCClient

# Simple connection (default settings)
rpc = RPCClient()

# Full configuration
rpc = RPCClient(
    host="127.0.0.1",        # Node hostname or IP
    port=10111,              # RPC port (default: 10111)
    token="your-token",      # RPC authentication token
    timeout=30,              # Request timeout in seconds
    use_ssl=False            # Use HTTPS instead of HTTP
)
```

### Wallet Methods

#### Get Balance

```python
# Get balance for an address
address = "tc1q..."
balance = rpc.get_balance(address)
print(f"Balance: {balance} Tenos")
print(f"Balance: {balance / 100000000} TEC")
```

#### List Unspent Outputs (UTXOs)

```python
# Get unspent outputs for an address
utxos = rpc.list_unspent(address, minconf=1)

for utxo in utxos:
    print(f"TXID: {utxo['txid']}")
    print(f"Vout: {utxo['vout']}")
    print(f"Amount: {utxo['amount']} Tenos")
    print(f"Confirmations: {utxo.get('confirmations', 0)}")
    print(f"ScriptPubKey: {utxo.get('scriptPubKey', '')}")
    print("---")
```

### Transaction Methods

#### Send Raw Transaction

```python
# Broadcast a raw transaction
tx_hex = "0100000001..."
txid = rpc.send_raw_transaction(tx_hex)
print(f"Transaction ID: {txid}")
```

#### Test Mempool Acceptance

```python
# Test if transaction would be accepted to mempool
result = rpc.test_mempool_accept(tx_hex)
print(f"Acceptable: {result}")
```

#### Get Transaction Information

```python
# Get transaction details
txid = "abc123..."
tx_info = rpc.get_transaction(txid)
print(tx_info)
```

#### Get Raw Transaction

```python
# Get raw transaction hex
raw_tx = rpc.get_raw_transaction(txid)
print(f"Raw Transaction: {raw_tx}")
```

#### Decode Raw Transaction

```python
# Decode raw transaction
decoded = rpc.decode_raw_transaction(tx_hex)
print(decoded)
# {
#     "txid": "...",
#     "version": 1,
#     "vin": [...],
#     "vout": [...],
#     ...
# }
```

### Blockchain Methods

#### Get Block Count

```python
# Get current block height
height = rpc.get_block_count()
print(f"Current Block Height: {height}")
```

#### Get Best Block Hash

```python
# Get hash of best block
best_hash = rpc.get_best_block_hash()
print(f"Best Block Hash: {best_hash}")
```

#### Get Block Information

```python
# Get block by height
block_info = rpc.get_block(height=1000)

# Get block by hash
block_info = rpc.get_block(block_hash="abc123...")

# Block information includes:
# - hash
# - height
# - time
# - transactions
# - ...
```

#### Get Block Header

```python
# Get block header only
block_hash = "abc123..."
header = rpc.get_block_header(block_hash)
```

#### Get Blockchain Info

```python
# Get blockchain information
info = rpc.get_blockchain_info()
print(f"Chain: {info.get('chain')}")
print(f"Blocks: {info.get('blocks')}")
print(f"Difficulty: {info.get('difficulty')}")
```

#### Get Mempool Info

```python
# Get mempool information
mempool_info = rpc.get_mempool_info()
print(f"Size: {mempool_info.get('size', 0)} transactions")
print(f"Bytes: {mempool_info.get('bytes', 0)} bytes")
```

#### Get Raw Mempool

```python
# Get raw mempool transactions
raw_mempool = rpc.get_raw_mempool()
print(f"Transactions in mempool: {len(raw_mempool)}")
```

### Network Methods

#### Get Network Info

```python
# Get network information
network_info = rpc.get_network_info()
print(f"Version: {network_info.get('version')}")
print(f"Subversion: {network_info.get('subversion')}")
```

#### Get Peer Info

```python
# Get peer information
peers = rpc.get_peer_info()
for peer in peers:
    print(f"Address: {peer.get('addr')}")
    print(f"Connected: {peer.get('connected')}")
    print(f"Version: {peer.get('version')}")
```

### Mining Methods

#### Get Work

```python
# Get work for mining
work = rpc.get_work()
print(work)
```

#### Submit Block

```python
# Submit a mined block
block_hex = "01000000..."
result = rpc.submit_block(block_hex)
print(result)
```

### Utility Methods

#### Validate Address

```python
# Validate a Tencoin address
result = rpc.validate_address("tc1q...")
print(f"Valid: {result.get('isvalid', False)}")
print(f"Address: {result.get('address')}")
```

#### Estimate Fee

```python
# Estimate fee for target confirmation blocks
fee_estimate = rpc.estimate_fee(blocks=6)
print(f"Fee Estimate: {fee_estimate}")
```

#### Get Difficulty

```python
# Get current difficulty
difficulty = rpc.get_difficulty()
print(difficulty)
```

---

## Address Utilities

### Address Validation

```python
from tencoinlib.transaction import is_valid_address, get_address_type

address = "tc1q..."

# Check if address is valid
if is_valid_address(address):
    print("Address is valid")
    
    # Get address type
    addr_type = get_address_type(address)
    print(f"Address type: {addr_type}")
    # Possible values: "p2wpkh", "p2pkh", "p2sh", "p2wsh"
else:
    print("Address is invalid")
```

### Decode Address

```python
from tencoinlib.transaction import decode_address

address = "tc1q..."
addr_type, hash_bytes = decode_address(address)

print(f"Type: {addr_type}")
print(f"Hash: {hash_bytes.hex()}")
```

### Address to ScriptPubKey

```python
from tencoinlib.transaction import address_to_script

address = "tc1q..."
script_pubkey = address_to_script(address)
print(f"ScriptPubKey: {script_pubkey.hex()}")
```

### Supported Address Types

The library supports multiple address types:

- **P2WPKH** (tc1q...): SegWit version 0 pay-to-witness-public-key-hash
- **P2PKH**: Pay-to-public-key-hash (legacy)
- **P2SH**: Pay-to-script-hash
- **P2WSH**: Pay-to-witness-script-hash

**Note**: Wallet creation only generates P2WPKH addresses, but you can create transactions to/from any address type.

---

## Fee Management

### FeeCalculator

The `FeeCalculator` class provides methods for calculating transaction fees.

#### Estimate Transaction Size

```python
from tencoinlib.transaction import FeeCalculator

# Estimate size for SegWit transaction
size = FeeCalculator.estimate_size(
    num_inputs=2,
    num_outputs=2,
    has_segwit=True
)
print(f"Estimated size: {size} bytes")

# Estimate size for Legacy transaction
size = FeeCalculator.estimate_size(
    num_inputs=2,
    num_outputs=2,
    has_segwit=False
)
```

#### Calculate Fee

```python
# Calculate fee for transaction
fee = FeeCalculator.calculate_fee(
    num_inputs=2,
    num_outputs=2,
    fee_rate=20,          # Tenos per byte
    has_segwit=True
)
print(f"Fee: {fee} Tenos")

# Use default fee rate
fee = FeeCalculator.calculate_fee(
    num_inputs=1,
    num_outputs=1,
    has_segwit=True
)
```

#### Calculate Fee for Transaction Object

```python
from tencoinlib.transaction import Transaction

tx = Transaction(...)  # Your transaction
fee = FeeCalculator.calculate_fee_for_transaction(tx, fee_rate=20)
print(f"Fee: {fee} Tenos")
```

#### Recommended Fee Rates

```python
# Get recommended fee rates
rates = FeeCalculator.get_recommended_fee_rates()
print(f"Priority: {rates['priority']} Tenos/byte")
print(f"Normal: {rates['normal']} Tenos/byte")
print(f"Economy: {rates['economy']} Tenos/byte")
```

### Fee Constants

```python
from tencoinlib.transaction import FeeCalculator

FeeCalculator.DEFAULT_FEE_RATE    # 20 Tenos/byte
FeeCalculator.PRIORITY_FEE_RATE   # 50 Tenos/byte
FeeCalculator.ECONOMY_FEE_RATE    # 10 Tenos/byte
```

### Setting Fees in TransactionBuilder

```python
builder = TransactionBuilder()

# Use default fee rate (20 Tenos/byte)
builder.add_input(...)
builder.add_output(...)
tx, fee = builder.build()

# Set custom fee rate
builder.set_fee_rate(50)  # Higher fee for faster confirmation
tx, fee = builder.build()

# Use recommended rates
from tencoinlib.transaction import FeeCalculator
builder.set_fee_rate(FeeCalculator.PRIORITY_FEE_RATE)
```

---

## Key Management

### BIP-39 Mnemonic

```python
from tencoinlib.keys.bip39 import (
    generate_mnemonic,
    validate_mnemonic,
    mnemonic_to_seed,
    mnemonic_to_entropy
)

# Generate mnemonic
mnemonic = generate_mnemonic(strength=128)  # 12 words
print(mnemonic)

# Validate mnemonic
if validate_mnemonic(mnemonic):
    print("Valid mnemonic")

# Convert mnemonic to seed
seed = mnemonic_to_seed(mnemonic, passphrase="")

# Convert mnemonic to entropy
entropy = mnemonic_to_entropy(mnemonic)
```

### BIP-32 Key Derivation & Extended Keys

Low-level BIP-32 helpers are available if you need direct access to extended keys:

```python
from tencoinlib.keys.bip32 import (
    ExtendedPrivateKey,
    ExtendedPublicKey,
    derive_path_from_seed,
)

seed = b"..."  # 64-byte seed
path = "m/84'/5353'/0'/0/0"

# Derive raw key + chain code from seed
private_key, chain_code = derive_path_from_seed(seed, path)

# Create master extended private key from seed
master_xprv = ExtendedPrivateKey.from_seed(seed)
master_xprv_str = master_xprv.to_xprv()
master_xpub_str = master_xprv.to_public().to_xpub()

# Derive account-level xprv/xpub (e.g., m/84'/5353'/0')
account_xprv = master_xprv.derive_path("m/84'/5353'/0'")
account_xpub = account_xprv.to_public()

print(account_xprv.to_xprv())
print(account_xpub.to_xpub())
```

### BIP-84 Address Derivation

```python
from tencoinlib.keys.bip84 import (
    derive_bip84_address_from_seed,
    public_key_to_segwit_v0
)

seed = b"..."  # 64-byte seed

# Derive address
private_key, address = derive_bip84_address_from_seed(
    seed,
    account=0,
    change=0,
    index=0
)

# Convert public key to SegWit address
from tencoinlib.keys.ec import privkey_to_pubkey
public_key = privkey_to_pubkey(private_key, compressed=True)
address = public_key_to_segwit_v0(public_key)
```

### EC Operations

```python
from tencoinlib.keys.ec import (
    privkey_to_pubkey,
    sign,
    verify
)

private_key = bytes.fromhex("...")

# Get public key
public_key = privkey_to_pubkey(private_key, compressed=True)

# Sign message hash
msg_hash = b"..."  # 32-byte hash
signature = sign(private_key, msg_hash)

# Verify signature
is_valid = verify(public_key, msg_hash, signature)
```

---

## Complete Examples

### Example 1: Complete Wallet Setup

```python
from tencoinlib import Wallet
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC

# Create or recover wallet
mnemonic = input("Enter mnemonic (or press Enter to create new): ")
if mnemonic:
    wallet = Wallet.recover(mnemonic)
else:
    wallet = Wallet.create()
    print(f"\n⚠️  IMPORTANT: Save this mnemonic phrase!")
    print(f"Mnemonic: {wallet.get_mnemonic()}\n")

# Connect to node
rpc = RPCClient(host="127.0.0.1", port=10111, token="your-token")

# Get balance
address = wallet.get_address()
balance_tenos = rpc.get_balance(address)
balance_tec = balance_tenos / TENOS_PER_TEC

print(f"\nWallet Information:")
print(f"Address: {address}")
print(f"Balance: {balance_tec:.8f} TEC")
print(f"Balance: {balance_tenos} Tenos")

# Show UTXOs
utxos = rpc.list_unspent(address)
print(f"\nUnspent Outputs: {len(utxos)}")
for utxo in utxos:
    print(f"  {utxo['amount']} Tenos from {utxo['txid'][:16]}...")
```

### Example 2: Complete Send Transaction

```python
from tencoinlib import Wallet, TransactionBuilder, TransactionSigner
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC
from tencoinlib.transaction.address import address_to_script

# Setup
wallet = Wallet.recover("your mnemonic phrase")
rpc = RPCClient(host="127.0.0.1", port=10111, token="your-token")
sender_address = wallet.get_address()

# Get recipient address and amount
recipient_address = input("Recipient address: ")
amount_tec = float(input("Amount (TEC): "))
amount_tenos = int(amount_tec * TENOS_PER_TEC)

# Get UTXOs
utxos = rpc.list_unspent(sender_address)
if not utxos:
    print("No UTXOs available!")
    exit(1)

# Calculate total available
total_available = sum(u["amount"] for u in utxos)
print(f"\nAvailable: {total_available / TENOS_PER_TEC:.8f} TEC")

# Build transaction
builder = TransactionBuilder()

# Add all UTXOs
for utxo in utxos:
    builder.add_input(
        txid=utxo["txid"],
        vout=utxo["vout"],
        value=utxo["amount"],
        script_pubkey=bytes.fromhex(utxo["scriptPubKey"])
    )

# Add output (supports SegWit, P2PKH, or P2SH addresses)
builder.add_output(recipient_address, amount_tenos)

# Set change address
builder.set_change_address(sender_address)

# Set fee rate
builder.set_fee_rate(20)

# Get summary
summary = builder.get_summary()
print(f"\nTransaction Summary:")
print(f"  Inputs: {summary['inputs_count']}")
print(f"  Outputs: {summary['outputs_count']}")
print(f"  Total Input: {summary['total_input'] / TENOS_PER_TEC:.8f} TEC")
print(f"  Total Output: {summary['total_output'] / TENOS_PER_TEC:.8f} TEC")
print(f"  Estimated Fee: {summary['fee'] / TENOS_PER_TEC:.8f} TEC")

# Check sufficient funds
total_needed = amount_tenos + summary['fee']
if total_available < total_needed:
    print(f"\n❌ Insufficient funds!")
    print(f"  Need: {total_needed / TENOS_PER_TEC:.8f} TEC")
    print(f"  Have: {total_available / TENOS_PER_TEC:.8f} TEC")
    exit(1)

# Build transaction
tx, actual_fee = builder.build()
print(f"\n  Actual Fee: {actual_fee / TENOS_PER_TEC:.8f} TEC")
if summary['has_change']:
    print(f"  Change: {summary['change_amount'] / TENOS_PER_TEC:.8f} TEC")

# Prepare for signing
utxo_data = []
private_keys = []

for utxo in utxos:
    utxo_data.append({
        "value": utxo["amount"],
        "script_pubkey": bytes.fromhex(utxo["scriptPubKey"]),
        "address": sender_address  # TransactionSigner detects address type automatically
    })
    private_keys.append(bytes.fromhex(wallet.get_private_key_hex()))

# Sign transaction (supports SegWit, P2PKH, and P2SH automatically)
print("\nSigning transaction...")
signed_tx = TransactionSigner.sign_transaction(tx, utxo_data, private_keys)

# Verify
print(f"Transaction ID: {signed_tx.txid()}")
print(f"Size: {signed_tx.calculate_size()} bytes")
print(f"Virtual Size: {signed_tx.calculate_vsize()} bytes")

# Confirm before sending
confirm = input("\nSend transaction? (yes/no): ")
if confirm.lower() != "yes":
    print("Transaction cancelled")
    exit(0)

# Broadcast
print("\nBroadcasting transaction...")
tx_hex = signed_tx.serialize().hex()
txid = rpc.send_raw_transaction(tx_hex)

print(f"\n✅ Transaction sent successfully!")
print(f"TXID: {txid}")
print(f"View on block explorer: https://explorer.tencoin.org/tx/{txid}")
```

### Example 3: Transaction History

```python
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC

rpc = RPCClient(host="127.0.0.1", port=10111, token="your-token")
address = "tc1q..."

# Get UTXOs (received transactions)
utxos = rpc.list_unspent(address)

print(f"Transaction History for {address}\n")
print(f"Unspent Outputs: {len(utxos)}\n")

for i, utxo in enumerate(utxos, 1):
    tx_info = rpc.get_transaction(utxo["txid"])
    
    print(f"Transaction {i}:")
    print(f"  TXID: {utxo['txid']}")
    print(f"  Amount: {utxo['amount'] / TENOS_PER_TEC:.8f} TEC")
    print(f"  Confirmations: {utxo.get('confirmations', 0)}")
    print(f"  Block Height: {tx_info.get('blockheight', 'Pending')}")
    print("---")
```

### Example 4: Multi-Address Wallet

```python
from tencoinlib import Wallet

wallet = Wallet.recover("your mnemonic phrase")

# Generate receiving addresses
print("Receiving Addresses:")
for i in range(10):
    priv, addr = wallet.derive_address(account=0, change=0, index=i)
    print(f"  {i:2d}: {addr}")

print("\nChange Addresses:")
for i in range(5):
    priv, addr = wallet.derive_address(account=0, change=1, index=i)
    print(f"  {i:2d}: {addr}")

# Get next unused address
priv, next_addr = wallet.get_next_address(change=0)
print(f"\nNext Receiving Address: {next_addr}")
```

---

## API Reference

### Wallet Class

#### Class Methods

**`Wallet.create(strength: int = 128) -> Wallet`**
- Create a new HD wallet from a freshly generated BIP-39 mnemonic
- **Parameters**: `strength` - Entropy strength in bits (128, 160, 192, 224, 256)
- **Returns**: New `Wallet` instance

**`Wallet.recover(mnemonic: str, passphrase: str = "") -> Wallet`**
- Recover wallet from mnemonic phrase
- **Parameters**: 
  - `mnemonic` - BIP-39 mnemonic phrase
  - `passphrase` - Optional BIP-39 passphrase
- **Returns**: Recovered `Wallet` instance
- **Raises**: `WalletError` if mnemonic is invalid

**`Wallet.from_xpub(xpub: str) -> Wallet`**
- Create a **watch-only** wallet from a master/account xpub
- Can derive addresses via `derive_address_from_xpub`, but has no access to private keys or seed

**`Wallet.from_xprv(xprv: str) -> Wallet`**
- Create a wallet from a master/account xprv
- Full private derivation is available, but no mnemonic/seed is required

**`Wallet.load_from_file(filepath: str, password: Optional[str] = None) -> Wallet`**
- Load wallet from file
- **Parameters**: 
  - `filepath` - Path to wallet file
  - `password` - Encryption password (not yet implemented)
- **Returns**: `Wallet` instance

#### Instance Methods

**`get_address(type: str = "p2wpkh", script: Optional[bytes] = None) -> str`**
- Get address for the current key in the requested form
- **Parameters**:
  - `type`: One of "p2wpkh" (default), "p2pkh", "p2sh", "p2wsh"
  - `script`: For "p2sh" (optional) or "p2wsh" (required), the redeem/witness script bytes
- **Returns**: Address string (tc1q..., T..., or M...)
- **Example**: `wallet.get_address("p2pkh")` → T..., `wallet.get_address("p2wsh", script=witness_script)` → tc1q...

**`get_private_key_hex() -> str`**
- Get private key as hex string for the default address
- **Raises**: `WalletError` in watch-only wallets

**`get_public_key_hex() -> str`**
- Get public key as hex string (compressed) for the default address

**`get_mnemonic() -> str`**
- Get mnemonic phrase (if available)
- **Raises**: `WalletError` if mnemonic not available

**`get_master_xprv() -> str`**
- Get master xprv (`m`) as Base58Check string (non-watch-only wallets only)

**`get_master_xpub() -> str`**
- Get master xpub (`m`) as Base58Check string

**`derive_xprv(path: str) -> str`**
- Derive extended private key at a BIP-32 path such as `"m/84'/5353'/0'"` (non-watch-only only)

**`derive_xpub(path: str) -> str`**
- Derive extended public key at a BIP-32 path
- From full wallets: supports hardened + non-hardened paths
- From watch-only (xpub-only) wallets: only non-hardened paths are allowed

**`get_account_xprv(account: int) -> str`**
- Get account-level xprv at `m/84'/5353'/account'` (non-watch-only only)

**`get_account_xpub(account: int) -> str`**
- Get account-level xpub at `m/84'/5353'/account'`

**`derive_address(account: int = 0, change: int = 0, index: int = 0) -> Tuple[str, str]`**
- Derive address at specific BIP-84 path from the seed
- **Returns**: `(private_key_hex, address)`
- **Raises**: `WalletError` in watch-only wallets

**`get_next_address(change: int = 0) -> Tuple[str, str]`**
- Get next unused address in sequence for the current account
- **Returns**: `(private_key_hex, address)`
- **Raises**: `WalletError` in watch-only wallets

**`derive_address_from_xpub(change: int, index: int) -> str`**
- Derive an address from the wallet's base xpub (watch-only or full)
- For BIP-84 account xpubs, this corresponds to `m/84'/5353'/account'/change/index`

**`export_xpub(path: str) -> str`**
- Export an xpub at an arbitrary BIP-32 path (wrapper around `derive_xpub`)

**`export_xprv(path: str) -> str`**
- Export an xprv at an arbitrary BIP-32 path (non-watch-only only; wrapper around `derive_xprv`)

**`import_xpub(xpub: str) -> None`**
- Import an external xpub and treat it as the wallet's base xpub for watch-only derivation

**`import_xprv(xprv: str) -> None`**
- Import an external xprv and treat it as the wallet's base xprv/xpub

**`to_dict() -> Dict`**
- Convert wallet to dictionary, including `is_watch_only` and imported xpub/xprv metadata

**`save_to_file(filepath: str, password: Optional[str] = None)`**
- Save wallet to file (unencrypted JSON; encryption not yet implemented)

### TransactionBuilder Class

#### Methods

**`add_input(txid: str, vout: int, value: int, script_pubkey: bytes, sequence: int = 0xffffffff) -> TransactionBuilder`**
- Add transaction input (UTXO)
- **Returns**: Self for method chaining
- **Raises**: `TransactionBuilderError` if invalid

**`add_output(address: str, amount: int) -> TransactionBuilder`**
- Add transaction output
- **Returns**: Self for method chaining
- **Raises**: `TransactionBuilderError` if amount below dust limit

**`set_change_address(address: str) -> TransactionBuilder`**
- Set change address
- **Returns**: Self for method chaining

**`set_fee_rate(fee_rate: int) -> TransactionBuilder`**
- Set custom fee rate (Tenos per byte)
- **Returns**: Self for method chaining

**`set_segwit(use_segwit: bool) -> TransactionBuilder`**
- Set whether to use SegWit inputs
- **Returns**: Self for method chaining

**`set_locktime(locktime: int) -> TransactionBuilder`**
- Set transaction locktime
- **Returns**: Self for method chaining

**`build() -> Tuple[Transaction, int]`**
- Build the transaction
- **Returns**: `(transaction, actual_fee)`
- **Raises**: `TransactionBuilderError` if build fails

**`build_raw() -> Tuple[str, int]`**
- Build transaction and return raw hex
- **Returns**: `(raw_hex, fee)`

**`get_summary() -> Dict[str, Any]`**
- Get transaction summary

**`calculate_total_input() -> int`**
- Calculate total input amount in Tenos

**`calculate_total_output(include_change: bool = False) -> int`**
- Calculate total output amount in Tenos

**`calculate_fee(include_change: bool = True) -> int`**
- Calculate estimated fee in Tenos

**`calculate_change() -> Tuple[int, bool]`**
- Calculate change amount
- **Returns**: `(change_amount, has_change)`

**`clear() -> TransactionBuilder`**
- Clear all inputs and outputs
- **Returns**: Self for method chaining

**`copy() -> TransactionBuilder`**
- Create a copy of this builder

### TransactionSigner Class

Universal transaction signer that automatically detects address types and uses the appropriate signing method.

#### Static Methods

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: List[bytes]) -> Transaction`**
- Sign a transaction with mixed input types (SegWit and Legacy)
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries with `value`, `script_pubkey`, `address`, and optionally `redeem_script` (for P2SH)
  - `private_keys` - List of private keys (32 bytes each)
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails
- **Supported Address Types**: P2WPKH (tc1q...), P2PKH (T...), P2SH (M...)

### LegacySigner Class

Legacy transaction signer for P2PKH and P2SH addresses.

#### Static Methods

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: List[bytes]) -> Transaction`**
- Sign a complete transaction with Legacy inputs (P2PKH or P2SH)
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries with `value`, `script_pubkey`, `address`, and optionally `redeem_script` (for P2SH)
  - `private_keys` - List of private keys (32 bytes each)
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails

**`sign_p2pkh_input(tx: Transaction, input_index: int, private_key: bytes, script_pubkey: bytes, sighash_type: int = 1)`**
- Sign a P2PKH input
- **Parameters**:
  - `tx` - Transaction (will be modified)
  - `input_index` - Input index to sign
  - `private_key` - 32-byte private key
  - `script_pubkey` - ScriptPubKey of the UTXO (P2PKH script)
  - `sighash_type` - SIGHASH type (default: SIGHASH_ALL = 1)

**`sign_p2sh_input(tx: Transaction, input_index: int, private_key: bytes, redeem_script: bytes, script_pubkey: bytes, sighash_type: int = 1)`**
- Sign a P2SH input (single-sig P2SH, e.g. P2SH-wrapped P2PKH)
- **Parameters**:
  - `tx` - Transaction (will be modified)
  - `input_index` - Input index to sign
  - `private_key` - 32-byte private key
  - `redeem_script` - Redeem script (e.g. P2PKH script)
  - `script_pubkey` - ScriptPubKey of the UTXO (P2SH script)
  - `sighash_type` - SIGHASH type (default: SIGHASH_ALL = 1)

**`legacy_digest(tx: Transaction, input_index: int, script_sig: bytes, sighash_type: int = 1) -> bytes`**
- Calculate legacy transaction digest (pre-SegWit)
- **Returns**: 32-byte digest

### SegWitSigner Class

SegWit transaction signer (BIP-143) for P2WPKH addresses.

#### Static Methods

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: List[bytes]) -> Transaction`**
- Sign a complete transaction with SegWit inputs
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries (must be P2WPKH addresses)
  - `private_keys` - List of private keys (32 bytes each)
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails

**`sign_input(tx: Transaction, input_index: int, utxo: dict, private_key: bytes)`**
- Sign a single SegWit input
- **Parameters**:
  - `tx` - Transaction (will be modified)
  - `input_index` - Input index to sign
  - `utxo` - UTXO dictionary
  - `private_key` - 32-byte private key

**`create_witness_signature(tx: Transaction, input_index: int, private_key: bytes, script_code: bytes, value: int, sighash_type: int = 1) -> bytes`**
- Create witness signature for SegWit input
- **Returns**: DER-encoded signature with sighash byte

**`verify_witness(tx: Transaction, input_index: int, public_key: bytes, script_code: bytes, value: int, witness: List[bytes]) -> bool`**
- Verify witness signature

### RPCClient Class

#### Constructor

**`RPCClient(host: str = "127.0.0.1", port: int = 10111, token: str = "", timeout: int = 30, use_ssl: bool = False)`**
- Initialize RPC client
- Tests connection on initialization

#### Wallet Methods

- `get_balance(address: str) -> int`
- `list_unspent(address: str, minconf: int = 1) -> List[Dict]`

#### Transaction Methods

- `send_raw_transaction(tx_hex: str) -> str`
- `test_mempool_accept(tx_hex: str) -> Dict`
- `get_transaction(txid: str) -> Dict`
- `get_raw_transaction(txid: str) -> str`
- `decode_raw_transaction(tx_hex: str) -> Dict`

#### Blockchain Methods

- `get_block_count() -> int`
- `get_best_block_hash() -> str`
- `get_block(block_hash: str = None, height: int = None) -> Dict`
- `get_block_header(block_hash: str) -> Dict`
- `get_blockchain_info() -> Dict`
- `get_mempool_info() -> Dict`
- `get_raw_mempool() -> Dict`

#### Network Methods

- `get_peer_info() -> List[Dict]`
- `get_network_info() -> Dict`

#### Mining Methods

- `get_work() -> Dict`
- `submit_block(block_hex: str) -> Dict`

#### Utility Methods

- `validate_address(address: str) -> Dict`
- `estimate_fee(blocks: int = 6) -> Dict`
- `get_difficulty() -> Dict`

### Script Building Functions

#### build_p2pkh_script

**`build_p2pkh_script(pubkey: bytes) -> bytes`**
- Build P2PKH redeem script: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
- **Parameters**: `pubkey` - 33-byte compressed public key
- **Returns**: Redeem script bytes

#### build_multisig_script

**`build_multisig_script(m: int, pubkeys: List[bytes], sort_pubkeys: bool = True) -> bytes`**
- Build m-of-n multisig redeem/witness script (standard form)
- **Parameters**:
  - `m` - Required signatures (1..16)
  - `pubkeys` - List of 33-byte compressed public keys (n = len(pubkeys), 1..16)
  - `sort_pubkeys` - If True, sort pubkeys for canonical form (recommended)
- **Returns**: Script bytes (use with `script_to_p2sh_address` or `script_to_p2wsh_address`)

#### script_to_p2sh_address

**`script_to_p2sh_address(script: bytes, version: int = P2SH_VERSION) -> str`**
- Encode a redeem script as P2SH address (M...)
- **Parameters**:
  - `script` - Redeem script bytes
  - `version` - P2SH version byte (default mainnet 0x32)
- **Returns**: Base58Check P2SH address

#### script_to_p2wsh_address

**`script_to_p2wsh_address(script: bytes, hrp: str = MAINNET_HRP) -> str`**
- Encode a witness script as P2WSH (SegWit v0) address (tc1q... with 32-byte program)
- **Parameters**:
  - `script` - Witness script bytes (e.g. multisig script)
  - `hrp` - Bech32 HRP (default mainnet "tc")
- **Returns**: Bech32 P2WSH address

#### pubkey_to_p2pkh_address

**`pubkey_to_p2pkh_address(pubkey: bytes, version: int = P2PKH_VERSION) -> str`**
- Convert public key to P2PKH address (T...)
- **Parameters**:
  - `pubkey` - 33-byte compressed public key
  - `version` - P2PKH version byte (default mainnet 0x41)
- **Returns**: Base58Check P2PKH address

#### pubkey_to_p2sh_p2pkh_address

**`pubkey_to_p2sh_p2pkh_address(pubkey: bytes, version: int = P2SH_VERSION) -> str`**
- Build P2SH address that pays to P2PKH redeem script (single-sig P2SH, M...)
- **Parameters**:
  - `pubkey` - 33-byte compressed public key
  - `version` - P2SH version byte (default mainnet 0x32)
- **Returns**: Base58Check P2SH address

#### Wallet.build_multisig_script (Static Method)

**`Wallet.build_multisig_script(m: int, pubkeys: List[Union[bytes, str]], sort_pubkeys: bool = True) -> bytes`**
- Build standard m-of-n multisig redeem/witness script (convenience method)
- **Parameters**:
  - `m` - Required signatures (1..16)
  - `pubkeys` - List of 33-byte compressed public keys (bytes or hex strings)
  - `sort_pubkeys` - If True, sort pubkeys for canonical form (recommended)
- **Returns**: Script bytes to pass to `get_address("p2sh", script=...)` or `get_address("p2wsh", script=...)`

---

## Error Handling

### Exception Classes

```python
from tencoinlib import WalletError
from tencoinlib.transaction import (
    TransactionBuilderError,
    SigningError,
    AddressError
)
from tencoinlib.rpc import (
    RPCError,
    ConnectionError,
    AuthenticationError,
    TimeoutError,
    ResponseError,
    InvalidMethodError
)
```

### Wallet Errors

```python
from tencoinlib import Wallet, WalletError

try:
    wallet = Wallet.recover("invalid mnemonic")
except WalletError as e:
    print(f"Wallet error: {e}")
```

### Transaction Errors

```python
from tencoinlib.transaction import (
    TransactionBuilder,
    TransactionBuilderError,
    AddressError
)

try:
    builder = TransactionBuilder()
    builder.add_output("invalid-address", 1000)
except AddressError:
    print("Invalid address")
except TransactionBuilderError as e:
    print(f"Transaction builder error: {e}")
```

### Signing Errors

```python
from tencoinlib import TransactionSigner, LegacySigner, SegWitSigner, SigningError

# Universal signer (recommended)
try:
    signed_tx = TransactionSigner.sign_transaction(tx, utxos, keys)
except SigningError as e:
    print(f"Signing error: {e}")

# Legacy signer
try:
    signed_tx = LegacySigner.sign_transaction(tx, utxos, keys)
except SigningError as e:
    print(f"Legacy signing error: {e}")

# SegWit signer
try:
    signed_tx = SegWitSigner.sign_transaction(tx, utxos, keys)
except SigningError as e:
    print(f"SegWit signing error: {e}")
```

### RPC Errors

```python
from tencoinlib.rpc import (
    RPCClient,
    ConnectionError,
    AuthenticationError,
    TimeoutError,
    ResponseError
)

try:
    rpc = RPCClient(host="invalid", port=10111)
except ConnectionError as e:
    print(f"Connection error: {e}")

try:
    balance = rpc.get_balance("tc1q...")
except AuthenticationError:
    print("Authentication failed")
except TimeoutError:
    print("Request timeout")
except ResponseError as e:
    print(f"Response error: {e}")
except RPCError as e:
    print(f"RPC error: {e}")
```

---

## Constants and Configuration

### Main Constants

```python
from tencoinlib import (
    MAINNET_HRP,           # "tc" - Human Readable Part for Bech32
    TENOS_PER_TEC,         # 100000000 - Number of Tenos in one TEC
    DUST_LIMIT,            # 546 - Minimum spendable amount
    DEFAULT_RPC_PORT,      # 10111 - Default RPC port
    DEFAULT_RPC_TOKEN,     # "" - Default RPC token
    COIN_TYPE,             # 5353 - Coin type for BIP-44-style paths
    DERIVATION_PATH        # "m/84'/5353'/0'/0/0" - Default BIP-84 (P2WPKH) derivation path
)
```

### Fee Constants

```python
from tencoinlib.transaction import FeeCalculator

FeeCalculator.DEFAULT_FEE_RATE    # 20 Tenos/byte
FeeCalculator.PRIORITY_FEE_RATE   # 50 Tenos/byte
FeeCalculator.ECONOMY_FEE_RATE    # 10 Tenos/byte
```

### Address Constants

```python
from tencoinlib.constants import (
    P2PKH_VERSION,    # 0x41 - Address version for P2PKH (legacy 'T...' addresses)
    P2SH_VERSION,     # 0x32 - Address version for P2SH (legacy 'M...' addresses)
    P2WPKH_VERSION    # 0     - Witness version for P2WPKH (SegWit 'tc1q...' addresses)
)
```

---

## Best Practices

### Security

1. **Never share private keys or mnemonics**
   - Store mnemonics securely (offline, encrypted)
   - Never commit private keys to version control

2. **Use passphrases for additional security**
   ```python
   wallet = Wallet.recover(mnemonic, passphrase="strong-passphrase")
   ```

3. **Validate addresses before sending**
   ```python
   from tencoinlib.transaction import is_valid_address
   if not is_valid_address(recipient_address):
       raise ValueError("Invalid recipient address")
   ```

4. **Double-check transaction details**
   - Always verify recipient address
   - Confirm amount before broadcasting
   - Check fee is reasonable

5. **Use change addresses**
   - Always set a change address to protect privacy
   - Use new change addresses for each transaction

### Performance

1. **Use SegWit**
   - SegWit transactions have lower fees
   - Faster confirmation times
   - Smaller transaction size

2. **Manage UTXOs efficiently**
   - Consolidate small UTXOs periodically
   - Too many small UTXOs increase fees

3. **Optimize fee rates**
   - Use appropriate fee rate for your needs
   - Priority: Fast confirmation (higher fee)
   - Normal: Standard confirmation (default fee)
   - Economy: Slow confirmation (lower fee)

### Transaction Building

1. **Check sufficient funds before building**
   ```python
   total_needed = amount + estimated_fee
   if total_available < total_needed:
       raise ValueError("Insufficient funds")
   ```

2. **Handle dust outputs**
   - Change below dust limit is added to fee
   - Minimum output: 546 Tenos

3. **Use transaction summary**
   ```python
   summary = builder.get_summary()
   # Review before building
   ```

4. **Test transactions first**
   ```python
   # Test before broadcasting
   result = rpc.test_mempool_accept(tx_hex)
   if result.get("allowed"):
       txid = rpc.send_raw_transaction(tx_hex)
   ```

### Error Handling

1. **Always use try/except blocks**
   ```python
   try:
       wallet = Wallet.recover(mnemonic)
   except WalletError as e:
       # Handle error appropriately
       pass
   ```

2. **Check connection before RPC calls**
   ```python
   try:
       rpc = RPCClient(...)
       balance = rpc.get_balance(address)
   except ConnectionError:
       # Handle connection issue
       pass
   ```

### Code Organization

1. **Separate concerns**
   - Wallet management
   - Transaction building
   - RPC interaction

2. **Reuse transaction builders**
   ```python
   builder = TransactionBuilder()
   # Reuse for multiple transactions
   builder.clear()
   ```

3. **Cache RPC results when appropriate**
   - Balance queries
   - UTXO lists (for short periods)

---
