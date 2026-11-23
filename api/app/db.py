from pathlib import Path
from urllib.parse import quote

from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from yoyo import get_backend, read_migrations

from app.config import DATABASE_URL

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

pool = ConnectionPool(DATABASE_URL, kwargs={"row_factory": dict_row}, open=False)


def _yoyo_url(url: str) -> str:
    """Build a yoyo URL (psycopg 3 driver) from the libpq URL.

    The user and password are re-encoded because yoyo parses the URL itself,
    and characters like '!' or '@' would otherwise break it.
    """
    p = conninfo_to_dict(url)
    auth = quote(p.get("user", ""), safe="")
    if p.get("password"):
        auth += ":" + quote(p["password"], safe="")
    return (
        f"postgresql+psycopg://{auth}@{p.get('host', 'localhost')}"
        f":{p.get('port', 5432)}/{p.get('dbname', '')}"
    )


def run_migrations() -> None:
    """Apply any pending yoyo migrations from ./migrations."""
    backend = get_backend(_yoyo_url(DATABASE_URL))
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def get_conn():
    """FastAPI dependency: one pooled connection per request.

    The transaction is committed when the request succeeds and rolled back on error.
    """
    with pool.connection() as conn:
        yield conn
