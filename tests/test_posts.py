import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.comment import Comment
from src.models.post import Post
from src.models.user import User


async def _create_post_in_db(
    session: AsyncSession,
    author: User,
    title: str = "Test Post",
    content: str = "Body",
) -> Post:
    post = Post(author_id=author.id, title=title, content=content)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def _create_comment_in_db(
    session: AsyncSession,
    post: Post,
    author: User,
    content: str = "A comment",
) -> Comment:
    comment = Comment(post_id=post.id, author_id=author.id, content=content)
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


class TestListPosts:
    async def test_list_posts_empty(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/posts", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["posts"] == []
        assert body["total"] == 0
        assert body["limit"] == 10
        assert body["offset"] == 0

    async def test_list_posts_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        await _create_post_in_db(db_session, test_user, "First Post", "Content one")
        await _create_post_in_db(db_session, test_user, "Second Post", "Content two")
        resp = await client.get("/posts", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["posts"]) == 2

    async def test_list_posts_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        for i in range(5):
            await _create_post_in_db(db_session, test_user, f"Post {i:02d}", "Body")
        resp = await client.get(
            "/posts", params={"limit": 2, "offset": 0}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["posts"]) == 2

    async def test_list_posts_keyword_search(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        await _create_post_in_db(db_session, test_user, "Python Guide", "Learn Python")
        await _create_post_in_db(db_session, test_user, "Java Guide", "Learn Java")
        resp = await client.get(
            "/posts", params={"keyword": "python"}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert "Python" in body["posts"][0]["title"]


class TestCreatePost:
    async def test_create_post_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {"title": "My Post", "content": "Hello world"}
        resp = await client.post("/posts", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "My Post"
        assert body["content"] == "Hello world"
        assert "id" in body
        assert "author" in body

    async def test_create_post_unauthenticated(self, client: AsyncClient) -> None:
        payload = {"title": "My Post", "content": "Hello"}
        resp = await client.post("/posts", json=payload)
        assert resp.status_code == 403

    async def test_create_post_empty_title(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        payload = {"title": "", "content": "Hello"}
        resp = await client.post("/posts", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_create_post_unverified_user(
        self, client: AsyncClient, unverified_auth_headers: dict
    ) -> None:
        payload = {"title": "My Post", "content": "Hello world"}
        resp = await client.post(
            "/posts", json=payload, headers=unverified_auth_headers
        )
        assert resp.status_code == 403
        assert "verification" in resp.json()["detail"].lower()


class TestGetPost:
    async def test_get_post_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        resp = await client.get(f"/posts/{post.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(post.id)
        assert body["title"] == "Test Post"
        assert "comments" in body
        assert isinstance(body["comments"], list)
        assert "likes_count" in body
        assert body["likes_count"] == 0

    async def test_get_post_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await client.get(f"/posts/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdatePost:
    async def test_update_post_owner(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        payload = {"title": "Updated Title"}
        resp = await client.patch(
            f"/posts/{post.id}", json=payload, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    async def test_update_post_non_owner(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        payload = {"title": "Hacked Title"}
        resp = await client.patch(
            f"/posts/{post.id}", json=payload, headers=second_auth_headers
        )
        assert resp.status_code == 403

    async def test_update_post_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await client.patch(
            f"/posts/{fake_id}", json={"title": "Valid Title"}, headers=auth_headers
        )
        assert resp.status_code == 404


class TestDeletePost:
    async def test_delete_post_owner(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        resp = await client.delete(f"/posts/{post.id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_post_non_owner(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        resp = await client.delete(f"/posts/{post.id}", headers=second_auth_headers)
        assert resp.status_code == 403

    async def test_delete_post_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await client.delete(f"/posts/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


class TestComments:
    async def test_create_comment_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        payload = {"content": "Nice post!"}
        resp = await client.post(
            f"/posts/{post.id}/comments", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["content"] == "Nice post!"
        assert body["post_id"] == str(post.id)
        assert "author" in body

    async def test_create_comment_post_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        fake_id = uuid.uuid4()
        payload = {"content": "Comment"}
        resp = await client.post(
            f"/posts/{fake_id}/comments", json=payload, headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_create_comment_unverified_user(
        self,
        client: AsyncClient,
        unverified_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        payload = {"content": "Nice post!"}
        resp = await client.post(
            f"/posts/{post.id}/comments",
            json=payload,
            headers=unverified_auth_headers,
        )
        assert resp.status_code == 403
        assert "verification" in resp.json()["detail"].lower()

    async def test_delete_comment_owner(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        comment = await _create_comment_in_db(db_session, post, test_user)
        resp = await client.delete(
            f"/posts/{post.id}/comments/{comment.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_delete_comment_non_owner(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        comment = await _create_comment_in_db(db_session, post, test_user)
        resp = await client.delete(
            f"/posts/{post.id}/comments/{comment.id}",
            headers=second_auth_headers,
        )
        assert resp.status_code == 403

    async def test_delete_comment_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        fake_id = uuid.uuid4()
        resp = await client.delete(
            f"/posts/{post.id}/comments/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestLike:
    async def test_like_post_success(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        resp = await client.post(f"/posts/{post.id}/like", headers=second_auth_headers)
        assert resp.status_code == 201
        assert resp.json()["detail"] == "Post liked successfully"

    async def test_like_own_post_forbidden(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        resp = await client.post(f"/posts/{post.id}/like", headers=auth_headers)
        assert resp.status_code == 403
        assert "own post" in resp.json()["detail"].lower()

    async def test_like_post_duplicate(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        await client.post(f"/posts/{post.id}/like", headers=second_auth_headers)
        resp = await client.post(f"/posts/{post.id}/like", headers=second_auth_headers)
        assert resp.status_code == 409

    async def test_unlike_post_success(
        self,
        client: AsyncClient,
        second_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        post = await _create_post_in_db(db_session, test_user)
        await client.post(f"/posts/{post.id}/like", headers=second_auth_headers)
        resp = await client.delete(
            f"/posts/{post.id}/like", headers=second_auth_headers
        )
        assert resp.status_code == 204
