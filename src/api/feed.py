from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db_session
from src.models.user import User
from src.schemas.feed import FeedPostResponse, FeedResponse, FeedUserResponse
from src.services.feed import FeedService

router = APIRouter(tags=["feed"])


@router.get(
    "/feed",
    response_model=FeedResponse,
)
async def get_feed(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    keyword: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> FeedResponse:
    feed_service = FeedService(session)
    users = await feed_service.get_feed(
        limit=limit,
        offset=offset,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    total = await feed_service.count_users(
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )

    return FeedResponse(
        users=[
            FeedUserResponse(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                posts=[
                    FeedPostResponse(
                        id=post.id,
                        title=post.title,
                        content=post.content,
                        created_at=post.created_at,
                        updated_at=post.updated_at,
                        liked_by=[like.user_id for like in post.likes],
                    )
                    for post in user.posts
                ],
            )
            for user in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
