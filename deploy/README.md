# Deploying to a VM

Every release on GitHub has two packages attached (every CI run also has them as
downloadable *Artifacts*, with a `0.0.0-dev.*` version):

| Package                            | Contains                                               | Installs to |
|------------------------------------|--------------------------------------------------------|-------------|
| `sample-users-api-X.Y.Z.tar.gz`    | API code, migrations, hash-pinned `requirements.txt`, systemd unit | `/opt/sample-users-api` |
| `sample-users-web-X.Y.Z.tar.gz`    | Built static site, nginx site config                   | `/var/www/sample-users-web` |

```
Browser ──► nginx :80/443 ──/───────► /var/www/sample-users-web/current   (static React app)
                         └──/api/──► uvicorn 127.0.0.1:8000             (systemd: sample-users-api)
                                        └──► PostgreSQL
```

The web app is built to call the API at `/api`, on the same origin, so no CORS setup is
needed and both auth modes (localStorage or cookie) work. To build packages that use
cookie mode, set the repository variable `VITE_AUTH_MODE=cookie` (*Settings → Secrets and
variables → Actions → Variables*).

These steps are for Ubuntu/Debian. Other distributions only differ in package names.

## 1. Prepare the VM (once)

```sh
sudo apt update && sudo apt install -y nginx postgresql curl
curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh

# Database and user for the app
sudo -u postgres psql -c "CREATE USER sample_users WITH PASSWORD 'choose-a-strong-password'"
sudo -u postgres psql -c "CREATE DATABASE users_db OWNER sample_users"
```

## 2. Download a release

```sh
VERSION=0.2.0
gh release download "v$VERSION" --repo OWNER/sample-users-app   # or download from the Releases page
sha256sum -c SHA256SUMS
tar xzf "sample-users-api-$VERSION.tar.gz"
tar xzf "sample-users-web-$VERSION.tar.gz"
```

## 3. Install the API

```sh
sudo "sample-users-api-$VERSION/deploy/install.sh"
```

The first run creates `/etc/sample-users-api/api.env` from
[api/api.env.example](api/api.env.example) and stops. Edit that file and replace every
`CHANGE_ME`:

- `DATABASE_URL`: the database from step 1.
- `JWT_SECRET`: the output of `openssl rand -hex 32`.
- `CARD_ENCRYPTION_KEYS`: generate it on any machine with the repo, using
  `cd api && uv run python -m app.keygen 1`. **Back it up**: without it, stored card
  numbers can't be decrypted.

Then run `install.sh` again. It:

1. copies the release to `/opt/sample-users-api/releases/$VERSION` and creates its own
   virtualenv there with uv, installing only hash-checked dependencies;
2. points `/opt/sample-users-api/current` at it, then installs and restarts the systemd
   service;
3. waits for `/health`. Database migrations run automatically when the service starts.

```sh
systemctl status sample-users-api
journalctl -u sample-users-api -f
curl -s localhost:8000/health        # {"status":"ok","version":"0.2.0"}
```

## 4. Install the web app

```sh
sudo "sample-users-web-$VERSION/deploy/install.sh"
```

This copies the site to `/var/www/sample-users-web/releases/$VERSION`, points `current`
at it, installs the nginx site the first time (replacing nginx's default site) and reloads
nginx. Open `http://<vm-address>/`. The site's version is at `/version.txt`, and the API docs
are at `/api/docs`.

**HTTPS:** point a DNS name at the VM, set `server_name` in
`/etc/nginx/sites-available/sample-users`, then run
`sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx`.
Keep `AUTH_COOKIE_SECURE=true` in `api.env`. Set it to `false` only if the site stays on
plain HTTP and you use cookie mode.

## Upgrading and rolling back

To upgrade, repeat steps 2 to 4 with the new version. Existing config and the nginx site are
kept, and new migrations run on startup.

Each release stays in `releases/`, so rolling back only means switching the `current` symlink back:

```sh
ls /opt/sample-users-api/releases
sudo ln -sfn /opt/sample-users-api/releases/0.1.0 /opt/sample-users-api/current
sudo systemctl restart sample-users-api

sudo ln -sfn /var/www/sample-users-web/releases/0.1.0 /var/www/sample-users-web/current
```

Migrations aren't rolled back automatically. If the newer release changed the schema
in a way the old code can't handle, restore the database from a backup as well. Old
releases can be deleted from `releases/` once you no longer need them.
