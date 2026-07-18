"""Shared fixtures for CLI tests.

Strategy: mock SupersonicClient via MagicMock (not pytest-httpx).
CLI layer tests assume SDK is already tested by Phase 1 (154 tests / 95% coverage).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture(autouse=True, scope="session")
def _register_cli_subcommands():
    """Ensure all CLI subcommand groups are registered for testing.

    main.py defers registration to cli_main() to allow standalone import,
    but tests that invoke `app` directly need the subcommands registered.
    """
    import supersonic.cli.main as _main

    if not _main._subcommands_registered:
        _main._register_subcommands()
        _main._subcommands_registered = True


@pytest.fixture
def cli_runner() -> CliRunner:
    """typer test runner, isolates stdout/stderr."""
    return CliRunner()


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock SDK SupersonicClient to avoid real HTTP.

    Each namespace has sensible defaults; individual tests can override.
    Patches get_client in common.py AND in all CLI subcommand modules that
    import it directly (``from supersonic.cli.common import get_client``
    creates a local binding that monkeypatch on common.py alone won't reach).
    """
    client = MagicMock(name="MockSupersonicClient")

    from supersonic.common.pagination import Page
    from supersonic.models.metric import Metric

    client.metrics.list.return_value = Page[Metric](
        items=[], total=0, page=1, page_size=10,
    )
    client.metrics.get.return_value = Metric(
        id=1, name="销售额", biz_name="sales_amt",
        model_id=10, define_type="MEASURE", type="NUMBER",
    )

    _fake_get_client = lambda ctx: client  # noqa: E731

    # Patch in common.py (the source of truth)
    monkeypatch.setattr("supersonic.cli.common.get_client", _fake_get_client)

    # Patch in every CLI subcommand module that imports get_client directly.
    # Using importlib to avoid ImportError for modules not yet created.
    import importlib

    _cli_modules = [
        "supersonic.cli.domain",
        "supersonic.cli.model",
        "supersonic.cli.dataset",
        "supersonic.cli.dimension",
        "supersonic.cli.metric",
        "supersonic.cli.database",
        "supersonic.cli.query",
    ]
    for mod_name in _cli_modules:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        if hasattr(mod, "get_client"):
            monkeypatch.setattr(f"{mod_name}.get_client", _fake_get_client)

    return client


@pytest.fixture
def sample_toml_config(tmp_path: Path) -> Path:
    """Temp TOML config file for --config tests."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""\
host = "http://from-toml:9080"
token = "jwt-from-toml"
app_key = "from-toml-app"

[retry]
max_retries = 5
""")
    return config_file


@pytest.fixture
def sample_env_file(tmp_path: Path) -> Path:
    """Temp dotenv file for --env-file tests."""
    env_file = tmp_path / ".env"
    env_file.write_text("""\
SUPERSONIC_HOST=http://from-env:9080
SUPERSONIC_TOKEN=jwt-from-env
""")
    return env_file


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure no SUPERSONIC_* env vars and no default config file."""
    for key in [
        "SUPERSONIC_HOST", "SUPERSONIC_TOKEN", "SUPERSONIC_APP_KEY",
        "SUPERSONIC_TIMEOUT", "SUPERSONIC_ENABLE_ASYNC", "SUPERSONIC_LOG_LEVEL",
        "SUPERSONIC_MAX_RETRIES",
    ]:
        monkeypatch.delenv(key, raising=False)
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setenv("HOME", str(empty_home))
