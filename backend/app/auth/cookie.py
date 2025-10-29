from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from jwt.exceptions import DecodeError

from ..utils.user_info import UserInfo

_COOKIE_NAME = "feedapp_session_token"


def set_auth_cookie(user_info: UserInfo, response: Response):
    """
    Create a JWT and store it in a cookie
    """
    token = jwt.encode(user_info.__dict__, "secret", algorithm="HS256")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # TODO: set this to True (breaks the TestClient)
        samesite="strict",
        max_age=3600,  # 1 hour
    )


def clear_auth_cookie(response: Response):
    """
    Clears the authentication cookie to log a user out.
    """
    response.delete_cookie(_COOKIE_NAME)


def get_current_user_optional(request: Request, response: Response) -> UserInfo | None:
    """
    Dependency to optionally get the current user.

    Use this when a route should be accessible to unauthenticated users,
    but you'd also like to have the user info if they are logged in.
    """
    token_str = request.cookies.get(_COOKIE_NAME)
    if not token_str:
        return None

    # TODO: Validate properly
    try:
        token = jwt.decode(token_str, "secret", algorithms=["HS256"])
    except DecodeError:
        raise

    user = UserInfo(
        id=token["id"],
        username=token["username"],
        email=token["email"],
    )

    # Renew the token
    set_auth_cookie(user, response)

    return user


CurrentUserOptional = Annotated[UserInfo | None, Depends(get_current_user_optional)]


def get_current_user_required(user: CurrentUserOptional) -> UserInfo:
    """
    Dependency to get the current user, that requires a user to be logged in.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


CurrentUserRequired = Annotated[UserInfo, Depends(get_current_user_required)]
