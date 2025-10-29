from pydantic import BaseModel, EmailStr

from app.db.sqlc.models import User


class UserInfo(BaseModel):
    id: int
    username: str
    email: EmailStr


def user_info_from_user(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
    )
