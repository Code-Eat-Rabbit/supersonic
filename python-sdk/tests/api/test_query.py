"""QueryAPI tests.

Review fix #1: inject HTTPClient directly, no dependency on SupersonicClient facade.
"""
import asyncio

import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.query import QueryAPI
from supersonic.exceptions import AsyncNotEnabledError, ServerError
from supersonic.models.query import (
    ChatQueryResult,
    QueryResult,
    ValidationResult,
)


class TestSqlQuery:
    def test_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQL}",
            method="POST",
            json=sample_query_result_dict,
        )
        result = query_api.sql("SELECT 1", data_set_id=1)
        assert isinstance(result, QueryResult)
        assert len(result.columns) == 2

    def test_async_with_enable_async(
        self, query_api_async: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        """Async path: use query_api_async fixture."""
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQL}",
            json=sample_query_result_dict,
        )
        result = asyncio.run(query_api_async.asql("SELECT 1"))
        assert isinstance(result, QueryResult)

    def test_async_without_enable_raises(
        self, query_api: QueryAPI,
    ):
        """query_api fixture has async_http=None; calling async should raise."""
        with pytest.raises(AsyncNotEnabledError):
            asyncio.run(query_api.asql("SELECT 1"))


class TestMetricQuery:
    def test_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.METRIC}",
            json=sample_query_result_dict,
        )
        result = query_api.metric(
            metrics=["销售额"],
            dimensions=["品类"],
        )
        assert isinstance(result, QueryResult)


class TestValidateQuery:
    def test_returns_validation_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.VALIDATE}",
            json={"isValid": True, "errorMsg": None, "correctedSql": None},
        )
        result = query_api.validate("SELECT 1")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True


class TestSqlsBatch:
    def test_returns_list(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQLS}",
            json=[sample_query_result_dict, sample_query_result_dict],
        )
        results = query_api.sqls(["SELECT 1", "SELECT 2"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert isinstance(results[0], QueryResult)


class TestChatDetailedModes:
    def test_default_returns_chat_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_chat_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json=sample_chat_result_dict,
        )
        result = query_api.chat("销售额最高的产品")
        assert isinstance(result, ChatQueryResult)
        assert result.selected_parse is not None

    def test_detailed_false_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_chat_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json=sample_chat_result_dict,
        )
        result = query_api.chat("销售额最高的产品", detailed=False)
        assert isinstance(result, QueryResult)
        assert not isinstance(result, ChatQueryResult)

    def test_detailed_false_on_parse_failure_raises(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url,
    ):
        """Concise mode on parse failure raises, does not return None."""
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json={
                "queryResult": None,
                "selectedParse": None,
                "candidateParses": [],
                "parseState": "FAILED",
            },
        )
        with pytest.raises(ServerError, match="detailed=True"):
            query_api.chat("无效查询", detailed=False)
