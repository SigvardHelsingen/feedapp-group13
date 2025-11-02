from typing import Annotated

import valkey.asyncio as valkey
from fastapi import Depends, Request

from app.config import Settings


async def create_valkey_pool(settings: Settings) -> valkey.ConnectionPool:
    pool = valkey.ConnectionPool.from_url(settings.VALKEY_CONN_STR)

    # Ensure we start with an empty DB
    async with valkey.Valkey(connection_pool=pool) as client:
        await client.flushdb()

    return pool


async def get_valkey_connection(request: Request):
    pool: valkey.ConnectionPool = request.app.state.valkey_pool
    async with valkey.Valkey(connection_pool=pool) as client:
        yield client


ValkeyConnection = Annotated[valkey.Valkey, Depends(get_valkey_connection)]
