"""Query-related pydantic model tests."""
from supersonic.models.query import (
    ChatQueryResult,
    DateConf,
    DateMode,
    Filter,
    FilterOperator,
    MapMode,
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


class TestEnums:
    def test_text2sql_type_values(self):
        assert Text2SqlType.LLM_OR_RULE.value == "LLM_OR_RULE"
        assert Text2SqlType.LLM_ONLY.value == "LLM_ONLY"
        assert Text2SqlType.RULE_ONLY.value == "RULE_ONLY"

    def test_map_mode_values(self):
        assert MapMode.STRICT.value == "STRICT"
        assert MapMode.LOOSE.value == "LOOSE"

    def test_parse_state_values(self):
        assert ParseState.COMPLETED.value == "COMPLETED"
        assert ParseState.FAILED.value == "FAILED"


class TestQueryResult:
    def test_parses_camel_case_response(self, sample_query_result_dict):
        result = QueryResult.model_validate(sample_query_result_dict)
        assert len(result.columns) == 2
        assert isinstance(result.columns[0], QueryColumn)
        assert result.columns[0].display_name == "品类"
        assert len(result.result_rows) == 2
        assert result.use_cache is False
        assert result.error_msg is None
        assert "SELECT" in result.sql

    def test_result_rows_default_empty(self):
        result = QueryResult(columns=[], result_rows=[])
        assert result.result_rows == []
        assert result.sql is None


class TestChatQueryResult:
    def test_parses_full_response(self, sample_chat_result_dict):
        result = ChatQueryResult.model_validate(sample_chat_result_dict)
        assert result.parse_state == ParseState.COMPLETED
        assert result.query_result is not None
        assert isinstance(result.selected_parse, SemanticParseInfo)
        assert len(result.candidate_parses) == 1
        assert isinstance(result.time_cost, ParseTimeCost)
        assert result.time_cost.execute_time == 800

    def test_failed_parse_no_query_result(self):
        """解析失败时 query_result 为 None。"""
        data = {
            "queryResult": None,
            "selectedParse": None,
            "candidateParses": [],
            "parseState": "FAILED",
        }
        result = ChatQueryResult.model_validate(data)
        assert result.parse_state == ParseState.FAILED
        assert result.query_result is None


class TestDateConf:
    def test_between_mode(self):
        d = DateConf(date_mode=DateMode.BETWEEN, start_date="2026-01-01", end_date="2026-06-30")
        assert d.start_date == "2026-01-01"

    def test_camel_case_alias(self):
        """snake_case 写的 date_mode，camelCase JSON 也能解析。"""
        d = DateConf.model_validate({
            "dateMode": "BETWEEN",
            "startDate": "2026-01-01",
            "endDate": "2026-06-30",
        })
        assert d.date_mode == DateMode.BETWEEN


class TestFilter:
    def test_eq_filter(self):
        f = Filter(name="category", operator=FilterOperator.EQ, value="手机")
        assert f.operator == FilterOperator.EQ

    def test_in_filter_with_list_value(self):
        f = Filter(name="category", operator=FilterOperator.IN, value=["手机", "电脑"])
        assert isinstance(f.value, list)


class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(is_valid=True)
        assert r.is_valid is True
        assert r.error_msg is None
        assert r.corrected_sql is None

    def test_invalid_with_corrected_sql(self):
        r = ValidationResult(is_valid=False, error_msg="syntax error",
                              corrected_sql="SELECT ...")
        assert r.corrected_sql == "SELECT ..."


class TestRequestTypes:
    def test_query_sql_req_camel_case(self):
        req = QuerySqlReq.model_validate({
            "sql": "SELECT 1",
            "dataSetId": 1,
            "limit": 100,
        })
        assert req.data_set_id == 1
        assert req.limit == 100

    def test_query_metric_req_required_metrics(self):
        req = QueryMetricReq(metrics=["销售额"])
        assert req.metrics == ["销售额"]
        assert req.dimensions is None

    def test_query_nl_req_defaults(self):
        req = QueryNLReq(query_text="销售额最高的产品")
        assert req.text2sql_type == Text2SqlType.LLM_OR_RULE
        assert req.map_mode == MapMode.LOOSE
        assert req.save_answer is True
        assert req.detailed is True
