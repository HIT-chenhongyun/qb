from config.celery import CeleryConfig
from config.sql import DatabaseConfig
from config.common import CommonConfig

class PBConfig(CeleryConfig,DatabaseConfig,CommonConfig):
    model_config = SettingsConfigDict(
        # read from dotenv format config file
        env_file=".env",
        env_file_encoding="utf-8",
        # ignore extra attributes
        extra="ignore",
    )

pd_config = PBConfig()

