"""异常体系测试。

规格参考：2026-07-16-python-sdk-design.md § 异常树
"""
import pytest

from supersonic.exceptions import (
    SupersonicError,
    AuthenticationError,
    ValidationError,
    FieldError,
    RateLimitError,
    ServerError,
    ConnectionError as SupersonicConnectionError,
    AsyncNotEnabledError,
    ResourceNotFoundError,
    DomainNotFoundError,
    ModelNotFoundError,
    DimensionNotFoundError,
    MetricNotFoundError,
    DatasetNotFoundError,
    DatabaseNotFoundError,
)


class TestSupersonicError:
    def test_root_carries_message_and_status_code(self):
        err = SupersonicError("boom", status_code=500, response_body={"k": "v"})
        assert err.message == "boom"
        assert err.status_code == 500
        assert err.response_body == {"k": "v"}
        assert isinstance(err, Exception)

    def test_status_code_defaults_to_none(self):
        err = SupersonicError("just a message")
        assert err.status_code is None
        assert err.response_body is None


class TestValidationError:
    def test_carries_field_errors(self):
        field_err = FieldError(field="name", message="不能为空")
        err = ValidationError(
            "validation failed",
            field_errors=[field_err],
        )
        assert err.status_code == 400
        assert err.field_errors == [field_err]

    def test_field_errors_defaults_to_empty_list(self):
        err = ValidationError("failed")
        assert err.field_errors == []

    def test_is_supersonic_error(self):
        err = ValidationError("x")
        assert isinstance(err, SupersonicError)


class TestResourceNotFound:
    def test_metric_not_found_carries_resource_id(self):
        err = MetricNotFoundError(resource_id=42)
        assert err.resource_id == 42
        assert err.status_code == 404
        assert "42" in str(err)
        assert isinstance(err, ResourceNotFoundError)

    def test_each_resource_subclass_exists(self):
        for cls in [DomainNotFoundError, ModelNotFoundError, DimensionNotFoundError,
                    MetricNotFoundError, DatasetNotFoundError, DatabaseNotFoundError]:
            assert issubclass(cls, ResourceNotFoundError)


class TestRateLimitError:
    def test_carries_retry_after(self):
        err = RateLimitError("slow down", retry_after=60)
        assert err.retry_after == 60
        assert err.status_code == 429


class TestAsyncNotEnabled:
    def test_message_is_helpful(self):
        err = AsyncNotEnabledError()
        assert "enable_async=True" in err.message
        assert isinstance(err, SupersonicError)


class TestConnectionError:
    def test_is_subclass_of_supersonic_error(self):
        err = SupersonicConnectionError("network down")
        assert isinstance(err, SupersonicError)
        assert isinstance(err, Exception)
