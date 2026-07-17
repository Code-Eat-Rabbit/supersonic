"""Convenience builders for common objects."""
from datetime import datetime, timedelta
from typing import Any, Literal

from supersonic.models.query import DateConf, DateMode, Filter, FilterOperator, Order


def date_range(start: str, end: str) -> DateConf:
    """Build BETWEEN-mode DateConf."""
    return DateConf(date_mode=DateMode.BETWEEN, start_date=start, end_date=end)


def last_n_days(n: int) -> DateConf:
    """Last N days from today."""
    end = datetime.now()
    start = end - timedelta(days=n)
    return DateConf(
        date_mode=DateMode.BETWEEN,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    )


def month_to_date() -> DateConf:
    """Month-to-date from day 1 of current month."""
    now = datetime.now()
    start = now.replace(day=1)
    return DateConf(
        date_mode=DateMode.BETWEEN,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=now.strftime("%Y-%m-%d"),
    )


def filter_eq(name: str, value: Any) -> Filter:
    return Filter(name=name, operator=FilterOperator.EQ, value=value)


def filter_in(name: str, values: list[Any]) -> Filter:
    return Filter(name=name, operator=FilterOperator.IN, value=values)


def order_by(name: str, direction: Literal["ASC", "DESC"] = "ASC") -> Order:
    return Order(name=name, direction=direction)
