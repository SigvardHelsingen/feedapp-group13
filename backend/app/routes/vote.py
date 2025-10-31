from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..auth.cookie import CurrentUserRequired
from ..db.db import DBConnection
from ..db.sqlc import vote as vote_queries

router = APIRouter(prefix="/vote", tags=["vote"])


class VotePayload(BaseModel):
    vote_option_id: int
    poll_id: int


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_vote(
    user: CurrentUserRequired, payload: VotePayload, conn: DBConnection
):
    q = vote_queries.AsyncQuerier(conn)
    await q.delete_user_vote_on_poll(poll_id=payload.poll_id, user_id=user.id)
    await q.submit_vote(user_id=user.id, vote_option_id=payload.vote_option_id)


@router.get("/{poll_id}", response_model=list[vote_queries.GetVoteCountsRow])
async def get_votes_for_poll(poll_id: int, conn: DBConnection):
    q = vote_queries.AsyncQuerier(conn)
    return [x async for x in q.get_vote_counts(id=poll_id)]
