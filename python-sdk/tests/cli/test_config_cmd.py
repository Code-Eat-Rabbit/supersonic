"""Tests for cli/config_cmd.py: config show."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestConfigShow:
    def test_shows_host_and_token_masked(self, cli_runner, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt-secret-token-12345")
        result = cli_runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "http://test:9080" in result.stdout
        # Token should be masked
        assert "jwt-secret-token-12345" not in result.stdout
        assert "***" in result.stdout

    def test_shows_default_when_unset(self, cli_runner, monkeypatch, tmp_path):
        for key in ["SUPERSONIC_HOST", "SUPERSONIC_TOKEN", "SUPERSONIC_APP_KEY"]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "empty"))
        result = cli_runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
