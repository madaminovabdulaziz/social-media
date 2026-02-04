import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db_session
from src.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidVerificationTokenError,
    UsernameAlreadyExistsError,
)
from src.core.limiter import limiter
from src.core.security import create_access_token, hash_password, verify_password
from src.models.user import User
from src.schemas.user import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    UserVerify,
)
from src.services.email import send_verification_email
from src.services.user import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    user_service = UserService(session)

    if await user_service.get_by_email(data.email):
        raise EmailAlreadyExistsError()

    if await user_service.get_by_username(data.username):
        raise UsernameAlreadyExistsError()

    hashed = hash_password(data.password)
    user = await user_service.create_user(
        email=data.email,
        username=data.username,
        password_hash=hashed,
        full_name=data.full_name,
    )

    code = await user_service.create_verification_token(user.id)
    await send_verification_email(data.email, code)
    logger.info(
        "Verification code issued for user %s (%s)",
        user.email,
        user.id,
    )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user_service = UserService(session)
    user = await user_service.get_by_email(data.email)

    if user is None or not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError()

    token = create_access_token(user_id=user.id)
    return TokenResponse(access_token=token)


@router.post(
    "/verify-email",
    response_model=UserResponse,
)
async def verify_email(
    data: UserVerify,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    user_service = UserService(session)
    user = await user_service.verify_email(email=data.email, code=data.code)
    if user is None:
        raise InvalidVerificationTokenError()
    return user


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_me(
    data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    user_service = UserService(session)

    if data.username is not None:
        existing = await user_service.get_by_username(data.username)
        if existing and existing.id != current_user.id:
            raise UsernameAlreadyExistsError()

    return await user_service.update_user(
        user=current_user,
        username=data.username,
        full_name=data.full_name,
    )
