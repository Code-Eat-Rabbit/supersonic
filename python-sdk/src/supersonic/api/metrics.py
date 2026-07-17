"""MetricsAPI - metric resource CRUD + publish/unpublish.

Phase 1 scope: sync methods only. Async metadata CRUD deferred to v0.2.
"""
from __future__ import annotations

import builtins
from typing import Any

from supersonic.api.paths import MetricPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq

_list = builtins.list


class MetricsAPI:
    """Metric resource CRUD. async_http kept for interface consistency but unused in Phase 1."""

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http  # unused in Phase 1, reserved for v0.2

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        model_id: int | None = None,
    ) -> Page[Metric]:
        """List metrics. Does not pass resource_type (review fix #4)."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if model_id is not None:
            params["modelId"] = model_id
        body = self._http.request(
            "POST", MetricPaths.LIST,
            params=params,
        )
        return Page[Metric].from_response(body, item_model=Metric)

    def get(self, metric_id: int) -> Metric:
        body = self._http.request(
            "GET", MetricPaths.GET,
            path_params={"id": metric_id},
            resource_type="metric",
            resource_id=metric_id,
        )
        return Metric.model_validate(body)

    def create(self, req: MetricCreateReq) -> Metric:
        body = self._http.request(
            "POST", MetricPaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="metric",
        )
        return Metric.model_validate(body)

    def update(self, metric_id: int, req: MetricUpdateReq) -> Metric:
        req.id = metric_id
        body = self._http.request(
            "POST", MetricPaths.UPDATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="metric",
            resource_id=metric_id,
        )
        return Metric.model_validate(body)

    def delete(self, metric_id: int) -> None:
        self._http.request(
            "DELETE", MetricPaths.DELETE,
            path_params={"id": metric_id},
            resource_type="metric",
            resource_id=metric_id,
        )

    def publish(self, metric_ids: _list[int]) -> None:
        self._http.request(
            "POST", MetricPaths.PUBLISH,
            json={"ids": metric_ids, "status": "ONLINE"},
        )

    def unpublish(self, metric_ids: _list[int]) -> None:
        self._http.request(
            "POST", MetricPaths.UNPUBLISH,
            json={"ids": metric_ids, "status": "OFFLINE"},
        )
