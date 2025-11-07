from typing import Annotated

import valkey.asyncio as valkey
from fastapi import Depends, Request
from pydantic import BaseModel

from app.config import Settings
from app.db.sqlc import vote as vote_queries


async def create_valkey_pool(settings: Settings) -> valkey.ConnectionPool:
    pool = valkey.ConnectionPool.from_url(settings.VALKEY_CONN_STR)

    # Ensure we start with an empty DB
    async with valkey.Valkey(connection_pool=pool) as client:
        await client.flushdb()

    return pool


async def _get_valkey_connection(request: Request):
    pool: valkey.ConnectionPool = request.app.state.valkey_pool
    async with valkey.Valkey(connection_pool=pool) as client:
        yield client


ValkeyConnection = Annotated[valkey.Valkey, Depends(_get_valkey_connection)]


class PollUpdateEvent(BaseModel):
    poll_id: int
    vote_counts: list[vote_queries.GetVoteCountsRow]


def poll_update_topic(poll_id: int) -> str:
    return f"vote-updates:poll:{poll_id}"


async def publish_poll_update(
    valkey: valkey.Valkey,
    poll_id: int,
    vote_counts: list[vote_queries.GetVoteCountsRow],
):
    # TODO: poll_id in the event might be redundant information...
    event = PollUpdateEvent(poll_id=poll_id, vote_counts=vote_counts)
    topic = poll_update_topic(poll_id)
    await valkey.publish(topic, event.model_dump_json())
