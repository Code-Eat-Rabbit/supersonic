"""DatabasesAPI tests.

Review fix #1: use databases_api fixture, no dependency on Client facade.
Review fix #9: create and update share createOrUpdateDatabase endpoint.
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.databases import DatabasesAPI
from supersonic.exceptions import DatabaseNotFoundError
from supersonic.models.database import (
    Database,
    DatabaseCreateReq,
    TableColumn,
    TestConnectionResult,
)


class TestList:
    def test_returns_paginated_databases(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url, sample_database_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.LIST}?page=1&pageSize=10",
            method="POST",
            json=sample_database_list_response,
        )
        page = databases_api.list(page=1, page_size=10)
        assert page.total == 5
        assert len(page.items) == 2
        assert isinstance(page.items[0], Database)
        assert page.items[0].type == "mysql"


class TestGet:
    def test_returns_database(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url, sample_database_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.GET.format(id=1)}",
            method="GET",
            json=sample_database_dict,
        )
        db = databases_api.get(1)
        assert db.id == 1
        assert db.name == "demo_mysql"

    def test_404_raises_database_not_found(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(DatabaseNotFoundError):
            databases_api.get(999)


class TestCreate:
    def test_creates_and_returns_database(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url, sample_database_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.CREATE}",
            method="POST",
            json=sample_database_dict,
        )
        req = DatabaseCreateReq(
            name="demo_mysql", type="mysql",
            host="localhost", port=3306,
            username="root", password="secret",
        )
        db = databases_api.create(req)
        assert db.id == 1


class TestUpdate:
    def test_updates_database(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url, sample_database_dict,
    ):
        sample_database_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.UPDATE}",
            method="POST",
            json=sample_database_dict,
        )
        req = DatabaseCreateReq(
            name="demo_mysql", type="mysql",
            host="localhost", port=3306,
            username="root", password="secret",
            description="新描述",
        )
        db = databases_api.update(1, req)
        assert db.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.GET.format(id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        databases_api.delete(1)


class TestTestConnect:
    def test_returns_success_result(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.TEST_CONNECT}",
            method="POST",
            json={"success": True, "errorMessage": None},
        )
        req = DatabaseCreateReq(
            name="test_db", type="mysql",
            host="localhost", port=3306,
            username="root", password="secret",
        )
        result = databases_api.test_connect(req)
        assert isinstance(result, TestConnectionResult)
        assert result.success is True

    def test_returns_failure_result(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.TEST_CONNECT}",
            method="POST",
            json={"success": False, "errorMessage": "Connection refused"},
        )
        req = DatabaseCreateReq(
            name="bad_db", type="mysql",
            host="badhost", port=3306,
            username="root", password="secret",
        )
        result = databases_api.test_connect(req)
        assert result.success is False
        assert result.error_message == "Connection refused"


class TestGetTables:
    def test_returns_table_list(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.GET_TABLES}?id=1",
            method="GET",
            json=["orders", "products", "customers"],
        )
        tables = databases_api.get_tables(database_id=1)
        assert tables == ["orders", "products", "customers"]


class TestGetColumns:
    def test_returns_column_list(
        self, databases_api: DatabasesAPI, httpx_mock: HTTPXMock,
        database_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{database_paths.GET_COLUMNS}?id=1&tableName=orders",
            method="GET",
            json=[
                {"name": "id", "type": "BIGINT", "comment": "主键"},
                {"name": "amount", "type": "DOUBLE", "comment": "金额"},
            ],
        )
        columns = databases_api.get_columns(database_id=1, table="orders")
        assert len(columns) == 2
        assert isinstance(columns[0], TableColumn)
        assert columns[0].name == "id"
        assert columns[0].type == "BIGINT"
