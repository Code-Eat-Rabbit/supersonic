"""HTTP 客户端（同步 + 异步）。

HTTPClient 与 AsyncHTTPClient 共享：
- _handle_response（异常映射）
- _compute_backoff（来自 config）
- _parse_retry_after（本模块私有，基于 httpx.Response）

差异：
- HTTPClient: httpx.Client，同步
- AsyncHTTPClient: httpx.AsyncClient，懒加载（避免事件循环绑定）
"""
import asyncio
import time
from typing import Any, cast

import httpx

from supersonic.auth import TokenAuth
from supersonic.common.logging import get_logger, redact_headers
from supersonic.config import RetryConfig, compute_backoff
from supersonic.exceptions import (
    AuthenticationError,
    DatabaseNotFoundError,
    DatasetNotFoundError,
    DimensionNotFoundError,
    DomainNotFoundError,
    FieldError,
    MetricNotFoundError,
    ModelNotFoundError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from supersonic.exceptions import (
    ConnectionError as SupersonicConnectionError,
)

_NOT_FOUND_MAP: dict[str, type[ResourceNotFoundError]] = {
    "domain": DomainNotFoundError,
    "model": ModelNotFoundError,
    "dimension": DimensionNotFoundError,
    "metric": MetricNotFoundError,
    "dataset": DatasetNotFoundError,
    "database": DatabaseNotFoundError,
}

log = get_logger()


def _parse_retry_after(resp: httpx.Response) -> float | None:
    """从 Retry-After header 解析秒数。仅支持 delta-seconds 格式。"""
    val = resp.headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_field_errors(body: dict[str, Any]) -> list[FieldError]:
    """从 SuperSonic 400 响应体解析字段级错误。

    支持三种格式：
    - {"errors": [{"field": "name", "message": "..."}]}  列表格式
    - {"fieldErrors": {"name": "..."}}                   字典格式
    - {"message": "..."}                                  无结构化字段错误
    """
    errors = body.get("errors") or body.get("fieldErrors") or []
    if isinstance(errors, dict):
        return [FieldError(field=k, message=str(v)) for k, v in errors.items()]
    if isinstance(errors, list):
        result: list[FieldError] = []
        for e in errors:
            if isinstance(e, dict) and "field" in e and "message" in e:
                result.append(FieldError(**e))
        return result
    return []


def _handle_response(
    resp: httpx.Response,
    *,
    path: str,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
) -> dict[str, Any]:
    """统一处理响应：2xx 返回 json，其他状态码抛出对应异常。

    sync/async 共用 -- httpx.Response 接口一致，无需 await。
    """
    if 200 <= resp.status_code < 300:
        if not resp.content:
            return {}
        return cast(dict[str, Any], resp.json())

    # 解析响应体（失败也给用户原始文本）
    try:
        body: dict[str, Any] = cast(dict[str, Any], resp.json())
    except Exception:
        body = {"raw": resp.text}

    log.debug(
        "HTTP error status=%s path=%s body=%s",
        resp.status_code, path, body,
    )

    if resp.status_code == 401:
        raise AuthenticationError(
            "Authentication failed (token invalid or expired)",
            status_code=401,
            response_body=body,
        )
    if resp.status_code == 404:
        # 统一签名，避免 resource_id 可能是空字符串的边界问题
        rid: int | str = resource_id if resource_id is not None else 0
        if resource_type and resource_type in _NOT_FOUND_MAP:
            exc_cls = _NOT_FOUND_MAP[resource_type]
            # Subclasses have __init__(resource_id), but mypy sees base
            # ResourceNotFoundError.__init__(resource_type, resource_id).
            raise exc_cls(rid)  # type: ignore[call-arg, arg-type]
        # 未知 resource_type：抛通用 ResourceNotFoundError
        raise ResourceNotFoundError(resource_type or "resource", rid)
    if resp.status_code == 429:
        raise RateLimitError(
            "Rate limit exceeded",
            status_code=429,
            response_body=body,
            retry_after=_parse_retry_after(resp),
        )
    if 400 <= resp.status_code < 500:
        field_errors = _parse_field_errors(body)
        message = body.get("message", resp.reason_phrase)
        raise ValidationError(
            f"Request validation failed: {message}",
            status_code=resp.status_code,
            response_body=body,
            field_errors=field_errors,
        )
    raise ServerError(
        f"Server error: {body.get('message', resp.reason_phrase)}",
        status_code=resp.status_code,
        response_body=body,
    )


class HTTPClient:
    """同步 HTTP 客户端，封装重试、退避、异常映射。

    Thread safety: NOT thread-safe. 每个线程应创建独立实例。
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        *,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self._auth = auth
        self._retry = retry or RetryConfig()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> dict[str, Any]:
        """发送 HTTP 请求，处理重试，映射异常。

        Returns: 解析后的 JSON dict（2xx）。
        Raises: SupersonicError 的子类（非 2xx）。
        """
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            headers = self._auth.headers()
            log.debug(
                "HTTP %s %s headers=%s payload=%s",
                method, url, redact_headers(headers), json,
            )

            try:
                resp = self._client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    time.sleep(compute_backoff(attempt, self._retry))
                    continue
                raise SupersonicConnectionError(f"Transport error: {e}") from e

            if (
                self._retry.max_retries > 0
                and resp.status_code in self._retry.retryable_status_codes
            ):
                if attempt < self._retry.max_retries:
                    retry_after = (
                        _parse_retry_after(resp) if resp.status_code == 429 else None
                    )
                    time.sleep(compute_backoff(attempt, self._retry, retry_after))
                    continue
                # Last attempt still retryable -> exhausted retries
                try:
                    body: dict[str, Any] = cast(dict[str, Any], resp.json())
                except Exception:
                    body = {"raw": resp.text}
                raise ServerError(
                    f"Max retries exceeded for {method} {url}: "
                    f"{body.get('message', resp.reason_phrase)}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            return _handle_response(
                resp,
                path=path,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        raise ServerError(
            f"Max retries exceeded for {method} {url}"
        ) from last_exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncHTTPClient:
    """异步 HTTP 客户端。

    与 HTTPClient 共享 _handle_response / compute_backoff / _parse_retry_after。
    差异：
    - 用 httpx.AsyncClient（懒加载，避免 __init__ 绑定事件循环）
    - time.sleep → asyncio.sleep
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        *,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        # 不在 __init__ 创建 AsyncClient，避免事件循环绑定问题
        self._base_url = base_url
        self._auth = auth
        self._timeout = timeout
        self._retry = retry or RetryConfig()
        self._async_client: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        """懒加载：首次调用才创建 AsyncClient。"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            )
        return self._async_client

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> dict[str, Any]:
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            headers = self._auth.headers()
            log.debug(
                "HTTP async %s %s headers=%s payload=%s",
                method, url, redact_headers(headers), json,
            )

            try:
                resp = await self._client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    await asyncio.sleep(compute_backoff(attempt, self._retry))
                    continue
                raise SupersonicConnectionError(f"Transport error: {e}") from e

            # 评审修复（同 HTTPClient）：最后一次重试仍为可重试状态码时，
            # 必须抛 "Max retries exceeded"，而不是走 _handle_response
            if (
                self._retry.max_retries > 0
                and resp.status_code in self._retry.retryable_status_codes
            ):
                if attempt < self._retry.max_retries:
                    retry_after = (
                        _parse_retry_after(resp) if resp.status_code == 429 else None
                    )
                    await asyncio.sleep(compute_backoff(attempt, self._retry, retry_after))
                    continue
                # 最后一次 attempt 仍是可重试状态码 -> exhausted
                try:
                    body: dict[str, Any] = cast(dict[str, Any], resp.json())
                except Exception:
                    body = {"raw": resp.text}
                raise ServerError(
                    f"Max retries exceeded for {method} {url}: "
                    f"{body.get('message', resp.reason_phrase)}",
                    status_code=resp.status_code,
                    response_body=body,
                )

            return _handle_response(
                resp,
                path=path,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        raise ServerError(f"Max retries exceeded for {method} {url}") from last_exc

    async def aclose(self) -> None:
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None
