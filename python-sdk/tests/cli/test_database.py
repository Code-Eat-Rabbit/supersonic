"""Tests for cli/database.py: CRUD + test-connect/get-tables/get-columns."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.database import Database, TableColumn, TestConnectionResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_database():
    return Database(
        id=5, name="main-db", type="mysql",
        host="localhost", port=3306,
    )


class TestDatabaseList:
    def test_list(self, cli_runner, mock_client, sample_database):
        mock_client.databases.list.return_value = Page[Database](
            items=[sample_database], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["database", "list"])
        assert result.exit_code == 0
        # Rich table may truncate column values
        assert "main" in result.stdout


class TestDatabaseCRUD:
    def test_get(self, cli_runner, mock_client, sample_database):
        mock_client.databases.get.return_value = sample_database
        result = cli_runner.invoke(app, ["database", "get", "--id", "5"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_database):
        result = cli_runner.invoke(
            app,
            [
                "database", "create",
                "--name", "main-db", "--type", "mysql",
                "--host", "localhost", "--port", "3306",
                "--username", "root", "--password", "secret",
            ],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["database", "delete", "--id", "5"])
        assert result.exit_code == 0


class TestDatabaseTestConnect:
    def test_test_connect_success(self, cli_runner, mock_client):
        mock_client.databases.test_connect.return_value = TestConnectionResult(success=True)
        result = cli_runner.invoke(
            app,
            [
                "database", "test-connect",
                "--name", "test-db", "--type", "mysql",
                "--host", "localhost", "--port", "3306",
                "--username", "root", "--password", "secret",
            ],
        )
        assert result.exit_code == 0


class TestDatabaseGetTables:
    def test_get_tables(self, cli_runner, mock_client):
        mock_client.databases.get_tables.return_value = ["orders", "users", "products"]
        result = cli_runner.invoke(app, ["database", "get-tables", "--id", "5"])
        assert result.exit_code == 0
        assert "orders" in result.stdout


class TestDatabaseGetColumns:
    def test_get_columns(self, cli_runner, mock_client):
        mock_client.databases.get_columns.return_value = [
            TableColumn(name="id", type="INT"),
            TableColumn(name="name", type="VARCHAR"),
        ]
        result = cli_runner.invoke(
            app,
            ["database", "get-columns", "--id", "5", "--table", "users"],
        )
        assert result.exit_code == 0
        assert "id" in result.stdout
