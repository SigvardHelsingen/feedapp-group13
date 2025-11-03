from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

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
    valkey: ValkeyConnection,
):
    a = auth_queries.AsyncQuerier(conn)
    vote_access = await a.can_user_do_at(
        user_id=user.id,
        poll_id=payload.poll_id,
        permission=Permission.POLL_VOTE,
        timestamp=None,
    )
    if vote_access is None or not vote_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have voting rights for this poll",
        )

    q = vote_queries.AsyncQuerier(conn)
    p = poll_queries.AsyncQuerier(conn)
    poll = await p.get_poll(poll_id=payload.poll_id, user_id=user.id)
    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )
    if payload.vote_option_id not in poll.option_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll option id not found"
        )

    await ensure_valkey_vote_table(payload.poll_id, conn, valkey)

    # Ensure new vote (and potential deletion of old) is written without conflicts to DB
    deleted_vote_option_id = await q.delete_user_vote_on_poll(
        poll_id=payload.poll_id, user_id=user.id
    )
    await q.submit_vote(user_id=user.id, vote_option_id=payload.vote_option_id)
    await conn.commit()

    # Atomically increment (and potentially decrement) vote counts
    pipe = valkey.pipeline()
    if deleted_vote_option_id is not None:
        pipe.hincrby(vote_table_key(payload.poll_id), str(deleted_vote_option_id), -1)
    pipe.hincrby(vote_table_key(payload.poll_id), str(payload.vote_option_id), 1)
    _ = await pipe.execute()


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
