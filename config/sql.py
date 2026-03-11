import os
from typing import Any
from urllib.parse import quote_plus, parse_qsl

from pydantic import Field, computed_field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    DB_HOST: str = Field(
        description="Hostname or IP address of the database server.",
        default="localhost",  # 数据库服务器地址
    )

    DB_PORT: PositiveInt = Field(
        description="Port number for database connection.",
        default=5432,  # PostgreSQL默认端口
    )

    DB_USERNAME: str = Field(
        description="Username for database authentication.",
        default="postgres",  # 默认管理员账号
    )

    DB_PASSWORD: str = Field(
        description="Password for database authentication.",
        default="",  # 数据库密码
    )

    DB_DATABASE: str = Field(
        description="Name of the database to connect to.",
        default="dify",  # 默认数据库名
    )

    DB_CHARSET: str = Field(
        description="Character set for database connection.",
        default="",  # 字符集设置（如utf8）
    )

    DB_EXTRAS: str = Field(
        description="Additional database connection parameters. Example: 'keepalives_idle=60&keepalives=1'",
        default="",  # 额外连接参数（URL编码格式）
    )

    SQLALCHEMY_DATABASE_URI_SCHEME: str = Field(
        description="Database URI scheme for SQLAlchemy connection.",
        default="postgresql",
    )

    @computed_field  # 标识这是需要动态计算的字段
    def SQLALCHEMY_DATABASE_URI(self) -> str:  # 动态URI生成
        db_extras = (  # 当字符集存在时，将字符集参数追加到额外参数末尾
            f"{self.DB_EXTRAS}&client_encoding={self.DB_CHARSET}" if self.DB_CHARSET else self.DB_EXTRAS
        ).strip("&")  # 去除可能出现在字符串首尾的&符号（例如当DB_EXTRAS为空时）
        db_extras = f"?{db_extras}" if db_extras else ""  # 当存在参数时添加问号前缀  # 参数存在性判断  # 无参数时保持空字符串
        return (  # 协议部分（如 postgresql:// 或 mysql://）
            f"{self.SQLALCHEMY_DATABASE_URI_SCHEME}://"
            f"{quote_plus(self.DB_USERNAME)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"  # 用户名密码部分（进行URL编码）  # 服务器地址部分
            f"{db_extras}"  # 查询参数部分
        )

    # 连接池配置
    SQLALCHEMY_POOL_SIZE: NonNegativeInt = Field(
        description="Maximum number of database connections in the pool.",
        default=30,  # 最大连接数
    )

    SQLALCHEMY_MAX_OVERFLOW: NonNegativeInt = Field(
        description="Maximum number of connections that can be created beyond the pool_size.",
        default=10,  # 允许超出pool_size的连接数
    )

    SQLALCHEMY_POOL_RECYCLE: NonNegativeInt = Field(
        description="Number of seconds after which a connection is automatically recycled.",
        default=3600,  # 连接1小时回收
    )

    SQLALCHEMY_POOL_PRE_PING: bool = Field(
        description="If True, enables connection pool pre-ping feature to check connections.",
        default=False,  # 关闭连接健康检查
    )

    SQLALCHEMY_ECHO: bool | str = Field(
        description="If True, SQLAlchemy will log all SQL statements.",
        default=False,
    )

    RETRIEVAL_SERVICE_EXECUTORS: NonNegativeInt = Field(
        description="Number of processes for the retrieval service, default to CPU cores.",
        default=os.cpu_count() or 1,  # 自动检测CPU核心数
    )

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict[str, Any]:
        # Parse DB_EXTRAS for 'options'
        db_extras_dict = dict(parse_qsl(self.DB_EXTRAS))  # 将URL参数解析为字典
        options = db_extras_dict.get("options", "")
        # Always include timezone
        timezone_opt = "-c timezone=UTC"  # 强制所有连接使用UTC时区
        if options:
            # Merge user options and timezone
            merged_options = f"{options} {timezone_opt}"
        else:
            merged_options = timezone_opt

        connect_args = {"options": merged_options}

        return {
            "pool_size": self.SQLALCHEMY_POOL_SIZE,
            "max_overflow": self.SQLALCHEMY_MAX_OVERFLOW,
            "pool_recycle": self.SQLALCHEMY_POOL_RECYCLE,
            "pool_pre_ping": self.SQLALCHEMY_POOL_PRE_PING,
            "connect_args": connect_args,
        }