# Sample Users App

A users app with a FastAPI and PostgreSQL REST API and a React frontend. It supports sign-up, login with a JWT, and creating, reading, updating and deleting users. Passwords are hashed and card numbers are encrypted before they are stored.

```
.
├── docker-compose.yml   # PostgreSQL + pgAdmin for local development
├── api/                 # FastAPI REST API (Python, managed with uv)
├── web/                 # React + Vite + TypeScript frontend
├── deploy/              # VM install scripts, systemd unit, nginx config
├── scripts/             # package.sh (build release tarballs), setup-github.sh
└── .github/workflows/   # CI, packaging and release automation
```

[![CI](https://github.com/salilp-dot-com/sample-users-app/actions/workflows/ci.yml/badge.svg)](https://github.com/salilp-dot-com/sample-users-app/actions/workflows/ci.yml)

- **Contributing, branching and releases:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deploying to a VM:** [deploy/README.md](deploy/README.md)

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), with Docker Compose v2.23 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/). It installs Python 3.12 and the project dependencies for you.
- [Node.js](https://nodejs.org/) 20.19+ or 22.12+, for the frontend

## 1. Start PostgreSQL

From the repository root:

```sh
docker compose up -d
docker compose ps        # postgres should show "healthy"
```

| Service    | Address                 | Credentials                                 |
|------------|-------------------------|---------------------------------------------|
| PostgreSQL | `localhost:5433`        | user `postgres`, password `Password123!`, database `users_db` |
| pgAdmin    | <http://localhost:5050> | no login; on first connect, enter the database password above |

PostgreSQL listens on host port **5433**, not 5432, so it doesn't clash with another Postgres running on your machine. To change the ports, set `POSTGRES_PORT` or `PGADMIN_PORT` in a `.env` file next to `docker-compose.yml`.

In pgAdmin, the database is already registered as **sample-users-app**. Your tables are under *Databases → users_db → Schemas → public → Tables*.

## 2. Configure the API

```sh
cd api
cp .env.example .env
uv run python -m app.keygen 1
```

Paste the line that `keygen` prints into `.env` as the value of `CARD_ENCRYPTION_KEYS`:

```sh
CARD_ENCRYPTION_KEYS=1:<the printed key>
```

The other defaults in `.env.example` already match the Docker database. `.env` is git-ignored, so keep your key out of version control. If you lose the key, card numbers stored with it can't be decrypted.

## 3. Start the API

```sh
cd api
uv run uvicorn app.main:app --reload
```

The first run installs dependencies. On every startup, the API applies any pending [yoyo](https://ollycope.com/software/yoyo/latest/) database migrations from `api/migrations/` before it accepts requests, so you never need to run migrations by hand.

- API: <http://localhost:8000>
- Interactive docs (Swagger UI): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

## 4. Start the frontend

In a second terminal:

```sh
cd web
npm install
npm run dev
```

Open <http://localhost:5173> and log in with the default user: the `DEFAULT_USER_EMAIL` and `DEFAULT_USER_PASSWORD` values from `api/.env`. You can also choose **Sign up** to create a new account. The **Users** page lists every user and lets you create, edit and delete them. When you edit a user, leave the card number and password blank to keep the current values.

The frontend calls the API at `http://localhost:8000` by default. To point it somewhere else, create `web/.env.local` containing, for example, `VITE_API_URL=http://localhost:8001`, and restart `npm run dev`. If you change the frontend's own port, add the new address to the API's `CORS_ORIGINS`.

Other scripts: `npm run build` (type-check and production build into `web/dist/`), `npm run lint`, `npm run typecheck` and `npm test`.

## Where the login token is kept: localStorage or cookie

The frontend can keep the JWT in one of two places. Choose with `VITE_AUTH_MODE` in `web/.env.local`, then restart `npm run dev` (Vite also restarts by itself when the file changes). A badge next to the app name shows which mode is active.

```sh
# web/.env.local
VITE_AUTH_MODE=cookie        # or localStorage (the default)
```

The API supports both at the same time, so you only change the frontend.

|                         | `localStorage` (default)                          | `cookie`                                                 |
|-------------------------|---------------------------------------------------|----------------------------------------------------------|
| Login                   | `POST /login` returns the JWT in JSON             | `POST /login?cookie=true` sets an `HttpOnly` cookie; the JSON has no token |
| Where it's stored       | `localStorage`, written by our code               | A cookie stored by the browser                           |
| Sent with each request  | Our code adds `Authorization: Bearer <jwt>`       | The browser attaches the cookie automatically            |
| After a page reload     | Decode the saved JWT                              | Call `GET /me` (JavaScript can't read the cookie)        |
| Logout                  | Delete it from `localStorage`                     | `POST /logout`; only the server can clear an `HttpOnly` cookie |
| Can JavaScript read it? | **Yes**: any script on the page, including injected (XSS) scripts | **No**                                                   |
| CSRF risk               | None; browsers never add the header themselves    | Yes, so writes must send `X-Requested-With` (see below)  |

**To demo the difference,** log in and open DevTools → Application:
- In `localStorage` mode, the token is under *Local storage*. Running `localStorage.getItem('token')` in the console prints it, which is exactly what an XSS attack would do.
- In `cookie` mode, the token is under *Cookies* with the HttpOnly box ticked. `document.cookie` doesn't show it, and `localStorage` is empty.

**CSRF protection in cookie mode:** the browser sends the cookie with *every* request to the API, including ones triggered by a form on another website. So for cookie-authenticated `POST`, `PUT`, `PATCH` and `DELETE` requests, the API also requires an `X-Requested-With` header. A cross-site form can't add custom headers, and CORS stops other sites' scripts from sending one. The cookie is also `SameSite=Lax`, which stops it being sent on cross-site writes. See `current_claims` in [api/app/security.py](api/app/security.py).

**When deploying with cookies,** set `AUTH_COOKIE_SECURE=true` on the API so the cookie is only sent over HTTPS.

## Using the API

| Method   | Path          | Auth     | Description                                    |
|----------|---------------|----------|------------------------------------------------|
| `POST`   | `/users`      | none     | Sign up (create a user)                        |
| `POST`   | `/login`      | none     | Exchange email + password for a JWT (`?cookie=true`: set it as an HttpOnly cookie instead) |
| `GET`    | `/me`         | Bearer or cookie | Who is logged in, and when the token expires |
| `POST`   | `/logout`     | none     | Clear the auth cookie                          |
| `GET`    | `/users`      | Bearer   | List users                                     |
| `GET`    | `/users/{id}` | Bearer   | Get one user                                   |
| `PUT`    | `/users/{id}` | Bearer   | Replace a user (all fields required)           |
| `PATCH`  | `/users/{id}` | Bearer   | Update only the fields sent                    |
| `DELETE` | `/users/{id}` | Bearer   | Delete a user                                  |

Example session:

```sh
# Sign up
curl -X POST localhost:8000/users -H 'Content-Type: application/json' -d '{
  "first_name": "Ada", "last_name": "Lovelace",
  "credit_card_number": "4111 1111 1111 1111",
  "email": "ada@example.com", "password": "secret123"
}'

# Log in and keep the token
TOKEN=$(curl -s -X POST localhost:8000/login -H 'Content-Type: application/json' \
  -d '{"email": "ada@example.com", "password": "secret123"}' | jq -r .access_token)

# Call a protected endpoint
curl localhost:8000/users -H "Authorization: Bearer $TOKEN"
```

In Swagger UI, click **Authorize** and paste the `access_token` to call protected endpoints.

Responses never include the password hash or salt, and card numbers are masked, for example `**** **** **** 1111`.

## Configuration

The API reads these settings from environment variables. For local development, set them in `api/.env`.

| Variable               | Default                                                     | Purpose |
|------------------------|-------------------------------------------------------------|---------|
| `DATABASE_URL`         | `postgresql://postgres:Password123!@localhost:5433/users_db` | Database connection |
| `JWT_SECRET`           | insecure dev value                                          | Signs JWTs. Change it outside local dev (`openssl rand -hex 32`) |
| `JWT_EXPIRE_MINUTES`   | `60`                                                        | How long a token is valid |
| `CORS_ORIGINS`         | `http://localhost:5173`                                     | Comma-separated browser origins allowed to call the API |
| `AUTH_COOKIE_SECURE`   | `false`                                                     | Send the auth cookie over HTTPS only. Set `true` when deployed |
| `CARD_KEY_PROVIDER`    | `env`                                                       | `env` (key in environment) or `kms` (AWS KMS) |
| `CARD_ENCRYPTION_KEYS` | **required**                                                | `version:base64key` pairs, separated by commas |
| `CARD_KMS_KEY_ID`      | —                                                           | `kms` only: KMS key id, ARN or alias |
| `DEFAULT_USER_EMAIL`   | `admin@example.com`                                         | Email of the default user |
| `DEFAULT_USER_PASSWORD`| unset                                                       | If set, migration `0002` creates the default user once. **Leave unset in production** |

### Default user

Migration `0002.insert-default-user.py` creates one user (Admin User, test card `4111 1111 1111 1111`) so you can log in to a fresh database. It runs once, and only when `DEFAULT_USER_PASSWORD` is set. If the variable isn't set, the migration is still recorded as applied but inserts nothing. Setting the variable later won't create the user, unless you recreate the database or sign up through the app.

The user is only created when the migration first runs. Changing the password in `.env` afterwards has no effect; change it through the app instead.

### Card encryption keys

Card numbers are encrypted with AES-256-GCM before they are stored. Each value gets a fresh random nonce.

- **Local (`env`):** `CARD_ENCRYPTION_KEYS` holds the raw 256-bit key.
- **AWS (`kms`):** `CARD_ENCRYPTION_KEYS` holds a data key that has been *encrypted by KMS*, so it is safe to put in configuration. The API asks KMS to decrypt it once at startup and keeps the result only in memory. To set this up:
  1. Set `CARD_KEY_PROVIDER=kms` and `CARD_KMS_KEY_ID`.
  2. Run `uv run python -m app.keygen 1` with credentials that have `kms:GenerateDataKey`.
  3. Give the API's IAM role `kms:Decrypt` on the key.
- **Rotating keys:** generate a new version (`uv run python -m app.keygen 2`) and append it to the existing value, for example `1:...,2:...`. New data uses the highest version. Keep the older versions so existing rows still decrypt.

## Common tasks

```sh
docker compose logs -f postgres     # database logs
docker compose down                 # stop containers (data is kept)
docker compose down -v              # stop and delete all data (DB + pgAdmin settings)

# Recreate just the database, keeping pgAdmin settings (stop the API first)
docker compose exec postgres psql -U postgres \
  -c "DROP DATABASE users_db WITH (FORCE)" -c "CREATE DATABASE users_db"
```

To change the schema, add a new migration file such as `api/migrations/0003.add-something.sql` and restart the API. Never edit a migration that has already been applied.

## Tests and CI

```sh
cd api && uv run pytest          # API: needs the docker compose Postgres (uses its own users_test DB)
cd web && npm test               # Web: Vitest + React Testing Library
```

GitHub Actions lints, tests and builds both apps on every pull request and every push to
`main`, and builds the deployable packages. Merging the release PR tags a semantic
version and attaches the packages to a GitHub Release. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Troubleshooting

- **`port is already allocated`**: another process is using the port. Set a different `POSTGRES_PORT` or `PGADMIN_PORT` in the root `.env` file, and update `DATABASE_URL` to match.
- **pgAdmin: `failed to resolve host 'postgres'`**: the postgres container isn't running. Check `docker compose ps` and `docker compose logs postgres`.
- **API won't start: `CARD_ENCRYPTION_KEYS is not set`**: follow [step 2](#2-configure-the-api).
- **API won't start: connection refused**: PostgreSQL isn't running, or `DATABASE_URL` points to the wrong port.
# sample-users-app
