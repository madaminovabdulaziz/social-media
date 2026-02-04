import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.verification_token import VerificationToken


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(
        self,
        email: str,
        username: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> User:
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user: User,
        username: str | None = None,
        full_name: str | None = None,
    ) -> User:
        if username is not None:
            user.username = username
        if full_name is not None:
            user.full_name = full_name
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def delete_unverified_stale(self, older_than: datetime) -> int:
        stmt = delete(User).where(
            User.is_verified == False,  # noqa: E712
            User.created_at < older_than,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    # -- Verification tokens --

    async def create_verification_token(
        self,
        user_id: uuid.UUID,
        expires_minutes: int = 10,
    ) -> str:
        # Remove any existing token for this user
        await self._session.execute(
            delete(VerificationToken).where(
                VerificationToken.user_id == user_id,
            )
        )
        code = f"{secrets.randbelow(10000):04d}"
        token = VerificationToken(
            user_id=user_id,
            token=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        )
        self._session.add(token)
        await self._session.commit()
        return code

    async def verify_email(self, email: str, code: str) -> User | None:
        user = await self.get_by_email(email)
        if user is None:
            return None

        stmt = select(VerificationToken).where(
            VerificationToken.user_id == user.id,
            VerificationToken.token == code,
        )
        result = await self._session.execute(stmt)
        token = result.scalar_one_or_none()
        if token is None:
            return None

        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            await self._session.delete(token)
            await self._session.commit()
            return None

        user.is_verified = True
        await self._session.delete(token)
        await self._session.commit()
        await self._session.refresh(user)
        return user
