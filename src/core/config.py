from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required — no defaults, must be set via env / .env file
    SECRET_KEY: str
    DATABASE_URL: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Connection pool sizing
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # Query / connection timeouts (seconds)
    DB_COMMAND_TIMEOUT: int = 60
    DB_CONNECT_TIMEOUT: int = 10

    # Logging
    DB_ECHO: bool = False

    # SMTP (optional — email sending is skipped when not configured)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters.")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("DATABASE_URL must not be empty")
        return v

    @field_validator("DB_POOL_SIZE")
    @classmethod
    def pool_size_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("DB_POOL_SIZE must be >= 1")
        return v

    @field_validator("DB_MAX_OVERFLOW")
    @classmethod
    def max_overflow_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("DB_MAX_OVERFLOW must be >= 0")
        return v


settings = Settings()
