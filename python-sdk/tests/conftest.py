"""pytest shared fixtures.

- sample dict fixtures (avoid each test re-constructing responses)
- endpoint path fixtures (avoid hardcoded URLs)
- base_url fixture (mock URL prefix)
- API-level fixtures (review fix #1: decouple API tests from Client facade)
"""
import pytest

from supersonic.api.paths import (
    QueryPaths, DomainPaths, ModelPaths, DimensionPaths,
    MetricPaths, DatabasePaths, DatasetPaths,
)


@pytest.fixture
def base_url() -> str:
    """Mock base_url for all tests. HTTPClient builds http://test + path."""
    return "http://test"


@pytest.fixture
def metric_paths():
    return MetricPaths


@pytest.fixture
def domain_paths():
    return DomainPaths


@pytest.fixture
def model_paths():
    return ModelPaths


@pytest.fixture
def dimension_paths():
    return DimensionPaths


@pytest.fixture
def database_paths():
    return DatabasePaths


@pytest.fixture
def dataset_paths():
    return DatasetPaths


@pytest.fixture
def query_paths():
    return QueryPaths


# ===== Sample response fixtures =====

@pytest.fixture
def sample_metric_dict():
    """Single Metric response."""
    return {
        "id": 1,
        "name": "销售额",
        "bizName": "sales_amt",
        "modelId": 10,
        "defineType": "MEASURE",
        "type": "NUMBER",
        "expression": "pay_amt",
        "description": "订单支付金额",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_metric_list_response():
    """Metric list paginated response (SuperSonic PageInfo format)."""
    return {
        "list": [
            {"id": 1, "name": "销售额", "bizName": "sales_amt", "modelId": 10,
             "defineType": "MEASURE", "type": "NUMBER"},
            {"id": 2, "name": "订单数", "bizName": "order_cnt", "modelId": 10,
             "defineType": "MEASURE", "type": "NUMBER"},
        ],
        "total": 50,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_domain_dict():
    """Single Domain response."""
    return {
        "id": 1,
        "name": "电商",
        "bizName": "ecommerce",
        "parentDomainId": None,
        "description": "电商业务域",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_domain_list_response():
    """Domain list paginated response."""
    return {
        "list": [
            {"id": 1, "name": "电商", "bizName": "ecommerce"},
            {"id": 2, "name": "供应链", "bizName": "supply_chain"},
        ],
        "total": 10,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_model_dict():
    """Single Model response."""
    return {
        "id": 1,
        "name": "订单模型",
        "bizName": "order_model",
        "domainId": 1,
        "databaseId": 5,
        "tableName": "orders",
        "description": "订单业务模型",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_model_list_response():
    """Model list paginated response."""
    return {
        "list": [
            {"id": 1, "name": "订单模型", "bizName": "order_model", "domainId": 1,
             "databaseId": 5},
            {"id": 2, "name": "商品模型", "bizName": "product_model", "domainId": 1,
             "databaseId": 5},
        ],
        "total": 20,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_dimension_dict():
    """Single Dimension response."""
    return {
        "id": 1,
        "name": "品类",
        "bizName": "category",
        "modelId": 10,
        "type": "VARCHAR",
        "expr": "category",
        "description": "商品品类",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_dimension_list_response():
    """Dimension list paginated response."""
    return {
        "list": [
            {"id": 1, "name": "品类", "bizName": "category", "modelId": 10,
             "type": "VARCHAR"},
            {"id": 2, "name": "地区", "bizName": "region", "modelId": 10,
             "type": "VARCHAR"},
        ],
        "total": 30,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_database_dict():
    """Single Database response."""
    return {
        "id": 1,
        "name": "demo_mysql",
        "type": "mysql",
        "host": "localhost",
        "port": 3306,
        "username": "root",
        "password": "***",
        "database": "demo",
        "version": "8.0",
        "description": "Demo MySQL database",
    }


@pytest.fixture
def sample_database_list_response():
    """Database list paginated response."""
    return {
        "list": [
            {"id": 1, "name": "demo_mysql", "type": "mysql"},
            {"id": 2, "name": "analytics_ck", "type": "clickhouse"},
        ],
        "total": 5,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_dataset_dict():
    """Single Dataset response."""
    return {
        "id": 1,
        "name": "电商数据集",
        "bizName": "ecommerce_dataset",
        "domainId": 1,
        "modelIds": [10, 11],
        "description": "电商综合数据集",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_dataset_list_response():
    """Dataset list paginated response."""
    return {
        "list": [
            {"id": 1, "name": "电商数据集", "bizName": "ecommerce_dataset",
             "domainId": 1, "modelIds": [10, 11]},
            {"id": 2, "name": "供应链数据集", "bizName": "supply_chain_dataset",
             "domainId": 2, "modelIds": [20]},
        ],
        "total": 8,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_query_result_dict():
    """QueryResult response."""
    return {
        "columns": [
            {"name": "category", "type": "VARCHAR", "displayName": "品类"},
            {"name": "sales_amt", "type": "DOUBLE", "displayName": "销售额"},
        ],
        "resultRows": [
            {"category": "手机", "sales_amt": 12000.0},
            {"category": "电脑", "sales_amt": 8500.0},
        ],
        "sql": "SELECT category, SUM(pay_amt) AS sales_amt FROM orders GROUP BY category",
        "useCache": False,
        "errorMsg": None,
    }


@pytest.fixture
def sample_chat_result_dict():
    """ChatQueryResult response (with parse info)."""
    return {
        "queryResult": {
            "columns": [{"name": "product", "type": "VARCHAR"}],
            "resultRows": [{"product": "iPhone"}],
            "sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1",
        },
        "selectedParse": {
            "sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1",
            "score": 0.95,
            "properties": {},
        },
        "candidateParses": [
            {"sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1",
             "score": 0.95, "properties": {}},
        ],
        "parseState": "COMPLETED",
        "timeCost": {"mapTime": 50, "parseTime": 200, "executeTime": 800},
    }


# ===== API-level fixtures (review fix #1: decouple API tests from Client facade) =====
#
# These fixtures let task 14-20 API tests independently TDD-verify without waiting
# for task 21 (Client). Each injects real HTTPClient (mock retry=0) + None async_http.

@pytest.fixture
def http_client():
    """Shared HTTPClient fixture (max_retries=0 to avoid slow retries)."""
    from supersonic.auth import TokenAuth
    from supersonic.common.http import HTTPClient
    from supersonic.config import RetryConfig
    client = HTTPClient(
        base_url="http://test",
        auth=TokenAuth(token="jwt"),
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    client.close()


@pytest.fixture
def async_http_client():
    """AsyncHTTPClient fixture (only for QueryAPI async tests)."""
    from supersonic.auth import TokenAuth
    from supersonic.common.http import AsyncHTTPClient
    from supersonic.config import RetryConfig
    client = AsyncHTTPClient(
        base_url="http://test",
        auth=TokenAuth(token="jwt"),
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    # Tests should explicitly await aclose() at end


@pytest.fixture
def query_api(http_client):
    """QueryAPI injected with HTTPClient, not dependent on Client facade."""
    from supersonic.api.query import QueryAPI
    return QueryAPI(http=http_client, async_http=None)


@pytest.fixture
def query_api_async(http_client, async_http_client):
    """QueryAPI + async client (only for async tests)."""
    from supersonic.api.query import QueryAPI
    return QueryAPI(http=http_client, async_http=async_http_client)


@pytest.fixture
def metrics_api(http_client):
    from supersonic.api.metrics import MetricsAPI
    return MetricsAPI(http=http_client, async_http=None)


@pytest.fixture
def domains_api(http_client):
    from supersonic.api.domains import DomainsAPI
    return DomainsAPI(http=http_client, async_http=None)


@pytest.fixture
def models_api(http_client):
    from supersonic.api.models import ModelsAPI
    return ModelsAPI(http=http_client, async_http=None)


@pytest.fixture
def dimensions_api(http_client):
    from supersonic.api.dimensions import DimensionsAPI
    return DimensionsAPI(http=http_client, async_http=None)


@pytest.fixture
def databases_api(http_client):
    from supersonic.api.databases import DatabasesAPI
    return DatabasesAPI(http=http_client, async_http=None)


@pytest.fixture
def datasets_api(http_client):
    from supersonic.api.datasets import DatasetsAPI
    return DatasetsAPI(http=http_client, async_http=None)
