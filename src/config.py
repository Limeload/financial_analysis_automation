from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Infrastructure
    database_url: str = "postgresql+asyncpg://firehose:firehose@localhost:5432/firehose"
    redis_url: str = "redis://localhost:6379"
    kafka_bootstrap_servers: str = "localhost:9094"

    # News feeds
    thenewsapi_key: str = ""

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"

    # API auth
    api_keys: str = "dev-secret-key-1"

    # Kafka topics
    kafka_topic_raw: str = "raw-articles"
    kafka_consumer_group: str = "firehose-processor"

    # Ingestion
    ingestion_interval_seconds: int = 60

    # Logging
    log_level: str = "INFO"

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


settings = Settings()
