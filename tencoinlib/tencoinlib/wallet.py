# tencoin/tencoinlib/wallet.py
"""
Main Wallet class - High-level HD wallet interface
"""
import json
import os
from typing import Dict, List, Optional, Tuple, Union

from .keys.bip32 import (
    ExtendedPrivateKey,
    ExtendedPublicKey,
    HARDENED_OFFSET,
    path_to_indices,
    derive_path_from_seed,
)
from .keys.bip39 import (
    generate_mnemonic,
    mnemonic_to_seed,
    validate_mnemonic,
)
from .keys.bip84 import get_default_address_from_seed, public_key_to_segwit_v0
from .constants import BIP44_PURPOSE, BIP84_PURPOSE, COIN_TYPE, DERIVATION_PATH
from .transaction.script import (
    build_multisig_script,
    pubkey_to_p2pkh_address,
    pubkey_to_p2sh_p2pkh_address,
    script_to_p2sh_address,
    script_to_p2wsh_address,
)


class WalletError(Exception):
    """Wallet related errors"""

    pass


class Wallet:
    """
    HD Wallet for Tencoin (BIP-39 + BIP-84 + full BIP-32).

    - Seed-based wallets: full access to xprv/xpub + private derivation
    - Watch-only wallets: created from xpub, only public derivation
    """

    def __init__(self, seed: bytes, mnemonic: str = ""):
        """
        Initialize wallet from seed.

        Args:
            seed: 64-byte seed
            mnemonic: Optional mnemonic phrase
        """
        if len(seed) != 64:
            raise WalletError(f"Invalid seed length: {len(seed)}")

        self.seed: bytes = seed
        self.mnemonic: str = mnemonic

        # Derive default BIP84 address (m/84'/COIN_TYPE'/0'/0/0)
        self.private_key, self.public_key, self.address = get_default_address_from_seed(
            seed
        )

        # Store additional info
        self.derivation_path: str = DERIVATION_PATH
        self.account_index: int = 0
        self.change_index: int = 0
        self.address_index: int = 0

        # HD / BIP32 state
        self.is_watch_only: bool = False
        self._master_xprv: Optional[ExtendedPrivateKey] = None
        self._master_xpub: Optional[ExtendedPublicKey] = None
        self._imported_xprv: Optional[str] = None
        self._imported_xpub: Optional[str] = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, strength: int = 128) -> "Wallet":
        """
        Create a new HD wallet (BIP-39 mnemonic + BIP-32/BIP-84).

        Args:
            strength: Entropy strength in bits (128 for 12 words)

        Returns:
            Wallet instance
        """
        from .keys.bip39 import generate_mnemonic as _generate_mnemonic
        from .keys.bip39 import mnemonic_to_seed as _mnemonic_to_seed

        # Generate mnemonic
        mnemonic = _generate_mnemonic(strength)

        # Convert to seed
        seed = _mnemonic_to_seed(mnemonic)

        # Create wallet
        return cls(seed, mnemonic)

    @classmethod
    def recover(cls, mnemonic: str, passphrase: str = "") -> "Wallet":
        """
        Recover wallet from mnemonic phrase.

        Args:
            mnemonic: 12, 15, 18, 21, or 24 words
            passphrase: Optional BIP-39 passphrase

        Returns:
            Wallet instance
        """
        from .keys.bip39 import validate_mnemonic as _validate_mnemonic
        from .keys.bip39 import mnemonic_to_seed as _mnemonic_to_seed

        # Validate mnemonic
        if not _validate_mnemonic(mnemonic):
            raise WalletError("Invalid mnemonic phrase")

        # Convert to seed
        seed = _mnemonic_to_seed(mnemonic, passphrase)

        # Create wallet
        return cls(seed, mnemonic)

    @classmethod
    def from_xpub(cls, xpub: str) -> "Wallet":
        """
        Create a watch-only wallet from an account/master xpub.

        The base xpub is treated as the root, and addresses are derived as
        `change/index` (e.g. 0/0, 0/1, 1/0, ...).
        """
        ext_pub = ExtendedPublicKey.from_xpub(xpub)

        # Default external address: change=0, index=0 relative to this xpub
        child_pub = ext_pub.derive_path("0/0").key
        address = public_key_to_segwit_v0(child_pub)

        wallet = cls.__new__(cls)  # bypass __init__
        wallet.seed = b""
        wallet.mnemonic = ""
        wallet.private_key = None
        wallet.public_key = child_pub.hex()
        wallet.address = address

        wallet.derivation_path = ""  # Unknown for pure xpub-based wallets
        wallet.account_index = 0
        wallet.change_index = 0
        wallet.address_index = 0

        wallet.is_watch_only = True
        wallet._master_xprv = None
        wallet._master_xpub = ext_pub
        wallet._imported_xprv = None
        wallet._imported_xpub = xpub
        return wallet

    @classmethod
    def from_xprv(cls, xprv: str) -> "Wallet":
        """
        Create a wallet from a master/account xprv.

        This does NOT require seed or mnemonic and is fully private (non watch-only).
        """
        ext_priv = ExtendedPrivateKey.from_xprv(xprv)
        ext_pub = ext_priv.to_public()

        # Default external address: change=0, index=0 relative to this xprv
        child_priv = ext_priv.derive_path("0/0")
        child_pub = child_priv.to_public().key
        address = public_key_to_segwit_v0(child_pub)

        wallet = cls.__new__(cls)  # bypass __init__
        wallet.seed = b""
        wallet.mnemonic = ""
        wallet.private_key = child_priv.key
        wallet.public_key = child_pub.hex()
        wallet.address = address

        wallet.derivation_path = ""  # Unknown from bare xprv
        wallet.account_index = 0
        wallet.change_index = 0
        wallet.address_index = 0

        wallet.is_watch_only = False
        wallet._master_xprv = ext_priv
        wallet._master_xpub = ext_pub
        wallet._imported_xprv = xprv
        wallet._imported_xpub = ext_pub.to_xpub()
        return wallet

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------
    def get_private_key_hex(self) -> str:
        """Get private key as hex string (default address)."""
        if self.is_watch_only or self.private_key is None:
            raise WalletError("Private key not available in watch-only wallet")
        return self.private_key.hex()

    def get_public_key_hex(self) -> str:
        """Get public key as hex string (default address)."""
        return self.public_key

    def get_address(
        self,
        type: str = "p2wpkh",
        script: Optional[bytes] = None,
    ) -> str:
        """
        Get address for the current key in the requested form.

        Args:
            type: One of "p2wpkh", "p2pkh", "p2sh", "p2wsh".
                - p2wpkh: SegWit v0 native (tc1q...) — default
                - p2pkh: Legacy pay-to-pubkey-hash (T...)
                - p2sh: Pay-to-script-hash (M...). If script is None, uses
                  single-sig P2SH(P2PKH). If script is provided, uses that
                  redeem script (e.g. multisig).
                - p2wsh: SegWit v0 script (tc1q... 32-byte). script is required
                  (witness script, e.g. multisig).
            script: For "p2sh" or "p2wsh", optional (p2sh) or required (p2wsh)
                redeem/witness script bytes.

        Returns:
            Address string (tc1q..., T..., or M...).

        Example:
            w = Wallet.create()
            w.get_address()                # tc1q...
            w.get_address("p2pkh")         # T...
            w.get_address("p2sh")          # M... (single-sig P2SH)
            w.get_address("p2sh", script=redeem_script)  # M... (custom/multisig)
            w.get_address("p2wsh", script=witness_script)  # tc1q... (e.g. 2-of-3)
        """
        addr_type = (type or "p2wpkh").lower().strip()

        if addr_type == "p2wpkh":
            # Default native SegWit address (BIP-84: m/84'/COIN_TYPE'/0'/0/0)
            return self.address
        if addr_type == "p2pkh":
            # Standard BIP-44 P2PKH address: m/44'/COIN_TYPE'/0'/0/0
            pubkey_bytes = self._derive_bip44_pubkey(account=0, change=0, index=0)
            return pubkey_to_p2pkh_address(pubkey_bytes)
        if addr_type == "p2sh":
            # Single-sig P2SH(P2PKH) using BIP-44 key by default
            if script is None:
                pubkey_bytes = self._derive_bip44_pubkey(account=0, change=0, index=0)
                return pubkey_to_p2sh_p2pkh_address(pubkey_bytes)
            return script_to_p2sh_address(script)
        if addr_type == "p2wsh":
            if script is None:
                raise WalletError("get_address('p2wsh') requires script= (witness script)")
            return script_to_p2wsh_address(script)
        raise WalletError(f"Unknown address type: {type!r}. Use p2wpkh, p2pkh, p2sh, or p2wsh.")

    @staticmethod
    def build_multisig_script(
        m: int,
        pubkeys: List[Union[bytes, str]],
        sort_pubkeys: bool = True,
    ) -> bytes:
        """
        Build standard m-of-n multisig redeem/witness script (for P2SH or P2WSH).

        Args:
            m: Required signatures (1..16).
            pubkeys: List of 33-byte compressed public keys (bytes or hex strings).
            sort_pubkeys: If True, sort pubkeys for canonical form (recommended).

        Returns:
            Script bytes to pass to get_address("p2sh", script=...) or
            get_address("p2wsh", script=...).

        Example:
            # 2-of-3 P2WSH: build script from three public keys (bytes or hex)
            script = Wallet.build_multisig_script(2, [pk1, pk2, pk3])
            addr = w.get_address("p2wsh", script=script)
        """
        normalized = []
        for p in pubkeys:
            if isinstance(p, str):
                p = bytes.fromhex(p)
            normalized.append(p)
        return build_multisig_script(m, normalized, sort_pubkeys=sort_pubkeys)

    def get_mnemonic(self) -> str:
        """Get mnemonic phrase."""
        if not self.mnemonic:
            raise WalletError("Mnemonic not available")
        return self.mnemonic

    # ------------------------------------------------------------------
    # Internal helpers for BIP32 master keys
    # ------------------------------------------------------------------
    def _ensure_master_xprv(self) -> ExtendedPrivateKey:
        if self.is_watch_only:
            raise WalletError("Master xprv not available in watch-only wallet")
        if self._master_xprv is None:
            self._master_xprv = ExtendedPrivateKey.from_seed(self.seed)
        return self._master_xprv

    def _ensure_master_xpub(self) -> ExtendedPublicKey:
        if self._master_xpub is not None:
            return self._master_xpub

        if self._master_xprv is not None:
            self._master_xpub = self._master_xprv.to_public()
        elif not self.is_watch_only:
            # Derive from seed
            self._master_xprv = ExtendedPrivateKey.from_seed(self.seed)
            self._master_xpub = self._master_xprv.to_public()
        else:
            raise WalletError("No xpub available for this wallet")

        return self._master_xpub

    # ------------------------------------------------------------------
    # Internal helpers for standard BIP44/BIP84 derivation
    # ------------------------------------------------------------------
    def _derive_bip44_pubkey(
        self, account: int = 0, change: int = 0, index: int = 0
    ) -> bytes:
        """
        Derive compressed public key at standard BIP-44 path:
        m/44'/COIN_TYPE'/account'/change/index
        """
        if not self.seed:
            raise WalletError("BIP-44 derivation requires seed-backed wallet")

        from .keys.ec import privkey_to_pubkey

        path = f"m/{BIP44_PURPOSE}'/{COIN_TYPE}'/{account}'/{change}/{index}"
        private_key, _ = derive_path_from_seed(self.seed, path)
        return privkey_to_pubkey(private_key, compressed=True)

    # ------------------------------------------------------------------
    # Core BIP32 API
    # ------------------------------------------------------------------
    def get_master_xprv(self) -> str:
        """
        Return master xprv (m) as Base58Check-encoded string.

        Only available for non-watch-only wallets.
        """
        master = self._ensure_master_xprv()
        return master.to_xprv()

    def get_master_xpub(self) -> str:
        """
        Return master xpub (m) as Base58Check-encoded string.
        """
        master_pub = self._ensure_master_xpub()
        return master_pub.to_xpub()

    def derive_xprv(self, path: str) -> str:
        """
        Derive extended private key at arbitrary BIP32 path (e.g. "m/84'/5353'/0'").

        Only available for non-watch-only wallets.
        """
        master = self._ensure_master_xprv()
        node = master.derive_path(path)
        return node.to_xprv()

    def derive_xpub(self, path: str) -> str:
        """
        Derive extended public key at arbitrary BIP32 path.

        - For full wallets (with seed/xprv): hardened or non-hardened steps allowed.
        - For watch-only wallets (xpub-only): only non-hardened steps allowed.
        """
        if not path.startswith("m"):
            raise WalletError("Path must be absolute and start with 'm'")

        if not self.is_watch_only:
            master = self._ensure_master_xprv()
            node = master.derive_path(path)
            return node.to_public().to_xpub()

        # Watch-only: derive purely from xpub (no hardened indices)
        master_pub = self._ensure_master_xpub()
        indices = path_to_indices(path)
        node = master_pub
        for index in indices:
            if index >= HARDENED_OFFSET:
                raise WalletError(
                    "Cannot derive hardened child from xpub-only watch-only wallet"
                )
            node = node.child(index)
        return node.to_xpub()

    # ------------------------------------------------------------------
    # Account-level BIP84 API (m/84'/COIN_TYPE'/account')
    # ------------------------------------------------------------------
    def _account_path(self, account: int) -> str:
        return f"m/{BIP84_PURPOSE}'/{COIN_TYPE}'/{account}'"

    def get_account_xprv(self, account: int) -> str:
        """
        Get account-level xprv at m/84'/COIN_TYPE'/account'.

        Only for non-watch-only wallets.
        """
        path = self._account_path(account)
        return self.derive_xprv(path)

    def get_account_xpub(self, account: int) -> str:
        """
        Get account-level xpub at m/84'/COIN_TYPE'/account'.
        """
        path = self._account_path(account)
        return self.derive_xpub(path)

    # ------------------------------------------------------------------
    # Address derivation (private + watch-only)
    # ------------------------------------------------------------------
    def derive_address(
        self, account: int = 0, change: int = 0, index: int = 0
    ) -> Tuple[str, str]:
        """
        Derive address at specific BIP84 path from seed.

        Args:
            account: Account number
            change: 0 for external, 1 for change
            index: Address index

        Returns:
            (private_key_hex, address)
        """
        if self.is_watch_only:
            raise WalletError("Cannot derive private addresses from watch-only wallet")

        from .keys.bip84 import derive_bip84_address_from_seed

        private_key, address = derive_bip84_address_from_seed(
            self.seed, account, change, index
        )

        return private_key.hex(), address

    def get_next_address(self, change: int = 0) -> Tuple[str, str]:
        """
        Get next unused address in sequence (private wallet only).

        Args:
            change: 0 for external, 1 for change

        Returns:
            (private_key_hex, address)
        """
        if self.is_watch_only:
            raise WalletError("Cannot derive next address from watch-only wallet")

        if change == 0:
            self.address_index += 1
        else:
            self.change_index += 1

        return self.derive_address(
            self.account_index,
            change,
            self.address_index if change == 0 else self.change_index,
        )

    def derive_address_from_xpub(self, change: int, index: int) -> str:
        """
        Derive address from the wallet's base xpub (watch-only or full).

        The stored xpub is treated as root and `change/index` is derived
        relative to it. For BIP84 account xpubs, this corresponds to
        m/84'/COIN_TYPE'/account'/change/index.
        """
        base_xpub = self._ensure_master_xpub()
        child_pub = base_xpub.derive_path(f"{change}/{index}").key
        return public_key_to_segwit_v0(child_pub)

    # ------------------------------------------------------------------
    # Generic export/import for xpub/xprv
    # ------------------------------------------------------------------
    def export_xpub(self, path: str) -> str:
        """Export xpub at arbitrary BIP32 path."""
        return self.derive_xpub(path)

    def export_xprv(self, path: str) -> str:
        """Export xprv at arbitrary BIP32 path (non-watch-only only)."""
        return self.derive_xprv(path)

    def import_xpub(self, xpub: str) -> None:
        """
        Import an external xpub and treat it as the wallet's base xpub
        for watch-only derivation (derive_address_from_xpub).
        """
        ext_pub = ExtendedPublicKey.from_xpub(xpub)
        self._master_xpub = ext_pub
        self._imported_xpub = xpub

    def import_xprv(self, xprv: str) -> None:
        """
        Import an external xprv and treat it as the wallet's base xprv/xpub.
        """
        ext_priv = ExtendedPrivateKey.from_xprv(xprv)
        self._master_xprv = ext_priv
        self._master_xpub = ext_priv.to_public()
        self._imported_xprv = xprv
        self._imported_xpub = self._master_xpub.to_xpub()
        self.is_watch_only = False

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict:
        """Convert wallet to dictionary (JSON-serializable)."""
        return {
            "mnemonic": self.mnemonic if self.mnemonic else None,
            "address": self.address,
            "public_key": self.public_key,
            "private_key": None
            if self.is_watch_only or self.private_key is None
            else self.get_private_key_hex(),
            "derivation_path": self.derivation_path,
            "account_index": self.account_index,
            "change_index": self.change_index,
            "address_index": self.address_index,
            "seed_available": bool(self.mnemonic),
            "is_watch_only": self.is_watch_only,
            "imported_xpub": self._imported_xpub,
            "imported_xprv": self._imported_xprv,
        }

    def save_to_file(self, filepath: str, password: Optional[str] = None) -> None:
        """
        Save wallet to (optionally encrypted) file.

        NOTE: Encryption is not yet implemented.
        """
        data = self.to_dict()

        if password:
            # TODO: Implement encryption
            raise NotImplementedError("Wallet encryption not yet implemented")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, password: Optional[str] = None) -> "Wallet":
        """
        Load wallet from file.

        Currently only mnemonic-based wallets are restored; watch-only /
        xpub/xprv-only metadata is ignored on load.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if password:
            # TODO: Implement decryption
            raise NotImplementedError("Wallet decryption not yet implemented")

        if data.get("mnemonic"):
            return cls.recover(data["mnemonic"])
        else:
            raise WalletError("Cannot load wallet without mnemonic")