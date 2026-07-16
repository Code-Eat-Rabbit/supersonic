"""SupersonicConfig 与 RetryConfig 测试。"""
import pytest

from supersonic.config import RetryConfig, SupersonicConfig, compute_backoff


class TestRetryConfig:
    def test_defaults(self):
        c = RetryConfig()
        assert c.max_retries == 3
        assert c.retry_delay == 1.0
        assert c.max_backoff == 30.0
        assert c.backoff_jitter is True
        assert 429 in c.retryable_status_codes
        assert 500 in c.retryable_status_codes
        assert 400 not in c.retryable_status_codes


class TestComputeBackoff:
    def test_exponential_backoff_without_jitter(self):
        c = RetryConfig(backoff_jitter=False)
        assert compute_backoff(0, c) == 1.0
        assert compute_backoff(1, c) == 2.0
        assert compute_backoff(2, c) == 4.0

    def test_capped_at_max_backoff(self):
        """attempt=10 时 2^10=1024，应被裁剪到 max_backoff。"""
        c = RetryConfig(retry_delay=1.0, max_backoff=30.0, backoff_jitter=False)
        assert compute_backoff(10, c) == 30.0

    def test_retry_after_header_takes_priority(self):
        c = RetryConfig(respect_retry_after=True)
        assert compute_backoff(0, c, retry_after=120.0) == 30.0  # 也受 max_backoff 限制

    def test_retry_after_disabled(self):
        c = RetryConfig(respect_retry_after=False, backoff_jitter=False)
        assert compute_backoff(0, c, retry_after=120.0) == 1.0

    def test_jitter_adds_random_within_0_1(self):
        """jitter 模式下，多次调用结果应该散布在 [base, base+1) 区间。"""
        c = RetryConfig(retry_delay=1.0, backoff_jitter=True)
        results = [compute_backoff(0, c) for _ in range(50)]
        assert all(1.0 <= r < 2.0 for r in results)
        assert len(set(results)) > 1  # 有随机性


class TestSupersonicConfigFromEnv:
    def test_reads_required_vars(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        monkeypatch.delenv("SUPERSONIC_APP_KEY", raising=False)
        config = SupersonicConfig.from_env()
        assert config.host == "http://test:9080"
        assert config.token == "jwt"
        assert config.app_key == "supersonic"

    def test_missing_required_raises_with_helpful_message(self, monkeypatch):
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        with pytest.raises(ValueError, match="SUPERSONIC_HOST"):
            SupersonicConfig.from_env()

    def test_optional_overrides(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        config = SupersonicConfig.from_env(timeout=60.0, enable_async=True)
        assert config.timeout == 60.0
        assert config.enable_async is True

    def test_log_level_env(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        monkeypatch.setenv("SUPERSONIC_LOG_LEVEL", "DEBUG")
        config = SupersonicConfig.from_env()
        assert config.log_level == "DEBUG"
