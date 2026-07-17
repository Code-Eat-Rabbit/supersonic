"""pydantic data models (split per resource, re-exported here).

Users can either:
    from supersonic.models import Metric, MetricCreateReq, QueryResult
or import directly:
    from supersonic.models.metric import Metric
"""
from supersonic.models.base import CamelModel
from supersonic.models.database import (
    Database,
    DatabaseCreateReq,
    TableColumn,
    TestConnectionResult,
)
from supersonic.models.dataset import Dataset
from supersonic.models.dimension import Dimension, DimensionCreateReq
from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq
from supersonic.models.model import Model, ModelCreateReq
from supersonic.models.query import (
    CacheConfig,
    ChatQueryResult,
    DateConf,
    DateMode,
    Filter,
    FilterOperator,
    MapMode,
    Order,
    Param,
    ParseState,
    ParseTimeCost,
    QueryColumn,
    QueryMetricReq,
    QueryNLReq,
    QueryResult,
    QuerySqlReq,
    SemanticParseInfo,
    Text2SqlType,
    ValidationResult,
)

__all__ = [
    # base
    "CamelModel",
    # enums
    "Text2SqlType",
    "MapMode",
    "ParseState",
    "DateMode",
    "FilterOperator",
    # query
    "QueryColumn",
    "QueryResult",
    "ChatQueryResult",
    "SemanticParseInfo",
    "ParseTimeCost",
    "DateConf",
    "Filter",
    "Order",
    "Param",
    "CacheConfig",
    "QuerySqlReq",
    "QueryMetricReq",
    "QueryNLReq",
    "ValidationResult",
    # metadata
    "Domain",
    "DomainCreateReq",
    "DomainUpdateReq",
    "Model",
    "ModelCreateReq",
    "Dimension",
    "DimensionCreateReq",
    "Metric",
    "MetricCreateReq",
    "MetricUpdateReq",
    "Database",
    "DatabaseCreateReq",
    "TableColumn",
    "TestConnectionResult",
    "Dataset",
]
