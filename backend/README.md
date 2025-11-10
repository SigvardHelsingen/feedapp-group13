# FeedApp Backend

This is the backend service for the FeedApp project.

It is built with the following components:
- **FastAPI**: Web framework
- **SQLAlchemy**: Database toolkit for managing connections and transactions with a PostgreSQL database via the `asyncpg` driver. Not used as an ORM in this project.
- **sqlc**: Generates typesafe models and queries from raw SQL code
- **dbmate**: Database migrations manager based writing raw SQL code
- **uv**: Dependency manager

## Project Structure

```
backend/
├── app/                       # The main FastAPI application package
│   ├── auth/                  # Authentication logic (cookie handling, user dependencies)
│   ├── db/                    # Database connection management and sqlc-generated code
│   │   ├── sqlc/              # sqlc auto-generated models and query functions. DO NOT EDIT.
│   │   ├── valkey.py          # Valkey connection pool setup and dependency injection logic
│   │   └── db.py              # SQLAlchemy engine setup and dependency injection logic
│   ├── routes/                # API route handlers, split by resource
│   ├── utils/                 # Utility models and functions
│   │   ├── user_info.py       # User model redacting sensitive information, redaction function
│   │   └── vote_counter.py    # Valkey-based concurrency-safe vote counter
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
TEST_DB_NAME=feedapp_test
VALKEY_CONN_STR=valkey://localhost/feedapp

# --- Auth / JWT / Cookie ---
# Use a long, random value here (see command below)
SECRET_KEY=change-me
JWT_ALGORITHM=HS256
SESSION_TTL_SECONDS=3600

# Cookie flags (enable Secure in production!)
COOKIE_SECURE=false
COOKIE_SAMESITE=strict
```

### 3. Database Setup

`dbmate` is our migration manager, and can create the database for you.
You need to provide a connection string conforming to the options you set in `.env`.

```sh
export DATABASE_URL=postgresql://your_postgres_user:your_postgres_password@localhost:5432/feedapp?sslmode=disable
dbmate --no-dump-schema up
```

### 4. Running the Application

Start the development server using Uvicorn.

```sh
uv run uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

## Core Concepts

### Dependency Injection

This project utilizes FastAPI's dependency injection system to provide resources to route handlers.
To inject a dependency, make the route accept an argument of the dependency type.

- **DBConnection**: defined in `app/db/db.py`, asynchronous transactional SQLAlchemy connection that can be used with the sqlc queries
- **ValkeyConnection**: defined in `app/db/valkey.py`, asynchronous Valkey connection from a pool. Entire database is flushed on every application startup.
- **CurrentUserOptional, CurrentUserRequired**: defined in `app/auth/cookie.py`, gets the current user from JWT cookie, either optionally or mandatorily

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
