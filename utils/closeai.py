from typing import List, Union, TypedDict, Required

import httpx
from openai import OpenAI
from openai._base_client import make_request_options
from openai._compat import cached_property
from openai._resource import SyncAPIResource
from openai._types import Headers, Query, Body, NotGiven, NOT_GIVEN
from openai._utils import maybe_transform
from openai import BaseModel

class Usage(BaseModel):
    total_tokens: int

class Document(BaseModel):
    text: str

class Rerank(BaseModel):  # 使用 Pydantic 定义了 Rerank 接口返回的数据格式
    document: Document
    index: int
    relevance_score: float

class CreateRerankResponse(BaseModel):
    results: List[Rerank]

    model: str

    id: str

    usage: Usage

class RerankCreateParams(TypedDict, total=False):
    query: Required[Union[str]]

    model: Required[Union[str]]

    documents: Required[List[str]]


class Reranks(SyncAPIResource):
    def create(
            self,
            *,
            query: Union[str],
            model: Union[str],
            documents: List[str],
            # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
            # The extra values given here take precedence over values defined on the client or passed to this method.
            extra_headers: Headers | None = None,
            extra_query: Query | None = None,
            extra_body: Body | None = None,
            timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> CreateRerankResponse:
        params = {
            "query": query,
            "model": model,
            "documents": documents
        }

        return self._post(
            "/rerank",  # <--- 关键点：向 /rerank 路径发送 POST 请求  POST 请求是 HTTP 协议中一种重要的请求方法，用于向服务器提交数据或发送请求
            body=maybe_transform(params, RerankCreateParams),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            ),
            cast_to=CreateRerankResponse,   # 自动把 JSON 转成上面定义的对象
        )

class CloseAI(OpenAI):  # CloseAI 继承自 OpenAI：这意味着 CloseAI 拥有 OpenAI 所有的功能（Chat, Embeddings 等）
    @cached_property
    def rerank(self) -> Reranks:  # 新增 rerank 属性：当你调用 client.rerank.create(...) 时，实际上是在调用上面定义的 Reranks 类
        return Reranks(self)