"""Utility function tests."""
import pytest

from supersonic.models.query import DateMode, FilterOperator, QueryColumn, QueryResult
from supersonic.utils.builders import (
    date_range,
    filter_eq,
    filter_in,
    last_n_days,
    order_by,
)
from supersonic.utils.format import format_result_table, format_sql
from supersonic.utils.validators import is_valid_s2sql, validate_host_url


class TestBuilders:
    def test_date_range_returns_between_mode(self):
        d = date_range("2026-01-01", "2026-06-30")
        assert d.date_mode == DateMode.BETWEEN
        assert d.start_date == "2026-01-01"
        assert d.end_date == "2026-06-30"

    def test_last_n_days(self):
        d = last_n_days(7)
        assert d.date_mode == DateMode.BETWEEN
        assert d.start_date is not None

    def test_filter_eq(self):
        f = filter_eq("category", "手机")
        assert f.operator == FilterOperator.EQ
        assert f.value == "手机"

    def test_filter_in(self):
        f = filter_in("category", ["手机", "电脑"])
        assert f.operator == FilterOperator.IN

    def test_order_by_default_asc(self):
        o = order_by("sales")
        assert o.direction == "ASC"

    def test_order_by_desc(self):
        o = order_by("sales", "DESC")
        assert o.direction == "DESC"


class TestValidators:
    def test_valid_select(self):
        assert is_valid_s2sql("SELECT * FROM model") is True

    def test_invalid_empty(self):
        assert is_valid_s2sql("") is False

    def test_invalid_no_select(self):
        assert is_valid_s2sql("DELETE FROM model") is False

    def test_validate_host_url_passes(self):
        validate_host_url("http://localhost:9080")  # no exception

    def test_validate_host_url_invalid_raises(self):
        with pytest.raises(ValueError):
            validate_host_url("not-a-url")


class TestFormat:
    def test_format_result_table(self):
        result = QueryResult(
            columns=[
                QueryColumn(name="product", type="VARCHAR"),
                QueryColumn(name="sales", type="DOUBLE"),
            ],
            result_rows=[
                {"product": "iPhone", "sales": 100.0},
                {"product": "iPad", "sales": 80.0},
            ],
        )
        table = format_result_table(result)
        assert "product" in table
        assert "iPhone" in table
        assert "100" in table

    def test_format_sql_indents(self):
        sql = "SELECT a, b FROM t WHERE a > 0"
        formatted = format_sql(sql, indent=2)
        assert isinstance(formatted, str)
        assert len(formatted) > len(sql)  # should have newlines
