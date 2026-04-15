"""
The Volt — encryption utilities.

Transparent encrypt-on-write / decrypt-on-read using Fernet symmetric encryption.
Key is derived per vault owner using PBKDF2-HMAC-SHA256 so each owner's data
is encrypted with a unique key derived from their owner ID + Django SECRET_KEY.

For v1 this is intentionally simple (no HSM/KMS). The key never leaves memory
and is re-derived on every call (fast, ~0.1 ms) so there is no key caching risk.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

_PBKDF2_ITERATIONS = 100_000


@lru_cache(maxsize=256)
def _derive_key(owner_id: int) -> bytes:
    """Derive a Fernet-compatible 32-byte key for owner_id.

    Key material = PBKDF2-HMAC-SHA256(
        password = SECRET_KEY bytes,
        salt     = b"volt_" + str(owner_id).encode(),
        iterations = 100_000,
        length = 32,
    ) encoded as URL-safe base64.

    The lru_cache keeps the derived key in process memory for performance.
    On SECRET_KEY rotation the cache auto-invalidates (new process = new cache).
    """
    password = settings.SECRET_KEY.encode()
    salt = b"volt_" + str(owner_id).encode()
    raw = hashlib.pbkdf2_hmac("sha256", password, salt, _PBKDF2_ITERATIONS, dklen=32)
    # Fernet requires URL-safe base64-encoded 32-byte key
    return base64.urlsafe_b64encode(raw)


def _fernet(owner_id: int):
    from cryptography.fernet import Fernet
    return Fernet(_derive_key(owner_id))


def encrypt_bytes(data: bytes, owner_id: int) -> bytes:
    """Encrypt plaintext bytes with the owner's derived key. Returns ciphertext."""
    return _fernet(owner_id).encrypt(data)


def decrypt_bytes(data: bytes, owner_id: int) -> bytes:
    """Decrypt ciphertext bytes with the owner's derived key. Returns plaintext."""
    return _fernet(owner_id).decrypt(data)


def hash_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of data (used for tamper detection)."""
    return hashlib.sha256(data).hexdigest()


def sign_package(data: bytes, owner_id: int) -> str:
    """Return an HMAC-SHA256 hex signature of data using the owner's derived key.

    Used by CheckoutService to sign the data package so the recipient can verify
    it was produced by The Volt and has not been tampered with.
    """
    key = _derive_key(owner_id)
    sig = hmac.new(key, data, hashlib.sha256).hexdigest()
    return sig


def verify_package(data: bytes, signature: str, owner_id: int) -> bool:
    """Verify an HMAC-SHA256 signature produced by sign_package."""
    expected = sign_package(data, owner_id)
    return hmac.compare_digest(expected, signature)


def generate_api_key() -> tuple[str, str]:
    """Generate a new subscriber API key.

    Returns:
        (raw_key, sha256_hash) — raw_key is returned ONCE to the caller and must
        be saved immediately. Only the hash is stored in the database.
    """
    raw = "volt_" + secrets.token_urlsafe(32)
    hashed = hash_bytes(raw.encode())
    return raw, hashed


def generate_otp() -> tuple[str, str]:
    """Generate a 6-digit OTP for the owner approval link.

    Returns:
        (otp_plaintext, otp_hash) — plaintext is sent via SMS, hash is stored.
    """
    otp = str(secrets.randbelow(900_000) + 100_000)  # always 6 digits
    otp_hash = hash_bytes(otp.encode())
    return otp, otp_hash


def hash_otp(otp: str) -> str:
    """Hash a plaintext OTP for comparison against stored hash."""
    return hash_bytes(otp.encode())


def package_to_bytes(package: dict) -> bytes:
    """Serialize a data package dict to canonical JSON bytes for signing/hashing."""
    return json.dumps(package, sort_keys=True, ensure_ascii=False, default=str).encode()
