from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tools_service_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/openclaw"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "documents"
    s3_endpoint: str = "http://garage:3900"
    s3_bucket: str = "openclaw"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    redis_url: str = "redis://redis:6379/0"
    speaches_url: str = "http://speaches:8080"
    speaches_model: str = "Systran/faster-whisper-large-v3"
    speaches_timeout: int = 300
    nats_url: str = "nats://nats:4222"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
