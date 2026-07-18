"""Tests for cli/dimension.py: CRUD + query-values."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.dimension import Dimension


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_dimension():
    return Dimension(
        id=100, name="category", biz_name="category",
        model_id=10, type="VARCHAR",
    )


class TestDimensionList:
    def test_list_with_model_id(self, cli_runner, mock_client, sample_dimension):
        mock_client.dimensions.list.return_value = Page[Dimension](
            items=[sample_dimension], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["dimension", "list", "--model-id", "10"])
        assert result.exit_code == 0


class TestDimensionCRUD:
    def test_get(self, cli_runner, mock_client, sample_dimension):
        mock_client.dimensions.get.return_value = sample_dimension
        result = cli_runner.invoke(app, ["dimension", "get", "--id", "100"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_dimension):
        result = cli_runner.invoke(
            app,
            [
                "dimension", "create",
                "--model-id", "10", "--name", "category", "--biz-name", "category",
                "--type", "VARCHAR",
            ],
        )
        assert result.exit_code == 0

    def test_update(self, cli_runner, mock_client, sample_dimension):
        result = cli_runner.invoke(
            app, ["dimension", "update", "--id", "100", "--description", "updated"],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["dimension", "delete", "--id", "100"])
        assert result.exit_code == 0


class TestDimensionQueryValues:
    def test_query_values_returns_list(self, cli_runner, mock_client):
        mock_client.dimensions.query_values.return_value = [
            {"value": "phone"}, {"value": "laptop"},
        ]
        result = cli_runner.invoke(
            app, ["dimension", "query-values", "--id", "100"],
        )
        assert result.exit_code == 0
        assert "phone" in result.stdout
