"""Query-related pydantic models.

Includes:
- Enums (Text2SqlType / MapMode / ParseState / DateMode / FilterOperator)
- Request bodies (QuerySqlReq / QueryMetricReq / QueryNLReq)
- Response bodies (QueryResult / ChatQueryResult / ValidationResult)
- Auxiliary models (QueryColumn / DateConf / Filter / Order / Param / CacheConfig)
"""
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from supersonic.models.base import CamelModel

# ===== Enums =====


class Text2SqlType(str, Enum):
    LLM_OR_RULE = "LLM_OR_RULE"
    LLM_ONLY = "LLM_ONLY"
    RULE_ONLY = "RULE_ONLY"


class MapMode(str, Enum):
    STRICT = "STRICT"
    LOOSE = "LOOSE"


class ParseState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DateMode(str, Enum):
    BETWEEN = "BETWEEN"
    IN = "IN"
    ALL = "ALL"
    LIST = "LIST"


class FilterOperator(str, Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    LIKE = "LIKE"
    BETWEEN = "BETWEEN"


# ===== Column / Result =====


class QueryColumn(CamelModel):
    name: str
    type: str
    display_name: str | None = None


class QueryResult(CamelModel):
    columns: list[QueryColumn]
    result_rows: list[dict[str, Any]] = Field(default_factory=list)
    sql: str | None = None
    use_cache: bool = False
    error_msg: str | None = None

    def to_dataframe(self) -> Any:
        """Convert to pandas DataFrame (requires pip install supersonic-sdk[pandas])."""
        try:
            import pandas as pd  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "to_dataframe requires pandas. "
                "Install with: pip install supersonic-sdk[pandas]"
            ) from e
        return pd.DataFrame(
            self.result_rows,
            columns=[c.name for c in self.columns],
        )


# ===== Chat Query =====


class SemanticParseInfo(CamelModel):
    sql: str | None = None
    score: float | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class ParseTimeCost(CamelModel):
    map_time: int | None = None
    parse_time: int | None = None
    execute_time: int | None = None


class ChatQueryResult(CamelModel):
    query_result: QueryResult | None = None
    selected_parse: SemanticParseInfo | None = None
    candidate_parses: list[SemanticParseInfo] = Field(default_factory=list)
    parse_state: ParseState
    time_cost: ParseTimeCost | None = None


# ===== Request Types =====


class DateConf(CamelModel):
    date_mode: DateMode
    start_date: str | None = None
    end_date: str | None = None
    date_list: list[str] | None = None
    period: str | None = None


class Filter(CamelModel):
    name: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None


class Order(CamelModel):
    name: str
    direction: Literal["ASC", "DESC"] = "ASC"


class Param(CamelModel):
    name: str
    type: str
    value: Any


class CacheConfig(CamelModel):
    enable: bool = True
    ttl: int = 3600


class QuerySqlReq(CamelModel):
    sql: str
    data_set_id: int | None = None
    model_ids: list[int] | None = None
    limit: int = 1000
    params: list[Param] | None = None
    cache: CacheConfig | None = None


class QueryMetricReq(CamelModel):
    metrics: list[str]
    dimensions: list[str] | None = None
    filters: list[Filter] | None = None
    date_info: DateConf | None = None
    orders: list[Order] | None = None
    limit: int = 1000


class QueryNLReq(CamelModel):
    query_text: str
    data_set_ids: list[int] | None = None
    text2sql_type: Text2SqlType = Text2SqlType.LLM_OR_RULE
    map_mode: MapMode = MapMode.LOOSE
    save_answer: bool = True
    query_filters: dict[str, Any] | None = None
    # SDK-side field, not sent to server
    detailed: bool = True


# ===== Validation =====


class ValidationResult(CamelModel):
    is_valid: bool
    error_msg: str | None = None
    corrected_sql: str | None = None
