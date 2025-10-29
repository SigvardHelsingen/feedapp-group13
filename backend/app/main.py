from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .db.db import create_db_engine
from .routes import user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to manage the SQLAlchemy engine lifecycle.
    The engine is created on startup and disposed of gracefully on shutdown.
    """
    settings = get_settings()

    print("Creating SQLAlchemy engine...")
    engine = create_db_engine(settings)
    app.state.db_engine = engine

    yield

    print("Disposing SQLAlchemy engine...")
    await engine.dispose()
    print("SQLAlchemy engine disposed.")


app = FastAPI(
    lifespan=lifespan,
    title="FeedApp API",
    description="API for the FeedApp project",
    version="0.1.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(user.router)
