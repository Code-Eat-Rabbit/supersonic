"""Tests for cli/dataset.py: list/get (read-only)."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.dataset import Dataset


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_dataset():
    return Dataset(
        id=1,
        name="销售数据集",
        biz_name="sales_dataset",
        domain_id=1,
        model_ids=[10, 11],
    )


class TestDatasetList:
    def test_list(self, cli_runner, mock_client, sample_dataset):
        mock_client.datasets.list.return_value = Page[Dataset](
            items=[sample_dataset], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["dataset", "list"])
        assert result.exit_code == 0


class TestDatasetGet:
    def test_get(self, cli_runner, mock_client, sample_dataset):
        mock_client.datasets.get.return_value = sample_dataset
        result = cli_runner.invoke(app, ["dataset", "get", "--id", "1"])
        assert result.exit_code == 0
