import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str | None


class PostCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    content: str = Field(..., min_length=1, max_length=10_000)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    content: str | None = Field(default=None, min_length=1, max_length=10_000)


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2_000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    author: AuthorResponse


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    author: AuthorResponse


class PostDetailResponse(PostResponse):
    comments: list[CommentResponse] = []
    likes_count: int = 0


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    limit: int
    offset: int
