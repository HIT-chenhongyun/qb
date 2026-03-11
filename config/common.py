from pydantic_settings import BaseSettings
from pydantic import Field


class CommonConfig(BaseSettings):
    REDIS_URL: str = Field(default="redis://localhost:6379",description="redis url")
    LLM_URL: str = Field(
        description="llm address",
        default="http://10.48.205.242:1025/v1",
    )
    LLM_API_KEY: str = Field(
        description="llm api key",
        default="aaa",
    )
    LLM_NAME: str = Field(
        description="llm name",
        default="DeepSeek-r1-32k_token",
    )
    EMBEDDING_URL: str = Field(
        description="embedding address",
        default="http://10.48.205.241:1025/embedding/v1",
    )
    EMBEDDING_API_KEY: str = Field(
        description="embedding api key",
        default="aaa",
    )
    RERANK_URL: str = Field(
        description="embedding address",
        default="http://10.48.205.241:1025/rerank/v1",
    )
    RERANK_API_KEY: str = Field(
        description="rerank api key",
        default="aaa",
    )
    SIM_RATE: float = Field(description="sim rate",default=0.5)
    RERANK_RATE: float = Field(description="rerank rate", default=0.2)
    RERANK_MIN_COUNT: int = Field(description="rerank min count", default=2)
