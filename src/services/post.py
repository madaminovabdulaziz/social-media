import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.comment import Comment
from src.models.like import Like
from src.models.post import Post


class PostService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_post(
        self,
        author_id: uuid.UUID,
        title: str,
        content: str,
    ) -> Post:
        post = Post(author_id=author_id, title=title, content=content)
        self._session.add(post)
        await self._session.commit()
        return await self._get_with_author(post.id)

    async def get_by_id(self, post_id: uuid.UUID) -> Post | None:
        stmt = select(Post).where(Post.id == post_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, post_id: uuid.UUID) -> Post | None:
        stmt = (
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.author),
                selectinload(Post.comments).selectinload(Comment.author),
                selectinload(Post.likes),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_posts(
        self,
        limit: int = 10,
        offset: int = 0,
        keyword: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[Post], int]:
        stmt = select(Post).options(selectinload(Post.author))
        count_stmt = select(func.count()).select_from(Post)

        if keyword:
            pattern = f"%{keyword}%"
            keyword_filter = or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
            )
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)

        if date_from:
            stmt = stmt.where(Post.created_at >= date_from)
            count_stmt = count_stmt.where(Post.created_at >= date_from)

        if date_to:
            stmt = stmt.where(Post.created_at <= date_to)
            count_stmt = count_stmt.where(Post.created_at <= date_to)

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        posts = list(result.scalars().all())

        return posts, total

    async def update_post(
        self,
        post: Post,
        title: str | None = None,
        content: str | None = None,
    ) -> Post:
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        await self._session.commit()
        return await self._get_with_author(post.id)

    async def delete_post(self, post: Post) -> None:
        await self._session.delete(post)
        await self._session.commit()

    async def create_comment(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
    ) -> Comment:
        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            content=content,
        )
        self._session.add(comment)
        await self._session.commit()
        stmt = (
            select(Comment)
            .where(Comment.id == comment.id)
            .options(selectinload(Comment.author))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_comment_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_comment(self, comment: Comment) -> None:
        await self._session.delete(comment)
        await self._session.commit()

    async def add_like(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
    ) -> Like:
        like = Like(user_id=user_id, post_id=post_id)
        self._session.add(like)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise ValueError("User has already liked this post")
        await self._session.refresh(like)
        return like

    async def remove_like(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
    ) -> bool:
        stmt = select(Like).where(
            Like.user_id == user_id,
            Like.post_id == post_id,
        )
        result = await self._session.execute(stmt)
        like = result.scalar_one_or_none()
        if like is None:
            return False
        await self._session.delete(like)
        await self._session.commit()
        return True

    async def _get_with_author(self, post_id: uuid.UUID) -> Post:
        stmt = select(Post).where(Post.id == post_id).options(selectinload(Post.author))
        result = await self._session.execute(stmt)
        return result.scalar_one()
