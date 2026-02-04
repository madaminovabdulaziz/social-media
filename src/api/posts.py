import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db_session
from src.core.exceptions import (
    AlreadyLikedError,
    CannotLikeSelfError,
    CommentNotFoundError,
    LikeNotFoundError,
    NotCommentOwnerError,
    NotPostOwnerError,
    NotVerifiedError,
    PostNotFoundError,
)
from src.models.user import User
from src.schemas.post import (
    CommentCreate,
    CommentResponse,
    PostCreate,
    PostDetailResponse,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from src.services.post import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get(
    "",
    response_model=PostListResponse,
)
async def list_posts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    keyword: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> dict:
    post_service = PostService(session)
    posts, total = await post_service.list_posts(
        limit=limit,
        offset=offset,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "posts": posts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    data: PostCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if not current_user.is_verified:
        raise NotVerifiedError()
    post_service = PostService(session)
    post = await post_service.create_post(
        author_id=current_user.id,
        title=data.title,
        content=data.content,
    )
    return post


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
)
async def get_post(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    post_service = PostService(session)
    post = await post_service.get_with_details(post_id)
    if post is None:
        raise PostNotFoundError()
    return {
        "id": post.id,
        "author_id": post.author_id,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "author": post.author,
        "comments": post.comments,
        "likes_count": len(post.likes),
    }


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
async def update_post(
    post_id: uuid.UUID,
    data: PostUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    if post.author_id != current_user.id:
        raise NotPostOwnerError("edit")
    post = await post_service.update_post(
        post=post,
        title=data.title,
        content=data.content,
    )
    return post


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    if post.author_id != current_user.id:
        raise NotPostOwnerError("delete")
    await post_service.delete_post(post)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: uuid.UUID,
    data: CommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    if not current_user.is_verified:
        raise NotVerifiedError()
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    comment = await post_service.create_comment(
        post_id=post_id,
        author_id=current_user.id,
        content=data.content,
    )
    return comment


@router.delete(
    "/{post_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    comment = await post_service.get_comment_by_id(comment_id)
    if comment is None or comment.post_id != post_id:
        raise CommentNotFoundError()
    if comment.author_id != current_user.id:
        raise NotCommentOwnerError()
    await post_service.delete_comment(comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{post_id}/like",
    status_code=status.HTTP_201_CREATED,
)
async def like_post(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    if post.author_id == current_user.id:
        raise CannotLikeSelfError()
    try:
        await post_service.add_like(
            user_id=current_user.id,
            post_id=post_id,
        )
    except ValueError:
        raise AlreadyLikedError()
    return {"detail": "Post liked successfully"}


@router.delete(
    "/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlike_post(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    post_service = PostService(session)
    post = await post_service.get_by_id(post_id)
    if post is None:
        raise PostNotFoundError()
    removed = await post_service.remove_like(
        user_id=current_user.id,
        post_id=post_id,
    )
    if not removed:
        raise LikeNotFoundError()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
