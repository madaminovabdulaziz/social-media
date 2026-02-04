import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedPostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    liked_by: list[uuid.UUID]


class FeedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str | None
    posts: list[FeedPostResponse]


class FeedResponse(BaseModel):
    users: list[FeedUserResponse]
    total: int
    limit: int
    offset: int
