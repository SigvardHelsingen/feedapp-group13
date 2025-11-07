from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.db.kafka import create_kafka_producer
from app.db.valkey import create_valkey_pool
from app.sse.manager import SSEManager

from .config import get_settings
from .db.db import create_db_engine
from .routes import poll, user, vote


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager to manage the SQLAlchemy engine lifecycle.
    The engine is created on startup and disposed of gracefully on shutdown.
    """
    settings = get_settings()

    print("Creating SQLAlchemy engine...")
    engine, db_semaphore = create_db_engine(settings)
    app.state.db_engine = engine
    app.state.db_semaphore = db_semaphore

    print("Creating Valkey connection pool")
    pool = await create_valkey_pool(settings)
    app.state.valkey_pool = pool

    print("Creating Kafka Producer")
    producer = await create_kafka_producer(settings)
    app.state.kafka_producer = producer

    print("Creating SSE Manager")
    sse_manager = SSEManager(
        settings.VALKEY_CONN_STR,
        max_connections_per_user=settings.SSE_MAX_CONNECTIONS_PER_USER,
        max_connections_total=settings.SSE_MAX_CONNECTIONS_TOTAL,
    )
    app.state.sse_manager = sse_manager

    yield

    print("Shutting down SSE Manager")
    await sse_manager.shutdown()

    print("Disposing Valkey connection pool")
    await pool.aclose()

    print("Disposing SQLAlchemy engine...")
    await engine.dispose()
    print("SQLAlchemy engine disposed.")

    print("Closing Kafka Producer")
    await producer.stop()


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
app.include_router(poll.router)
app.include_router(vote.router)

# Make the OpenAPI operation ids match the route function name
# Ensures nicer names on the generated client
for route in app.routes:
    if isinstance(route, APIRoute):
        route.operation_id = route.name
