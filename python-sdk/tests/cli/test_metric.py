"""Tests for cli/metric.py: CRUD + publish/unpublish."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.metric import Metric


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_metric():
    return Metric(
        id=1, name="sales_amt", biz_name="sales_amt",
        model_id=10, define_type="MEASURE", type="NUMBER",
    )


class TestMetricList:
    def test_list_table(self, cli_runner, mock_client, sample_metric):
        mock_client.metrics.list.return_value = Page[Metric](
            items=[sample_metric], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["metric", "list", "--model-id", "10"])
        assert result.exit_code == 0


class TestMetricCRUD:
    def test_get(self, cli_runner, mock_client, sample_metric):
        mock_client.metrics.get.return_value = sample_metric
        result = cli_runner.invoke(app, ["metric", "get", "--id", "1"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_metric):
        result = cli_runner.invoke(
            app,
            [
                "metric", "create",
                "--model-id", "10", "--name", "sales_amt", "--biz-name", "sales_amt",
                "--define-type", "MEASURE", "--type", "NUMBER",
                "--expression", "pay_amt",
            ],
        )
        assert result.exit_code == 0

    def test_update(self, cli_runner, mock_client, sample_metric):
        result = cli_runner.invoke(
            app, ["metric", "update", "--id", "1", "--description", "updated"],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "delete", "--id", "1"])
        assert result.exit_code == 0


class TestMetricPublishUnpublish:
    def test_publish(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "publish", "--ids", "1,2,3"])
        assert result.exit_code == 0
        mock_client.metrics.publish.assert_called_once_with([1, 2, 3])

    def test_unpublish(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "unpublish", "--ids", "1,2,3"])
        assert result.exit_code == 0
        mock_client.metrics.unpublish.assert_called_once_with([1, 2, 3])
