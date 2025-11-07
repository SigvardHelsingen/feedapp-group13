# FeedApp Backend

This is the backend service for the FeedApp project.

It is built with the following components:
- **FastAPI**: Web framework
- **SQLAlchemy**: Database toolkit for managing connections and transactions with a PostgreSQL database via the `asyncpg` driver. Not used as an ORM in this project.
- **sqlc**: Generates typesafe models and queries from raw SQL code
- **dbmate**: Database migrations manager based writing raw SQL code
- **uv**: Dependency manager
- **Redpanda**: Event streaming for asynchronous vote processing (Kafka-compatible)
- **Valkey**: In-memory data store for materialized vote counts and pub/sub messaging
- **Server-Sent Events (SSE)**: Real-time updates for connected clients

## Project Structure

```
backend/
├── app/                       # The main FastAPI application package
│   ├── auth/                  # Authentication logic (cookie handling, user dependencies)
│   ├── db/                    # Database connection management and sqlc-generated code
│   │   ├── sqlc/              # sqlc auto-generated models and query functions. DO NOT EDIT.
│   │   ├── kafka.py           # Kafka producer setup and vote event models
│   │   ├── valkey.py          # Valkey connection pool setup and dependency injection logic
│   │   └── db.py              # SQLAlchemy engine setup and dependency injection logic
│   ├── routes/                # API route handlers, split by resource
│   ├── sse/                   # Server-Sent Events
│   │   └── manager.py         # SSE manager using Valkey pub/sub
│   ├── utils/                 # Utility models and functions
│   │   ├── user_info.py       # User model redacting sensitive information, redaction function
│   │   └── vote_counter.py    # Valkey-based concurrency-safe vote counter
│   ├── consume.py             # Kafka consumer process for vote processing
│   ├── main.py                # FastAPI application entrypoint and lifespan manager
│   └── config.py              # Configuration
├── db/                        # Database directory (dbmate and sqlc)
│   ├── migrations/            # dbmate migration files (and sqlc schema source of truth)
│   └── queries/               # Raw SQL queries for sqlc, split by resource
├── tests/                     # Automated tests for the application
│   ├── integration/           # End-to-end tests for API workflows
│   └── conftest.py            # Test configuration
├── pyproject.toml             # Project definition and dependencies for uv
└── sqlc.yaml                  # sqlc configuration
```

## Getting Started

