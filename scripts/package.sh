#!/usr/bin/env bash
# Build the deployable packages for a version:
#
#   scripts/package.sh <version> [out-dir]      (out-dir defaults to ./dist)
#
# Produces:
#   sample-users-api-<version>.tar.gz   API source, migrations, hash-pinned requirements.txt,
#                                       systemd unit and install script
#   sample-users-web-<version>.tar.gz   built static site, nginx config and install script
#   SHA256SUMS
#
# The web app is built to call the API at /api (same origin, via nginx). Override with
# VITE_API_URL / VITE_AUTH_MODE environment variables.
# Requires: uv, and `npm ci` already run in web/.
set -euo pipefail

VERSION=${1:?usage: scripts/package.sh <version> [out-dir]}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "${2:-$ROOT/dist}"
OUT=$(cd "${2:-$ROOT/dist}" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
export COPYFILE_DISABLE=1 # macOS: keep ._* metadata files out of the tarballs

API=sample-users-api-$VERSION
WEB=sample-users-web-$VERSION

echo "==> $API"
mkdir -p "$STAGE/$API/deploy"
cp -R "$ROOT/api/app" "$ROOT/api/migrations" "$STAGE/$API/"
cp "$ROOT/api/pyproject.toml" "$ROOT/api/uv.lock" "$ROOT/api/.python-version" \
  "$ROOT/api/.env.example" "$STAGE/$API/"
cp "$ROOT"/deploy/api/* "$STAGE/$API/deploy/"
(cd "$ROOT/api" && uv export --quiet --frozen --no-dev --no-emit-project --no-header \
  --format requirements-txt --output-file "$STAGE/$API/requirements.txt" >/dev/null)
echo "$VERSION" >"$STAGE/$API/VERSION"
find "$STAGE/$API" -name __pycache__ -prune -exec rm -rf {} +

echo "==> $WEB"
(cd "$ROOT/web" &&
  VITE_API_URL="${VITE_API_URL:-/api}" VITE_AUTH_MODE="${VITE_AUTH_MODE:-localStorage}" \
    npm run --silent build)
mkdir -p "$STAGE/$WEB/deploy"
cp -R "$ROOT/web/dist" "$STAGE/$WEB/html"
echo "$VERSION" >"$STAGE/$WEB/html/version.txt" # lets you check what's live: /version.txt
echo "$VERSION" >"$STAGE/$WEB/VERSION"
cp "$ROOT"/deploy/web/* "$STAGE/$WEB/deploy/"

chmod +x "$STAGE/$API/deploy/install.sh" "$STAGE/$WEB/deploy/install.sh"
tar -C "$STAGE" -czf "$OUT/$API.tar.gz" "$API"
tar -C "$STAGE" -czf "$OUT/$WEB.tar.gz" "$WEB"

cd "$OUT"
if command -v sha256sum >/dev/null; then
  sha256sum "$API.tar.gz" "$WEB.tar.gz" >SHA256SUMS
else
  shasum -a 256 "$API.tar.gz" "$WEB.tar.gz" >SHA256SUMS
fi
echo "==> Packages in $OUT"
ls -lh "$OUT"
