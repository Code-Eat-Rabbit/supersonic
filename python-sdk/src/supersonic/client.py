"""SupersonicClient - SDK main entry (facade).

Only assembles; does not make business requests directly.
Business calls go through .query / .metrics / .domains etc.
"""
from __future__ import annotations

from typing import Any

from supersonic.api.databases import DatabasesAPI
from supersonic.api.datasets import DatasetsAPI
from supersonic.api.dimensions import DimensionsAPI
from supersonic.api.domains import DomainsAPI
from supersonic.api.metrics import MetricsAPI
from supersonic.api.models import ModelsAPI
from supersonic.api.query import QueryAPI
from supersonic.auth import TokenAuth
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.logging import configure_logging
from supersonic.config import RetryConfig, SupersonicConfig


class SupersonicClient:
    """SuperSonic Python SDK main entry.

    Thread safety:
        SupersonicClient is NOT thread-safe. The underlying httpx.Client
        uses a shared connection pool that does not support concurrent
        requests across threads.

        For multi-threaded usage:
        - Create a separate SupersonicClient per thread (recommended)
        - Or use enable_async=True with asyncio instead of threads
        - Or wrap client access with an external lock (not recommended,
          kills concurrency)

    Async safety:
        AsyncHTTPClient methods can be called concurrently from asyncio
        tasks (httpx.AsyncClient supports concurrent requests within a
        single event loop).
    """

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        *,
        app_key: str = "supersonic",
        timeout: float = 30.0,
        enable_async: bool = False,
        retry: RetryConfig | None = None,
        log_level: str | None = None,
    ) -> None:
        if not host or not token:
            raise ValueError(
                "host and token are required. "
                "Use from_env() to read from environment variables."
            )
        self._config = SupersonicConfig(
            host=host,
            token=token,
            app_key=app_key,
            timeout=timeout,
            enable_async=enable_async,
            retry=retry or RetryConfig(),
            log_level=log_level or "WARNING",
        )
        configure_logging(self._config.log_level)

        auth = TokenAuth(token=token, app_key=app_key)
        self._http = HTTPClient(
            base_url=host, auth=auth, timeout=timeout, retry=retry,
        )
        self._async_http: AsyncHTTPClient | None = None
        if enable_async:
            self._async_http = AsyncHTTPClient(
                base_url=host, auth=auth, timeout=timeout, retry=retry,
            )

        # Lazy namespace cache
        self._query: QueryAPI | None = None
        self._domains: DomainsAPI | None = None
        self._models: ModelsAPI | None = None
        self._dimensions: DimensionsAPI | None = None
        self._metrics: MetricsAPI | None = None
        self._databases: DatabasesAPI | None = None
        self._datasets: DatasetsAPI | None = None

    # ===== Namespace properties (lazy) =====

    @property
    def query(self) -> QueryAPI:
        if self._query is None:
            self._query = QueryAPI(self._http, self._async_http)
        return self._query

    @property
    def domains(self) -> DomainsAPI:
        if self._domains is None:
            self._domains = DomainsAPI(self._http, self._async_http)
        return self._domains

    @property
    def models(self) -> ModelsAPI:
        if self._models is None:
            self._models = ModelsAPI(self._http, self._async_http)
        return self._models

    @property
    def dimensions(self) -> DimensionsAPI:
        if self._dimensions is None:
            self._dimensions = DimensionsAPI(self._http, self._async_http)
        return self._dimensions

    @property
    def metrics(self) -> MetricsAPI:
        if self._metrics is None:
            self._metrics = MetricsAPI(self._http, self._async_http)
        return self._metrics

    @property
    def databases(self) -> DatabasesAPI:
        if self._databases is None:
            self._databases = DatabasesAPI(self._http, self._async_http)
        return self._databases

    @property
    def datasets(self) -> DatasetsAPI:
        if self._datasets is None:
            self._datasets = DatasetsAPI(self._http, self._async_http)
        return self._datasets

    # ===== Constructors =====

    @classmethod
    def from_env(cls, **overrides: Any) -> SupersonicClient:
        config = SupersonicConfig.from_env(**overrides)
        return cls.from_config(config)

    @classmethod
    def from_config(cls, config: SupersonicConfig) -> SupersonicClient:
        return cls(
            host=config.host,
            token=config.token,
            app_key=config.app_key,
            timeout=config.timeout,
            enable_async=config.enable_async,
            retry=config.retry,
            log_level=config.log_level,
        )

    # ===== Resource management =====

    def close(self) -> None:
        self._http.close()

    async def aclose(self) -> None:
        self._http.close()
        if self._async_http is not None:
            await self._async_http.aclose()

    def __enter__(self) -> SupersonicClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
