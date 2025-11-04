from fastapi import APIRouter
from app.auth.cookie import CurrentUserRequired
from app.utils.user_info import UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/whoami", response_model=UserInfo)
def whoami(user: CurrentUserRequired) -> UserInfo:
    return user
