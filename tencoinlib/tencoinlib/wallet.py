# tencoinlib/wallet.py
"""
Main Wallet class — HD wallet with locked/unlocked state machine.

Security model
--------------
A Wallet object can be in one of two states:

  LOCKED
    - No secret material (seed, mnemonic, xprv, private keys) is held in RAM.
    - Public metadata (address, xpub, derivation path, indices) is available.
    - The .tcw file on disk is always encrypted.

  UNLOCKED
    - Secret material is present in volatile attributes (_seed, _mnemonic,
      _master_xprv, _imported_xprv).
    - All wallet operations are available.
    - Call lock() or use the context manager to discard secrets from RAM.

Lifecycle:
    wallet = Wallet.create(password)         # new wallet → LOCKED
    wallet = Wallet.recover(mnemonic, pw)    # from mnemonic → LOCKED
    wallet = Wallet.load("wallet.tcw")       # load header only → LOCKED

    wallet.save("wallet.tcw", password)      # encrypt → disk
    wallet.unlock(password)                  # decrypt → UNLOCKED
    wallet.sign_transaction(...)             # requires UNLOCKED
    wallet.lock()                            # zeroize → LOCKED

    # Context-manager form (auto-lock):
    with wallet.unlocked(password):
        tx = wallet.sign_transaction(...)

File format
-----------
Files use the TCW v1 binary format (see wallet_storage/tcw.py):
    AES-256-GCM encryption, Argon2id KDF, binary header with AAD.

Address types
-------------
The wallet's *canonical* address type is determined at construction:
  - create() / recover()  → P2WPKH (BIP-84, m/84'/COIN_TYPE'/0'/0/0)
  - from_xpub()           → P2WPKH (derived from provided xpub at 0/0)
  - from_xprv()           → P2WPKH (derived from provided xprv at 0/0)

get_address(type=...) still allows on-the-fly derivation of other
address forms (P2PKH, P2SH, P2WSH) from the seed, but these are
*not* the canonical wallet identity and are not stored in the .tcw file.
"""

import json
import os
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional, Tuple, Union

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
from .wallet_storage import save_wallet, load_wallet, read_header, TCWHeader
from .wallet_storage.tcw import TCWFormatError, TCWAuthError, TCWVersionError
from .wallet_storage.kdf import verify_password_strength


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WalletError(Exception):
    """General wallet error."""


class WalletLockedError(WalletError):
    """Raised when a secret-requiring operation is attempted on a locked wallet."""


class WalletAuthError(WalletError):
    """Raised when unlock() is called with the wrong password."""


# ---------------------------------------------------------------------------
# Wallet class
# ---------------------------------------------------------------------------

