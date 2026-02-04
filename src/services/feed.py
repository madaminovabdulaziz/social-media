from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.post import Post
from src.models.user import User


class FeedService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_feed(
        self,
        limit: int,
        offset: int,
        keyword: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.posts).selectinload(Post.likes),
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if keyword or date_from or date_to:
            stmt = stmt.join(User.posts)
            if keyword:
                pattern = f"%{keyword}%"
                stmt = stmt.where(
                    or_(
                        Post.title.ilike(pattern),
                        Post.content.ilike(pattern),
                    )
                )
            if date_from:
                stmt = stmt.where(Post.created_at >= date_from)
            if date_to:
                stmt = stmt.where(Post.created_at <= date_to)
            stmt = stmt.distinct()

        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_users(
        self,
        keyword: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count(func.distinct(User.id))).select_from(User)

        if keyword or date_from or date_to:
            stmt = select(func.count(func.distinct(User.id))).select_from(
                User
            ).join(User.posts)
            if keyword:
                pattern = f"%{keyword}%"
                stmt = stmt.where(
                    or_(
                        Post.title.ilike(pattern),
                        Post.content.ilike(pattern),
                    )
                )
            if date_from:
                stmt = stmt.where(Post.created_at >= date_from)
            if date_to:
                stmt = stmt.where(Post.created_at <= date_to)

        result = await self._session.execute(stmt)
        return result.scalar_one()
