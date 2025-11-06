import base64
import datetime
import random

from fastapi import status
from fastapi.testclient import TestClient


def test_full_poll_workflow(client: TestClient):
    random_suffix_1 = random.randint(1000, 9999)

    password = str(base64.encodebytes(random.randbytes(100)))
    user_data = {
        "username": f"testuser_{random_suffix_1}",
        "email": f"testuser_{random_suffix_1}@example.com",
        "password": password,
    }
    poll_data_expiry = {
        "question": f"testquestion_{random_suffix_1}",
        "options": [
            f"testoption_{random_suffix_1}",
            f"testoption_{random_suffix_1}",
            f"testoption_{random_suffix_1}",
        ],
        "poll_perms": "public_vote",
        "expires_at": (
            datetime.datetime.now() + datetime.timedelta(days=1)
        ).isoformat(),
    }

    login_payload = {"username": user_data["username"], "password": password}

    # 1. Non-authorized user cannot vote on a poll.
    vote_without_auth = client.post("api/vote/submit")
    assert (
        vote_without_auth.status_code == status.HTTP_401_UNAUTHORIZED
    ), "Voting without being authorized not permitted"

    # 2. Authorized vote on poll
    _ = client.post("/api/user/register", json=user_data)
    _ = client.post("/api/user/login", json=login_payload)
    returned_poll = client.post("/api/poll/create", json=poll_data_expiry)
    poll_data = returned_poll.json()
    vote_data = {
        "vote_option_id": poll_data["option_ids"][0],
        "poll_id": poll_data["id"],
    }
    register_vote = client.post("/api/vote/submit", json=vote_data)
    assert (
        register_vote.status_code == status.HTTP_201_CREATED
    ), f"Failed to submit vote for poll {poll_data['id']}"

    # 3. Trying to vote on a non-existing poll.
    vote_data_non_existing_poll = {
        "vote_option_id": poll_data["option_ids"][0],
        "poll_id": 10000,
    }
    register_vote = client.post("/api/vote/submit", json=vote_data_non_existing_poll)
    assert (
        register_vote.status_code == status.HTTP_403_FORBIDDEN
    ), "Cannot vote on non-existing poll"

    # 4. Trying to vote on a non-existing vote-option.
    vote_data_non_existing_vote_option = {
        "vote_option_id": 1000,
        "poll_id": poll_data["id"],
    }
    register_vote = client.post(
        "/api/vote/submit", json=vote_data_non_existing_vote_option
    )
    assert (
        register_vote.status_code == status.HTTP_404_NOT_FOUND
    ), "Cannot vote on non-existing vote_option"
