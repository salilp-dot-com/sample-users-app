from pydantic import BaseModel, EmailStr, Field, field_validator


def _clean_card(value: str | None) -> str | None:
    if value is None:
        return None
    digits = value.replace(" ", "").replace("-", "")
    if not digits.isdigit() or not 12 <= len(digits) <= 19:
        raise ValueError("must be 12-19 digits")
    return digits


class UserCreate(BaseModel):
    """Body for POST and PUT (PUT replaces every field)."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    credit_card_number: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    _card = field_validator("credit_card_number")(_clean_card)


class UserPatch(BaseModel):
    """Body for PATCH: send only the fields you want to change."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    credit_card_number: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    _card = field_validator("credit_card_number")(_clean_card)


class UserOut(BaseModel):
    """What the API returns. The password hash and salt are never exposed,
    and the card number is masked to its last 4 digits."""

    id: int
    first_name: str
    last_name: str
    credit_card_number: str
    email: EmailStr

    @classmethod
    def from_row(cls, row: dict) -> "UserOut":
        return cls(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            credit_card_number="**** **** **** " + row["card_last4"],
            email=row["email"],
        )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    # None in cookie mode: the token is only in the HttpOnly cookie, never in JS-visible JSON.
    access_token: str | None
    token_type: str  # "bearer" or "cookie"
    expires_in: int  # seconds
    user_id: int
    email: EmailStr


class MeResponse(BaseModel):
    id: int
    email: EmailStr
    expires_at: int  # token expiry, Unix seconds
