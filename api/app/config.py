import os

from dotenv import load_dotenv

# Load api/.env for local development. Real environment variables win.
load_dotenv()

# Defaults match ../docker-compose.yml so the app works out of the box locally.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Password123!@localhost:5433/users_db",
)

# Change this in any non-local environment, e.g. JWT_SECRET=$(openssl rand -hex 32)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# --- Cookie auth (POST /login?cookie=true) -------------------------------------
# The JWT is stored in an HttpOnly cookie that JavaScript cannot read.
AUTH_COOKIE_NAME = "access_token"
# Secure cookies are only sent over HTTPS. Off for http://localhost; set true when deployed.
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
# Cookie-authenticated writes must send this header (CSRF protection, see security.py).
CSRF_HEADER = "X-Requested-With"

# --- Card number encryption (AES-256-GCM) -------------------------------------
# CARD_KEY_PROVIDER picks where the AES keys come from:
#   env - CARD_ENCRYPTION_KEYS holds the raw keys (local development)
#   kms - CARD_ENCRYPTION_KEYS holds data keys *encrypted by AWS KMS*; they are
#         decrypted with KMS once at startup and only kept in memory (AWS)
# Either way the format is "version:base64,version:base64". The highest version
# encrypts new data; older versions stay so existing rows still decrypt.
# Generate a key for the current provider with:  uv run python -m app.keygen
CARD_KEY_PROVIDER = os.getenv("CARD_KEY_PROVIDER", "env").lower()
CARD_ENCRYPTION_KEYS = os.getenv("CARD_ENCRYPTION_KEYS", "")
# kms only: the KMS key (id, ARN or alias) the data keys were encrypted under.
# Region and credentials come from the usual AWS settings (AWS_REGION, IAM role, ...).
CARD_KMS_KEY_ID = os.getenv("CARD_KMS_KEY_ID")

# Origins allowed to call the API from a browser (Vite dev server by default).
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
