import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from valkey.asyncio import Valkey

from app.db.kafka import VOTE_EVENT_TOPIC, KafkaProducer, VoteEvent
from app.db.sqlc.models import Permission
from app.db.valkey import PollUpdateEvent
from app.sse.manager import SSEManager
from app.utils.vote_counter import ensure_valkey_vote_table, vote_table_key

from ..auth.cookie import CurrentUserOptional, CurrentUserRequired
from ..db.db import DBConnection
from ..db.sqlc import auth as auth_queries, poll as poll_queries, vote as vote_queries
from ..db.valkey import ValkeyConnection

router = APIRouter(prefix="/vote", tags=["vote"])


class VotePayload(BaseModel):
    vote_option_id: int
    poll_id: int


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_vote(
    user: CurrentUserRequired,
    payload: VotePayload,
    conn: DBConnection,
    producer: KafkaProducer,
):
    recv_time = datetime.now(tz=timezone.utc)
    recv_time = recv_time.replace(microsecond=(recv_time.microsecond // 1000) * 1000)
    recv_unix_ms = int(recv_time.timestamp() * 1000)

    a = auth_queries.AsyncQuerier(conn)
    vote_access = await a.can_user_do_at(
        user_id=user.id,
        poll_id=payload.poll_id,
        permission=Permission.POLL_VOTE,
        timestamp=recv_time,
    )
    if vote_access is None or not vote_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have voting rights for this poll",
        )

    p = poll_queries.AsyncQuerier(conn)
    ok = await p.poll_option_belongs_to_poll(
        poll_id=payload.poll_id, poll_option_id=payload.vote_option_id
    )
    if ok is None or not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The provided poll option is not valid for the poll",
        )

    await producer.send(
        topic=VOTE_EVENT_TOPIC,
        value=VoteEvent(user_id=user.id, poll_option_id=payload.vote_option_id),
        # not a key in the sense of dictionaries, rather a hint for partitioning
        key=payload.poll_id,
        timestamp_ms=recv_unix_ms,
    )


@router.get(
    "/{poll_id}", response_model=list[vote_queries.GetVoteCountsRow], deprecated=True
)
async def get_votes_for_poll(
    poll_id: int, conn: DBConnection, valkey: ValkeyConnection
):
    """This endpoint is deprecated, use the SSE one instead"""
    await ensure_valkey_vote_table(poll_id, conn, valkey)

    # Get materialized vote counts from valkey
    vote_counts: dict[int, int] = await valkey.hgetall(vote_table_key(poll_id))

    return [
        vote_queries.GetVoteCountsRow(vote_option_id=k, vote_count=v)
        for k, v in vote_counts.items()
    ]


@router.get("/stream/{poll_id}")
async def stream_vote_updates(
    poll_id: int,
    request: Request,
    user: CurrentUserOptional,
):
    """SSE endpoint for live poll vote counts"""
    user_id = user.id if user else None

    # BAD: Hacks around dependency injection.
    # I was concerned about leaking connections (keeping them up for too long)
    # TODO: fix
    db_engine = request.app.state.db_engine
    valkey_pool = request.app.state.valkey_pool

    async with db_engine.begin() as conn, Valkey(
        connection_pool=valkey_pool
    ) as valkey_conn:
        # Check permissions
        a = auth_queries.AsyncQuerier(conn)
        view_access = await a.can_user_do_at(
            user_id=user_id,
            poll_id=poll_id,
            permission=Permission.POLL_VIEW,
            timestamp=None,
        )
        if view_access is None or not view_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this poll",
            )

        # Get initial data so the client won't have to wait for an update
        await ensure_valkey_vote_table(poll_id, conn, valkey_conn)
        vote_counts: dict[bytes, bytes] = await valkey_conn.hgetall(
            vote_table_key(poll_id)
        )
        initial_data = [
            {
                "vote_option_id": int(k.decode()),
                "vote_count": int(v.decode()),
            }
            for k, v in vote_counts.items()
        ]

    # TODO: dependency inject?
    sse_manager: SSEManager = request.app.state.sse_manager

    async def event_generator():
        # Try to subscribe through the manager, might fail on too many connections
        try:
            client_queue = await sse_manager.subscribe(poll_id, user_id)
        except RuntimeError as e:
            yield {
                "event": "error",
                "data": {"error": str(e)},
            }
            return

        try:
            # Send initial vote counts
            yield {"event": "vote_update", "data": json.dumps(initial_data)}

            while True:
                if await request.is_disconnected():
                    break

                # Wait for updates, but periodically send keepalives
                try:
                    event: PollUpdateEvent = await asyncio.wait_for(
                        client_queue.get(), timeout=30.0
                    )

                    data = [
                        {
                            "vote_option_id": row.vote_option_id,
                            "vote_count": row.vote_count,
                        }
                        for row in event.vote_counts
                    ]

                    yield {"event": "vote_update", "data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        finally:
            await sse_manager.unsubscribe(poll_id, user_id, client_queue)

    return EventSourceResponse(event_generator())
