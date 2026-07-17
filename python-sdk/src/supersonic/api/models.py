"""ModelsAPI - model resource CRUD.

Phase 1 scope: sync methods only. Async metadata CRUD deferred to v0.2.
"""
from __future__ import annotations

from typing import Any

from supersonic.api.paths import ModelPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.model import Model, ModelCreateReq


class ModelsAPI:
    """Model resource CRUD. async_http kept for interface consistency but unused in Phase 1."""

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http  # unused in Phase 1, reserved for v0.2

    def list(
        self,
        *,
        domain_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Page[Model]:
        """List models by domain. domain_id is required (path parameter).

        Does not pass resource_type (review fix #4).
        """
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        body = self._http.request(
            "POST", ModelPaths.LIST,
            path_params={"domain_id": domain_id},
            params=params,
        )
        return Page[Model].from_response(body, item_model=Model)

    def get(self, model_id: int) -> Model:
        body = self._http.request(
            "GET", ModelPaths.GET,
            path_params={"id": model_id},
            resource_type="model",
            resource_id=model_id,
        )
        return Model.model_validate(body)

    def create(self, req: ModelCreateReq) -> Model:
        body = self._http.request(
            "POST", ModelPaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="model",
        )
        return Model.model_validate(body)

    def update(self, model_id: int, req: ModelCreateReq) -> Model:
        """Update model. Reuses ModelCreateReq body; server uses fields present."""
        update_data = req.model_dump(by_alias=True, exclude_none=True)
        update_data["id"] = model_id
        body = self._http.request(
            "POST", ModelPaths.UPDATE,
            json=update_data,
            resource_type="model",
            resource_id=model_id,
        )
        return Model.model_validate(body)

    def delete(self, model_id: int) -> None:
        self._http.request(
            "DELETE", ModelPaths.DELETE,
            path_params={"model_id": model_id},
            resource_type="model",
            resource_id=model_id,
        )
