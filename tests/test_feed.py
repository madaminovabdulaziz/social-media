from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.like import Like
from src.models.post import Post
from src.models.user import User


class TestFeed:
    async def test_feed_empty(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ) -> None:
        resp = await client.get("/feed", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "users" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert body["total"] >= 1

    async def test_feed_with_posts_and_likes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = Post(author_id=test_user.id, title="Feed Post", content="Content")
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)

        like = Like(user_id=test_user.id, post_id=post.id)
        db_session.add(like)
        await db_session.commit()

        db_session.expire_all()

        resp = await client.get("/feed", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()

        user_entry = next(
            (u for u in body["users"] if u["id"] == str(test_user.id)), None
        )
        assert user_entry is not None
        assert len(user_entry["posts"]) >= 1

        feed_post = next(
            (p for p in user_entry["posts"] if p["id"] == str(post.id)), None
        )
        assert feed_post is not None
        assert feed_post["title"] == "Feed Post"
        assert isinstance(feed_post["liked_by"], list)
        assert str(test_user.id) in feed_post["liked_by"]

    async def test_feed_pagination(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ) -> None:
        resp = await client.get(
            "/feed", params={"limit": 1, "offset": 0}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 1
        assert body["offset"] == 0
        assert len(body["users"]) <= 1

    async def test_feed_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/feed")
        assert resp.status_code == 403
