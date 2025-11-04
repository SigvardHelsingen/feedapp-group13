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

    TEST_DB_NAME: str

    VALKEY_CONN_STR: str

    # Auth - JWT - Cookie /defaults
    SECRET_KEY: str = "PLEASE-CHANGE-ME-TO-A-LONG-RANDOM-SECRET"
    JWT_ALGORITHM: str = "HS256"
    SESSION_TTL_SECONDS: int = 3600
    COOKIE_SECURE: bool = False #SET TRUE
    COOKIE_SAMESITE: str = "strict"
    COOKIE_DOMAIN: str | None = None
    SLIDING_RENEW_THRESHOLD_SEC: int = 900

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
