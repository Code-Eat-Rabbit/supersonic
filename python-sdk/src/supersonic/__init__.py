"""SuperSonic Python SDK.

Import Guide:

    # Client (main entry)
    from supersonic import SupersonicClient

    # Exceptions (for precise catch)
    from supersonic import (
        SupersonicError, AuthenticationError, ValidationError,
        RateLimitError, ServerError, AsyncNotEnabledError,
        MetricNotFoundError, DatasetNotFoundError,
    )

    # Common models
    from supersonic import (
        QueryResult, Metric, MetricCreateReq,
        Filter, DateConf, Text2SqlType,
    )

    # Utility functions
    from supersonic.utils import date_range, filter_eq

Quick Start:

    from supersonic import SupersonicClient

    with SupersonicClient.from_env() as client:
        result = client.query.sql("SELECT sales FROM sales_table")
        print(result.result_rows)
"""
from supersonic.auth import TokenAuth
from supersonic.client import SupersonicClient
from supersonic.config import RetryConfig, SupersonicConfig
from supersonic.exceptions import (
    AsyncNotEnabledError,
    AuthenticationError,
    DatabaseNotFoundError,
    DatasetNotFoundError,
    DimensionNotFoundError,
    DomainNotFoundError,
    FieldError,
    MetricNotFoundError,
    ModelNotFoundError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    SupersonicError,
    ValidationError,
)
from supersonic.exceptions import (
    ConnectionError as ConnectionError,
)
from supersonic.models.database import Database, DatabaseCreateReq
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

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # client / config / auth
    "SupersonicClient",
    "SupersonicConfig",
    "RetryConfig",
    "TokenAuth",
    # exceptions
    "SupersonicError",
    "AuthenticationError",
    "ValidationError",
    "FieldError",
    "RateLimitError",
    "ServerError",
    "ConnectionError",
    "AsyncNotEnabledError",
    "ResourceNotFoundError",
    "DomainNotFoundError",
    "ModelNotFoundError",
    "DimensionNotFoundError",
    "MetricNotFoundError",
    "DatasetNotFoundError",
    "DatabaseNotFoundError",
    # query models
    "QueryResult",
    "ChatQueryResult",
    "QueryColumn",
    "SemanticParseInfo",
    "ParseTimeCost",
    "ParseState",
    "Text2SqlType",
    "MapMode",
    "DateMode",
    "FilterOperator",
    "DateConf",
    "Filter",
    "Order",
    "Param",
    "CacheConfig",
    "QuerySqlReq",
    "QueryMetricReq",
    "QueryNLReq",
    "ValidationResult",
    # metadata models
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
    "Dataset",
]
