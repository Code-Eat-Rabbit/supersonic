"""Tests for cli/query.py: sql/sqls/validate/metric/chat subcommands."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.models.query import (
    ChatQueryResult,
    ParseState,
    QueryColumn,
    QueryResult,
    SemanticParseInfo,
    ValidationResult,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestSqlSubcommand:
    def test_sql_returns_query_result_table(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[QueryColumn(name="product", type="VARCHAR")],
            result_rows=[{"product": "iPhone"}],
        )
        result = cli_runner.invoke(app, ["query", "sql", "SELECT product FROM sales"])
        assert result.exit_code == 0
        assert "iPhone" in result.stdout

    def test_sql_json_output(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[QueryColumn(name="x", type="INT")],
            result_rows=[{"x": 1}],
        )
        result = cli_runner.invoke(app, ["--json", "query", "sql", "SELECT 1"])
        assert result.exit_code == 0
        assert '"columns"' in result.stdout

    def test_sql_with_data_set_id(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[], result_rows=[],
        )
        result = cli_runner.invoke(
            app, ["query", "sql", "SELECT 1", "--data-set-id", "5"],
        )
        assert result.exit_code == 0
        _, kwargs = mock_client.query.sql.call_args
        assert kwargs.get("data_set_id") == 5


class TestSqlsSubcommand:
    def test_sqls_from_file(self, cli_runner, mock_client, tmp_path):
        sqls_file = tmp_path / "queries.txt"
        sqls_file.write_text("SELECT 1\nSELECT 2\n")
        mock_client.query.sqls.return_value = [
            QueryResult(columns=[], result_rows=[]),
            QueryResult(columns=[], result_rows=[]),
        ]
        result = cli_runner.invoke(
            app, ["query", "sqls", "--sqls-file", str(sqls_file)],
        )
        assert result.exit_code == 0

    def test_sqls_file_not_found(self, cli_runner):
        result = cli_runner.invoke(
            app, ["query", "sqls", "--sqls-file", "/nonexistent/file.txt"],
        )
        assert result.exit_code != 0

    def test_sqls_empty_file(self, cli_runner, mock_client, tmp_path):
        sqls_file = tmp_path / "empty.txt"
        sqls_file.write_text("  \n  \n")
        result = cli_runner.invoke(
            app, ["query", "sqls", "--sqls-file", str(sqls_file)],
        )
        assert result.exit_code != 0


class TestValidateSubcommand:
    def test_validate_returns_validation_result(self, cli_runner, mock_client):
        mock_client.query.validate.return_value = ValidationResult(is_valid=True)
        result = cli_runner.invoke(app, ["query", "validate", "SELECT 1"])
        assert result.exit_code == 0

    def test_validate_invalid(self, cli_runner, mock_client):
        mock_client.query.validate.return_value = ValidationResult(
            is_valid=False,
            error_msg="Unknown column 'foo'",
        )
        result = cli_runner.invoke(app, ["query", "validate", "SELECT foo"])
        assert result.exit_code == 0


class TestMetricSubcommand:
    def test_metric_query_with_date_range(self, cli_runner, mock_client):
        mock_client.query.metric.return_value = QueryResult(
            columns=[QueryColumn(name="category", type="VARCHAR"),
                     QueryColumn(name="sales", type="DOUBLE")],
            result_rows=[{"category": "phone", "sales": 100.0}],
        )
        result = cli_runner.invoke(
            app,
            [
                "query", "metric",
                "--metrics", "sales_amt",
                "--dimensions", "category",
                "--start", "2026-01-01",
                "--end", "2026-06-30",
            ],
        )
        assert result.exit_code == 0
        _, kwargs = mock_client.query.metric.call_args
        assert kwargs["metrics"] == ["sales_amt"]
        assert kwargs["dimensions"] == ["category"]

    def test_metric_partial_date_rejected(self, cli_runner):
        result = cli_runner.invoke(
            app,
            [
                "query", "metric",
                "--metrics", "sales_amt",
                "--start", "2026-01-01",
            ],
        )
        assert result.exit_code != 0


class TestChatSubcommand:
    def test_chat_detailed_default(self, cli_runner, mock_client):
        mock_client.query.chat.return_value = ChatQueryResult(
            query_result=QueryResult(
                columns=[QueryColumn(name="p", type="VARCHAR")],
                result_rows=[{"p": "iPhone"}],
            ),
            selected_parse=SemanticParseInfo(sql="SELECT p FROM sales LIMIT 1", score=0.95),
            parse_state=ParseState.COMPLETED,
        )
        result = cli_runner.invoke(app, ["query", "chat", "--text", "top product"])
        assert result.exit_code == 0

    def test_chat_concise_mode(self, cli_runner, mock_client):
        mock_client.query.chat.return_value = QueryResult(
            columns=[QueryColumn(name="p", type="VARCHAR")],
            result_rows=[{"p": "iPhone"}],
        )
        result = cli_runner.invoke(
            app, ["query", "chat", "--text", "top product", "--concise"],
        )
        assert result.exit_code == 0
        _, kwargs = mock_client.query.chat.call_args
        assert kwargs["detailed"] is False

    def test_chat_with_data_set_ids(self, cli_runner, mock_client):
        mock_client.query.chat.return_value = ChatQueryResult(
            query_result=QueryResult(
                columns=[], result_rows=[],
            ),
            parse_state=ParseState.COMPLETED,
        )
        result = cli_runner.invoke(
            app, ["query", "chat", "--text", "sales", "--data-set-ids", "1,2,3"],
        )
        assert result.exit_code == 0
        _, kwargs = mock_client.query.chat.call_args
        assert kwargs["data_set_ids"] == [1, 2, 3]
