"""Tests for cli/domain.py: list/get/create/update/delete subcommands.

domain is the template for all 6 metadata resource command groups.
"""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.domain import Domain


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_domain():
    return Domain(
        id=1,
        name="销售域",
        biz_name="sales",
        parent_domain_id=0,
        status="ONLINE",
    )


class TestDomainList:
    def test_list_table_output(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.list.return_value = Page[Domain](
            items=[sample_domain], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["domain", "list"])
        assert result.exit_code == 0
        assert "Total: 1" in result.stdout

    def test_list_json_output(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.list.return_value = Page[Domain](
            items=[sample_domain], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["--json", "domain", "list"])
        assert result.exit_code == 0
        assert '"name": "销售域"' in result.stdout


class TestDomainGet:
    def test_get_returns_domain(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.get.return_value = sample_domain
        result = cli_runner.invoke(app, ["domain", "get", "--id", "1"])
        assert result.exit_code == 0

    def test_get_404_non_zero_exit(self, cli_runner, mock_client):
        from supersonic.exceptions import DomainNotFoundError

        mock_client.domains.get.side_effect = DomainNotFoundError(resource_id=999)
        result = cli_runner.invoke(app, ["domain", "get", "--id", "999"])
        assert result.exit_code != 0
        assert isinstance(result.exception, DomainNotFoundError)


class TestDomainCreate:
    def test_create_minimal(self, cli_runner, mock_client, sample_domain):
        result = cli_runner.invoke(
            app,
            ["domain", "create", "--name", "销售域", "--biz-name", "sales"],
        )
        assert result.exit_code == 0
        mock_client.domains.create.assert_called_once()


class TestDomainUpdate:
    def test_update_description(self, cli_runner, mock_client, sample_domain):
        result = cli_runner.invoke(
            app,
            ["domain", "update", "--id", "1", "--description", "新描述"],
        )
        assert result.exit_code == 0


class TestDomainDelete:
    def test_delete_succeeds(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["domain", "delete", "--id", "1"])
        assert result.exit_code == 0
        mock_client.domains.delete.assert_called_once_with(1)
