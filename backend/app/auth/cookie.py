from typing import Annotated

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

from ..config import get_settings
from ..utils.user_info import UserInfo


_COOKIE_NAME = "feedapp_session_token"

def create_jwt(user_info: UserInfo) -> str:
    """ Create a signed JWT for the given user."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.SESSION_TTL_SECONDS)

    payload = {
        "sub": str(user_info.id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "id": user_info.id,
        "username": user_info.username,
        "email": str(user_info.email),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)




def set_auth_cookie(user_info: UserInfo, response: Response):
    """
    Create a JWT and store it in a cookie
    """
    settings = get_settings()
    token = create_jwt(user_info)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),  # TODO: set this to True (breaks the TestClient)
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
    )


def clear_auth_cookie(response: Response):
    """
    Clears the authentication cookie to log a user out.
    """
    settings = get_settings()
    response.delete_cookie(_COOKIE_NAME)


def get_current_user_optional(request: Request, response: Response) -> UserInfo | None:
    """
    Dependency to optionally get the current user.

    Use this when a route should be accessible to unauthenticated users,
    but you'd also like to have the user info if they are logged in.
    """
    settings = get_settings()
    token_str = request.cookies.get(_COOKIE_NAME)
    if not token_str:
        return None
    try:
        payload = jwt.decode(token_str, settings.SECRET_KEY, settings.ALGORITHM)
    except ExpiredSignatureError:
        #Token is expired: clear the cookie, treat as not logged in
        clear_auth_cookie(response)
        return None
    except (DecodeError, InvalidTokenError): #might delete l8r
        clear_auth_cookie(response)
        return None

    #Sanity check (cuz im going insane w this sh)
    user_id = payload.get("id") or payload.get("sub")
    username = payload.get("username")
    email = payload.get("email")

    if user_id is None or username is None or email is None:
        clear_auth_cookie(response)
        return None

    user = UserInfo(id=int(user_id), username=str(username), email=str(email))
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
