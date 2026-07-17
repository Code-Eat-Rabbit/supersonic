"""DomainsAPI - domain resource CRUD.

Phase 1 scope: sync methods only. Async metadata CRUD deferred to v0.2.
"""
from __future__ import annotations

from typing import Any

from supersonic.api.paths import DomainPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq


class DomainsAPI:
    """Domain resource CRUD. async_http kept for interface consistency but unused in Phase 1."""

    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http  # unused in Phase 1, reserved for v0.2

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> Page[Domain]:
        """List domains. Does not pass resource_type (review fix #4)."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        body = self._http.request(
            "POST", DomainPaths.LIST,
            params=params,
        )
        return Page[Domain].from_response(body, item_model=Domain)

    def get(self, domain_id: int) -> Domain:
        body = self._http.request(
            "GET", DomainPaths.GET,
            path_params={"id": domain_id},
            resource_type="domain",
            resource_id=domain_id,
        )
        return Domain.model_validate(body)

    def create(self, req: DomainCreateReq) -> Domain:
        body = self._http.request(
            "POST", DomainPaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="domain",
        )
        return Domain.model_validate(body)

    def update(self, domain_id: int, req: DomainUpdateReq) -> Domain:
        req.id = domain_id
        body = self._http.request(
            "POST", DomainPaths.UPDATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="domain",
            resource_id=domain_id,
        )
        return Domain.model_validate(body)

    def delete(self, domain_id: int) -> None:
        self._http.request(
            "DELETE", DomainPaths.DELETE,
            path_params={"domain_id": domain_id},
            resource_type="domain",
            resource_id=domain_id,
        )
