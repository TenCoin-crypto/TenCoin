# tencoinlib/wallet_storage/__init__.py
"""
TCW wallet storage subsystem.

Provides the TCW v1 binary container format with:
  - Argon2id password-based key derivation  (kdf.py)
  - AES-256-GCM authenticated encryption    (encryption.py)
  - TCW binary container format             (tcw.py)

Public surface:
    save_wallet(filepath, payload_dict, password)
    load_wallet(filepath, password) -> dict
    read_header(filepath) -> TCWHeader
"""

from .tcw import save_wallet, load_wallet, read_header, TCWHeader

__all__ = ["save_wallet", "load_wallet", "read_header", "TCWHeader"]