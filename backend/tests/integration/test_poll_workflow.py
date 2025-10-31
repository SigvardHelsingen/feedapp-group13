import base64
import datetime
import random

from fastapi import status
from fastapi.testclient import TestClient


def test_full_poll_workflow(client: TestClient):
    random_suffix_1 = random.randint(1000, 9999)
    random_suffix_2 = random.randint(1000, 9999)

    password = str(base64.encodebytes(random.randbytes(100)))
    user_data_1 = {
        "username": f"testuser_{random_suffix_1}",
        "email": f"testuser_{random_suffix_1}@example.com",
        "password": password,
    }
    user_data_2 = {
        "username": f"testuser_{random_suffix_2}",
        "email": f"testuser_{random_suffix_2}@example.com",
        "password": password,
    }
    poll_data_non_expiry = {
        "question": f"testquestion_{random_suffix_1}",
        "options": [
            f"testoption_{random_suffix_1}",
            f"testoption_{random_suffix_1}",
            f"testoption_{random_suffix_1}",
        ],
        "expires_at": None,
    }
    poll_data_expiry = {
        "question": f"testquestion_{random_suffix_2}",
        "options": [
            f"testoption_{random_suffix_2}",
            f"testoption_{random_suffix_2}",
            f"testoption_{random_suffix_2}",
        ],
        "expires_at": (
            datetime.datetime.now() + datetime.timedelta(days=1)
        ).isoformat(),
    }
    login_payload_1 = {"username": user_data_1["username"], "password": password}
    login_payload_2 = {"username": user_data_2["username"], "password": password}

    # 1. Non-authorized user cannot create a poll
    poll_without_auth = client.post("/api/poll/create", json=poll_data_non_expiry)
    assert (
        poll_without_auth.status_code == status.HTTP_401_UNAUTHORIZED
    ), "Failed to create poll, no user found"

    # 2. Authorized user can create a poll without expiry date.
    client.post("/api/user/register", json=user_data_1)
    client.post("api/user/login", json=login_payload_1)
    created_response = client.post("api/poll/create", json=poll_data_non_expiry)
    assert (
        created_response.status_code == status.HTTP_201_CREATED
    ), "Failed to create poll"

    # 3. Authorize user can create a poll with expiry date.
    created_response = client.post("api/poll/create", json=poll_data_expiry)
    assert (
        created_response.status_code == status.HTTP_201_CREATED
    ), "Failed to create poll"

    # 4. Any user can get all polls
    get_polls_response = client.get("api/poll/all")
    assert len(get_polls_response.json()) == 2, "Cannot get all polls"

    # 5. User can delete their own poll
    user_owned_poll = get_polls_response.json()[0]["id"]
    deleted_response = client.delete(f"api/poll/{user_owned_poll}")
    assert (
        deleted_response.status_code == status.HTTP_204_NO_CONTENT
    ), f"Failed to delete poll with id {user_owned_poll}"

    # 6. User cannot delete an already deleted poll
    deleted_response = client.delete(f"api/poll/{user_owned_poll}")
    assert (
        deleted_response.status_code == status.HTTP_400_BAD_REQUEST
    ), "Cannot delete poll, does not exist"

    # 7. User cannot delete another users poll
    _ = client.post("api/user/logout")
    _ = client.post("api/user/create", json=user_data_2)
    _ = client.post("api/user/login", json=login_payload_2)
    user_owned_poll = get_polls_response.json()[1]["id"]
    deleted_response = client.delete(f"api/poll/{user_owned_poll}")
    assert (
        deleted_response.status_code == status.HTTP_401_UNAUTHORIZED
    ), f"Failed to delete poll {user_owned_poll}"
