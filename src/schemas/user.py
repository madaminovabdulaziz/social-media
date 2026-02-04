import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
_FULL_NAME_RE = re.compile(r"^[a-zA-Zа-яА-ЯёЁ \-]+$")


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=32)
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not _USERNAME_RE.fullmatch(v):
            raise ValueError(
                "Username must contain only Latin letters, digits, and underscores"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_characters(cls, v: str | None) -> str | None:
        if v is not None and not _FULL_NAME_RE.fullmatch(v):
            raise ValueError(
                "Full name must contain only letters, spaces, and hyphens"
            )
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=32)
    full_name: str | None = Field(default=None, min_length=2, max_length=100)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str | None) -> str | None:
        if v is not None and not _USERNAME_RE.fullmatch(v):
            raise ValueError(
                "Username must contain only Latin letters, digits, and underscores"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_characters(cls, v: str | None) -> str | None:
        if v is not None and not _FULL_NAME_RE.fullmatch(v):
            raise ValueError(
                "Full name must contain only letters, spaces, and hyphens"
            )
        return v


class UserVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
