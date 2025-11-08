import asyncio
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.db.sqlc.models import Permission, Role

from ..auth.cookie import CurrentUserOptional, CurrentUserRequired
from ..db.db import DBConnection
from ..db.sqlc import auth as auth_queries, poll as poll_queries

router = APIRouter(prefix="/poll", tags=["poll"])


class PollPerms(Enum):
    PUBLIC_VIEW = "public_view"
    PUBLIC_VOTE = "public_vote"
    PRIVATE = "private"


class GiveAccessPayload(BaseModel):
    role: Role
    user_id: int


class CreatePollPayload(BaseModel):
    question: str
    options: list[str]
    expires_at: datetime | None
    poll_perms: PollPerms


@router.post(
    "/create",
    response_model=poll_queries.GetPollRow,
    status_code=status.HTTP_201_CREATED,
)
async def create_poll(
    payload: CreatePollPayload,
    user: CurrentUserRequired,
    conn: DBConnection,
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

    await q.assign_role(user_id=user.id, poll_id=poll_id, role=Role.CREATOR)
    if payload.poll_perms == PollPerms.PUBLIC_VIEW:
        await q.assign_public_perms(poll_id=poll_id, role=Role.VIEWER)
    elif payload.poll_perms == PollPerms.PUBLIC_VOTE:
        await q.assign_public_perms(poll_id=poll_id, role=Role.VOTER)

    coros = [
        q.create_vote_option(caption=cap, poll_id=poll_id, presentation_order=i)
        for i, cap in enumerate(payload.options)
    ]
    _ = await asyncio.gather(*coros)
    poll = await q.get_poll(user_id=user.id, poll_id=poll_id)

    return poll


@router.get(
    "/all",
    response_model=list[poll_queries.GetPollsRow],
    status_code=status.HTTP_201_CREATED,
)
async def get_all_polls(conn: DBConnection, user: CurrentUserOptional):
    q = poll_queries.AsyncQuerier(conn)
    return [x async for x in q.get_polls(user_id=user.id if user else None)]


@router.get("/{poll_id}", response_model=poll_queries.GetPollRow)
async def get_poll_by_id(poll_id: int, conn: DBConnection, user: CurrentUserOptional):
    q = poll_queries.AsyncQuerier(conn)
    poll = await q.get_poll(poll_id=poll_id, user_id=user.id if user else None)
    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested poll does not exist, or access is not granted",
        )
    return poll


@router.post("/assign/", response_model=list[int])
async def assign_role_to_user(
    curr_user: CurrentUserRequired,
    payload: list[GiveAccessPayload],
    poll_id: int,
    conn: DBConnection,
):
    a = auth_queries.AsyncQuerier(conn)
    has_access = await a.can_user_do_at(
        user_id=curr_user.id,
        poll_id=poll_id,
        permission=Permission.POLL_ASSIGN_ROLE,
        timestamp=None,
    )
    if has_access is None or not has_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have assign access to this poll, or it does not exist",
        )

    q = poll_queries.AsyncQuerier(conn)
    marked_instances: list[int] = []
    for instance in payload:
        try:
            if instance.role == Role.VOTER:
                _ = q.assign_role(
                    role=Role.VOTER, user_id=instance.user_id, poll_id=poll_id
                )
            elif instance.role == Role.VIEWER:
                _ = q.assign_role(
                    role=Role.VIEWER, user_id=instance.user_id, poll_id=poll_id
                )
            elif instance.role == Role.CREATOR:
                _ = q.assign_role(
                    role=Role.CREATOR, user_id=instance.user_id, poll_id=poll_id
                )
        except IntegrityError:
            marked_instances.append(instance.user_id)
    return marked_instances


@router.get("/users{poll_id}", response_model=list[poll_queries.GetActivePollRolesRow])
async def get_users_for_poll(
    user: CurrentUserRequired, conn: DBConnection, poll_id: int
):
    a = auth_queries.AsyncQuerier(conn)
    has_access = await a.can_user_do_at(
        user_id=user.id,
        poll_id=poll_id,
        permission=Permission.POLL_DELETE,
        timestamp=None,
    )
    if has_access is None or not has_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have get access to this poll, or it does not exist",
        )

    q = poll_queries.AsyncQuerier(conn)
    poll_active_users = q.get_active_poll_roles(poll_id=poll_id)
    return poll_active_users


@router.delete("/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll_by_id(
    poll_id: int, user: CurrentUserRequired, conn: DBConnection
):
    a = auth_queries.AsyncQuerier(conn)
    delete_access = await a.can_user_do_at(
        user_id=user.id,
        poll_id=poll_id,
        permission=Permission.POLL_DELETE,
        timestamp=None,
    )
    if delete_access is None or not delete_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have delete access to this poll, or it does not exist",
        )

    q = poll_queries.AsyncQuerier(conn)
    await q.delete_grants_for_poll(poll_id=poll_id)
    await q.delete_vote_options_for_poll(poll_id=poll_id)
    await q.delete_poll(id=poll_id)
