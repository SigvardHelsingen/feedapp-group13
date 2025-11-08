from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Defines the application's configuration settings,
    read from .env file using pydantic-settings
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_MAX_POOL_SIZE: int

    TEST_DB_NAME: str

    VALKEY_CONN_STR: str
    KAFKA_BOOTSTRAP_SERVERS: str

    SSE_MAX_CONNECTIONS_PER_USER: int = 5
    SSE_MAX_CONNECTIONS_TOTAL: int = 1000

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def test_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.TEST_DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a Settings instance (might be cached)
    """
    print("Loading application settings...")
    settings = Settings()
    return settings
