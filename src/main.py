from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.admin import router as admin_router
from src.api.auth import router as auth_router
from src.api.feed import router as feed_router
from src.api.posts import router as posts_router
from src.core.database import close_engine, init_engine
from src.core.limiter import limiter


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_engine()
    yield
    await close_engine()


app = FastAPI(
    title="Social Media API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(feed_router)
app.include_router(admin_router)
