"""DatasetsAPI - dataset read-only (list/get).

Phase 1 scope: sync methods only. Datasets are managed through the SuperSonic
web UI; the SDK only provides read access.
"""
from __future__ import annotations

from typing import Any

from supersonic.api.paths import DatasetPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.dataset import Dataset


class DatasetsAPI:
    """Dataset read-only API (list/get).

    async_http kept for interface consistency but unused in Phase 1.
    """

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http  # unused in Phase 1, reserved for v0.2

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> Page[Dataset]:
        """List datasets. Does not pass resource_type (review fix #4)."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        body = self._http.request(
            "POST", DatasetPaths.LIST,
            params=params,
        )
        return Page[Dataset].from_response(body, item_model=Dataset)

    def get(self, dataset_id: int) -> Dataset:
        body = self._http.request(
            "GET", DatasetPaths.GET,
            path_params={"id": dataset_id},
            resource_type="dataset",
            resource_id=dataset_id,
        )
        return Dataset.model_validate(body)
