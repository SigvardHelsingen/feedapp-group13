from datetime import datetime, timezone

import uvloop
from sqlalchemy.ext.asyncio import AsyncConnection
from valkey.asyncio import ConnectionPool, Valkey

from app.config import Settings
from app.db.db import create_db_engine
from app.db.kafka import VoteEvent, create_kafka_consumer
from app.db.sqlc import vote as vote_queries
from app.utils.vote_counter import ensure_valkey_vote_table, vote_table_key


async def process_vote(
    poll_id: int,
    ve: VoteEvent,
    _recv_time: datetime,
    conn: AsyncConnection,
    valkey: Valkey,
):
    await ensure_valkey_vote_table(poll_id, conn, valkey)

    q = vote_queries.AsyncQuerier(conn)
    # Ensure new vote (and potential deletion of old) is written without conflicts to DB
    deleted_vote_option_id = await q.delete_user_vote_on_poll(
        poll_id=poll_id, user_id=ve.user_id
    )
    await q.submit_vote(user_id=ve.user_id, vote_option_id=ve.poll_option_id)
    await conn.commit()

    # Atomically increment (and potentially decrement) vote counts
    pipe = valkey.pipeline()
    if deleted_vote_option_id is not None:
        pipe.hincrby(vote_table_key(poll_id), str(deleted_vote_option_id), -1)
    pipe.hincrby(vote_table_key(poll_id), str(ve.poll_option_id), 1)
    _ = await pipe.execute()


async def main():
    settings = Settings()

    db_engine, _ = create_db_engine(settings)
    pool = ConnectionPool.from_url(settings.VALKEY_CONN_STR)
    consumer = await create_kafka_consumer(settings)

    try:
        async for msg in consumer:
            poll_id: int = msg.key
            ve: VoteEvent = msg.value
            recv_time = datetime.fromtimestamp(msg.timestamp / 1000, tz=timezone.utc)

            async with db_engine.begin() as conn, Valkey(
                connection_pool=pool
            ) as valkey:
                await process_vote(poll_id, ve, recv_time, conn, valkey)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    uvloop.run(main())
