from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:
    engine = create_async_engine(settings.database_url)
    return engine


async def get_db_connection(request: Request) -> AsyncGenerator[AsyncConnection, None]:
    """
    Provides a connection and a transaction context.
    Handles transaction (commit on success, rollback on error) automatically.
    """
    engine: AsyncEngine = request.app.state.db_engine
    async with engine.begin() as conn:
        yield conn


# Injectable dependency for our routes
DBConnection = Annotated[AsyncConnection, Depends(get_db_connection)]
