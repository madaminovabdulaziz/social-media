from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.models.user import User


class TestCleanupUsers:
    async def test_cleanup_deletes_stale_unverified(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        stale_user = User(
            email="stale@example.com",
            username="staleuser",
            password_hash=hash_password("StalePass1"),
            full_name="Stale User",
            is_verified=False,
        )
        db_session.add(stale_user)
        await db_session.commit()
        await db_session.refresh(stale_user)

        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        stmt = (
            update(User)
            .where(User.id == stale_user.id)
            .values(created_at=old_time)
        )
        await db_session.execute(stmt)
        await db_session.commit()

        resp = await client.delete("/admin/cleanup-users", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted_count"] >= 1

    async def test_cleanup_keeps_recent_unverified(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ) -> None:
        resp = await client.delete("/admin/cleanup-users", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted_count"] == 0

    async def test_cleanup_keeps_verified_users(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ) -> None:
        verified_user = User(
            email="verified@example.com",
            username="verifieduser",
            password_hash=hash_password("Verified1"),
            full_name="Verified User",
            is_verified=True,
        )
        db_session.add(verified_user)
        await db_session.commit()
        await db_session.refresh(verified_user)

        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        stmt = (
            update(User)
            .where(User.id == verified_user.id)
            .values(created_at=old_time)
        )
        await db_session.execute(stmt)
        await db_session.commit()

        resp = await client.delete("/admin/cleanup-users", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted_count"] == 0
