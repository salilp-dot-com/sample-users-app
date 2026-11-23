#!/usr/bin/env bash
# Install or upgrade the API on a Linux VM with systemd.
#
#   tar xzf sample-users-api-<version>.tar.gz
#   sudo sample-users-api-<version>/deploy/install.sh
#
# Layout:
#   /opt/sample-users-api/releases/<version>/   one directory per release (own .venv)
#   /opt/sample-users-api/current -> releases/<version>
#   /etc/sample-users-api/api.env                 secrets/config (created on first run)
#
# Rollback:  sudo ln -sfn /opt/sample-users-api/releases/<old> /opt/sample-users-api/current
#            sudo systemctl restart sample-users-api
# Requires:  uv (https://docs.astral.sh/uv/), curl, a reachable PostgreSQL.
set -euo pipefail

APP=sample-users-api
PKG_DIR=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(cat "$PKG_DIR/VERSION")
PREFIX=/opt/$APP
RELEASE=$PREFIX/releases/$VERSION
ENV_DIR=/etc/$APP
ENV_FILE=$ENV_DIR/api.env

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi
UV=$(command -v uv || true)
if [[ -z "$UV" ]]; then
  echo "uv is required: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

echo "==> Installing $APP $VERSION"
id -u "$APP" >/dev/null 2>&1 ||
  useradd --system --home-dir "$PREFIX" --no-create-home --shell /usr/sbin/nologin "$APP"

# 1. Configuration: create from the template on first install, then insist it's filled in.
if [[ ! -f "$ENV_FILE" ]]; then
  install -d -m 750 -o root -g "$APP" "$ENV_DIR"
  install -m 640 -o root -g "$APP" "$PKG_DIR/deploy/api.env.example" "$ENV_FILE"
  echo "Created $ENV_FILE from the template. Edit it (replace every CHANGE_ME), then re-run." >&2
  exit 1
fi
if grep -q CHANGE_ME "$ENV_FILE"; then
  echo "$ENV_FILE still contains CHANGE_ME values. Fill them in, then re-run." >&2
  exit 1
fi

# 2. Unpack this release with its own virtualenv (pinned, hash-checked dependencies).
mkdir -p "$PREFIX/releases"
rm -rf "$RELEASE"
cp -a "$PKG_DIR" "$RELEASE"
export UV_PYTHON_INSTALL_DIR=$PREFIX/python # uv-managed Python, readable by the service
"$UV" venv --quiet --python 3.12 "$RELEASE/.venv"
"$UV" pip install --quiet --python "$RELEASE/.venv/bin/python" \
  --require-hashes -r "$RELEASE/requirements.txt"
chown -R root:root "$RELEASE" "$PREFIX/python" # code is read-only for the service user

# 3. Switch traffic to the new release.
ln -sfn "$RELEASE" "$PREFIX/current"
install -m 644 "$PKG_DIR/deploy/$APP.service" "/etc/systemd/system/$APP.service"
systemctl daemon-reload
systemctl enable "$APP" >/dev/null
systemctl restart "$APP"

# 4. Wait for the health check (startup also runs database migrations).
for _ in $(seq 1 30); do
  if health=$(curl -fsS http://127.0.0.1:8000/health 2>/dev/null); then
    echo "==> Running: $health"
    exit 0
  fi
  sleep 1
done
echo "API did not become healthy. Check: journalctl -u $APP -n 50" >&2
exit 1
