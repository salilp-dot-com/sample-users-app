"""AES-256-GCM encryption for credit card numbers.

Stored value layout (one BYTEA column): 12-byte random nonce || ciphertext || 16-byte tag.
The key version is stored in its own column so keys can be rotated.

Where the AES keys come from is set by CARD_KEY_PROVIDER (see app/config.py):
  env - raw keys from an environment variable (local development)
  kms - envelope encryption: the env var holds data keys encrypted by AWS KMS,
        which are decrypted once at startup and only ever held in memory
"""

import base64
import os
from functools import cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import CARD_ENCRYPTION_KEYS, CARD_KEY_PROVIDER, CARD_KMS_KEY_ID

NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256
# Associated data: binds ciphertexts to this purpose, so a blob encrypted with the
# same key for something else can't be swapped in and decrypt successfully.
AAD = b"users.credit_card_number"
# KMS encryption context: must match between keygen and decrypt; also shows up in
# CloudTrail, so every KMS call is auditable by purpose.
KMS_CONTEXT = {"purpose": "card-data-key", "app": "sample-users-api"}


def _parse_spec(spec: str) -> dict[int, bytes]:
    """'1:base64,2:base64' -> {1: bytes, 2: bytes}"""
    out = {}
    for pair in filter(None, (p.strip() for p in spec.split(","))):
        version, sep, b64 = pair.partition(":")
        if not sep:
            raise ValueError("CARD_ENCRYPTION_KEYS entries must look like 'version:base64'")
        out[int(version)] = base64.b64decode(b64, validate=True)
    if not out:
        raise RuntimeError(
            "CARD_ENCRYPTION_KEYS is not set. Generate one with: uv run python -m app.keygen"
        )
    return out


def kms_client():
    import boto3  # only needed in AWS

    return boto3.client("kms")


def _decrypt_with_kms(encrypted_keys: dict[int, bytes]) -> dict[int, bytes]:
    kms = kms_client()
    extra = {"KeyId": CARD_KMS_KEY_ID} if CARD_KMS_KEY_ID else {}
    return {
        version: kms.decrypt(
            CiphertextBlob=blob, EncryptionContext=KMS_CONTEXT, **extra
        )["Plaintext"]
        for version, blob in encrypted_keys.items()
    }


@cache
def _keyring() -> dict[int, AESGCM]:
    keys = _parse_spec(CARD_ENCRYPTION_KEYS)
    if CARD_KEY_PROVIDER == "kms":
        keys = _decrypt_with_kms(keys)
    elif CARD_KEY_PROVIDER != "env":
        raise ValueError(f"Unknown CARD_KEY_PROVIDER {CARD_KEY_PROVIDER!r} (use env or kms)")
    for version, key in keys.items():
        if len(key) != KEY_SIZE:
            raise ValueError(f"Card key version {version} must be {KEY_SIZE} bytes (AES-256)")
    return {version: AESGCM(key) for version, key in keys.items()}


def load_keys() -> None:
    """Load (and with KMS, decrypt) the keys now, so misconfiguration fails at startup."""
    _keyring()


def current_key_version() -> int:
    return max(_keyring())


def encrypt_card(number: str) -> tuple[bytes, int]:
    """Return (nonce + ciphertext, key_version). A fresh nonce is used every call."""
    version = current_key_version()
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = _keyring()[version].encrypt(nonce, number.encode(), AAD)
    return nonce + ciphertext, version


def decrypt_card(blob: bytes, key_version: int) -> str:
    """Decrypt a stored card number. Raises InvalidTag if the data was tampered with."""
    blob = bytes(blob)
    nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    return _keyring()[key_version].decrypt(nonce, ciphertext, AAD).decode()
