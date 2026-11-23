-- Create the users table
-- depends:

CREATE TABLE users (
    id                    SERIAL PRIMARY KEY,
    first_name            VARCHAR(100) NOT NULL,
    last_name             VARCHAR(100) NOT NULL,
    -- Card number, AES-256-GCM encrypted by the app (app/crypto.py):
    -- 12-byte nonce || ciphertext || 16-byte auth tag. Never stored in plaintext.
    credit_card_encrypted BYTEA        NOT NULL,
    card_key_version      SMALLINT     NOT NULL,  -- which key encrypted it (rotation)
    card_last4            CHAR(4)      NOT NULL,  -- for masked display without decrypting
    email                 VARCHAR(255) NOT NULL UNIQUE,
    password              VARCHAR(128) NOT NULL,  -- PBKDF2-SHA256 hash (hex), never plaintext
    salt                  VARCHAR(64)  NOT NULL   -- per-user random salt (hex)
);
