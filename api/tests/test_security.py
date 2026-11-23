"""Unit tests for password hashing and card encryption (no database needed)."""

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import NONCE_SIZE, decrypt_card, encrypt_card
from app.security import hash_password, new_salt, verify_password


def test_password_hash_round_trip():
    salt = new_salt()
    hashed = hash_password("s3cret-pass", salt)
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", salt, hashed)
    assert not verify_password("wrong-pass", salt, hashed)


def test_same_password_different_salt_gives_different_hash():
    assert hash_password("same", new_salt()) != hash_password("same", new_salt())


def test_card_encryption_round_trip():
    blob, version = encrypt_card("4111111111111111")
    assert version == 1
    assert b"4111111111111111" not in blob
    assert decrypt_card(blob, version) == "4111111111111111"


def test_card_encryption_uses_fresh_nonce_each_time():
    first, _ = encrypt_card("4111111111111111")
    second, _ = encrypt_card("4111111111111111")
    assert first[:NONCE_SIZE] != second[:NONCE_SIZE]
    assert first != second


def test_tampered_ciphertext_is_rejected():
    blob, version = encrypt_card("4111111111111111")
    tampered = blob[:-1] + bytes([blob[-1] ^ 1])
    with pytest.raises(InvalidTag):
        decrypt_card(tampered, version)
