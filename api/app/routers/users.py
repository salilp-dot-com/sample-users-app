import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response, status
from psycopg import sql

from app.crypto import encrypt_card
from app.db import get_conn
from app.schemas import UserCreate, UserOut, UserPatch
from app.security import current_user_id, hash_password, new_salt

router = APIRouter(prefix="/users", tags=["users"])

# The encrypted card is never selected: responses only need the last 4 digits.
COLUMNS = "id, first_name, last_name, card_last4, email"


def _not_found(user_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")


def _email_taken() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")


def _db_fields(data: dict) -> dict:
    """Turn API fields into DB columns: hash the password (with a fresh salt)
    and encrypt the card number (AES-256-GCM)."""
    data = dict(data)
    if "credit_card_number" in data:
        number = data.pop("credit_card_number")
        data["credit_card_encrypted"], data["card_key_version"] = encrypt_card(number)
        data["card_last4"] = number[-4:]
    if "password" in data:
        data["salt"] = new_salt()
        data["password"] = hash_password(data["password"], data["salt"])
    if "email" in data:
        data["email"] = data["email"].lower()
    return data


@router.get("", response_model=list[UserOut])
def list_users(conn=Depends(get_conn), _: int = Depends(current_user_id)):
    rows = conn.execute(f"SELECT {COLUMNS} FROM users ORDER BY id").fetchall()
    return [UserOut.from_row(r) for r in rows]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, conn=Depends(get_conn), _: int = Depends(current_user_id)):
    row = conn.execute(f"SELECT {COLUMNS} FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise _not_found(user_id)
    return UserOut.from_row(row)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, conn=Depends(get_conn)):
    """Sign-up endpoint, so it does not require a token."""
    data = _db_fields(body.model_dump())
    try:
        row = conn.execute(
            f"""INSERT INTO users
                  (first_name, last_name, credit_card_encrypted, card_key_version,
                   card_last4, email, password, salt)
                VALUES (%(first_name)s, %(last_name)s, %(credit_card_encrypted)s,
                        %(card_key_version)s, %(card_last4)s,
                        %(email)s, %(password)s, %(salt)s)
                RETURNING {COLUMNS}""",
            data,
        ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise _email_taken() from None
    return UserOut.from_row(row)


def _update(conn, user_id: int, data: dict) -> UserOut:
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No fields to update")
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k)) for k in data
    )
    query = sql.SQL("UPDATE users SET {} WHERE id = {} RETURNING {}").format(
        assignments, sql.Placeholder("_id"), sql.SQL(COLUMNS)
    )
    try:
        row = conn.execute(query, {**data, "_id": user_id}).fetchone()
    except psycopg.errors.UniqueViolation:
        raise _email_taken() from None
    if row is None:
        raise _not_found(user_id)
    return UserOut.from_row(row)


@router.put("/{user_id}", response_model=UserOut)
def replace_user(
    user_id: int,
    body: UserCreate,
    conn=Depends(get_conn),
    _: int = Depends(current_user_id),
):
    """Replace every field of a user."""
    return _update(conn, user_id, _db_fields(body.model_dump()))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserPatch,
    conn=Depends(get_conn),
    _: int = Depends(current_user_id),
):
    """Change only the fields sent in the body."""
    return _update(conn, user_id, _db_fields(body.model_dump(exclude_unset=True)))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, conn=Depends(get_conn), _: int = Depends(current_user_id)):
    cur = conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
    if cur.rowcount == 0:
        raise _not_found(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
