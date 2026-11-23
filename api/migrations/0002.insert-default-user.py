"""
Insert a default user so you can log in to a fresh database.

Credentials come from DEFAULT_USER_EMAIL / DEFAULT_USER_PASSWORD (see .env.example).
If DEFAULT_USER_PASSWORD is not set (e.g. production), nothing is inserted, so no
account with a known password ever exists there.

This is a Python migration because the password must be hashed (PBKDF2 + salt) and
the card number encrypted (AES-256-GCM) with the app's own code and keys.
"""

import os

from yoyo import step

from app.crypto import encrypt_card
from app.security import hash_password, new_salt

__depends__ = {"0001.create-users-table"}

EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@example.com").lower()
PASSWORD = os.getenv("DEFAULT_USER_PASSWORD")
CARD = "4111111111111111"  # standard test card number, not a real card


def apply(conn):
    if not PASSWORD:
        print("DEFAULT_USER_PASSWORD not set: skipping default user")
        return
    salt = new_salt()
    card_encrypted, key_version = encrypt_card(CARD)
    conn.cursor().execute(
        """INSERT INTO users (first_name, last_name, credit_card_encrypted, card_key_version,
                              card_last4, email, password, salt)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (email) DO NOTHING""",
        ("Admin", "User", card_encrypted, key_version, CARD[-4:],
         EMAIL, hash_password(PASSWORD, salt), salt),
    )


def rollback(conn):
    conn.cursor().execute("DELETE FROM users WHERE email = %s", (EMAIL,))


steps = [step(apply, rollback)]
