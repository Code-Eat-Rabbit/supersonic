"""SuperSonic SDK 异常体系。

所有异常都继承 SupersonicError，便于用户 `except SupersonicError` 兜底。
资源特化异常（MetricNotFoundError 等）便于精准 catch。
"""
from typing import Any

from pydantic import BaseModel


class SupersonicError(Exception):
    """所有 SDK 异常的根。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        return self.message


class FieldError(BaseModel):
    """字段级校验错误详情。"""

    field: str
    message: str
    rejected_value: Any | None = None


class ValidationError(SupersonicError):
    """400 错误，携带字段级错误详情。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        response_body: dict | None = None,
        field_errors: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.field_errors = field_errors or []


class AuthenticationError(SupersonicError):
    """401 错误，token 失效或缺失。"""

    def __init__(self, message: str = "Authentication failed", *,
                 status_code: int = 401, response_body: dict | None = None) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)


class RateLimitError(SupersonicError):
    """429 错误，携带服务器建议的 retry_after（秒）。"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        status_code: int = 429,
        response_body: dict | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.retry_after = retry_after


class ServerError(SupersonicError):
    """5xx 服务器错误。"""


class ConnectionError(SupersonicError):
    """网络层错误（httpx.TransportError 的包装）。"""


class AsyncNotEnabledError(SupersonicError):
    """调用 .alist()/.acreate() 等异步方法但未启用 enable_async=True。"""

    def __init__(self) -> None:
        super().__init__(
            "Async methods require enable_async=True. "
            "Recreate SupersonicClient with enable_async=True to use async API."
        )


class ResourceNotFoundError(SupersonicError):
    """404 资源不存在异常的基类。"""

    def __init__(self, resource_type: str, resource_id: int | str) -> None:
        super().__init__(
            f"{resource_type} {resource_id} not found",
            status_code=404,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class DomainNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("domain", resource_id)


class ModelNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("model", resource_id)


class DimensionNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("dimension", resource_id)


class MetricNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("metric", resource_id)


class DatasetNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("dataset", resource_id)


class DatabaseNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("database", resource_id)
