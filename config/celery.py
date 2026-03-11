from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, PositiveFloat, computed_field


class CeleryConfig(BaseSettings):
    CELERY_BACKEND: str = Field(
        description="Backend for Celery task results. Options: 'database', 'redis'.",
        default="redis",
    )

    CELERY_BROKER_URL: Optional[str] = Field(
        description="URL of the message broker for Celery tasks.",
        default=None,
    )

    CELERY_USE_SENTINEL: Optional[bool] = Field(
        description="Whether to use Redis Sentinel for high availability.",
        default=False,
    )

    CELERY_SENTINEL_MASTER_NAME: Optional[str] = Field(
        description="Name of the Redis Sentinel master.",
        default=None,
    )

    CELERY_SENTINEL_SOCKET_TIMEOUT: Optional[PositiveFloat] = Field(
        description="Timeout for Redis Sentinel socket operations in seconds.",
        default=0.1,
    )

    @computed_field
    def CELERY_RESULT_BACKEND(self) -> str | None:
        return (
            "db+{}".format(self.SQLALCHEMY_DATABASE_URI)
            if self.CELERY_BACKEND == "database"
            else self.CELERY_BROKER_URL
        )

    @property
    def BROKER_USE_SSL(self) -> bool:
        return self.CELERY_BROKER_URL.startswith("rediss://") if self.CELERY_BROKER_URL else False