class Wallet:
    """
    HD Wallet for Tencoin (BIP-39 + BIP-84 + full BIP-32).

    Supports:
      - Seed-based wallets (create / recover)
      - xpub-only watch-only wallets (from_xpub)
      - xprv-only wallets without mnemonic (from_xprv)
      - Locked / unlocked state machine with TCW v1 encrypted storage
    """

    # ------------------------------------------------------------------
    # Construction helpers  (internal — do not call directly)
    # ------------------------------------------------------------------

    def __new__(cls) -> "Wallet":
        """Allocate a blank Wallet; all attributes set by class-methods."""
        instance = super().__new__(cls)
        # Public / non-secret metadata
        instance.address:          str  = ""
        instance.public_key:       str  = ""
        instance.derivation_path:  str  = ""
        instance.account_index:    int  = 0
        instance.change_index:     int  = 0
        instance.address_index:    int  = 0
        instance.is_watch_only:    bool = False
        instance._wallet_type:     str  = "hd"  # "hd" | "xpub" | "xprv"

        # Public extended keys (not secret; available while locked)
        instance._master_xpub:    Optional[ExtendedPublicKey] = None
        instance._imported_xpub:  Optional[str]               = None

        # Volatile / secret attributes — None when locked
        instance._seed:           Optional[bytes]              = None
        instance._mnemonic:       Optional[str]                = None
        instance._master_xprv:    Optional[ExtendedPrivateKey] = None
        instance._private_key:    Optional[bytes]              = None
        instance._imported_xprv:  Optional[str]               = None

        instance._locked:         bool = True
        return instance

    # ------------------------------------------------------------------
    # Public constructors
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, strength: int = 128) -> "Wallet":
        """
        Create a new HD wallet (BIP-39 mnemonic + BIP-32/BIP-84).

        The returned wallet is UNLOCKED (secrets are in RAM).
        Call save() to persist to a TCW file, then lock() or use the
        context manager.

        Args:
            strength: Entropy strength in bits (128 → 12 words).

        Returns:
            UNLOCKED Wallet instance.
        """
        mnemonic = generate_mnemonic(strength)
        seed     = mnemonic_to_seed(mnemonic)
        return cls._from_seed(seed, mnemonic)

    @classmethod
    def recover(cls, mnemonic: str, passphrase: str = "") -> "Wallet":
        """
        Recover wallet from mnemonic phrase.

        The returned wallet is UNLOCKED.

        Args:
            mnemonic:   12/15/18/21/24-word BIP-39 phrase.
            passphrase: Optional BIP-39 passphrase.

        Returns:
            UNLOCKED Wallet instance.
        """
        if not validate_mnemonic(mnemonic):
            raise WalletError("Invalid mnemonic phrase")
        seed = mnemonic_to_seed(mnemonic, passphrase)
        return cls._from_seed(seed, mnemonic)

    @classmethod
    def from_xpub(cls, xpub: str) -> "Wallet":
        """
        Create a watch-only wallet from an account/master xpub.

        The base xpub is treated as the root; addresses are derived as
        change/index (e.g. 0/0, 0/1, 1/0, …).

        The returned wallet is UNLOCKED (xpub is not secret).
        Watch-only wallets cannot sign transactions.
        """
        ext_pub   = ExtendedPublicKey.from_xpub(xpub)
        child_pub = ext_pub.derive_path("0/0").key
        address   = public_key_to_segwit_v0(child_pub)

        w = cls()
        w.address         = address
        w.public_key      = child_pub.hex()
        w.is_watch_only   = True
        w._wallet_type    = "xpub"
        w._master_xpub    = ext_pub
        w._imported_xpub  = xpub
        w._locked         = False   # xpub is not secret
        return w

    @classmethod
    def from_xprv(cls, xprv: str) -> "Wallet":
        """
        Create a wallet from a master/account xprv.

        No mnemonic or seed required.  The returned wallet is UNLOCKED.
        """
        ext_priv  = ExtendedPrivateKey.from_xprv(xprv)
        ext_pub   = ext_priv.to_public()
        child_priv = ext_priv.derive_path("0/0")
        child_pub  = child_priv.to_public().key
        address    = public_key_to_segwit_v0(child_pub)

        w = cls()
        w.address         = address
        w.public_key      = child_pub.hex()
        w.is_watch_only   = False
        w._wallet_type    = "xprv"
        w._master_xprv    = ext_priv
        w._master_xpub    = ext_pub
        w._private_key    = child_priv.key
        w._imported_xprv  = xprv
        w._imported_xpub  = ext_pub.to_xpub()
        w._locked         = False
        return w

    @classmethod
    def _resolve_filepath(cls, filepath: str) -> str:
        """
        Resolve the actual path of a TCW file.

        Rules:
        - If the caller supplied a ``.tcw`` extension (case-insensitive),
          use the path as-is (and raise FileNotFoundError if not found).
        - If NO extension was given, first try ``filepath`` as-is; if that
          does not exist, append ``.tcw`` and try again.

        Examples:
            "my_wallet"          → tries my_wallet, then my_wallet.tcw
            "my_wallet.tcw"      → uses my_wallet.tcw  (exact)
            "backup.TCW"         → uses backup.TCW      (exact)
        """
        has_extension = filepath.lower().endswith(".tcw")

        if has_extension:
            # Caller was explicit — honour it exactly.
            return filepath

        # No extension: try the bare name first, then with .tcw appended.
        if os.path.exists(filepath):
            return filepath

        with_ext = filepath + ".tcw"
        if os.path.exists(with_ext):
            return with_ext

        # Neither exists — raise a helpful error pointing to the .tcw variant.
        raise FileNotFoundError(
            f"Wallet file not found: '{filepath}' or '{with_ext}'"
        )

    @classmethod
    def load(cls, filepath: str) -> "Wallet":
        """
        Load a TCW wallet file WITHOUT decrypting it.

        The returned wallet is LOCKED.  Call unlock(password) before
        using any operation that requires secret material.

        The ``.tcw`` extension is resolved automatically if omitted:
            Wallet.load("my_wallet")      # finds my_wallet.tcw automatically
            Wallet.load("my_wallet.tcw")  # explicit path, used as-is
            Wallet.load("backup.TCW")     # explicit path, used as-is

        To go directly to an unlocked wallet:
            wallet = Wallet.load(path).unlock(password)
            # or
            with Wallet.load(path).unlocked(password) as wallet:
                ...

        Args:
            filepath:  Path to a .tcw file (extension optional).

        Returns:
            LOCKED Wallet instance.

        Raises:
            TCWFormatError:    File is not a valid TCW container.
            TCWVersionError:   File version is not supported.
            FileNotFoundError: File does not exist.
        """
        filepath = cls._resolve_filepath(filepath)

        # Validate that it's a real TCW file by reading the header.
        _header: TCWHeader = read_header(filepath)   # raises on bad magic/version

        w = cls()
        w._tcw_filepath = filepath
        w._locked       = True
        return w

    # ------------------------------------------------------------------
    # Lock / unlock
    # ------------------------------------------------------------------

    def unlock(self, password: str) -> "Wallet":
        """
        Decrypt the wallet's TCW file and load secrets into RAM.

        Sets the wallet state to UNLOCKED.  Returns self for chaining:
            wallet.unlock(password).sign_transaction(tx)

        Args:
            password:  The passphrase used when the wallet was saved.

        Returns:
            self (UNLOCKED)

        Raises:
            WalletAuthError:  Wrong password or corrupted file.
            WalletError:      If the wallet was not created via load()
                              (has no associated TCW file).
            TCWFormatError:   If the file is structurally invalid.
        """
        if not self._locked:
            return self   # already unlocked

        filepath = getattr(self, "_tcw_filepath", None)
        if not filepath:
            raise WalletError(
                "unlock() requires a wallet loaded from a .tcw file. "
                "Use Wallet.load(filepath) first."
            )

        try:
            payload = load_wallet(filepath, password)
        except TCWAuthError as exc:
            raise WalletAuthError(str(exc)) from exc

        self._load_from_payload(payload)
        self._locked = False
        return self

    def lock(self) -> None:
        """
        Discard all secret material from RAM and set state to LOCKED.

        Best-effort zeroization is performed where Python allows it.
        Public metadata (address, xpub, indices) is preserved.
        """
        # Zeroize bytearray secrets where possible
        _zeroize_attr(self, "_seed")
        _zeroize_attr(self, "_private_key")

        # Drop all secret references
        self._seed          = None
        self._mnemonic      = None
        self._master_xprv   = None
        self._private_key   = None
        self._imported_xprv = None

        self._locked = True

    @contextmanager
    def unlocked(self, password: str) -> Generator["Wallet", None, None]:
        """
        Context manager: unlock, yield self, then lock automatically.

        Usage:
            with wallet.unlocked("my-password") as w:
                signed_tx = w.sign_transaction(tx)
        """
        self.unlock(password)
        try:
            yield self
        finally:
            self.lock()

    @property
    def is_locked(self) -> bool:
        """True when no secret material is held in RAM."""
        return self._locked

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_filepath(filepath: str) -> str:
        """
        Ensure filepath ends with .tcw (case-insensitive), then find a
        non-colliding filename by appending ``_N`` before the extension
        if the resolved path already exists on disk.

        The suffix uses the preserved original extension casing so that
        ``backup.TCW`` stays ``backup.TCW``, not ``backup.tcw``.

        Examples (assuming my_wallet.tcw already exists on disk):
            "my_wallet"        → "my_wallet_1.tcw"
            "my_wallet.tcw"    → "my_wallet_1.tcw"
            "my_wallet_1.tcw"  → "my_wallet_2.tcw"   (if _1 also exists)
            "new_wallet"       → "new_wallet.tcw"     (no conflict)
            "backup.TCW"       → "backup.TCW"         (no conflict, casing kept)
        """
        # 1. Ensure extension is present; remember the original suffix casing.
        if filepath.lower().endswith(".tcw"):
            # Already has extension — split it off to get stem + ext.
            stem = filepath[:-4]          # everything before ".tcw" / ".TCW"
            ext  = filepath[-4:]          # ".tcw" / ".TCW" (original casing)
        else:
            stem = filepath
            ext  = ".tcw"

        candidate = stem + ext

        # 2. No conflict → done.
        if not os.path.exists(candidate):
            return candidate

        # 3. Strip any existing trailing _N suffix from stem so that calling
        #    save("my_wallet_1") when _1 already exists produces _2, not _1_1.
        import re
        base_stem = re.sub(r"_\d+$", "", stem)

        # 4. Increment counter until a free slot is found.
        counter = 1
        while True:
            candidate = f"{base_stem}_{counter}{ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def save(self, filepath: str, password: str) -> str:
        """
        Encrypt and write the wallet to a TCW v1 file.

        The wallet MUST be unlocked to save (secrets need to be in RAM
        so they can be serialised and encrypted).

        **Extension handling** — ``.tcw`` is added automatically if omitted:
            wallet.save("my_wallet", ...)      → my_wallet.tcw
            wallet.save("my_wallet.tcw", ...)  → my_wallet.tcw  (unchanged)
            wallet.save("backup.TCW", ...)     → backup.TCW     (unchanged)

        **Collision avoidance** — if the resolved filename already exists,
        a numeric suffix is appended before the extension:
            my_wallet.tcw exists   → saves as  my_wallet_1.tcw
            my_wallet_1.tcw exists → saves as  my_wallet_2.tcw

        Args:
            filepath: Destination path.  Extension ``.tcw`` is appended
                      automatically if not present.
            password: Passphrase used to derive the AES-256 key.
                      Must be at least 8 characters.

        Returns:
            The actual path the file was written to (useful when a
            collision was resolved automatically).

        Raises:
            WalletLockedError: Wallet is locked; call unlock() first.
            ValueError:        Password is too short.
        """
        self._require_unlocked("save")
        verify_password_strength(password)

        filepath = self._normalize_filepath(filepath)
        payload  = self._to_payload()
        save_wallet(filepath, payload, password)

        # Remember the file path so unlock() can find it later.
        self._tcw_filepath = filepath
        return filepath

    # Legacy aliases for backward compatibility
    def save_to_file(self, filepath: str, password: str) -> str:
        """Alias for save(). Returns the actual path written (collision-safe)."""
        return self.save(filepath, password)

    @classmethod
    def load_from_file(cls, filepath: str, password: str) -> "Wallet":
        """
        Load and fully decrypt a TCW wallet file, returning an UNLOCKED wallet.

        This is a convenience method equivalent to:
            Wallet.load(filepath).unlock(password)

        The ``.tcw`` extension is resolved automatically if omitted
        (see :meth:`load` for details).

        Args:
            filepath:  Path to a .tcw file (extension optional).
            password:  Passphrase.

        Returns:
            UNLOCKED Wallet instance.
        """
        return cls.load(filepath).unlock(password)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def wallet_type(self) -> str:
        """One of "hd", "xpub", "xprv"."""
        return self._wallet_type

    # ------------------------------------------------------------------
    # Basic accessors  (require UNLOCKED for secret material)
    # ------------------------------------------------------------------

    def get_private_key_hex(self) -> str:
        """Get canonical private key as hex (UNLOCKED required)."""
        self._require_unlocked("get_private_key_hex")
        if self.is_watch_only or self._private_key is None:
            raise WalletError("Private key not available in watch-only wallet")
        return self._private_key.hex()

    def get_public_key_hex(self) -> str:
        """Get canonical public key as hex (available while locked)."""
        return self.public_key

    def get_mnemonic(self) -> str:
        """Get mnemonic phrase (UNLOCKED required)."""
        self._require_unlocked("get_mnemonic")
        if not self._mnemonic:
            raise WalletError("Mnemonic not available for this wallet type")
        return self._mnemonic

    def get_address(
        self,
        type: str = "p2wpkh",
        script: Optional[bytes] = None,
    ) -> str:
        """
        Return an address for the current key in the requested form.

        For p2wpkh: available while locked (uses public metadata).
        For p2pkh / p2sh: requires UNLOCKED (seed derivation needed).
        For p2wsh: script= required, no unlock needed if script is provided.

        Args:
            type:   "p2wpkh" | "p2pkh" | "p2sh" | "p2wsh"
            script: For p2sh (optional) or p2wsh (required).

        Returns:
            Address string.
        """
        addr_type = (type or "p2wpkh").lower().strip()

        if addr_type == "p2wpkh":
            return self.address

        if addr_type == "p2pkh":
            self._require_unlocked("get_address('p2pkh')")
            pubkey_bytes = self._derive_bip44_pubkey(account=0, change=0, index=0)
            return pubkey_to_p2pkh_address(pubkey_bytes)

        if addr_type == "p2sh":
            if script is None:
                self._require_unlocked("get_address('p2sh')")
                pubkey_bytes = self._derive_bip44_pubkey(account=0, change=0, index=0)
                return pubkey_to_p2sh_p2pkh_address(pubkey_bytes)
            return script_to_p2sh_address(script)

        if addr_type == "p2wsh":
            if script is None:
                raise WalletError(
                    "get_address('p2wsh') requires script= (witness script)"
                )
            return script_to_p2wsh_address(script)

        raise WalletError(
            f"Unknown address type: {type!r}. Use p2wpkh, p2pkh, p2sh, or p2wsh."
        )

    # ------------------------------------------------------------------
    # Multisig helper
    # ------------------------------------------------------------------

    @staticmethod
    def build_multisig_script(
        m: int,
        pubkeys: List[Union[bytes, str]],
        sort_pubkeys: bool = True,
    ) -> bytes:
        """
        Build standard m-of-n multisig redeem/witness script.

        Args:
            m:           Required signatures (1..16).
            pubkeys:     33-byte compressed public keys (bytes or hex).
            sort_pubkeys: Sort for canonical form (recommended).

        Returns:
            Script bytes for get_address("p2sh", script=…) or
            get_address("p2wsh", script=…).
        """
        normalized = [
            bytes.fromhex(p) if isinstance(p, str) else p
            for p in pubkeys
        ]
        return build_multisig_script(m, normalized, sort_pubkeys=sort_pubkeys)

    # ------------------------------------------------------------------
    # Core BIP-32 API  (UNLOCKED required for xprv operations)
    # ------------------------------------------------------------------

    def get_master_xprv(self) -> str:
        """Master xprv as Base58Check string (UNLOCKED required)."""
        self._require_unlocked("get_master_xprv")
        return self._ensure_master_xprv().to_xprv()

    def get_master_xpub(self) -> str:
        """Master xpub as Base58Check string (available while locked)."""
        return self._ensure_master_xpub().to_xpub()

    def derive_xprv(self, path: str) -> str:
        """Derive xprv at path (UNLOCKED required)."""
        self._require_unlocked("derive_xprv")
        return self._ensure_master_xprv().derive_path(path).to_xprv()

    def derive_xpub(self, path: str) -> str:
        """
        Derive xpub at path.

        Full wallets: hardened or non-hardened steps.
        Watch-only:   non-hardened only.
        """
        if not path.startswith("m"):
            raise WalletError("Path must be absolute and start with 'm'")

        if not self.is_watch_only:
            self._require_unlocked("derive_xpub (hardened path)")
            return self._ensure_master_xprv().derive_path(path).to_public().to_xpub()

        master_pub = self._ensure_master_xpub()
        for index in path_to_indices(path):
            if index >= HARDENED_OFFSET:
                raise WalletError(
                    "Cannot derive hardened child from xpub-only watch-only wallet"
                )
            master_pub = master_pub.child(index)
        return master_pub.to_xpub()

    # ------------------------------------------------------------------
    # Account-level BIP-84 API
    # ------------------------------------------------------------------

    def _account_path(self, account: int) -> str:
        return f"m/{BIP84_PURPOSE}'/{COIN_TYPE}'/{account}'"

    def get_account_xprv(self, account: int) -> str:
        """Account xprv at m/84'/COIN_TYPE'/account' (UNLOCKED required)."""
        return self.derive_xprv(self._account_path(account))

    def get_account_xpub(self, account: int) -> str:
        """Account xpub at m/84'/COIN_TYPE'/account'."""
        return self.derive_xpub(self._account_path(account))

    # ------------------------------------------------------------------
    # Address derivation
    # ------------------------------------------------------------------

    def derive_address(
        self, account: int = 0, change: int = 0, index: int = 0
    ) -> Tuple[str, str]:
        """
        Derive BIP-84 address at specific path (UNLOCKED required).

        Returns:
            (private_key_hex, address)
        """
        self._require_unlocked("derive_address")
        if self.is_watch_only:
            raise WalletError("Cannot derive private addresses from watch-only wallet")

        from .keys.bip84 import derive_bip84_address_from_seed

        private_key, address = derive_bip84_address_from_seed(
            self._seed, account, change, index
        )
        return private_key.hex(), address

    def get_next_address(self, change: int = 0) -> Tuple[str, str]:
        """
        Increment address index and return the next address (UNLOCKED required).

        Returns:
            (private_key_hex, address)
        """
        self._require_unlocked("get_next_address")
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
        Derive address from the wallet's base xpub (watch-only safe).

        The stored xpub is treated as root; change/index is derived
        relative to it.
        """
        base_xpub = self._ensure_master_xpub()
        child_pub  = base_xpub.derive_path(f"{change}/{index}").key
        return public_key_to_segwit_v0(child_pub)

    # ------------------------------------------------------------------
    # Generic export / import for xpub / xprv
    # ------------------------------------------------------------------

    def export_xpub(self, path: str) -> str:
        """Export xpub at arbitrary BIP-32 path."""
        return self.derive_xpub(path)

    def export_xprv(self, path: str) -> str:
        """Export xprv at arbitrary BIP-32 path (UNLOCKED required)."""
        return self.derive_xprv(path)

    def import_xpub(self, xpub: str) -> None:
        """Import external xpub as the wallet's base xpub for watch-only derivation."""
        ext_pub           = ExtendedPublicKey.from_xpub(xpub)
        self._master_xpub = ext_pub
        self._imported_xpub = xpub

    def import_xprv(self, xprv: str) -> None:
        """Import external xprv (UNLOCKED required for secret storage)."""
        self._require_unlocked("import_xprv")
        ext_priv              = ExtendedPrivateKey.from_xprv(xprv)
        self._master_xprv     = ext_priv
        self._master_xpub     = ext_priv.to_public()
        self._imported_xprv   = xprv
        self._imported_xpub   = self._master_xpub.to_xpub()
        self.is_watch_only    = False

    # ------------------------------------------------------------------
    # Serialisation  (internal)
    # ------------------------------------------------------------------

    def _to_payload(self) -> Dict:
        """
        Build the dict that goes into the encrypted TCW payload.

        All secret fields are included.  Public fields are included too
        for full restore without re-derivation, and for privacy (no
        metadata leaks even for xpub).
        """
        self._require_unlocked("_to_payload")
        return {
            "format":          "TCW",
            "version":         1,
            "wallet_type":     self._wallet_type,
            # --- secret material ---
            "mnemonic":        self._mnemonic,
            "seed_hex":        self._seed.hex() if self._seed else None,
            "imported_xprv":   self._imported_xprv,
            # --- public material (kept inside payload for privacy) ---
            "imported_xpub":   self._imported_xpub,
            "address":         self.address,
            "public_key":      self.public_key,
            "derivation_path": self.derivation_path,
            "account_index":   self.account_index,
            "change_index":    self.change_index,
            "address_index":   self.address_index,
            "is_watch_only":   self.is_watch_only,
        }

    def _load_from_payload(self, payload: Dict) -> None:
        """
        Restore wallet state from a decrypted TCW payload dict.
        Called by unlock() after successful decryption.
        """
        fmt = payload.get("format")
        if fmt != "TCW":
            raise WalletError(f"Unexpected payload format: {fmt!r}")

        wallet_type = payload.get("wallet_type", "hd")
        self._wallet_type    = wallet_type
        self.is_watch_only   = payload.get("is_watch_only", False)
        self.address         = payload.get("address", "")
        self.public_key      = payload.get("public_key", "")
        self.derivation_path = payload.get("derivation_path", "")
        self.account_index   = payload.get("account_index", 0)
        self.change_index    = payload.get("change_index", 0)
        self.address_index   = payload.get("address_index", 0)
        self._imported_xpub  = payload.get("imported_xpub")

        # Restore public extended key (not secret)
        if self._imported_xpub:
            self._master_xpub = ExtendedPublicKey.from_xpub(self._imported_xpub)

        # Restore secret material
        mnemonic = payload.get("mnemonic")
        seed_hex = payload.get("seed_hex")
        imp_xprv = payload.get("imported_xprv")

        if wallet_type == "hd":
            if mnemonic:
                self._mnemonic   = mnemonic
                self._seed       = bytes.fromhex(seed_hex) if seed_hex else mnemonic_to_seed(mnemonic)
                priv, pub, addr  = get_default_address_from_seed(self._seed)
                self._private_key = priv
                self.public_key   = pub
                self.address      = addr
                # Lazily derive master keys on demand
            elif seed_hex:
                self._seed        = bytes.fromhex(seed_hex)
                priv, pub, addr   = get_default_address_from_seed(self._seed)
                self._private_key = priv
                self.public_key   = pub
                self.address      = addr
            else:
                raise WalletError("HD wallet payload is missing mnemonic and seed")

        elif wallet_type == "xprv":
            if not imp_xprv:
                raise WalletError("xprv wallet payload is missing imported_xprv")
            self._imported_xprv = imp_xprv
            ext_priv            = ExtendedPrivateKey.from_xprv(imp_xprv)
            self._master_xprv   = ext_priv
            self._master_xpub   = ext_priv.to_public()
            child_priv          = ext_priv.derive_path("0/0")
            self._private_key   = child_priv.key

        elif wallet_type == "xpub":
            # Watch-only: no secret material to restore
            pass

        else:
            raise WalletError(f"Unknown wallet_type in payload: {wallet_type!r}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_unlocked(self, operation: str = "") -> None:
        if self._locked:
            op_str = f" for '{operation}'" if operation else ""
            raise WalletLockedError(
                f"Wallet is locked{op_str}. Call unlock(password) first."
            )

    def _ensure_master_xprv(self) -> ExtendedPrivateKey:
        if self.is_watch_only:
            raise WalletError("Master xprv not available in watch-only wallet")
        if self._master_xprv is None:
            if self._seed is None:
                raise WalletLockedError(
                    "Seed not available. Call unlock(password) first."
                )
            self._master_xprv = ExtendedPrivateKey.from_seed(self._seed)
        return self._master_xprv

    def _ensure_master_xpub(self) -> ExtendedPublicKey:
        if self._master_xpub is not None:
            return self._master_xpub

        if self._master_xprv is not None:
            self._master_xpub = self._master_xprv.to_public()
        elif not self.is_watch_only:
            if self._seed is None:
                raise WalletLockedError(
                    "Seed not available. Call unlock(password) first."
                )
            self._master_xprv = ExtendedPrivateKey.from_seed(self._seed)
            self._master_xpub = self._master_xprv.to_public()
        else:
            raise WalletError("No xpub available for this wallet")

        return self._master_xpub

    def _derive_bip44_pubkey(
        self, account: int = 0, change: int = 0, index: int = 0
    ) -> bytes:
        """
        Derive compressed public key at m/44'/COIN_TYPE'/account'/change/index.
        Requires UNLOCKED state (seed needed).
        """
        if not self._seed:
            raise WalletLockedError(
                "Seed not available. Call unlock(password) first."
            )
        from .keys.ec import privkey_to_pubkey

        path = f"m/{BIP44_PURPOSE}'/{COIN_TYPE}'/{account}'/{change}/{index}"
        private_key, _ = derive_path_from_seed(self._seed, path)
        return privkey_to_pubkey(private_key, compressed=True)

    # ------------------------------------------------------------------
    # Internal constructor helper
    # ------------------------------------------------------------------

    @classmethod
    def _from_seed(cls, seed: bytes, mnemonic: str = "") -> "Wallet":
        """Build an UNLOCKED HD wallet from a raw seed."""
        if len(seed) != 64:
            raise WalletError(f"Invalid seed length: {len(seed)}")

        w = cls()
        w._wallet_type    = "hd"
        w._seed           = seed
        w._mnemonic       = mnemonic
        w.derivation_path = DERIVATION_PATH
        w.account_index   = 0
        w.change_index    = 0
        w.address_index   = 0
        w.is_watch_only   = False
        w._locked         = False

        priv, pub, addr   = get_default_address_from_seed(seed)
        w._private_key    = priv
        w.public_key      = pub
        w.address         = addr

        return w

    # ------------------------------------------------------------------
    # repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = "LOCKED" if self._locked else "UNLOCKED"
        wtype = self._wallet_type
        addr  = self.address or "(unknown)"
        return f"<Wallet type={wtype!r} state={state} address={addr!r}>"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _zeroize_attr(obj: object, attr: str) -> None:
    """
    Best-effort zeroization of a bytes/bytearray attribute.

    In CPython, bytes objects are immutable, so we can only delete the
    reference.  bytearray objects can be overwritten in-place.
    """
    value = getattr(obj, attr, None)
    if isinstance(value, bytearray):
        for i in range(len(value)):
            value[i] = 0
    # For plain bytes, we can only unlink; the GC decides when memory is freed.
    setattr(obj, attr, None)