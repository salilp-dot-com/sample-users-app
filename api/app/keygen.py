"""Generate a new card encryption key for the configured CARD_KEY_PROVIDER.

    uv run python -m app.keygen [version]

env: prints a random 256-bit key (base64). Keep it secret.
kms: asks AWS KMS for a new data key under CARD_KMS_KEY_ID and prints only the
     KMS-encrypted copy. The plaintext key never leaves this process, so the
     printed value is safe to store in config / a task definition.

Append the output to CARD_ENCRYPTION_KEYS (keep the old versions for rotation).
"""

import base64
import os
import sys

from app.config import CARD_KEY_PROVIDER, CARD_KMS_KEY_ID
from app.crypto import KEY_SIZE, KMS_CONTEXT, kms_client


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "1"
    if CARD_KEY_PROVIDER == "env":
        key = os.urandom(KEY_SIZE)
    elif CARD_KEY_PROVIDER == "kms":
        if not CARD_KMS_KEY_ID:
            sys.exit("Set CARD_KMS_KEY_ID to the KMS key id, ARN or alias first")
        key = kms_client().generate_data_key(
            KeyId=CARD_KMS_KEY_ID, KeySpec="AES_256", EncryptionContext=KMS_CONTEXT
        )["CiphertextBlob"]
    else:
        sys.exit(f"Unknown CARD_KEY_PROVIDER {CARD_KEY_PROVIDER!r}")
    print(f"{version}:{base64.b64encode(key).decode()}")


if __name__ == "__main__":
    main()
