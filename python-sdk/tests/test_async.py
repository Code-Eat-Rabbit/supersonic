"""AsyncHTTPClient 单元测试。"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.auth import TokenAuth
from supersonic.common.http import AsyncHTTPClient
from supersonic.config import RetryConfig


@pytest.fixture
def auth():
    return TokenAuth(token="jwt")


@pytest.fixture
def async_http(auth):
    """max_retries=0，避免重试拖慢测试。"""
    client = AsyncHTTPClient(
        base_url="http://test",
        auth=auth,
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    # 在测试结束关闭（如果 _async_client 已创建）


class TestAsyncRequest:
    async def test_get_returns_json(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/api/foo", json={"ok": True})
        result = await async_http.request("GET", "/api/foo")
        assert result == {"ok": True}
        await async_http.aclose()

    async def test_post_with_json(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/api/bar", json={"id": 1})
        result = await async_http.request("POST", "/api/bar", json={"name": "x"})
        assert result == {"id": 1}
        await async_http.aclose()

    async def test_path_params(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/items/42", json={"id": 42})
        result = await async_http.request(
            "GET", "/items/{id}", path_params={"id": 42}
        )
        assert result == {"id": 42}
        await async_http.aclose()


class TestAsyncLazyInit:
    async def test_async_client_not_created_in_init(self, auth):
        """AsyncClient 应该懒加载——__init__ 阶段 _async_client 为 None。"""
        client = AsyncHTTPClient(base_url="http://test", auth=auth)
        assert client._async_client is None
        await client.aclose()

    async def test_async_client_created_on_first_request(
        self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/x", json={})
        assert async_http._async_client is None
        await async_http.request("GET", "/x")
        assert async_http._async_client is not None
        await async_http.aclose()


class TestAsyncRetry:
    async def test_retries_on_500(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/x", status_code=500, json={})
        httpx_mock.add_response(url="http://test/x", status_code=200, json={"ok": True})
        client = AsyncHTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=2, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            result = await client.request("GET", "/x")
            assert result == {"ok": True}
        finally:
            await client.aclose()
