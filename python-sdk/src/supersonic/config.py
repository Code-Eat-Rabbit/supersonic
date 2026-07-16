"""SDK 配置：RetryConfig + SupersonicConfig。

SupersonicConfig.from_env() 是推荐入口，环境变量见规格 § 环境变量表。
"""
import os
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetryConfig:
    """重试与退避策略。"""

    max_retries: int = 3
    retry_delay: float = 1.0
    max_backoff: float = 30.0
    backoff_jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )
    respect_retry_after: bool = True


def compute_backoff(
    attempt: int,
    config: RetryConfig,
    retry_after: float | None = None,
) -> float:
    """指数退避 + 可选 jitter + Retry-After 优先。

    attempt 从 0 开始（首次失败）。
    """
    if config.respect_retry_after and retry_after is not None:
        return min(retry_after, config.max_backoff)
    delay: float = config.retry_delay * (2 ** attempt)
    if config.backoff_jitter:
        delay += random.uniform(0, 1.0)
    return min(delay, config.max_backoff)


def _parse_retry_after(resp: Any) -> float | None:
    """从响应 Retry-After header 解析秒数。支持 delta-seconds 格式。"""
    val = resp.headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None  # HTTP-date 格式暂不支持


@dataclass
class SupersonicConfig:
    """SDK 主配置。from_env() 是推荐入口。"""

    host: str
    token: str
    app_key: str = "supersonic"
    timeout: float = 30.0
    enable_async: bool = False
    retry: RetryConfig = field(default_factory=RetryConfig)
    log_level: str = "WARNING"

    @classmethod
    def from_env(cls, **overrides: Any) -> "SupersonicConfig":
        """从环境变量构造配置。

        必填：SUPERSONIC_HOST, SUPERSONIC_TOKEN
        可选：SUPERSONIC_APP_KEY, SUPERSONIC_TIMEOUT, SUPERSONIC_MAX_RETRIES,
              SUPERSONIC_ENABLE_ASYNC, SUPERSONIC_LOG_LEVEL
        overrides 显式覆盖环境变量值。
        """
        host = overrides.pop("host", None) or os.environ.get("SUPERSONIC_HOST")
        token = overrides.pop("token", None) or os.environ.get("SUPERSONIC_TOKEN")

        missing: list[str] = []
        if not host:
            missing.append("SUPERSONIC_HOST")
        if not token:
            missing.append("SUPERSONIC_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Set them or pass host=.../token=... explicitly."
            )

        host = str(host)
        token = str(token)

        # 可选变量
        app_key = overrides.pop("app_key", None) or os.environ.get(
            "SUPERSONIC_APP_KEY", "supersonic"
        )
        timeout = overrides.pop(
            "timeout", None
        ) or float(os.environ.get("SUPERSONIC_TIMEOUT", "30.0"))
        enable_async = overrides.pop("enable_async", None)
        if enable_async is None:
            enable_async = (
                os.environ.get("SUPERSONIC_ENABLE_ASYNC", "").lower() == "true"
            )
        log_level = overrides.pop("log_level", None) or os.environ.get(
            "SUPERSONIC_LOG_LEVEL", "WARNING"
        )

        retry_overrides: dict[str, Any] = {}
        max_retries_env = os.environ.get("SUPERSONIC_MAX_RETRIES")
        if max_retries_env:
            retry_overrides["max_retries"] = int(max_retries_env)
        retry = overrides.pop("retry", None) or RetryConfig(**retry_overrides)

        return cls(
            host=host,
            token=token,
            app_key=app_key,
            timeout=timeout,
            enable_async=enable_async,
            retry=retry,
            log_level=log_level,
            **overrides,
        )
