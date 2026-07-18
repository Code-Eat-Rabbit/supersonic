"""Tests for cli/config_schema.py: TOML/dotenv parsing + CliConfig validation."""
from pathlib import Path

import pytest

from supersonic.cli.config_schema import (
    CliConfig,
    load_config_file,
)


class TestCliConfig:
    def test_empty_config_valid(self):
        c = CliConfig()
        assert c.host is None
        assert c.token is None
        assert c.retry is None

    def test_full_config_parses(self):
        c = CliConfig(
            host="http://test:9080",
            token="jwt-xxx",
            app_key="test-app",
            timeout=60.0,
            enable_async=True,
            log_level="DEBUG",
            retry={"max_retries": 5, "retry_delay": 2.0},
        )
        assert c.host == "http://test:9080"
        assert c.retry is not None
        assert c.retry.max_retries == 5

    def test_invalid_type_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CliConfig(timeout="not-a-float")

    def test_to_flat_dict_excludes_none(self):
        c = CliConfig(host="http://x", token="jwt")
        flat = c.to_flat_dict()
        assert flat["host"] == "http://x"
        assert flat["token"] == "jwt"
        assert "app_key" not in flat
        assert "retry" not in flat


class TestLoadConfigFile:
    def test_toml_load(self, tmp_path: Path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""\
host = "http://from-toml:9080"
token = "jwt-from-toml"
timeout = 45.0

[retry]
max_retries = 5
""")
        result = load_config_file(config_file, None)
        assert result["host"] == "http://from-toml:9080"
        assert result["token"] == "jwt-from-toml"
        assert result["timeout"] == 45.0
        assert result["retry"]["max_retries"] == 5

    def test_env_file_load(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("""\
SUPERSONIC_HOST=http://from-env:9080
SUPERSONIC_TOKEN=jwt-from-env
SUPERSONIC_APP_KEY=env-app
""")
        result = load_config_file(None, env_file)
        assert result["host"] == "http://from-env:9080"
        assert result["token"] == "jwt-from-env"
        assert result["app_key"] == "env-app"

    def test_config_and_env_file_mutually_exclusive(self, tmp_path: Path):
        import typer

        config_file = tmp_path / "config.toml"
        config_file.write_text('host = "http://x"')
        env_file = tmp_path / ".env"
        env_file.write_text("SUPERSONIC_HOST=http://y")

        with pytest.raises(typer.BadParameter):
            load_config_file(config_file, env_file)

    def test_config_file_not_found_raises(self, tmp_path: Path):
        import typer

        missing = tmp_path / "nonexistent.toml"
        with pytest.raises(typer.BadParameter):
            load_config_file(missing, None)

    def test_env_file_not_found_raises(self, tmp_path: Path):
        import typer

        missing = tmp_path / "nonexistent.env"
        with pytest.raises(typer.BadParameter):
            load_config_file(None, missing)

    def test_default_path_used_when_no_args(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """When neither --config nor --env-file, check ~/.supersonic/config.toml."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_dir = fake_home / ".supersonic"
        config_dir.mkdir()
        default_config = config_dir / "config.toml"
        default_config.write_text('host = "http://default:9080"\ntoken = "jwt-default"')

        monkeypatch.setenv("HOME", str(fake_home))

        result = load_config_file(None, None)
        assert result["host"] == "http://default:9080"
        assert result["token"] == "jwt-default"

    def test_returns_empty_when_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """No --config, no --env-file, no ~/.supersonic/config.toml -> empty dict."""
        fake_home = tmp_path / "empty-home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        result = load_config_file(None, None)
        assert result == {}

    def test_env_file_parses_retry_not_supported(self, tmp_path: Path):
        """dotenv cannot express nested retry; only flat keys loaded."""
        env_file = tmp_path / ".env"
        env_file.write_text("SUPERSONIC_HOST=http://x\nSUPERSONIC_MAX_RETRIES=5")

        result = load_config_file(None, env_file)
        assert result["host"] == "http://x"
        # MAX_RETRIES maps into retry dict via merge_priority, not in load_config_file
        # The load_config_file just returns flat mapping
