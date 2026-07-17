"""QueryAPI - NL / S2SQL / structured metric queries.

5 methods: sql / sqls / validate / metric / chat (with detailed dual-mode).
"""
from typing import Any, Literal, overload

from supersonic.api.paths import QueryPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.exceptions import AsyncNotEnabledError, ServerError
from supersonic.models.query import (
    ChatQueryResult,
    DateConf,
    Filter,
    MapMode,
    Order,
    Param,
    QueryMetricReq,
    QueryNLReq,
    QueryResult,
    QuerySqlReq,
    Text2SqlType,
    ValidationResult,
)


class QueryAPI:
    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http

    # ===== S2SQL =====

    def sql(
        self,
        sql: str,
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
        limit: int = 1000,
        params: list[Param] | None = None,
    ) -> QueryResult:
        req = QuerySqlReq(
            sql=sql,
            data_set_id=data_set_id,
            model_ids=model_ids,
            limit=limit,
            params=params,
        )
        body = self._http.request(
            "POST", QueryPaths.SQL,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    async def asql(self, sql: str, **kwargs: Any) -> QueryResult:
        if self._async_http is None:
            raise AsyncNotEnabledError()
        req = QuerySqlReq(sql=sql, **kwargs)
        body = await self._async_http.request(
            "POST", QueryPaths.SQL,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    # ===== Batch S2SQL =====

    def sqls(
        self,
        sqls: list[str],
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
        limit: int = 1000,
    ) -> list[QueryResult]:
        body = self._http.request(
            "POST", QueryPaths.SQLS,
            json={
                "sqls": sqls,
                "dataSetId": data_set_id,
                "modelIds": model_ids,
                "limit": limit,
            },
        )
        return [QueryResult.model_validate(item) for item in body]

    # ===== Validate =====

    def validate(
        self,
        sql: str,
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
    ) -> ValidationResult:
        body = self._http.request(
            "POST", QueryPaths.VALIDATE,
            json={
                "sql": sql,
                "dataSetId": data_set_id,
                "modelIds": model_ids,
            },
        )
        return ValidationResult.model_validate(body)

    # ===== Structured metric query =====

    def metric(
        self,
        metrics: list[str],
        *,
        dimensions: list[str] | None = None,
        filters: list[Filter] | None = None,
        date_info: DateConf | None = None,
        orders: list[Order] | None = None,
        limit: int = 1000,
    ) -> QueryResult:
        req = QueryMetricReq(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            date_info=date_info,
            orders=orders,
            limit=limit,
        )
        body = self._http.request(
            "POST", QueryPaths.METRIC,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    # ===== NL query (detailed dual-mode) =====

    @overload
    def chat(
        self, query_text: str, *,
        detailed: Literal[True] = True, **kwargs: Any,
    ) -> ChatQueryResult: ...

    @overload
    def chat(
        self, query_text: str, *,
        detailed: Literal[False], **kwargs: Any,
    ) -> QueryResult: ...

    def chat(
        self,
        query_text: str,
        *,
        detailed: bool = True,
        data_set_ids: list[int] | None = None,
        text2sql_type: Text2SqlType = Text2SqlType.LLM_OR_RULE,
        map_mode: MapMode = MapMode.LOOSE,
        save_answer: bool = True,
        query_filters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChatQueryResult | QueryResult:
        req = QueryNLReq(
            query_text=query_text,
            data_set_ids=data_set_ids,
            text2sql_type=text2sql_type,
            map_mode=map_mode,
            save_answer=save_answer,
            query_filters=query_filters,
        )
        body = self._http.request(
            "POST", QueryPaths.CHAT,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        full = ChatQueryResult.model_validate(body)

        if detailed:
            return full

        # Concise mode: parse failure raises explicitly
        if full.query_result is None:
            raise ServerError(
                f"Chat query parse failed (state={full.parse_state.value}). "
                f"Use detailed=True to inspect parse info."
            )
        return full.query_result
