from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.kafka import VOTE_EVENT_TOPIC, KafkaProducer, VoteEvent
from app.db.sqlc.models import Permission
from app.utils.vote_counter import ensure_valkey_vote_table, vote_table_key

from ..auth.cookie import CurrentUserRequired
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


@router.get("/{poll_id}", response_model=list[vote_queries.GetVoteCountsRow])
async def get_votes_for_poll(
    poll_id: int, conn: DBConnection, valkey: ValkeyConnection
):
    await ensure_valkey_vote_table(poll_id, conn, valkey)

    # Get materialized vote counts from valkey
    vote_counts: dict[int, int] = await valkey.hgetall(vote_table_key(poll_id))

    return [
        vote_queries.GetVoteCountsRow(vote_option_id=k, vote_count=v)
        for k, v in vote_counts.items()
    ]
