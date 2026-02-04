from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db_session
from src.models.user import User
from src.services.user import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete("/cleanup-users")
async def cleanup_unverified_users(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    user_service = UserService(session)
    deleted_count = await user_service.delete_unverified_stale(older_than=cutoff)
    return {"deleted_count": deleted_count}
