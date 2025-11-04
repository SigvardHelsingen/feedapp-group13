from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from jwt.exceptions import DecodeError

from ..utils.user_info import UserInfo
try:
    from app.utils.config import get_settings
except Exception:
    get_settings = None

_COOKIE_NAME = "feedapp_session_token"
# config (...)
SECRET_KEY: str = (
    getattr(settings, "SECRET_KEY", None) or
    getattr(settings, "JWT_SECRET_KEY", None) or
    "REMEMBER-TO_CHANGE-ME-TO-SOMETHING-USEFUL-PLEASE"
)
ALGORITHM: str = getattr(settings, "ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_SECONDS: int = int(
    getattr(settings, "ACCESS_TOKEN_EXPIRE_SECONDS", 3600)
)
COOKIE_SECURE: bool = getattr(settings, "COOKIE_SECURE", False)
COOKIE_SAMESITE: str = getattr(settings, "COOKIE_SAMESITE", "strict")
COOKIE_DOMAIN: Optional[str] = getattr(settings, "COOKIE_DOMAIN", None)

#sliding session refresh
SLIDING_RENEW_THRESHOLD_SEC: int = getattr(settings, "SLIDING_RENEW_THRESHOLD", 15*60)

""" 
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
"""

def create_jwt(user_info: UserInfo) -> str:
    """ Create a a signed JWT for the given user."""
    now = datetime.utcnow()
    exp = now + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)

    payload = {
        "sub": str(user_info.id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "id": user_info.id,
        "username": user_info.username,
        "email": user_info.email,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _maybe_renew_sliding_token(payload: dict, response: Response, user: UserInfo):
    """Renew the cookie only if token is close to expiry"""
    exp_ts = payload.get("exp")
    if not isinstance(exp_ts, int):
        # if missing/invalid, just issue a fresh one
        set_auth_cookie(user, response)
        return

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if exp_ts - now_ts <= SLIDING_RENEW_THRESHOLD_SEC :
        set_auth_cookie(user, response)



def set_auth_cookie(user_info: UserInfo, response: Response):
    """
    Create a JWT and store it in a cookie
    """
    token = create_jwt(user_info) #token = jwt.encode(user_info.__dict__, "secret", algorithm="HS256")
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # TODO: set this to True (breaks the TestClient)
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS
        #max_age=3600,  # 1 hour
    )


def clear_auth_cookie(response: Response):
    """
    Clears the authentication cookie to log a user out.
    """
    response.delete_cookie(_COOKIE_NAME, domain=COOKIE_DOMAIN)


def get_current_user_optional(request: Request, response: Response) -> UserInfo | None:
    """
    Dependency to optionally get the current user.

    Use this when a route should be accessible to unauthenticated users,
    but you'd also like to have the user info if they are logged in.
    """
    token_str = request.cookies.get(_COOKIE_NAME)
    if not token_str:
        return None

    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
        # jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM], issuer="feedapp", audience="feedapp_client")
    except ExpiredSignatureError:
        #Token is expired: clear the cookie, treat as not logged in
        clear_auth_cookie(response)
        return None
    except DecodeError:
        #Token is invalid/malformed: cleark cookie, treat as "not logged in"
        clear_auth_cookie(response)
        return None

    #Sanity check
    user_id = payload.get("id") or payload.get("sub")
    username = payload.get("username")
    email = payload.get("email")

    if user_id is None or username is None or email is None:
        clear_auth_cookie(response)
        return None

    user = UserInfo( #user = UserInfo(id=int(user_id), username=str(username), email=str(email))
        id=token["id"],
        username=token["username"],
        email=token["email"],
    )


    # Renew the token
    # set_auth_cookie(user, response)
    _maybe_renew_sliding_token(payload, response, user)

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
