# TenCoin (TEC)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Network Status](https://img.shields.io/badge/Network-Mainnet-green.svg)]()

**TenCoin** is a decentralized, peer-to-peer cryptocurrency designed for secure, autonomous transactions. Inspired by Bitcoin, TenCoin supports standard UTXO-based transactions with advanced script capabilities for **timer** and **verify-code** conditions.

🌐 Official website: [tencoin.io](https://tencoin.io)

---

## 📖 Table of Contents
- [Introduction](#introduction)
- [Key Features](#key-features)
- [Technical Details](#technical-details)
- [Getting Started](#getting-started)
- [Example Usage](#example-usage)
- [Contributing](#contributing)
- [License](#license)

---

## Introduction
TenCoin (TEC) is a blockchain network that provides secure and autonomous transactions. Scripts can include timers and verify-code conditions directly at the output level, enabling flexible conditional transfers without changing the core UTXO model.  

- **Ticker:** `TEC`  
- **Smallest Unit:** `Teno` (8 decimals, like satoshi)  
- **Total Supply:** `10,000,000 TEC`  

---

## Key Features
- **UTXO-based transaction model** for transparency and security.  
- **Timer and verify-code scripts**: conditional execution stored at the script level.  
- **Single transaction fee**: standard fee paid to miners, no additional completed_fee.  
- **Multisig & advanced scripts**: supports timelock, multisignature, and custom conditions.  
- **P2P network** with dedicated ports:
  - Mainnet: `10110` (P2P), `10111` (RPC)
    
- **JSON RPC API**: compatible with standard wallets like Trust Wallet.  
- **Cross-platform nodes**: lightweight nodes can run autonomously, even on limited hardware.

---

## Technical Details
- **Consensus:** PoW initially, upgradeable to PoS in the future.
- **Halving:** every 100,000 blocks, initial block reward 50 TEC.  
- **Transaction Fees:** only a standard fee paid to miners.  
- **Script behavior:** timer or verify-code conditions stored at the output script level; executed when conditions are met.  
- **Refunds or conditional unlocks:** handled via script execution rules, fully deterministic.

---

## Getting Started

### Prerequisites
- Rust >= 1.88.0  
- Cargo >= 1.88.0  
- Compatible OS: Linux, Windows, macOS  

### Installation & Running a Node


# Clone the repository
git clone https://github.com/TenCoin-crypto/TenCoin.git
cd TenCoin

# (Optional) create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run the node on mainnet
python tencoin_node.py --network mainnet
