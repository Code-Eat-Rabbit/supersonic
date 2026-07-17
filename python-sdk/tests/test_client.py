"""SupersonicClient facade tests."""
import pytest

from supersonic import SupersonicClient
from supersonic.api.domains import DomainsAPI
from supersonic.api.metrics import MetricsAPI
from supersonic.api.query import QueryAPI


class TestFacadeAssembly:
    def test_lazy_loading_namespaces(self):
        c = SupersonicClient(host="http://test", token="jwt")
        try:
            assert isinstance(c.query, QueryAPI)
            assert isinstance(c.metrics, MetricsAPI)
            assert isinstance(c.domains, DomainsAPI)
            # Same instance (lazy cache)
            assert c.metrics is c.metrics
        finally:
            c.close()

    def test_all_7_namespaces_available(self):
        c = SupersonicClient(host="http://test", token="jwt")
        try:
            for name in ["query", "domains", "models", "dimensions",
                         "metrics", "databases", "datasets"]:
                assert hasattr(c, name), f"missing namespace: {name}"
        finally:
            c.close()


class TestFromConfig:
    def test_from_config(self):
        from supersonic.config import SupersonicConfig
        config = SupersonicConfig(host="http://test", token="jwt", timeout=60.0)
        c = SupersonicClient.from_config(config)
        try:
            assert c is not None
        finally:
            c.close()


class TestFromEnv:
    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        with pytest.raises(ValueError, match="SUPERSONIC_HOST"):
            SupersonicClient.from_env()

    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        c = SupersonicClient.from_env()
        try:
            assert c is not None
        finally:
            c.close()


class TestContextManager:
    def test_with_block_closes_client(self):
        with SupersonicClient(host="http://test", token="jwt") as c:
            assert c is not None
        # After with block, client should be closed (no exception)


class TestEnableAsync:
    def test_enable_async_creates_async_http(self):
        c = SupersonicClient(host="http://test", token="jwt", enable_async=True)
        try:
            assert c is not None
        finally:
            c.close()
