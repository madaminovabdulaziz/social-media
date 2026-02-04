import uuid
from typing import Annotated, AsyncGenerator

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session_factory
from src.core.exceptions import InvalidTokenError
from src.core.security import decode_access_token
from src.models.user import User
from src.services.user import UserService

security_scheme = HTTPBearer()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise InvalidTokenError()
        user_id = uuid.UUID(user_id_str)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise InvalidTokenError()

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise InvalidTokenError()

    return user
