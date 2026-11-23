#!/usr/bin/env bash
# Install or upgrade the web app on a Linux VM with nginx.
#
#   tar xzf sample-users-web-<version>.tar.gz
#   sudo sample-users-web-<version>/deploy/install.sh
#
# Layout:
#   /var/www/sample-users-web/releases/<version>/   static files per release
#   /var/www/sample-users-web/current -> releases/<version>
#
# Rollback:  sudo ln -sfn /var/www/sample-users-web/releases/<old> /var/www/sample-users-web/current
# The nginx site is only installed the first time, so your edits (e.g. certbot's HTTPS
# settings) are kept on upgrade.
set -euo pipefail

PKG_DIR=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(cat "$PKG_DIR/VERSION")
ROOT=/var/www/sample-users-web
RELEASE=$ROOT/releases/$VERSION
SITE=/etc/nginx/sites-available/sample-users

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi
command -v nginx >/dev/null || {
  echo "nginx is required: sudo apt install nginx" >&2
  exit 1
}

echo "==> Installing sample-users-web $VERSION"
mkdir -p "$ROOT/releases"
rm -rf "$RELEASE"
cp -a "$PKG_DIR/html" "$RELEASE"
chmod -R a+rX "$RELEASE"
ln -sfn "$RELEASE" "$ROOT/current"

if [[ ! -f "$SITE" ]]; then
  install -m 644 "$PKG_DIR/deploy/nginx.conf" "$SITE"
  ln -sfn "$SITE" /etc/nginx/sites-enabled/sample-users
  rm -f /etc/nginx/sites-enabled/default # the stock site would also claim port 80
  echo "==> Installed nginx site $SITE"
fi

nginx -t
systemctl reload nginx
echo "==> Serving $VERSION from $ROOT/current"
