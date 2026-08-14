# Tencoinlib Documentation

Complete and comprehensive documentation for the Tencoinlib Python library.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Wallet](#wallet)
5. [Wallet Storage](#wallet-storage)
6. [Transactions](#transactions)
7. [RPC Client](#rpc-client)
8. [Address Utilities](#address-utilities)
9. [Fee Management](#fee-management)
   - [Setting Fees in TransactionBuilder](#setting-fees-in-transactionbuilder)
   - [set_fee_rate — Rate-Based Fee](#set_fee_rate--rate-based-fee)
   - [set_fee — Fixed Exact Fee](#set_fee--fixed-exact-fee)
10. [OP_RETURN Outputs](#op_return-outputs)
10. [Key Management](#key-management)
11. [Transaction Signing](#transaction-signing)
12. [Multisig Transactions](#multisig-transactions)
13. [Message Signing](#message-signing)
14. [Complete Examples](#complete-examples)
15. [API Reference](#api-reference)
16. [Error Handling](#error-handling)
17. [Constants and Configuration](#constants-and-configuration)
18. [Best Practices](#best-practices)

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
- ✅ **Transaction Signing**: Automatic detection and signing for SegWit (BIP-143), Legacy (P2PKH/P2SH), and Multisig (P2SH/P2WSH, any m-of-n up to 15-of-15) inputs
- ✅ **Message Signing**: Bitcoin Core–compatible message signing and verification with public key recovery
- ✅ **Key Derivation**: Standard BIP-84 derivation path `m/84'/5353'/0'/0/0` + generic BIP-32 paths
- ✅ **Mnemonic Phrases**: 12, 15, 18, 21, or 24 word English mnemonics
- ✅ **Wallet Recovery**: Restore wallets from mnemonic phrases
- ✅ **Encrypted Wallet Storage**: TCW v1 binary format with AES-256-GCM encryption and Argon2id key derivation
- ✅ **Locked/Unlocked State Machine**: Secret material only in RAM when needed; explicit lock/unlock lifecycle
- ✅ **Transaction Building**: Create and sign transactions with all address types
- ✅ **RPC Client**: Connect to Tencoin nodes via JSON-RPC
- ✅ **Fee Calculation**: Automatic fee estimation and management
  - Rate-based (`set_fee_rate`) and exact fixed-fee (`set_fee`) modes
  - Unit-aware: accepts TEC (float) or Teno (int), case-insensitive
- ✅ **OP_RETURN Outputs**: Embed arbitrary metadata (text, hashes, bytes) on-chain
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
- `coincurve>=13.0.0` - For message signing and public key recovery
- `cryptography>=41.0.0` - For AES-256-GCM wallet encryption
- `argon2-cffi>=21.3.0` - For Argon2id key derivation

---

## Quick Start

### Create a New Wallet

```python
from tencoinlib import Wallet

# Create a new wallet with 12-word mnemonic (returned UNLOCKED)
wallet = Wallet.create()

print(f"Mnemonic: {wallet.get_mnemonic()}")
print(f"Address:  {wallet.get_address()}")

# Save to an encrypted .tcw file
wallet.save("my_wallet.tcw", password="my-strong-password")
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

# Load and unlock wallet from encrypted file
wallet = Wallet.load("my_wallet.tcw").unlock("my-strong-password")
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

### Wallet Storage

Wallets are saved as **TCW v1** (TenCoin Wallet) encrypted binary files. Every `.tcw` file on disk is always encrypted — there is no plaintext save option.

#### TCW v1 Format

The `.tcw` file uses a binary container with the following structure:

```
┌──────────────────────────────┐
│ Magic + Version   4 bytes    │  b"TCW" + 0x01
│ KDF / Cipher IDs  2 bytes    │  Argon2id / AES-256-GCM
│ Flags, lengths    6 bytes    │
│ Payload length    8 bytes    │
├──────────────────────────────┤
│ Salt             32 bytes    │  random, stored in file
│ KDF parameters    4 bytes    │  time/memory/parallelism
│ Nonce            12 bytes    │  random, unique per save
├──────────────────────────────┤
│ Encrypted payload            │  AES-256-GCM ciphertext
│ + GCM tag        16 bytes    │  authentication tag
└──────────────────────────────┘
```

The fixed header is used as **AAD** (Additional Authenticated Data), meaning any tampering with the header — including version, algorithm IDs, or length fields — causes decryption to fail.

#### Save Wallet

The wallet must be **unlocked** to save (secrets need to be in RAM).

```python
# Create a new wallet (returned UNLOCKED)
wallet = Wallet.create()

# Save to encrypted .tcw file
wallet.save("my_wallet.tcw", password="my-strong-password")

# save_to_file() is an alias
wallet.save_to_file("my_wallet.tcw", password="my-strong-password")
```

#### Load Wallet (Locked)

`Wallet.load()` reads only the file header — no decryption, no secrets in RAM.

```python
# Load header only — wallet is LOCKED
wallet = Wallet.load("my_wallet.tcw")

print(wallet.is_locked)   # True
print(wallet.address)     # available (empty until unlocked)
```

#### Unlock Wallet

```python
wallet = Wallet.load("my_wallet.tcw")
wallet.unlock("my-strong-password")

print(wallet.is_locked)              # False
print(wallet.get_mnemonic())         # available
print(wallet.get_private_key_hex())  # available
```

#### Load and Unlock (one-liner)

```python
# Equivalent to Wallet.load(path).unlock(password)
wallet = Wallet.load_from_file("my_wallet.tcw", password="my-strong-password")
```

#### Lock Wallet

Call `lock()` to discard all secret material from RAM. Public metadata (address, indices) is preserved.

```python
wallet.unlock("my-strong-password")
# ... do work ...
wallet.lock()

print(wallet.is_locked)   # True
# wallet.get_mnemonic()   → raises WalletLockedError
```

#### Context Manager (Auto-lock)

The `unlocked()` context manager unlocks the wallet, yields it, then automatically locks on exit — even if an exception occurs.

```python
with wallet.unlocked("my-strong-password") as w:
    signed_tx = w.sign_transaction(tx)
    mnemonic  = w.get_mnemonic()

# wallet is locked again here
print(wallet.is_locked)   # True
```

#### Checking Wallet State

```python
print(wallet.is_locked)    # True / False
print(wallet.wallet_type)  # "hd" | "xpub" | "xprv"
print(wallet.is_watch_only)
```

#### Wrong Password

```python
from tencoinlib import WalletAuthError

try:
    wallet.unlock("wrong-password")
except WalletAuthError:
    print("Wrong password or corrupted file")
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
print(f"Inputs:           {summary['inputs_count']}")
print(f"Outputs:          {summary['outputs_count']}")   # spendable + OP_RETURN + change
print(f"OP_RETURN count:  {summary['op_return_count']}")
print(f"Total Input:      {summary['total_input']} Tenos")
print(f"Total Output:     {summary['total_output']} Tenos")
print(f"Estimated Fee:    {summary['fee']} Tenos")
print(f"Fixed Fee:        {summary['fixed_fee']}")       # None if rate-based
print(f"Fee Rate:         {summary['fee_rate']} Tenos/byte")
print(f"Change Amount:    {summary['change_amount']} Tenos")
print(f"Has Change:       {summary['has_change']}")
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

## Multisig Transactions

Multisig (multi-signature) transactions require M-of-N participants to sign before funds can be spent. Tencoinlib supports two multisig address types:

- **P2SH multisig** (`M...`): Legacy multisig — redeem script is revealed at spend time.
- **P2WSH multisig** (`tc1q...`): Native SegWit multisig — lower fees, same security model.

Both types support any m-of-n combination from 1-of-1 up to 15-of-15.

### Overview

| Type | Address | Script committed at creation | Signing overhead |
|---|---|---|---|
| P2SH multisig | `M...` | Hash of redeem script | scriptSig |
| P2WSH multisig | `tc1q...` | Hash of witness script | Witness |

### Key Concepts

**Redeem script / Witness script**: The raw multisig script that encodes M, N, and all N public keys. For P2SH this is called the redeem script; for P2WSH it is called the witness script. Both are built with `build_multisig_script()`.

**Script hash**: The on-chain address stores only the hash of this script. The full script must be provided again at spend time.

**Canonical pubkey ordering**: Passing `sort_pubkeys=True` (the default) sorts the public keys lexicographically before embedding them in the script. All participants must use the same ordering, so always sort or always preserve insertion order — never mix.

---

### Building a Multisig Address

#### P2SH Multisig Address (M...)

```python
from tencoinlib.transaction import build_multisig_script, script_to_p2sh_address

# Compressed public keys from each participant (33 bytes each)
pubkeys = [
    bytes.fromhex("02a1b2c3d4e5f6..."),   # Participant 1
    bytes.fromhex("03d4e5f6a1b2c3..."),   # Participant 2
    bytes.fromhex("0298a7b8c9d0e1..."),   # Participant 3
]

# Build 2-of-3 multisig redeem script
redeem_script = build_multisig_script(m=2, pubkeys=pubkeys, sort_pubkeys=True)
print(f"Redeem script ({len(redeem_script)} bytes): {redeem_script.hex()}")

# Derive P2SH address from the redeem script
p2sh_address = script_to_p2sh_address(redeem_script)
print(f"P2SH multisig address: {p2sh_address}")   # M...

# Save the redeem script — you need it to spend funds later
```

#### P2WSH Multisig Address (tc1q...)

```python
from tencoinlib.transaction import build_multisig_script, script_to_p2wsh_address

pubkeys = [
    bytes.fromhex("02a1b2c3d4e5f6..."),
    bytes.fromhex("03d4e5f6a1b2c3..."),
    bytes.fromhex("0298a7b8c9d0e1..."),
]

# Build 2-of-3 multisig witness script (identical call — same function)
witness_script = build_multisig_script(m=2, pubkeys=pubkeys, sort_pubkeys=True)

# Derive P2WSH address (SegWit native — lower fees)
p2wsh_address = script_to_p2wsh_address(witness_script)
print(f"P2WSH multisig address: {p2wsh_address}")  # tc1q...

# Save the witness script — you need it to spend funds later
```

#### Using Wallet.build_multisig_script()

The `Wallet` class provides a convenience static method that also accepts hex strings:

```python
from tencoinlib import Wallet
from tencoinlib.transaction import script_to_p2sh_address, script_to_p2wsh_address

pubkeys_hex = [
    "02a1b2c3d4e5f6...",
    "03d4e5f6a1b2c3...",
    "0298a7b8c9d0e1...",
]

# Accepts both bytes and hex strings
script = Wallet.build_multisig_script(m=2, pubkeys=pubkeys_hex, sort_pubkeys=True)

p2sh_addr  = script_to_p2sh_address(script)
p2wsh_addr = script_to_p2wsh_address(script)

print(f"P2SH : {p2sh_addr}")
print(f"P2WSH: {p2wsh_addr}")
```

---

### Deriving Participant Keys

Each participant in a multisig wallet derives their own key independently. The public keys are then shared and combined to create the multisig address.

```python
from tencoinlib import Wallet
from tencoinlib.keys.ec import privkey_to_pubkey
from tencoinlib.keys.bip32 import derive_path_from_seed

# --- Participant 1 ---
wallet1 = Wallet.create()
seed1 = wallet1.seed
priv1, _ = derive_path_from_seed(seed1, "m/84'/5353'/0'/0/0")
pub1 = privkey_to_pubkey(priv1, compressed=True)

# --- Participant 2 ---
wallet2 = Wallet.create()
seed2 = wallet2.seed
priv2, _ = derive_path_from_seed(seed2, "m/84'/5353'/0'/0/0")
pub2 = privkey_to_pubkey(priv2, compressed=True)

# --- Participant 3 ---
wallet3 = Wallet.create()
seed3 = wallet3.seed
priv3, _ = derive_path_from_seed(seed3, "m/84'/5353'/0'/0/0")
pub3 = privkey_to_pubkey(priv3, compressed=True)

# Participants exchange public keys and build the shared address
from tencoinlib.transaction import build_multisig_script, script_to_p2wsh_address

witness_script = build_multisig_script(m=2, pubkeys=[pub1, pub2, pub3], sort_pubkeys=True)
shared_address = script_to_p2wsh_address(witness_script)

print(f"Shared 2-of-3 P2WSH address: {shared_address}")
print(f"Witness script: {witness_script.hex()}")
```

> **Important**: Every participant must store the complete `witness_script` (or `redeem_script` for P2SH). Without it, funds cannot be recovered. It is not stored on-chain at deposit time.

---

### Signing a Multisig Transaction

#### Private Keys Format

`sign_transaction` accepts three equivalent formats for `private_keys`. All three produce identical results:

```python
# Format 1 — flat list (original single-sig API, one key per input)
# Works only when each input needs exactly one key.
private_keys = [key1, key2]

# Format 2 — nested list (one list of keys per input, recommended for multisig)
private_keys = [
    [key1, key2],       # Input 0: two keys for a 2-of-3 multisig
    [key3],             # Input 1: one key for a single-sig input
]

# Format 3 — mixed (flat bytes and lists in the same list)
private_keys = [
    key_a,              # single key → wrapped automatically to [key_a]
    [key_b, key_c],     # multiple keys for a multisig input
]
```

Additionally, extra co-signer keys can always be attached directly to the UTXO dict instead:

```python
utxo = {
    "address": p2wsh_address,
    "value": 5_000_000,
    "witness_script": witness_script,
    "cosigner_keys": [key2, key3],   # merged with whatever is in private_keys[i]
}
# private_keys[i] = key1   (first key)
# Final set used for signing: {key1, key2, key3}  (deduplicated by pubkey)
```

Both sources of keys are merged and deduplicated automatically — there is no need to avoid overlap.

---

#### P2WSH Multisig Transaction (SegWit, tc1q...)

```python
from tencoinlib import TransactionSigner, TransactionBuilder
from tencoinlib.transaction import (
    build_multisig_script,
    script_to_p2wsh_address,
    address_to_script,
)

# --- Setup (all participants agree on the same script) ---
witness_script = build_multisig_script(m=2, pubkeys=[pub1, pub2, pub3], sort_pubkeys=True)
p2wsh_address  = script_to_p2wsh_address(witness_script)

# --- Build transaction ---
builder = TransactionBuilder()
builder.add_input(
    txid="abcdef1234567890" * 4,         # 64-char hex TXID
    vout=0,
    value=5_000_000,                     # Tenos
    script_pubkey=address_to_script(p2wsh_address)
)
builder.add_output("tc1q...", 4_000_000) # recipient
builder.set_change_address(p2wsh_address)
builder.set_fee_rate(20)

tx, estimated_fee = builder.build()
print(f"Estimated fee: {estimated_fee} Tenos")

# --- Sign (2-of-3: participant 1 and participant 2 sign) ---
utxos = [{
    "address":       p2wsh_address,
    "value":         5_000_000,
    "witness_script": witness_script,    # required for P2WSH
}]

# Nested list: both keys for the single P2WSH input
private_keys = [[priv1, priv2]]

signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)

print(f"TXID          : {signed_tx.txid()}")
print(f"Has witness   : {signed_tx.has_witness}")
print(f"Witness items : {len(signed_tx.vin[0].witness)}")
# witness items = 1 (OP_0 placeholder) + 2 (signatures) + 1 (witness_script) = 4
```

#### P2SH Multisig Transaction (Legacy, M...)

```python
from tencoinlib import TransactionSigner, TransactionBuilder
from tencoinlib.transaction import (
    build_multisig_script,
    script_to_p2sh_address,
    address_to_script,
)

# --- Setup ---
redeem_script = build_multisig_script(m=2, pubkeys=[pub1, pub2, pub3], sort_pubkeys=True)
p2sh_address  = script_to_p2sh_address(redeem_script)

# --- Build transaction ---
builder = TransactionBuilder()
builder.add_input(
    txid="abcdef1234567890" * 4,
    vout=0,
    value=5_000_000,
    script_pubkey=address_to_script(p2sh_address)
)
builder.add_output("tc1q...", 4_000_000)
builder.set_change_address(p2sh_address)

tx, estimated_fee = builder.build()

# --- Sign (2-of-3: participant 1 and participant 2 sign) ---
utxos = [{
    "address":       p2sh_address,
    "script_pubkey": address_to_script(p2sh_address),
    "redeem_script": redeem_script,      # required for P2SH
    "value":         5_000_000,
}]

private_keys = [[priv1, priv2]]

signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)

print(f"TXID           : {signed_tx.txid()}")
print(f"ScriptSig size : {len(signed_tx.vin[0].script_sig)} bytes")
# scriptSig = OP_0 <sig1> <sig2> PUSHDATA1 <len> <redeem_script>
```

---

### Mixed Inputs: Multisig and Single-Sig in One Transaction

`TransactionSigner` handles any combination of address types in a single call. Each input is signed independently according to its own address type.

```python
from tencoinlib import TransactionSigner, TransactionBuilder, Wallet
from tencoinlib.transaction import (
    build_multisig_script,
    script_to_p2wsh_address,
    address_to_script,
)

single_wallet    = Wallet.create()
single_address   = single_wallet.get_address()            # P2WPKH tc1q...
single_priv      = bytes.fromhex(single_wallet.get_private_key_hex())

witness_script   = build_multisig_script(m=2, pubkeys=[pub1, pub2, pub3], sort_pubkeys=True)
multisig_address = script_to_p2wsh_address(witness_script) # P2WSH tc1q...

# --- Build transaction with two inputs ---
builder = TransactionBuilder()

# Input 0: single-sig P2WPKH
builder.add_input(
    txid="aaaa" * 16,
    vout=0,
    value=2_000_000,
    script_pubkey=address_to_script(single_address)
)

# Input 1: 2-of-3 P2WSH multisig
builder.add_input(
    txid="bbbb" * 16,
    vout=1,
    value=3_000_000,
    script_pubkey=address_to_script(multisig_address)
)

builder.add_output("tc1q...", 4_000_000)
builder.set_change_address(single_address)
tx, fee = builder.build()

# --- Sign: flat key for input 0, nested list for input 1 ---
utxos = [
    {
        "address": single_address,
        "value":   2_000_000,
    },
    {
        "address":        multisig_address,
        "value":          3_000_000,
        "witness_script": witness_script,
    },
]

private_keys = [
    single_priv,          # Input 0: one key (flat bytes)
    [priv1, priv2],       # Input 1: two keys (nested list)
]

signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)

print(f"TXID         : {signed_tx.txid()}")
print(f"Has witness  : {signed_tx.has_witness}")     # True
print(f"Input 0 witness items : {len(signed_tx.vin[0].witness)}")  # 2 (P2WPKH)
print(f"Input 1 witness items : {len(signed_tx.vin[1].witness)}")  # 4 (P2WSH 2-of-3)
```

---

### Using cosigner_keys in the UTXO Dict

When co-signers provide their keys through a different code path (e.g., collected over the network), attach them directly to the UTXO dict via `cosigner_keys`. They are merged with the `private_keys` argument automatically.

```python
utxos = [{
    "address":        p2wsh_address,
    "value":          5_000_000,
    "witness_script": witness_script,
    "cosigner_keys":  [priv2, priv3],   # keys from co-signers
}]

# private_keys provides priv1; cosigner_keys adds priv2 and priv3.
# Final set: {priv1, priv2, priv3} — deduplicated by pubkey.
private_keys = [priv1]

signed_tx = TransactionSigner.sign_transaction(tx, utxos, private_keys)
```

> The same `cosigner_keys` field works identically for P2SH multisig inputs.

---

### Complete End-to-End Example

```python
from tencoinlib import Wallet, TransactionSigner, TransactionBuilder
from tencoinlib.transaction import (
    build_multisig_script,
    script_to_p2wsh_address,
    address_to_script,
)
from tencoinlib.keys.ec import privkey_to_pubkey
from tencoinlib.keys.bip32 import derive_path_from_seed
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC

# ── 1. Key generation (each participant runs this independently) ──────────
wallet1 = Wallet.create()
wallet2 = Wallet.create()
wallet3 = Wallet.create()

priv1, _ = derive_path_from_seed(wallet1.seed, "m/84'/5353'/0'/0/0")
priv2, _ = derive_path_from_seed(wallet2.seed, "m/84'/5353'/0'/0/0")
priv3, _ = derive_path_from_seed(wallet3.seed, "m/84'/5353'/0'/0/0")

pub1 = privkey_to_pubkey(priv1, compressed=True)
pub2 = privkey_to_pubkey(priv2, compressed=True)
pub3 = privkey_to_pubkey(priv3, compressed=True)

# ── 2. Build shared address (all participants must agree) ─────────────────
witness_script = build_multisig_script(m=2, pubkeys=[pub1, pub2, pub3], sort_pubkeys=True)
multisig_addr  = script_to_p2wsh_address(witness_script)

print(f"2-of-3 P2WSH address : {multisig_addr}")
print(f"Witness script       : {witness_script.hex()}")
print()

# ── 3. (Off-chain) Fund the multisig address, then retrieve UTXOs ─────────
rpc   = RPCClient(host="127.0.0.1", port=10111, token="your-token")
utxos = rpc.list_unspent(multisig_addr)

if not utxos:
    print("No UTXOs found — send funds to the multisig address first.")
    exit(1)

total_available = sum(u["amount"] for u in utxos)
print(f"Available: {total_available / TENOS_PER_TEC:.8f} TEC across {len(utxos)} UTXO(s)")

# ── 4. Build the spending transaction ─────────────────────────────────────
SEND_AMOUNT    = 1_000_000    # 0.01 TEC
recipient_addr = "tc1q..."    # replace with actual recipient

builder = TransactionBuilder()
for u in utxos:
    builder.add_input(
        txid=u["txid"],
        vout=u["vout"],
        value=u["amount"],
        script_pubkey=address_to_script(multisig_addr)
    )
builder.add_output(recipient_addr, SEND_AMOUNT)
builder.set_change_address(multisig_addr)
builder.set_fee_rate(20)

tx, estimated_fee = builder.build()
print(f"Estimated fee: {estimated_fee} Tenos")

# ── 5. Sign (participants 1 and 2 provide signatures) ─────────────────────
utxo_data = [{
    "address":        multisig_addr,
    "value":          u["amount"],
    "witness_script": witness_script,
} for u in utxos]

# Nested list: one key-list per input (all inputs share the same multisig here)
private_keys = [[priv1, priv2]] * len(utxos)

signed_tx = TransactionSigner.sign_transaction(tx, utxo_data, private_keys)

print(f"TXID     : {signed_tx.txid()}")
print(f"Size     : {signed_tx.calculate_size()} bytes")
print(f"vSize    : {signed_tx.calculate_vsize()} bytes")

# ── 6. Validate and broadcast ─────────────────────────────────────────────
tx_hex = signed_tx.serialize().hex()

result = rpc.test_mempool_accept(tx_hex)
if not result.get("allowed"):
    print(f"Transaction rejected: {result.get('reject-reason', 'unknown')}")
    exit(1)

txid = rpc.send_raw_transaction(tx_hex)
print(f"\n✅ Transaction broadcast successfully!")
print(f"TXID: {txid}")
```

---

### Supported m-of-n Combinations

All combinations from 1-of-1 up to 15-of-15 are supported. Practical limits imposed by the Tencoin node's script size policy may apply for very large n.

| m \ n | 1 | 2 | 3 | 5 | 10 | 15 |
|---|---|---|---|---|---|---|
| 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | — | — | ✅ | ✅ | ✅ | ✅ |
| 5 | — | — | — | ✅ | ✅ | ✅ |
| 10 | — | — | — | — | ✅ | ✅ |
| 15 | — | — | — | — | — | ✅ |

**Script size and push opcode used for the redeem/witness script in scriptSig:**

| n | Script size | Push opcode |
|---|---|---|
| 1–2 | ≤ 75 bytes | Single byte length prefix |
| 3–7 | 76–255 bytes | `OP_PUSHDATA1` (0x4c) |
| 8–15 | 256–513 bytes | `OP_PUSHDATA2` (0x4d) |

Tencoinlib selects the correct push opcode automatically via `_push_data`.

---

### Error Handling

```python
from tencoinlib import TransactionSigner, SigningError
from tencoinlib.transaction import ScriptError

# Not enough matching private keys for the required m
try:
    signed_tx = TransactionSigner.sign_transaction(tx, utxos, [[priv1]])
    # Will raise if 2-of-3 is required and only 1 key is provided
except SigningError as e:
    print(f"Signing failed: {e}")
    # e.g. "multisig requires 2 signatures but only 1 matching private keys provided"

# Missing witness_script for a P2WSH input
try:
    signed_tx = TransactionSigner.sign_transaction(
        tx,
        [{"address": p2wsh_address, "value": 1_000_000}],   # no witness_script
        [priv1]
    )
except SigningError as e:
    print(f"Signing failed: {e}")
    # "P2WSH input UTXO must contain 'witness_script'"

# Invalid multisig parameters
try:
    from tencoinlib.transaction import build_multisig_script
    build_multisig_script(m=5, pubkeys=[pub1, pub2])   # m > n
except ScriptError as e:
    print(f"Script error: {e}")
    # "m and n must be 1..16 and m <= n"
```

---

### Best Practices for Multisig

1. **Always store the full script** — the redeem script (P2SH) or witness script (P2WSH) is not stored on-chain at deposit time. Every participant should back it up independently.

2. **Use `sort_pubkeys=True` consistently** — all participants must build the script with the same pubkey order. Sorting guarantees determinism regardless of insertion order.

3. **Prefer P2WSH over P2SH** — P2WSH uses the witness field, which is discounted in vSize calculation. For large multisig scripts (n ≥ 3) the fee saving is significant.

4. **Verify the address before sending funds** — all participants should independently derive the multisig address from the agreed script and confirm it matches before depositing.

5. **Test on small amounts first** — always send a small test amount, verify you can spend it, then use the address for larger amounts.

6. **Use `test_mempool_accept` before broadcasting** — validates the signed transaction against node policy without risking a broadcast failure.

   ```python
   result = rpc.test_mempool_accept(signed_tx.serialize().hex())
   if result.get("allowed"):
       txid = rpc.send_raw_transaction(signed_tx.serialize().hex())
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

`TransactionBuilder` supports two independent fee modes. They are mutually exclusive — whichever was set last wins.

---

#### `set_fee_rate` — Rate-Based Fee

The default mode. The builder estimates the transaction's virtual size and multiplies it by the rate you supply.

```python
builder = TransactionBuilder()

# Use the library default (20 Tenos/byte)
builder.add_input(...)
builder.add_output(...)
tx, fee = builder.build()

# Override with a custom rate
builder.set_fee_rate(50)   # 50 Tenos/byte — faster confirmation
tx, fee = builder.build()

# Use a named constant
from tencoinlib.transaction import FeeCalculator
builder.set_fee_rate(FeeCalculator.PRIORITY_FEE_RATE)   # 50 Tenos/byte
builder.set_fee_rate(FeeCalculator.DEFAULT_FEE_RATE)    # 20 Tenos/byte
builder.set_fee_rate(FeeCalculator.ECONOMY_FEE_RATE)    # 10 Tenos/byte
```

**Notes:**
- Calling `set_fee_rate()` clears any fixed fee previously set with `set_fee()`.
- A rate of `0` is accepted (zero-fee transaction).

---

#### `set_fee` — Fixed Exact Fee

Use this when you want to specify the exact fee amount instead of letting the builder estimate it. The size-estimation step is bypassed entirely.

##### Unit: TEC

Pass a float value in TEC. The builder converts it to Tenos internally (multiplied by `100_000_000`).

```python
builder.set_fee(0.0022, unit="TEC")   # → 220_000 Tenos
builder.set_fee(0.001,  unit="TEC")   # → 100_000 Tenos
builder.set_fee(0.0,    unit="TEC")   # → 0 Tenos (zero-fee)
```

##### Unit: Teno

Pass an integer value in Tenos directly. No conversion is applied.

```python
builder.set_fee(220000, unit="Teno")  # → 220_000 Tenos
builder.set_fee(1000,   unit="Teno")  # → 1_000 Tenos
builder.set_fee(0,      unit="Teno")  # → 0 Tenos (zero-fee)
```

##### Unit is Case-Insensitive

All of the following are equivalent:

```python
builder.set_fee(0.0022, unit="TEC")
builder.set_fee(0.0022, unit="tec")
builder.set_fee(0.0022, unit="Tec")

builder.set_fee(220000, unit="Teno")
builder.set_fee(220000, unit="teno")
builder.set_fee(220000, unit="TENO")
```

##### Switching Back to Rate-Based Fee

If you call `set_fee_rate()` after `set_fee()`, the fixed fee is discarded and rate-based calculation resumes:

```python
builder.set_fee(220000, unit="Teno")   # fixed fee active
builder.set_fee_rate(20)               # clears fixed fee; rate-based again
```

##### Complete Example

```python
from tencoinlib import TransactionBuilder, TransactionSigner, Wallet
from tencoinlib.rpc import RPCClient

wallet = Wallet.load("my_wallet.tcw").unlock("my-password")
rpc    = RPCClient(host="127.0.0.1", port=10111, token="your-token")

utxos = rpc.list_unspent(wallet.get_address())

builder = TransactionBuilder()
for utxo in utxos:
    builder.add_input(
        txid=utxo["txid"],
        vout=utxo["vout"],
        value=utxo["amount"],
        script_pubkey=bytes.fromhex(utxo["scriptPubKey"])
    )

builder.add_output("tc1q...", 500_000)
builder.set_change_address(wallet.get_address())

# Exact fee: 0.0015 TEC = 150_000 Tenos
builder.set_fee(0.0015, unit="TEC")

tx, actual_fee = builder.build()
print(f"Fee paid: {actual_fee} Tenos")   # 150000
```

**Error cases:**

```python
# Unknown unit
builder.set_fee(1000, unit="BTC")
# → TransactionBuilderError: Unknown fee unit 'BTC'. Use 'TEC' or 'Teno'.

# Teno must be a whole number
builder.set_fee(100.5, unit="Teno")
# → TransactionBuilderError: Teno amount must be a whole number, got 100.5

# Negative fee
builder.set_fee(-500, unit="Teno")
# → TransactionBuilderError: Fee cannot be negative: -500

# Insufficient funds (fixed fee + outputs exceed inputs)
builder.set_fee(999_999_999, unit="Teno")
tx, fee = builder.build()
# → TransactionBuilderError: Insufficient funds: have X, need Y
```

---

## OP_RETURN Outputs

`OP_RETURN` is a standard script opcode that marks an output as provably unspendable. It is used to embed arbitrary data (metadata, hashes, messages, timestamps) directly into the blockchain. The output value is always `0` Tenos.

### Basic Usage

#### Embed a Text String

```python
from tencoinlib import TransactionBuilder

builder = TransactionBuilder()
builder.add_input(txid="abc123...", vout=0, value=1_000_000,
                  script_pubkey=bytes.fromhex("..."))
builder.add_output("tc1q...", 800_000)
builder.set_change_address("tc1q...")

# Embed a UTF-8 string — encoded automatically
builder.op_return("Hello, Tencoin!")

tx, fee = builder.build()
```

#### Embed Raw Bytes

```python
# Embed arbitrary bytes (e.g., a hash or a protocol marker)
payload = bytes.fromhex("deadbeef01020304")
builder.op_return(payload)
```

#### Embed a SHA-256 Hash

A common pattern is to anchor a document hash on-chain:

```python
import hashlib

document = open("contract.pdf", "rb").read()
doc_hash = hashlib.sha256(document).digest()   # 32 bytes

builder.op_return(doc_hash)
```

### Input Types

| Argument type | Behaviour |
|---|---|
| `str` | Encoded to UTF-8 bytes before embedding |
| `bytes` | Used as-is |
| `bytearray` | Converted to `bytes`, then used as-is |
| Any other type | Raises `TransactionBuilderError` |

### Payload Size Limit

The maximum payload is **80 bytes** (protocol limit). Payloads of 76–80 bytes use `OP_PUSHDATA1` internally; payloads of 0–75 bytes use a direct push opcode. This is handled automatically — you never need to manage push opcodes yourself.

```python
# 80-byte payload — maximum allowed
builder.op_return(b"A" * 80)   # OK

# 81 bytes — raises an error
builder.op_return(b"A" * 81)
# → TransactionBuilderError: OP_RETURN payload too large: 81 bytes (max 80)
```

### Multiple OP_RETURN Outputs

You can add more than one `op_return()` call to a single transaction. Each call appends one zero-value output with its own script.

```python
builder.op_return("protocol:tencoin")
builder.op_return(doc_hash)
builder.op_return(b"\x01\x00\x00\x00")   # version marker

tx, fee = builder.build()
```

> **Note:** Although tencoinlib allows multiple OP_RETURN outputs per transaction, some nodes and explorers may only relay or index transactions with a single OP_RETURN output. Check the policy of your target network before using more than one.

### Combining with set_fee

OP_RETURN outputs have zero value and do not affect change calculation. They do, however, add bytes to the transaction, which slightly increases the rate-based fee estimate. If you need an exact fee, combine with `set_fee()`:

```python
builder.add_input(txid="abc123...", vout=0, value=1_000_000,
                  script_pubkey=bytes.fromhex("..."))
builder.add_output("tc1q...", 700_000)
builder.set_change_address("tc1q...")
builder.op_return("my-app:data-v1")
builder.set_fee(5_000, unit="Teno")    # exact fee regardless of size

tx, fee = builder.build()
print(fee)   # 5000
```

### Transaction Summary with OP_RETURN

`get_summary()` includes an `op_return_count` field:

```python
summary = builder.get_summary()
print(f"OP_RETURN outputs: {summary['op_return_count']}")
print(f"Total outputs:     {summary['outputs_count']}")
# outputs_count = spendable outputs + op_return outputs + change (if any)
```

### Error Handling

```python
from tencoinlib import TransactionBuilder, TransactionBuilderError

builder = TransactionBuilder()

# Wrong type
try:
    builder.op_return(12345)
except TransactionBuilderError as e:
    print(e)
# → OP_RETURN data must be str or bytes, got int

# Payload too large
try:
    builder.op_return("x" * 81)
except TransactionBuilderError as e:
    print(e)
# → OP_RETURN payload too large: 81 bytes (max 80)
```

### Script Format Reference

Internally, `op_return()` builds the following `scriptPubKey`:

| Payload length | Script bytes |
|---|---|
| 0–75 bytes | `OP_RETURN <len> <data>` |
| 76–80 bytes | `OP_RETURN OP_PUSHDATA1 <len> <data>` |

The opcodes are sourced from `tencoinlib.constants`:

```python
from tencoinlib.constants import OP_RETURN, OP_PUSHDATA1

print(hex(OP_RETURN))    # 0x6a
print(hex(OP_PUSHDATA1)) # 0x4c
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

## Message Signing

Tencoinlib provides Bitcoin Core–compatible message signing and verification through the `tencoinlib.message` module. This allows users to cryptographically prove ownership of an address by signing arbitrary messages with the corresponding private key — without broadcasting any transaction.

### Overview

The implementation follows the same standard used in Bitcoin Core:

- The message is prefixed with `\x18Tencoin Signed Message:\n` before hashing.
- The digest is computed as `SHA256(SHA256(prefix + varint(len) + message))`.
- Signing uses a **recoverable ECDSA signature** (secp256k1), which allows the verifier to reconstruct the public key directly from the signature — no prior knowledge of the public key is required.
- The output is a **65-byte Base64-encoded** signature: `r[32] + s[32] + recovery_byte[1]`.
- Recovery bytes `31–34` indicate a **compressed** public key (standard for Tencoin).

> **Dependency**: Message signing requires `coincurve`. Install it with:
> ```bash
> pip install coincurve
> ```

### Importing

```python
from tencoinlib.message import (
    sign_message,
    verify_message,
    recover_address_from_signature,
    MessageSigningError,
)

# Or directly from the top-level package
from tencoinlib import (
    sign_message,
    verify_message,
    recover_address_from_signature,
    MessageSigningError,
)
```

### Signing a Message

```python
from tencoinlib import Wallet, sign_message, recover_address_from_signature

# Create or recover a wallet
wallet = Wallet.create()
private_key = bytes.fromhex(wallet.get_private_key_hex())

# Define the message to sign
message = "I am the owner of this Tencoin address."

# Sign the message
signature = sign_message(private_key, message)

# Recover the corresponding P2PKH address from the signature
address = recover_address_from_signature(message, signature)

print(f"Address   : {address}")
print(f"Message   : {message}")
print(f"Signature : {signature}")
```

**Example output:**

```
Address   : TxK9mR3...
Message   : I am the owner of this Tencoin address.
Signature : H3k9mR2...  (88-character Base64 string)
```

### Verifying a Message

```python
from tencoinlib import verify_message

address   = "TxK9mR3..."     # The claimed address
message   = "I am the owner of this Tencoin address."
signature = "H3k9mR2..."     # Base64 signature from sign_message()

is_valid = verify_message(address, message, signature)

if is_valid:
    print("✓ Signature is valid — message was signed by the owner of this address.")
else:
    print("✗ Signature is invalid.")
```

### Recovering the Signer's Address

When you only have the message and signature (but not the address), you can recover the signer's address directly:

```python
from tencoinlib import recover_address_from_signature

message   = "I am the owner of this Tencoin address."
signature = "H3k9mR2..."

address = recover_address_from_signature(message, signature)

if address:
    print(f"Signer's address: {address}")
else:
    print("Address recovery failed — invalid signature.")
```

### Signing File Hashes

A common use case is proving ownership of a file by signing its SHA256 hash:

```python
import hashlib
from tencoinlib import Wallet, sign_message, verify_message

def hash_file(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

wallet = Wallet.create()
private_key = bytes.fromhex(wallet.get_private_key_hex())

# Hash the file and sign its hex digest as a message
file_hash = hash_file("document.pdf")
signature = sign_message(private_key, file_hash)

print(f"File SHA256 : {file_hash}")
print(f"Signature   : {signature}")

# Verify later
is_valid = verify_message(wallet.get_address("p2pkh"), file_hash, signature)
print(f"Valid: {is_valid}")
```

### Error Handling

```python
from tencoinlib import sign_message, verify_message, MessageSigningError

# Signing
try:
    signature = sign_message(private_key, message)
except MessageSigningError as e:
    print(f"Signing failed: {e}")

# Verification
try:
    is_valid = verify_message(address, message, signature)
except MessageSigningError as e:
    # Raised for malformed signatures (invalid Base64, wrong length, bad recovery byte)
    print(f"Verification error: {e}")
```

Common causes of `MessageSigningError`:

| Cause | Description |
|---|---|
| `coincurve` not installed | Install with `pip install coincurve` |
| Private key is not 32 bytes | Must be exactly 32 bytes |
| Invalid Base64 signature | Signature string is malformed |
| Signature length ≠ 65 bytes | Decoded bytes must be exactly 65 |
| Invalid recovery byte | Must be in the range 27–34 |

### Address Compatibility

Message signing only supports **P2PKH addresses** (`T...`). SegWit addresses (`tc1q...`) and P2SH addresses (`M...`) are not supported by the message signing standard, consistent with Bitcoin Core behavior.

```python
from tencoinlib import Wallet, sign_message, recover_address_from_signature

wallet = Wallet.create()
private_key = bytes.fromhex(wallet.get_private_key_hex())

# Use P2PKH address for message signing
p2pkh_address = wallet.get_address("p2pkh")   # T...

signature = sign_message(private_key, "Hello Tencoin!")
recovered  = recover_address_from_signature("Hello Tencoin!", signature)

assert recovered == p2pkh_address  # Always holds for the same key
```

### Recovery Byte and Signature Format

The recovery byte encodes both the parity of the public key's Y coordinate and whether the key is compressed:

| Recovery byte | Meaning |
|---|---|
| 31–34 | Compressed public key (standard for Tencoin) |
| 27–30 | Uncompressed public key (legacy compatibility) |

Unlike Bitcoin (which almost exclusively produces `H` or `I` signatures due to its `0x00` address version byte), Tencoin uses version byte `0x41`, which allows all four values — `H`, `I`, `J`, `K` — to appear depending on the key. This is expected behavior and does not affect validity.

---

## Complete Examples

### Example 1: Complete Wallet Setup

```python
from tencoinlib import Wallet, WalletAuthError
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC
import os

WALLET_FILE = "my_wallet.tcw"

# Create a new wallet or load an existing one
if not os.path.exists(WALLET_FILE):
    wallet = Wallet.create()
    print(f"\n⚠️  IMPORTANT: Save this mnemonic phrase safely!")
    print(f"Mnemonic: {wallet.get_mnemonic()}\n")
    password = input("Set a wallet password: ")
    wallet.save(WALLET_FILE, password=password)
    print(f"Wallet saved to {WALLET_FILE}")
else:
    password = input("Enter wallet password: ")
    try:
        wallet = Wallet.load(WALLET_FILE).unlock(password)
    except WalletAuthError:
        print("Wrong password!")
        exit(1)

# Connect to node
rpc = RPCClient(host="127.0.0.1", port=10111, token="your-token")

# Get balance
address = wallet.get_address()
balance_tenos = rpc.get_balance(address)
balance_tec   = balance_tenos / TENOS_PER_TEC

print(f"\nWallet Information:")
print(f"Address: {address}")
print(f"Balance: {balance_tec:.8f} TEC ({balance_tenos} Tenos)")

# Show UTXOs
utxos = rpc.list_unspent(address)
print(f"\nUnspent Outputs: {len(utxos)}")
for utxo in utxos:
    print(f"  {utxo['amount']} Tenos from {utxo['txid'][:16]}...")

# Lock when done
wallet.lock()
```

### Example 2: Complete Send Transaction

```python
from tencoinlib import Wallet, TransactionBuilder, TransactionSigner, WalletAuthError
from tencoinlib.rpc import RPCClient
from tencoinlib.constants import TENOS_PER_TEC
from tencoinlib.transaction.address import address_to_script

# Load and unlock wallet
password = input("Wallet password: ")
try:
    wallet = Wallet.load("my_wallet.tcw").unlock(password)
except WalletAuthError:
    print("Wrong password!")
    exit(1)

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
- **Returns**: New `Wallet` instance (UNLOCKED)

**`Wallet.recover(mnemonic: str, passphrase: str = "") -> Wallet`**
- Recover wallet from mnemonic phrase
- **Parameters**:
  - `mnemonic` - BIP-39 mnemonic phrase
  - `passphrase` - Optional BIP-39 passphrase
- **Returns**: Recovered `Wallet` instance (UNLOCKED)
- **Raises**: `WalletError` if mnemonic is invalid

**`Wallet.from_xpub(xpub: str) -> Wallet`**
- Create a watch-only wallet from a master/account xpub
- Can derive addresses via `derive_address_from_xpub`, but has no access to private keys or seed

**`Wallet.from_xprv(xprv: str) -> Wallet`**
- Create a wallet from a master/account xprv
- Full private derivation is available, but no mnemonic/seed is required

**`Wallet.load(filepath: str) -> Wallet`**
- Read a `.tcw` file header without decrypting — returns a LOCKED wallet
- **Parameters**: `filepath` - Path to a `.tcw` file
- **Returns**: LOCKED `Wallet` instance
- **Raises**: `TCWFormatError` if file is invalid, `TCWVersionError` if version unsupported, `FileNotFoundError`

**`Wallet.load_from_file(filepath: str, password: str) -> Wallet`**
- Convenience method: load and fully decrypt in one call
- Equivalent to `Wallet.load(filepath).unlock(password)`
- **Returns**: UNLOCKED `Wallet` instance

#### Lock / Unlock

**`wallet.unlock(password: str) -> Wallet`**
- Decrypt the wallet's `.tcw` file and load secrets into RAM
- **Returns**: self (UNLOCKED) — supports chaining: `Wallet.load(path).unlock(pw)`
- **Raises**: `WalletAuthError` if password is wrong or file is corrupted, `WalletError` if no `.tcw` file is associated

**`wallet.lock() -> None`**
- Discard all secret material from RAM; set state to LOCKED
- Public metadata (address, xpub, indices) is preserved

**`wallet.unlocked(password: str) -> ContextManager`**
- Context manager: unlock on enter, lock on exit (even if an exception occurs)
- Usage: `with wallet.unlocked("pw") as w: ...`

**`wallet.is_locked -> bool`** *(property)*
- `True` when no secret material is held in RAM

#### Persistence

**`wallet.save(filepath: str, password: str) -> None`**
- Encrypt and write wallet to a TCW v1 binary file
- Wallet must be UNLOCKED; password must be at least 8 characters
- **Raises**: `WalletLockedError`, `ValueError` if password too short

**`wallet.save_to_file(filepath: str, password: str) -> None`**
- Alias for `save()`

#### Instance Methods

**`get_address(type: str = "p2wpkh", script: Optional[bytes] = None) -> str`**
- Get address for the current key in the requested form
- `p2wpkh` is available while LOCKED; `p2pkh` and `p2sh` require UNLOCKED
- **Parameters**:
  - `type`: One of `"p2wpkh"` (default), `"p2pkh"`, `"p2sh"`, `"p2wsh"`
  - `script`: For `"p2sh"` (optional) or `"p2wsh"` (required)
- **Returns**: Address string (`tc1q...`, `T...`, or `M...`)

**`get_private_key_hex() -> str`**
- Get private key as hex string (UNLOCKED required)
- **Raises**: `WalletLockedError`, `WalletError` in watch-only wallets

**`get_public_key_hex() -> str`**
- Get public key as hex string (compressed); available while LOCKED

**`get_mnemonic() -> str`**
- Get mnemonic phrase (UNLOCKED required)
- **Raises**: `WalletLockedError`, `WalletError` if wallet has no mnemonic

**`get_master_xprv() -> str`**
- Get master xprv as Base58Check string (UNLOCKED required, non-watch-only only)

**`get_master_xpub() -> str`**
- Get master xpub as Base58Check string

**`derive_xprv(path: str) -> str`**
- Derive extended private key at a BIP-32 path (UNLOCKED required, non-watch-only only)

**`derive_xpub(path: str) -> str`**
- Derive extended public key at a BIP-32 path
- Full wallets support hardened + non-hardened; watch-only: non-hardened only

**`get_account_xprv(account: int) -> str`**
- Get account-level xprv at `m/84'/5353'/account'` (UNLOCKED required)

**`get_account_xpub(account: int) -> str`**
- Get account-level xpub at `m/84'/5353'/account'`

**`derive_address(account: int = 0, change: int = 0, index: int = 0) -> Tuple[str, str]`**
- Derive BIP-84 address at a specific path (UNLOCKED required)
- **Returns**: `(private_key_hex, address)`

**`get_next_address(change: int = 0) -> Tuple[str, str]`**
- Increment address index and return the next address (UNLOCKED required)
- **Returns**: `(private_key_hex, address)`

**`derive_address_from_xpub(change: int, index: int) -> str`**
- Derive address from the wallet's base xpub; watch-only safe

**`export_xpub(path: str) -> str`**  
**`export_xprv(path: str) -> str`**  
**`import_xpub(xpub: str) -> None`**  
**`import_xprv(xprv: str) -> None`**
- BIP-32 import/export helpers; xprv operations require UNLOCKED

**`wallet_type -> str`** *(property)*
- One of `"hd"`, `"xpub"`, `"xprv"`

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
- Set fee rate in Tenos per byte; the builder estimates transaction size and multiplies by this rate
- Calling this clears any fixed fee previously set by `set_fee()`
- A rate of `0` is accepted (zero-fee)
- **Returns**: Self for method chaining
- **Raises**: `TransactionBuilderError` if `fee_rate` is negative

**`set_fee(amount: Union[int, float], unit: str = "Teno") -> TransactionBuilder`**
- Set an exact fixed fee, bypassing size estimation entirely
- `unit` is case-insensitive: `"TEC"` / `"tec"` / `"Tec"` or `"Teno"` / `"teno"` / `"TENO"`
- For `unit="TEC"`: `fee_tenos = round(amount × 100_000_000)` — float accepted
- For `unit="Teno"`: amount must be a whole number (int or float with no fractional part)
- A fee of `0` is accepted
- Calling `set_fee_rate()` afterwards clears the fixed fee
- **Returns**: Self for method chaining
- **Raises**: `TransactionBuilderError` if unit is unknown, amount is fractional (Teno), or fee is negative

**`op_return(data: Union[str, bytes, bytearray]) -> TransactionBuilder`**
- Append a zero-value unspendable `OP_RETURN` output carrying `data` as payload
- `str` is encoded to UTF-8; `bytes`/`bytearray` is used as-is
- Maximum payload: 80 bytes after encoding
- Multiple calls are allowed; each adds one separate `OP_RETURN` output
- **Returns**: Self for method chaining
- **Raises**: `TransactionBuilderError` if payload exceeds 80 bytes or type is unsupported

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

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: Union[List[bytes], List[List[bytes]]]) -> Transaction`**
- Sign a transaction with any combination of address types
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries. Fields by type:
    - All: `address` (str)
    - P2PKH / P2SH: `script_pubkey` (bytes)
    - P2SH: `redeem_script` (bytes, required), `cosigner_keys` (List[bytes], optional)
    - P2WPKH: `value` (int)
    - P2WSH: `value` (int), `witness_script` (bytes, required), `cosigner_keys` (List[bytes], optional)
  - `private_keys` - One entry per input. Three accepted formats:
    - Flat: `[key_a, key_b]` — one key per input (single-sig)
    - Nested: `[[key_a1, key_a2], [key_b1]]` — one list per input (multisig)
    - Mixed: `[key_a, [key_b1, key_b2]]` — any combination
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails or fewer keys than required m are provided
- **Supported Address Types**: P2WPKH, P2WSH, P2PKH, P2SH (single-sig and multisig)

### LegacySigner Class

Legacy transaction signer for P2PKH and P2SH addresses.

#### Static Methods

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: Union[List[bytes], List[List[bytes]]]) -> Transaction`**
- Sign a complete transaction with Legacy inputs (P2PKH or P2SH, single-sig or multisig)
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries with `address`, `script_pubkey`, and optionally `redeem_script` and `cosigner_keys`
  - `private_keys` - Flat, nested, or mixed list of keys (same format as `TransactionSigner`)
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails

**`sign_p2pkh_input(tx: Transaction, input_index: int, private_key: bytes, script_pubkey: bytes, sighash_type: int = 1)`**
- Sign a P2PKH input. Produces `scriptSig = <sig> <pubkey>`.
- **Parameters**:
  - `tx` - Transaction (modified in place)
  - `input_index` - Input index to sign
  - `private_key` - 32-byte private key
  - `script_pubkey` - ScriptPubKey of the UTXO
  - `sighash_type` - SIGHASH type (default: SIGHASH_ALL = 1)

**`sign_p2sh_input(tx: Transaction, input_index: int, keys_for_input: List[bytes], redeem_script: bytes, script_pubkey: bytes, sighash_type: int = 1)`**
- Unified P2SH input signer — auto-detects single-sig vs multisig from the redeem script.
- For single-sig: `scriptSig = <sig> <pubkey> <redeem_script>`
- For multisig: `scriptSig = OP_0 <sig1> ... <sigM> <redeem_script>`
- **Parameters**:
  - `tx` - Transaction (modified in place)
  - `input_index` - Input index to sign
  - `keys_for_input` - All available private keys for this input
  - `redeem_script` - Redeem script bytes
  - `script_pubkey` - ScriptPubKey of the UTXO
  - `sighash_type` - SIGHASH type (default: SIGHASH_ALL = 1)

**`sign_p2sh_multisig_input(tx: Transaction, input_index: int, private_keys_for_input: List[bytes], redeem_script: bytes, sighash_type: int = 1)`**
- Sign a P2SH multisig input (BIP-11). Produces `OP_0 <sig1> ... <sigM> <redeem_script>`.
- `private_keys_for_input` must contain at least M keys that match pubkeys in the redeem script.

**`legacy_digest(tx: Transaction, input_index: int, script_code: bytes, sighash_type: int = 1) -> bytes`**
- Calculate legacy transaction digest (pre-SegWit SIGHASH_ALL)
- **Returns**: 32-byte digest

### SegWitSigner Class

SegWit transaction signer (BIP-143) for P2WPKH addresses.

#### Static Methods

**`sign_transaction(tx: Transaction, utxos: List[dict], private_keys: Union[List[bytes], List[List[bytes]]]) -> Transaction`**
- Sign a complete transaction with SegWit inputs (P2WPKH or P2WSH)
- **Parameters**:
  - `tx` - Unsigned transaction
  - `utxos` - List of UTXO dictionaries. P2WSH inputs must include `witness_script`; multisig inputs may also include `cosigner_keys`.
  - `private_keys` - Flat, nested, or mixed list of keys (same format as `TransactionSigner`)
- **Returns**: Signed transaction
- **Raises**: `SigningError` if signing fails

**`sign_p2wpkh_input(tx: Transaction, input_index: int, utxo: dict, private_key: bytes)`**
- Sign a P2WPKH input. Sets `witness = [sig, pubkey]`.
- **Parameters**:
  - `tx` - Transaction (modified in place)
  - `input_index` - Input index to sign
  - `utxo` - UTXO dict with `value` and `address`
  - `private_key` - 32-byte private key

**`sign_p2wsh_input(tx: Transaction, input_index: int, utxo: dict, keys_for_input: List[bytes])`**
- Sign a P2WSH input (single-sig or multisig).
- For multisig: `witness = [b"", sig1, ..., sigM, witness_script]`
- For single-sig: `witness = [sig, pubkey, witness_script]`
- **Parameters**:
  - `tx` - Transaction (modified in place)
  - `input_index` - Input index to sign
  - `utxo` - UTXO dict with `value`, `address`, `witness_script`, and optionally `cosigner_keys`
  - `keys_for_input` - All available private keys for this input

**`sign_input(tx: Transaction, input_index: int, utxo: dict, private_key: bytes)`**
- Backward-compatible alias for `sign_p2wpkh_input`. Signs a single P2WPKH input.
- **Parameters**:
  - `tx` - Transaction (modified in place)
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

### Message Signing Module

#### sign_message

**`sign_message(private_key: bytes, message: str) -> str`**
- Sign an arbitrary message with a secp256k1 private key.
- **Parameters**:
  - `private_key` — 32-byte raw private key
  - `message` — UTF-8 message string
- **Returns**: Base64-encoded 65-byte recoverable signature
- **Raises**: `MessageSigningError` if `coincurve` is unavailable or signing fails

#### verify_message

**`verify_message(address: str, message: str, signature_b64: str) -> bool`**
- Verify that a signature was produced by the owner of the given P2PKH address.
- Recovers the public key from the signature and compares the derived address.
- Supports both compressed (31–34) and uncompressed (27–30) recovery bytes.
- **Parameters**:
  - `address` — Tencoin P2PKH address (`T...`)
  - `message` — Original UTF-8 message string
  - `signature_b64` — Base64-encoded signature from `sign_message()`
- **Returns**: `True` if valid, `False` if the signature does not match the address
- **Raises**: `MessageSigningError` for malformed input (invalid Base64, wrong length, bad recovery byte)

#### recover_address_from_signature

**`recover_address_from_signature(message: str, signature_b64: str) -> Optional[str]`**
- Recover the P2PKH address of the signer without knowing it in advance.
- **Parameters**:
  - `message` — Original UTF-8 message string
  - `signature_b64` — Base64-encoded signature from `sign_message()`
- **Returns**: Tencoin P2PKH address string, or `None` if recovery fails
- **Raises**: `MessageSigningError` if `coincurve` is unavailable

#### MessageSigningError

**`class MessageSigningError(Exception)`**
- Raised for all message signing and verification errors, including missing dependencies, malformed input, and cryptographic failures.

---

## Error Handling

### Exception Classes

```python
from tencoinlib import WalletError, WalletLockedError, WalletAuthError
from tencoinlib.wallet_storage.tcw import TCWFormatError, TCWVersionError, TCWAuthError
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
from tencoinlib.message import MessageSigningError
```

### Wallet Errors

```python
from tencoinlib import Wallet, WalletError, WalletLockedError, WalletAuthError
from tencoinlib.wallet_storage.tcw import TCWFormatError, TCWVersionError

# Invalid mnemonic
try:
    wallet = Wallet.recover("invalid mnemonic")
except WalletError as e:
    print(f"Wallet error: {e}")

# Wrong password
try:
    wallet = Wallet.load("my_wallet.tcw").unlock("wrong-password")
except WalletAuthError:
    print("Wrong password or file is corrupted")

# Operation on a locked wallet
wallet = Wallet.load("my_wallet.tcw")   # LOCKED
try:
    wallet.get_mnemonic()               # requires UNLOCKED
except WalletLockedError as e:
    print(f"Wallet is locked: {e}")

# Invalid or unsupported .tcw file
try:
    wallet = Wallet.load("not_a_wallet.bin")
except TCWFormatError as e:
    print(f"Not a valid TCW file: {e}")
except TCWVersionError as e:
    print(f"Unsupported TCW version: {e}")
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

### Message Signing Errors

```python
from tencoinlib import sign_message, verify_message, MessageSigningError

try:
    signature = sign_message(private_key, "Hello Tencoin!")
except MessageSigningError as e:
    print(f"Signing error: {e}")

try:
    is_valid = verify_message(address, "Hello Tencoin!", signature)
except MessageSigningError as e:
    print(f"Verification error: {e}")
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

### Script Opcode Constants

```python
from tencoinlib.constants import (
    OP_DUP,          # 0x76
    OP_HASH160,      # 0xa9
    OP_EQUALVERIFY,  # 0x88
    OP_CHECKSIG,     # 0xac
    OP_EQUAL,        # 0x87
    OP_RETURN,       # 0x6a — marks output as unspendable; used for metadata embedding
    OP_PUSHDATA1,    # 0x4c — push opcode for payloads of 76–255 bytes
)
```

---

## Best Practices

### Message Signing

1. **Always use P2PKH addresses for message signing**
   ```python
   # Correct — use P2PKH address (T...)
   address = wallet.get_address("p2pkh")
   is_valid = verify_message(address, message, signature)
   ```

2. **Verify before trusting**
   - Always call `verify_message()` on receipt before acting on a signed claim.

3. **Sign file hashes, not file contents**
   - Pass the hex SHA256 digest of a file as the message to keep signatures portable and reproducible.

4. **Do not reuse signatures across contexts**
   - A valid signature proves ownership at the time of signing. Include timestamps or nonces in the message when freshness matters.

---

### Security

1. **Always save wallets to encrypted `.tcw` files**
   ```python
   wallet.save("my_wallet.tcw", password="strong-password")
   ```
   Never store raw mnemonics or private keys in plaintext files.

2. **Keep wallets locked when not in use**
   ```python
   # Preferred: context manager auto-locks on exit
   with wallet.unlocked("my-password") as w:
       signed_tx = w.sign_transaction(tx)

   # Or lock explicitly
   wallet.unlock("my-password")
   # ... do work ...
   wallet.lock()
   ```

3. **Use BIP-39 passphrases for additional protection**
   ```python
   wallet = Wallet.recover(mnemonic, passphrase="strong-passphrase")
   ```
   The passphrase is separate from the file encryption password and provides a second layer of security.

4. **Use strong, unique passwords for wallet files**
   - Minimum 8 characters (enforced)
   - Argon2id KDF makes brute-force attacks expensive
   - A strong password is the last line of defence if the `.tcw` file is stolen

5. **Back up the mnemonic phrase — not the `.tcw` file**
   - The `.tcw` file can always be recreated from the mnemonic
   - Store the mnemonic offline and in a physically secure location
   - Never commit mnemonics or `.tcw` files to version control

6. **Validate addresses before sending**
   ```python
   from tencoinlib.transaction import is_valid_address
   if not is_valid_address(recipient_address):
       raise ValueError("Invalid recipient address")
   ```

7. **Double-check transaction details**
   - Always verify recipient address
   - Confirm amount before broadcasting
   - Check fee is reasonable

8. **Use change addresses**
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