from argon2 import PasswordHasher
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from app.utils.user_info import UserInfo, user_info_from_user

from ..auth.cookie import CurrentUserRequired, clear_auth_cookie, set_auth_cookie
from ..db.db import DBConnection
from ..db.sqlc import user as user_queries

router = APIRouter(prefix="/user", tags=["user"])


class CreateUserPayload(BaseModel):
    username: str
    email: EmailStr
    password: str


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: CreateUserPayload, conn: DBConnection, response: Response
):
    ph = PasswordHasher()
    password_hash = ph.hash(payload.password)

    q = user_queries.AsyncQuerier(conn)
    try:
        user = await q.create_user(
            username=payload.username, email=payload.email, password_hash=password_hash
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username or email already exists",
        )

    assert user is not None, "User should exist if created successfully"

    user_info = user_info_from_user(user)
    set_auth_cookie(user_info, response)
    return user_info


class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(payload: LoginPayload, response: Response, conn: DBConnection):
    q = user_queries.AsyncQuerier(conn)
    user = await q.get_user_by_username_or_email(username=payload.username)

    # TODO: maybe secure against timing attacks
    ph = PasswordHasher()
    validated = (
        ph.verify(user.password_hash, payload.password) if user is not None else False
    )

    if user is None or not validated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user_info = user_info_from_user(user)
    set_auth_cookie(user_info, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    clear_auth_cookie(response)


@router.get("/me", response_model=UserInfo)
async def read_users_me(current_user: CurrentUserRequired):
    return current_user
