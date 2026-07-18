"""Tests for cli/common.py shared utilities."""
from unittest.mock import MagicMock

from supersonic.cli.common import (
    exit_code_for,
    format_output,
    get_client,
)
from supersonic.common.pagination import Page
from supersonic.exceptions import (
    AuthenticationError,
    DatabaseNotFoundError,
    MetricNotFoundError,
    RateLimitError,
    ServerError,
    SupersonicError,
    ValidationError,
)
from supersonic.exceptions import (
    ConnectionError as SupersonicConnectionError,
)
from supersonic.models.metric import Metric
from supersonic.models.query import QueryColumn, QueryResult


class TestExitCodeFor:
    """Review spec: error handling and exit codes."""

    def test_authentication_error_returns_2(self):
        assert exit_code_for(AuthenticationError()) == 2

    def test_resource_not_found_returns_3(self):
        assert exit_code_for(MetricNotFoundError(resource_id=99)) == 3
        assert exit_code_for(DatabaseNotFoundError(resource_id=1)) == 3

    def test_validation_error_returns_4(self):
        assert exit_code_for(ValidationError("bad")) == 4

    def test_server_error_returns_5(self):
        assert exit_code_for(ServerError("boom", status_code=500)) == 5

    def test_connection_error_returns_5(self):
        assert exit_code_for(SupersonicConnectionError("net down")) == 5

    def test_rate_limit_returns_1(self):
        """RateLimitError not in 2-5 range, falls through to generic 1."""
        assert exit_code_for(RateLimitError(retry_after=60)) == 1

    def test_generic_supersonic_error_returns_1(self):
        assert exit_code_for(SupersonicError("other")) == 1

    def test_unexpected_exception_returns_1(self):
        assert exit_code_for(ValueError("unexpected")) == 1


class TestFormatOutput:
    def test_json_mode_for_pydantic_model(self, capsys):
        m = Metric(
            id=1, name="销售额", biz_name="sales_amt",
            model_id=10, define_type="MEASURE",
        )
        format_output(m, as_json=True, no_color=True)
        captured = capsys.readouterr()
        assert '"name": "销售额"' in captured.out
        assert '"id": 1' in captured.out

    def test_json_mode_for_page(self, capsys):
        page = Page[Metric](
            items=[Metric(id=1, name="x", biz_name="x", model_id=1, define_type="MEASURE")],
            total=1, page=1, page_size=10,
        )
        format_output(page, as_json=True, no_color=True)
        captured = capsys.readouterr()
        assert '"total": 1' in captured.out
        assert '"items":' in captured.out

    def test_table_mode_for_query_result(self, capsys):
        result = QueryResult(
            columns=[QueryColumn(name="product", type="VARCHAR")],
            result_rows=[{"product": "iPhone"}],
        )
        format_output(result, as_json=False, no_color=True)
        captured = capsys.readouterr()
        assert "product" in captured.out
        assert "iPhone" in captured.out

    def test_table_mode_for_page(self, capsys):
        page = Page[Metric](
            items=[
                Metric(
                    id=1, name="sales", biz_name="sales_amt",
                    model_id=10, define_type="MEASURE",
                )
            ],
            total=1, page=1, page_size=10,
        )
        format_output(page, as_json=False, no_color=True, columns=["id", "name", "biz_name"])
        captured = capsys.readouterr()
        assert "sales" in captured.out
        assert "Total: 1" in captured.out

    def test_table_mode_for_single_model(self, capsys):
        m = Metric(id=42, name="test_metric", biz_name="test", model_id=1, define_type="MEASURE")
        format_output(m, as_json=False, no_color=True)
        captured = capsys.readouterr()
        # rich may truncate column values in narrow terminals; check for field name
        assert "Field" in captured.out
        assert "Value" in captured.out


class TestGetClient:
    def test_get_client_returns_supersonic_client(self):
        """get_client reads merged config from ctx.obj, constructs SupersonicClient."""
        import typer

        from supersonic.client import SupersonicClient

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {
            "host": "http://test:9080",
            "token": "jwt-test",
            "app_key": "test-app",
            "timeout": 60.0,
        }
        client = get_client(ctx)
        assert isinstance(client, SupersonicClient)
        client.close()
