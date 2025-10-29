import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..auth.cookie import CurrentUserRequired
from ..db.db import DBConnection
from ..db.sqlc import poll as poll_queries

router = APIRouter(prefix="/poll", tags=["poll"])


class CreatePollPayload(BaseModel):
    question: str
    options: list[str]
    expires_at: datetime | None


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_poll(
    payload: CreatePollPayload, user: CurrentUserRequired, conn: DBConnection
):
    if len(payload.question) == 0 or len(payload.options) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You need to provide a question with at least 1 vote option",
        )

    q = poll_queries.AsyncQuerier(conn)
    poll_id = await q.create_poll(
        question=payload.question, created_by=user.id, expires_at=payload.expires_at
    )
    if poll_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store poll to database",
        )

    coros = [
        q.create_vote_option(caption=cap, poll_id=poll_id, presentation_order=i)
        for i, cap in enumerate(payload.options)
    ]
    _ = await asyncio.gather(*coros)


@router.get("/all", response_model=list[poll_queries.GetPollsRow])
async def get_all_polls(conn: DBConnection):
    q = poll_queries.AsyncQuerier(conn)
    return [x async for x in q.get_polls()]


@router.get("/{poll_id}", response_model=poll_queries.GetPollRow)
async def get_poll_by_id(poll_id: int, conn: DBConnection):
    q = poll_queries.AsyncQuerier(conn)
    poll = await q.get_poll(id=poll_id)
    if poll is None:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested poll does not exist",
        )

    return poll


@router.delete("/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll_by_id(
    poll_id: int, user: CurrentUserRequired, conn: DBConnection
):
    q = poll_queries.AsyncQuerier(conn)

    poll = await q.get_poll(id=poll_id)
    if poll is None:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested poll does not exist",
        )

    if poll.creator_name != user.username:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You can only delete your own polls",
        )

    await q.delete_vote_options_for_poll(poll_id=poll.id)
    await q.delete_poll(id=poll.id)
