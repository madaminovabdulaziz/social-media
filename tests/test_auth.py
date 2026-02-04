import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.verification_token import VerificationToken


class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        payload = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "SecureP@ss1",
            "full_name": "New User",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "new@example.com"
        assert body["username"] == "newuser"
        assert body["full_name"] == "New User"
        assert body["is_verified"] is False
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        assert "password_hash" not in body
        assert "password" not in body

    async def test_register_creates_verification_token(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        payload = {
            "email": "verify@example.com",
            "username": "verifyuser",
            "password": "SecureP@ss1",
            "full_name": "Verify User",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        user_id = uuid.UUID(resp.json()["id"])

        from sqlalchemy import select

        stmt = select(VerificationToken).where(
            VerificationToken.user_id == user_id
        )
        result = await db_session.execute(stmt)
        token = result.scalar_one_or_none()
        assert token is not None
        assert len(token.token) == 4
        assert token.token.isdigit()

    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user: User
    ) -> None:
        payload = {
            "email": test_user.email,
            "username": "uniquename",
            "password": "SecureP@ss1",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409
        assert "email" in resp.json()["detail"].lower()

    async def test_register_duplicate_username(
        self, client: AsyncClient, test_user: User
    ) -> None:
        payload = {
            "email": "unique@example.com",
            "username": test_user.username,
            "password": "SecureP@ss1",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409
        assert "username" in resp.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        payload = {
            "email": "not-an-email",
            "username": "validuser",
            "password": "SecureP@ss1",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_register_password_too_short(self, client: AsyncClient) -> None:
        payload = {
            "email": "short@example.com",
            "username": "validuser",
            "password": "Short1",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_register_username_too_short(self, client: AsyncClient) -> None:
        payload = {
            "email": "u@example.com",
            "username": "ab",
            "password": "SecureP@ss1",
        }
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(
        self, client: AsyncClient, test_user: User
    ) -> None:
        payload = {
            "email": "testuser@example.com",
            "password": "StrongPass123",
        }
        resp = await client.post("/auth/login", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    async def test_login_wrong_password(
        self, client: AsyncClient, test_user: User
    ) -> None:
        payload = {
            "email": "testuser@example.com",
            "password": "WrongPassword",
        }
        resp = await client.post("/auth/login", json=payload)
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        payload = {
            "email": "nobody@example.com",
            "password": "SomePass123",
        }
        resp = await client.post("/auth/login", json=payload)
        assert resp.status_code == 401


class TestMe:
    async def test_me_authenticated(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ) -> None:
        resp = await client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(test_user.id)
        assert body["email"] == test_user.email
        assert body["username"] == test_user.username

    async def test_me_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/auth/me")
        assert resp.status_code == 403


class TestUpdateMe:
    async def test_update_username(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ) -> None:
        resp = await client.patch(
            "/auth/me",
            json={"username": "newname"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    async def test_update_full_name(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ) -> None:
        resp = await client.patch(
            "/auth/me",
            json={"full_name": "New Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "New Name"

    async def test_update_duplicate_username(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        second_user: User,
    ) -> None:
        resp = await client.patch(
            "/auth/me",
            json={"username": second_user.username},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_update_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.patch("/auth/me", json={"username": "hack"})
        assert resp.status_code == 403


class TestVerifyEmail:
    async def test_verify_email_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Register a new user
        payload = {
            "email": "toverify@example.com",
            "username": "toverify",
            "password": "SecureP@ss1",
            "full_name": "To Verify",
        }
        reg_resp = await client.post("/auth/register", json=payload)
        assert reg_resp.status_code == 201
        assert reg_resp.json()["is_verified"] is False

        # Grab the token from DB
        from sqlalchemy import select

        user_id = uuid.UUID(reg_resp.json()["id"])
        stmt = select(VerificationToken).where(
            VerificationToken.user_id == user_id
        )
        result = await db_session.execute(stmt)
        vt = result.scalar_one()

        # Verify with POST email + code
        resp = await client.post(
            "/auth/verify-email",
            json={"email": "toverify@example.com", "code": vt.token},
        )
        assert resp.status_code == 200
        assert resp.json()["is_verified"] is True

    async def test_verify_email_invalid_code(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/auth/verify-email",
            json={"email": "nobody@example.com", "code": "9999"},
        )
        assert resp.status_code == 400

    async def test_verify_email_wrong_code(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        payload = {
            "email": "wrongcode@example.com",
            "username": "wrongcode",
            "password": "SecureP@ss1",
            "full_name": "Wrong Code",
        }
        reg_resp = await client.post("/auth/register", json=payload)
        assert reg_resp.status_code == 201

        resp = await client.post(
            "/auth/verify-email",
            json={"email": "wrongcode@example.com", "code": "0000"},
        )
        assert resp.status_code == 400
