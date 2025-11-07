import asyncio
from contextlib import asynccontextmanager

from app.db.db import DBConnection
from app.db.sqlc import vote as vote_queries
from app.db.valkey import ValkeyConnection


@asynccontextmanager
async def acquire_valkey_lock(valkey: ValkeyConnection, lock_key: str):
    # Atomically sets lock only if it is not already set
    acquired = await valkey.set(lock_key, "locked", nx=True)
    try:
        if acquired:
            yield True
        else:
            yield False
    finally:
        await valkey.delete(lock_key)


def vote_table_key(poll_id: int) -> str:
    return f"poll:{poll_id}:votes"


async def ensure_valkey_vote_table(
    poll_id: int, conn: DBConnection, valkey: ValkeyConnection
):
    """
    Atomically ensure a vote counts table exists in Valkey.
    If it does not exist, it will be created exactly once by reading from the database.
    All other callers of this function wait until the count is finished.
    """
    table_key = vote_table_key(poll_id)
    lock_key = f"{table_key}:lock"

    if await valkey.exists(table_key):
        return

    while True:
        async with acquire_valkey_lock(valkey, lock_key) as acquired:
            if not acquired:
                # Wait and check if created successfully
                await asyncio.sleep(0.5)
                if await valkey.exists(table_key):
                    return

                continue

            # Lock acquired
            if await valkey.exists(table_key):
                return

            # Create vote table
            q = vote_queries.AsyncQuerier(conn)
            _ = await valkey.hset(
                table_key,
                mapping={
                    x.vote_option_id: x.vote_count
                    async for x in q.get_vote_counts(id=poll_id)
                },
            )
            return
