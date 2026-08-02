# tencoinlib/message/__init__.py

from .signing import (
    sign_message,
    verify_message,
    recover_address_from_signature,
    MessageSigningError,
)

__all__ = [
    "sign_message",
    "verify_message",
    "recover_address_from_signature",
    "MessageSigningError",
]