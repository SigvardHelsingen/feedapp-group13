import os
import subprocess
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings
from app.db.db import get_db_connection
from app.main import app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


@pytest.fixture(scope="session", autouse=True)
def manage_test_database(test_settings: Settings):
    """
    Manage the test database for the entire session.
    It uses dbmate to create a fresh one from our current migrations
    """
    env = os.environ.copy()

    # dbmate uses a different DATABASE_URL format
    sync_test_url = (
        test_settings.test_database_url.replace("+asyncpg", "") + "?sslmode=disable"
    )
    env["DATABASE_URL"] = sync_test_url

    print("Dropping test database...")
    subprocess.run(["dbmate", "drop"], env=env, check=True, capture_output=True)

    print("Creating and migrating test database...")
    subprocess.run(["dbmate", "up"], env=env, check=True, capture_output=True)

    print("Test database is ready.")
    yield
    # Teardown intentionally left out, for debugging purposes


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """
    Get a FastAPI TestClient instance, with appropriate dependency overrides
    """
    # TODO: Ideally, this should not be so complicated of an override
    engine = create_async_engine(test_settings.test_database_url)

    async def get_db_test_connection():
        async with engine.begin() as conn:
            yield conn

    app.dependency_overrides[get_db_connection] = get_db_test_connection

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
