"""日志工具测试。"""

import logging

from supersonic.common.logging import configure_logging, get_logger, redact_headers


class TestGetLogger:
    def test_returns_supersonic_namespaced_logger(self):
        log = get_logger()
        assert log.name == "supersonic"

    def test_returns_same_instance(self):
        assert get_logger() is get_logger()


class TestConfigureLogging:
    def test_sets_level_on_logger(self):
        configure_logging("DEBUG")
        assert get_logger().level == logging.DEBUG
        # 还原默认避免污染其他测试
        configure_logging("WARNING")


class TestRedactHeaders:
    def test_redacts_authorization(self):
        headers = {
            "Authorization": "Bearer jwt-secret-token",
            "App-Key": "supersonic",
            "Content-Type": "application/json",
        }
        redacted = redact_headers(headers)
        assert redacted["Authorization"] == "Bearer ***"
        assert redacted["App-Key"] == "supersonic"  # 不打码
        assert redacted["Content-Type"] == "application/json"

    def test_handles_missing_authorization(self):
        headers = {"App-Key": "supersonic"}
        redacted = redact_headers(headers)
        assert "Authorization" not in redacted
