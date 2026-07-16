"""HTTPClient unit tests (pytest-httpx mock).

Spec: HTTPClient (common/http.py) + error mapping
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.auth import TokenAuth
from supersonic.common.http import HTTPClient, _parse_field_errors
from supersonic.config import RetryConfig
from supersonic.exceptions import (
    AuthenticationError,
    MetricNotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)


@pytest.fixture
def auth():
    return TokenAuth(token="jwt", app_key="test-app")


@pytest.fixture
def retry_config():
    """测试用：no jitter（可预测），no retry（直接失败）便于断言。"""
    return RetryConfig(max_retries=0, backoff_jitter=False)


@pytest.fixture
def http(auth, retry_config):
    client = HTTPClient(
        base_url="http://test",
        auth=auth,
        retry=retry_config,
    )
    yield client
    client.close()


class TestRequestSuccess:
    def test_get_returns_json(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/foo",
            method="GET",
            json={"ok": True},
        )
        result = http.request("GET", "/api/foo")
        assert result == {"ok": True}

    def test_post_with_json_body(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/bar",
            method="POST",
            json={"id": 1},
        )
        result = http.request("POST", "/api/bar", json={"name": "x"})
        assert result == {"id": 1}

    def test_path_params_substitution(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/metric/getMetric/42",
            method="GET",
            json={"id": 42},
        )
        result = http.request(
            "GET", "/api/metric/getMetric/{id}", path_params={"id": 42}
        )
        assert result == {"id": 42}

    def test_empty_body_returns_empty_dict(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/noContent",
            method="DELETE",
            status_code=204,
        )
        result = http.request("DELETE", "/api/noContent")
        assert result == {}


class TestErrorMapping:
    def test_401_raises_authentication_error(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=401,
            json={"message": "invalid token"},
        )
        with pytest.raises(AuthenticationError) as exc:
            http.request("GET", "/api/foo")
        assert exc.value.status_code == 401

    def test_404_with_resource_type_raises_specific_exception(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/metric/getMetric/99", status_code=404
        )
        with pytest.raises(MetricNotFoundError) as exc:
            http.request(
                "GET",
                "/api/metric/getMetric/99",
                resource_type="metric",
                resource_id=99,
            )
        assert exc.value.resource_id == 99

    def test_404_without_resource_type_raises_generic(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        from supersonic.exceptions import ResourceNotFoundError

        httpx_mock.add_response(url="http://test/api/foo", status_code=404)
        with pytest.raises(ResourceNotFoundError):
            http.request("GET", "/api/foo")

    def test_429_raises_rate_limit_with_retry_after(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=429,
            headers={"Retry-After": "60"},
        )
        with pytest.raises(RateLimitError) as exc:
            http.request("GET", "/api/foo")
        assert exc.value.retry_after == 60.0

    def test_400_raises_validation_error_with_field_errors(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=400,
            json={
                "errors": [
                    {"field": "name", "message": "不能为空"},
                    {"field": "type", "message": "无效值", "rejected_value": "X"},
                ]
            },
        )
        with pytest.raises(ValidationError) as exc:
            http.request("POST", "/api/foo")
        assert len(exc.value.field_errors) == 2
        assert exc.value.field_errors[0].field == "name"

    def test_500_raises_server_error(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=500,
            json={"message": "internal"},
        )
        with pytest.raises(ServerError):
            http.request("GET", "/api/foo")


class TestParseFieldErrors:
    def test_list_format(self):
        body = {"errors": [{"field": "name", "message": "x"}]}
        result = _parse_field_errors(body)
        assert len(result) == 1
        assert result[0].field == "name"

    def test_dict_format(self):
        body = {"fieldErrors": {"name": "必填"}}
        result = _parse_field_errors(body)
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].message == "必填"

    def test_no_errors_returns_empty(self):
        body = {"message": "整体错误"}
        assert _parse_field_errors(body) == []

    def test_wrong_type_returns_empty(self):
        body = {"errors": "wrong string"}
        assert _parse_field_errors(body) == []


class TestRetry:
    def test_retries_on_500_then_succeeds(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        """max_retries=2，第 1 次 500，第 2 次成功。"""
        httpx_mock.add_response(
            url="http://test/api/foo", status_code=500, json={"err": 1}
        )
        httpx_mock.add_response(
            url="http://test/api/foo", status_code=200, json={"ok": True}
        )
        client = HTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=2, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            result = client.request("GET", "/api/foo")
            assert result == {"ok": True}
        finally:
            client.close()

    def test_exhausts_retries_raises_server_error(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo", status_code=500, is_reusable=True
        )
        client = HTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=1, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            with pytest.raises(ServerError, match="Max retries exceeded"):
                client.request("GET", "/api/foo")
        finally:
            client.close()
