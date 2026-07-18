"""Tests for cli/model.py."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.model import Model


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_model():
    return Model(
        id=10,
        name="订单模型",
        biz_name="order",
        domain_id=1,
        database_id=5,
    )


class TestModelList:
    def test_list_requires_domain_id(self, cli_runner, mock_client, sample_model):
        """--domain-id is required for model list."""
        mock_client.models.list.return_value = Page[Model](
            items=[sample_model], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["model", "list"])
        assert result.exit_code != 0

    def test_list_with_domain_id(self, cli_runner, mock_client, sample_model):
        mock_client.models.list.return_value = Page[Model](
            items=[sample_model], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["model", "list", "--domain-id", "1"])
        assert result.exit_code == 0


class TestModelGet:
    def test_get_returns_model(self, cli_runner, mock_client, sample_model):
        mock_client.models.get.return_value = sample_model
        result = cli_runner.invoke(app, ["model", "get", "--id", "10"])
        assert result.exit_code == 0


class TestModelCreate:
    def test_create_minimal(self, cli_runner, mock_client, sample_model):
        result = cli_runner.invoke(
            app,
            [
                "model", "create",
                "--domain-id", "1", "--database-id", "5",
                "--name", "订单模型", "--biz-name", "order",
                "--table-name", "orders",
            ],
        )
        assert result.exit_code == 0
        mock_client.models.create.assert_called_once()


class TestModelUpdate:
    def test_update_description(self, cli_runner, mock_client, sample_model):
        result = cli_runner.invoke(
            app, ["model", "update", "--id", "10", "--table-name", "new_orders"],
        )
        assert result.exit_code == 0


class TestModelDelete:
    def test_delete_succeeds(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["model", "delete", "--id", "10"])
        assert result.exit_code == 0
        mock_client.models.delete.assert_called_once_with(10)
