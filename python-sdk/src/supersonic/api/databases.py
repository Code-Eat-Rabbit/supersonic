"""DatabasesAPI - database resource CRUD + test_connect / get_tables / get_columns.

Phase 1 scope: sync methods only. Async metadata CRUD deferred to v0.2.
"""
from __future__ import annotations

import builtins
from typing import Any

from supersonic.api.paths import DatabasePaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.database import (
    Database,
    DatabaseCreateReq,
    TableColumn,
    TestConnectionResult,
)

_list = builtins.list


class DatabasesAPI:
    """Database resource CRUD + utility methods.

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
    ) -> Page[Database]:
        """List databases. Does not pass resource_type (review fix #4)."""
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        body = self._http.request(
            "POST", DatabasePaths.LIST,
            params=params,
        )
        return Page[Database].from_response(body, item_model=Database)

    def get(self, database_id: int) -> Database:
        body = self._http.request(
            "GET", DatabasePaths.GET,
            path_params={"id": database_id},
            resource_type="database",
            resource_id=database_id,
        )
        return Database.model_validate(body)

    def create(self, req: DatabaseCreateReq) -> Database:
        """Create database. Server endpoint is upsert (createOrUpdateDatabase)."""
        body = self._http.request(
            "POST", DatabasePaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="database",
        )
        return Database.model_validate(body)

    def update(self, database_id: int, req: DatabaseCreateReq) -> Database:
        """Update database. Server endpoint is upsert (createOrUpdateDatabase).

        Review fix #9: create and update share the same endpoint.
        """
        update_data = req.model_dump(by_alias=True, exclude_none=True)
        update_data["id"] = database_id
        body = self._http.request(
            "POST", DatabasePaths.UPDATE,
            json=update_data,
            resource_type="database",
            resource_id=database_id,
        )
        return Database.model_validate(body)

    def delete(self, database_id: int) -> None:
        self._http.request(
            "DELETE", DatabasePaths.GET,
            path_params={"id": database_id},
            resource_type="database",
            resource_id=database_id,
        )

    def test_connect(self, req: DatabaseCreateReq) -> TestConnectionResult:
        """Test database connection before creating/updating."""
        body = self._http.request(
            "POST", DatabasePaths.TEST_CONNECT,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return TestConnectionResult.model_validate(body)

    def get_tables(
        self,
        database_id: int,
        db: str | None = None,
    ) -> _list[str]:
        """Get table names from a database."""
        params: dict[str, Any] = {"id": database_id}
        if db is not None:
            params["db"] = db
        body = self._http.request(
            "GET", DatabasePaths.GET_TABLES,
            params=params,
            resource_type="database",
            resource_id=database_id,
        )
        if isinstance(body, list):
            return body
        return body.get("list", [])  # type: ignore[no-any-return]

    def get_columns(
        self,
        database_id: int,
        table: str,
        db: str | None = None,
    ) -> _list[TableColumn]:
        """Get column metadata for a table."""
        params: dict[str, Any] = {"id": database_id, "tableName": table}
        if db is not None:
            params["db"] = db
        body = self._http.request(
            "GET", DatabasePaths.GET_COLUMNS,
            params=params,
            resource_type="database",
            resource_id=database_id,
        )
        if isinstance(body, list):
            return [TableColumn.model_validate(col) for col in body]
        return [TableColumn.model_validate(col) for col in body.get("list", [])]
