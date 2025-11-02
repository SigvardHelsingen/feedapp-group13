import asyncio
import random
import time
from typing import Any

import httpx
import uvloop

from app.auth.cookie import _COOKIE_NAME


async def send_request(
    client: httpx.AsyncClient, url: str, body: dict[str, Any], cookies: dict[str, str]
):
    start = time.perf_counter()
    response = await client.post(url, json=body, cookies=cookies)
    latency = time.perf_counter() - start
    return latency, response.status_code, response.cookies.get(_COOKIE_NAME)


async def load_test_vote_counting():
    rec_count = 500

    create_user_url = "http://localhost:8000/api/user/register"
    create_user_requests = [
        {
            "username": f"user-{i}",
            "email": f"user-{i}@example.com",
            "password": "hunter2",
        }
        for i in range(rec_count)
    ]

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=10), timeout=60
    ) as client:
        tasks = [
            send_request(client, create_user_url, r, {}) for r in create_user_requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    _latencies = [r[0] for r in results if isinstance(r, tuple)]
    sessions = [r[2] for r in results if isinstance(r, tuple) and r[2] is not None]
    print(f"Valid sessions: {len(sessions)}")

    create_poll_url = "http://localhost:8000/api/poll/create"
    create_poll_requests = [
        {
            "question": "What's up with cats??",
            "options": [
                "they're fun",
                "i don't like them",
                "i'm ambivalent",
            ],
            "expires_at": None,
        },
        {
            "question": "What is your favorite artist?",
            "options": [
                "Kendrick Lamar",
                "Taylor Swift",
                "Vivaldi",
                "Bring me to the Horizon",
                "Eminem",
            ],
            "expires_at": None,
        },
    ]

    limits = httpx.Limits(max_connections=100)
    async with httpx.AsyncClient(limits=limits, timeout=60) as client:
        tasks = [
            send_request(client, create_poll_url, r, {_COOKIE_NAME: sessions[0]})
            for r in create_poll_requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    statuses = [r[1] for r in results if isinstance(r, tuple)]
    print(f"Poll creation status: {statuses}")

    async with httpx.AsyncClient(limits=limits) as client:
        res = await client.get("http://localhost:8000/api/poll/all")
        polls = res.json()

    polls = [
        {
            "poll_id": x["id"],
            "option_ids": x["option_ids"],
            "counts": {oid: 0 for oid in x["option_ids"]},
        }
        for x in polls
    ]

    vote_requests = []
    for poll in polls:
        s_opts: dict[str, int] = {}
        for _ in range(100):
            vote_requests.append([])
            for s in sessions:
                option: int = random.choice(poll["option_ids"])
                old_option = s_opts.get(s, None)

                s_opts[s] = option
                poll["counts"][option] += 1
                if old_option is not None:
                    poll["counts"][old_option] -= 1

                vote_requests[-1].append(
                    (
                        {
                            "vote_option_id": option,
                            "poll_id": poll["poll_id"],
                        },
                        s,
                    )
                )

    print(
        f"submitting: {len(vote_requests)} * {len(vote_requests[0])} = {len(vote_requests) * len(vote_requests[0])} votes"
    )

    vote_endpoint = "http://localhost:8000/api/vote/submit"
    async with httpx.AsyncClient(limits=limits, timeout=60) as client:
        for reqs in vote_requests:
            tasks = [
                send_request(client, vote_endpoint, r, {_COOKIE_NAME: s})
                for r, s in reqs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        statuses = [r[1] for r in results if isinstance(r, tuple)]
        for x in statuses:
            if x != 201:
                print(x)
                return

    print(polls)


if __name__ == "__main__":
    uvloop.run(load_test_vote_counting())
