import asyncio
import signal
from datetime import datetime, timezone
from types import FrameType

import uvloop
from sqlalchemy.ext.asyncio import AsyncConnection
from valkey.asyncio import ConnectionPool, Valkey

from app.config import Settings
from app.db.db import create_db_engine
from app.db.kafka import VoteEvent, create_kafka_consumer
from app.db.sqlc import vote as vote_queries
from app.db.valkey import publish_poll_update
from app.utils.vote_counter import ensure_valkey_vote_table, vote_table_key

shutdown_event = asyncio.Event()


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

    # Get the updated vote counts and publish to Redis pub/sub
    vote_counts: dict[int, int] = await valkey.hgetall(vote_table_key(poll_id))
    vote_counts_list = [
        vote_queries.GetVoteCountsRow(vote_option_id=k, vote_count=v)
        for k, v in vote_counts.items()
    ]
    await publish_poll_update(valkey, poll_id, vote_counts_list)


def handle_shutdown_signal(signum: int, _frame: FrameType):
    print(f"\nReceived signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def main():
    settings = Settings()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    db_engine, _ = create_db_engine(settings)
    pool = ConnectionPool.from_url(settings.VALKEY_CONN_STR)
    consumer = await create_kafka_consumer(settings)

    print("Consumer started, processing vote events...")
    print("Press Ctrl+C to gracefully shutdown")

    try:
        while not shutdown_event.is_set():
            try:
                # Get messages while periodically checking for shutdown signals
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)

                # TODO: what should happen on a deleted / nonexistent poll?
                poll_id: int = msg.key
                ve: VoteEvent = msg.value
                recv_time = datetime.fromtimestamp(
                    msg.timestamp / 1000, tz=timezone.utc
                )

                async with db_engine.begin() as conn, Valkey(
                    connection_pool=pool
                ) as valkey:
                    await process_vote(poll_id, ve, recv_time, conn, valkey)
            except asyncio.TimeoutError:
                continue
    finally:
        print("Stopping Kafka consumer...")
        await consumer.stop()
        print("Closing database connection pool...")
        await db_engine.dispose()
        print("Closing Valkey connection pool...")
        await pool.aclose()
        print("Consumer shutdown complete")


if __name__ == "__main__":
    uvloop.run(main())
