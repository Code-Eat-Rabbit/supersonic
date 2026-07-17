"""DimensionsAPI - dimension resource CRUD + query_values.

Phase 1 scope: sync methods only. Async metadata CRUD deferred to v0.2.
"""
from __future__ import annotations

import builtins
from typing import Any

from supersonic.api.paths import DimensionPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.dimension import Dimension, DimensionCreateReq
from supersonic.models.query import Filter

_list = builtins.list
_dict = builtins.dict


class DimensionsAPI:
    """Dimension resource CRUD + query_values.

    async_http kept for interface consistency but unused in Phase 1.
    """

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http  # unused in Phase 1, reserved for v0.2

    def list(
        self,
        *,
        model_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Page[Dimension]:
        """List dimensions by model. model_id is required (path parameter).

        Does not pass resource_type (review fix #4).
        """
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        body = self._http.request(
            "POST", DimensionPaths.LIST,
            path_params={"model_id": model_id},
            params=params,
        )
        return Page[Dimension].from_response(body, item_model=Dimension)

    def get(self, dimension_id: int) -> Dimension:
        body = self._http.request(
            "GET", DimensionPaths.GET,
            path_params={"id": dimension_id},
            resource_type="dimension",
            resource_id=dimension_id,
        )
        return Dimension.model_validate(body)

    def create(self, req: DimensionCreateReq) -> Dimension:
        body = self._http.request(
            "POST", DimensionPaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="dimension",
        )
        return Dimension.model_validate(body)

    def update(self, dimension_id: int, req: DimensionCreateReq) -> Dimension:
        """Update dimension. Reuses DimensionCreateReq body; server uses fields present."""
        update_data = req.model_dump(by_alias=True, exclude_none=True)
        update_data["id"] = dimension_id
        body = self._http.request(
            "POST", DimensionPaths.UPDATE,
            json=update_data,
            resource_type="dimension",
            resource_id=dimension_id,
        )
        return Dimension.model_validate(body)

    def delete(self, dimension_id: int) -> None:
        self._http.request(
            "DELETE", DimensionPaths.DELETE,
            path_params={"id": dimension_id},
            resource_type="dimension",
            resource_id=dimension_id,
        )

    def query_values(
        self,
        dimension_id: int,
        filters: _list[Filter] | None = None,
    ) -> _list[_dict[str, Any]]:
        """Query dimension values (e.g. for dropdown / tag options).

        POST body includes dimensionId and optional filters.
        """
        payload: dict[str, Any] = {"dimensionId": dimension_id}
        if filters:
            payload["filters"] = [
                f.model_dump(by_alias=True, exclude_none=True) for f in filters
            ]
        body = self._http.request(
            "POST", DimensionPaths.QUERY_VALUES,
            json=payload,
        )
        # Server returns raw list of dicts
        if isinstance(body, list):
            return body
        return body.get("list", [])  # type: ignore[no-any-return]
