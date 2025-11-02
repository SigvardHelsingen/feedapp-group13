import asyncio
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import Settings

db_semaphore = None


def create_db_engine(settings: Settings) -> AsyncEngine:
    global db_semaphore
    engine = create_async_engine(
        settings.database_url, pool_size=2, max_overflow=settings.DB_MAX_POOL_SIZE - 2
    )
    db_semaphore = asyncio.Semaphore(settings.DB_MAX_POOL_SIZE)
    return engine


async def get_db_connection(request: Request) -> AsyncGenerator[AsyncConnection, None]:
    """
    Provides a connection and a transaction context.
    Handles transaction (commit on success, rollback on error) automatically.
    """
    global db_semaphore
    engine: AsyncEngine = request.app.state.db_engine
    async with db_semaphore:
        async with engine.begin() as conn:
            yield conn


# Injectable dependency for our routes
DBConnection = Annotated[AsyncConnection, Depends(get_db_connection)]
