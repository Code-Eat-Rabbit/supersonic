"""Public utility functions.

- builders: convenience constructors (date_range, filter_eq, etc.)
- validators: local validation (is_valid_s2sql, etc.)
- format: output formatting (format_result_table, format_sql)
"""
from supersonic.utils.builders import (
    date_range,
    filter_eq,
    filter_in,
    last_n_days,
    month_to_date,
    order_by,
)
from supersonic.utils.format import format_result_table, format_sql
from supersonic.utils.validators import is_valid_s2sql, validate_host_url

__all__ = [
    "date_range",
    "last_n_days",
    "month_to_date",
    "filter_eq",
    "filter_in",
    "order_by",
    "is_valid_s2sql",
    "validate_host_url",
    "format_result_table",
    "format_sql",
]