### Prerequisites
- Python 3.14+
- `uv` (https://docs.astral.sh/uv/)
- A running PostgreSQL server
- A running Valkey server
- A running Redpanda server (Kafka compatible)
- `dbmate` (needs to be installed with an external package manager, e.g., `brew install dbmate`)
- `sqlc` (needs to be installed with an external package manager, e.g., `brew install sqlc`)

### 1. Installation

Use `uv` to create a virtual env and install dependencies.

```sh
uv sync
```

### 2. Environment Configuration

The application is configured using environment variables. Create a `.env` file in the `backend` directory with the following content:

```env
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=feedapp
DB_MAX_POOL_SIZE=5
TEST_DB_NAME=feedapp_test
VALKEY_CONN_STR=valkey://localhost/feedapp
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 3. Database Setup

`dbmate` is our migration manager, and can create the database for you.
You need to provide a connection string conforming to the options you set in `.env`.

```sh
export DATABASE_URL=postgresql://your_postgres_user:your_postgres_password@localhost:5432/feedapp?sslmode=disable
dbmate --no-dump-schema up
```

### 4. Running the Application

The application consists of two processes that need to be run separately:

#### FastAPI Server

Start the development server using Uvicorn.

```sh
uv run uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

#### Kafka Consumer

Start the consumer process to handle vote processing.

```sh
uv run python app/consume.py
```

The consumer listens to vote events from Kafka, processes them by updating the database and Valkey cache, and publishes updates to connected clients via Redis pub/sub.

## Core Concepts

### Dependency Injection

This project utilizes FastAPI's dependency injection system to provide resources to route handlers.
To inject a dependency, make the route accept an argument of the dependency type.

- **DBConnection**: defined in `app/db/db.py`, asynchronous transactional SQLAlchemy connection that can be used with the sqlc queries
- **ValkeyConnection**: defined in `app/db/valkey.py`, asynchronous Valkey connection from a pool. Entire database is flushed on every application startup.
- **KafkaProducer**: defined in `app/db/kafka.py`, Kafka producer for publishing vote events
- **CurrentUserOptional, CurrentUserRequired**: defined in `app/auth/cookie.py`, gets the current user from JWT cookie, either optionally or mandatorily

### Event-Driven Architecture: Vote Processing Pipeline

The application uses an event-driven architecture for vote processing to ensure scalability and real-time updates.

#### Vote Submission Flow

1. **Client submits vote**: POST to `/api/vote/submit`
2. **FastAPI validates**: Checks user permissions and poll option validity
3. **Publishes to Kafka**: Vote event sent to `vote-event` topic (keyed by poll_id)
4. **Returns immediately**: Vote processing is handled by another process

#### Vote Processing Flow

1. **Consumer reads from Kafka**: `app/consume.py` processes vote events
2. **Updates database**: Removes old vote (if exists) and inserts new vote
3. **Updates Valkey materialized counts**: Atomically increments/decrements materialized vote counts
4. **Publishes to Valkey pub/sub**: Sends poll update to topic `vote-updates:poll:{poll_id}`

#### Real-Time Updates Flow

1. **Client connects**: GET to `/api/vote/stream/{poll_id}` (Server-Sent Events)
2. **Immedeately returns most recent count**: Client doesn't need to wait for an update
3. **SSE Manager subscribes**: Makes sure it's listening to Valkey pub/sub topic for the poll
4. **Receives updates**: When votes are processed, SSE Manager broadcasts to connected clients
5. **Client updates UI**: Receives vote counts in real-time without polling

This architecture provides:
- **At-least-once delivery**: all votes are guaranteed to be processed
- **Same-order vote delivery**: votes for a poll are processed in the exact order they were received
- **Idempotency**: processing the same vote multiple times causes no change to the database
- **Low latency**: for clients (immediate response on submission)
- **Real-time updates**: with low overhead compared to WebSockets, and no client polling
- **Scalability**: Kafka partitioning and many stateless FastAPI instances

### Database Workflow: `dbmate` and `sqlc`

This project uses "SQL-first" workflow where migration files are the single source of truth.

1. **`db/migrations` defines the schema.** Changes to the database schema are defined as plain SQL files in this directory, commented with `up` and `down` for applying or reverting a migration.
2. **`sqlc` reads these migrations directly.** `sqlc` parses all of the `up` migrations to understand the newest state of the schema.
3. **`db/queries` contains the application's queries.** Write standard SQL here, organized into multiple files by domain (e.g., `users.sql`). Comments for naming the generated methods and specifying if they return one or many rows.
4. **`sqlc` generates the data access layer.** It reads the schema and queries and produces type-safe Python models and methods.

#### Updating the Schema

1.  **Create a `dbmate` Migration**: Generate a new SQL migration file.
    ```sh
    dbmate new your_migration_name
    ```
    This creates a new timestamped file in `db/migrations/`. Edit this file to add your `ALTER TABLE` statement in the `-- migrate:up` section and the rollback logic in the `-- migrate:down` section.

2.  **Apply the Migration**: Run the migration to update your local database. Make sure `DATABASE_URL` is an available environment variable.
    ```sh
    dbmate --no-dump-schema up
    ```

3.  **Regenerate `sqlc` Code**: Update the Python data access layer. `sqlc` will automatically read the new migration file. Optionally remove the existing generated code
    ```sh
    rm -r app/db/sqlc
    sqlc generate
    ```

If you only wrote new queries, it is sufficient to only run the last step here.

## Testing

We use `pytest` for testing. There are integration tests to test entire workflows, with unit tests planned for the future.
See `tests/conftest.py` for test configuration. In the future, use `pytest_mock` to mock features when writing tests.

To run the tests:

```sh
uv run pytest
```

The first time, or any time after having ran `uv sync`, you might get an error: "No module named 'app'".
To fix this, install the application as an editable component to the virtual environment:

```sh
uv pip install -e .
```

### Manual tests

We've got a load test for checking if vote counting is done correctly. Run the application in a Docker container with a fresh database, then run the script:

```sh
uv run python tests/manual/load_test_vote_counting.py
```

You might need to adjust some numbers here: max concurrent requests, number of users, timeouts, and maybe DB connection pool size in the container.

## Code Formatting with Black and isort

This project uses `black` and `isort` for code formatting and input sorting, enforced by `pre-commit`.
The frontend also uses this to format its code with `biome`.

### One-Time Setup

Before your first commit, install the Git hook:

```sh
uv run pre-commit install
```

### Workflow

When you run `git commit`, `pre-commit` will automatically format your staged files.
If files are changed, the commit will be aborted. Simply `git add` the changes and commit again.
