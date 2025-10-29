import base64
import random

from fastapi import status
from fastapi.testclient import TestClient


def test_full_user_workflow(client: TestClient):
    random_suffix = random.randint(1000, 9999)
    password = str(base64.encodebytes(random.randbytes(100)))
    user_data = {
        "username": f"testuser_{random_suffix}",
        "email": f"testuser_{random_suffix}@example.com",
        "password": password,
    }
    login_payload = {"username": user_data["username"], "password": password}

    # 1. Register a new user
    register_response = client.post("/api/user/register", json=user_data)
    assert (
        register_response.status_code == status.HTTP_201_CREATED
    ), "Failed to register user"
    registered_user: dict[str, str] = register_response.json()
    assert registered_user["username"] == user_data["username"]

    # 2. Log in
    login_response = client.post("/api/user/login", json=login_payload)
    assert login_response.status_code == status.HTTP_204_NO_CONTENT, "Failed to log in"
    # The TestClient automatically handles cookies for subsequent requests

    # 3. Access protected route
    profile_response = client.get("/api/user/me")
    assert (
        profile_response.status_code == status.HTTP_200_OK
    ), "Failed to access protected route"
    assert profile_response.json()["username"] == user_data["username"]

    # 4. Log out
    logout_response = client.post("/api/user/logout")
    assert (
        logout_response.status_code == status.HTTP_204_NO_CONTENT
    ), "Failed to log out"

    # 5. Verify protected route is no longer accessible
    profile_after_logout_response = client.get("/api/user/me")
    assert (
        profile_after_logout_response.status_code == status.HTTP_401_UNAUTHORIZED
    ), "Protected route was accessible after logout"
