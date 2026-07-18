"""CLI config schema: TOML/dotenv parsing + pydantic validation.

Review spec: config loading flow.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel, ConfigDict

# tomllib (3.11+) or tomli backport (3.10)
try:
    import tomllib  # type: ignore[import-untyped]
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]


class RetryConfigFile(BaseModel):
    """Retry config section in TOML file."""

    model_config = ConfigDict(extra="ignore")

    max_retries: int | None = None
    retry_delay: float | None = None
    max_backoff: float | None = None
    backoff_jitter: bool | None = None


class CliConfig(BaseModel):
    """Top-level CLI config schema (parsed from TOML or env vars)."""

    model_config = ConfigDict(extra="ignore")

    host: str | None = None
    token: str | None = None
    app_key: str | None = None
    timeout: float | None = None
    enable_async: bool | None = None
    log_level: str | None = None
    retry: RetryConfigFile | None = None

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten to dict with None values excluded.

        Nested 'retry' is kept as a dict if present.
        """
        data = self.model_dump(exclude_none=True)
        if self.retry is not None:
            data["retry"] = self.retry.model_dump(exclude_none=True)
        return data


def _load_toml(path: Path) -> dict[str, Any]:
    """Load TOML file, return raw dict."""
    with path.open("rb") as f:
        result: dict[str, Any] = tomllib.load(f)
        return result


def _load_dotenv(path: Path) -> dict[str, Any]:
    """Load dotenv file, mapping SUPERSONIC_X to flat keys."""
    env_to_key = {
        "SUPERSONIC_HOST": "host",
        "SUPERSONIC_TOKEN": "token",
        "SUPERSONIC_APP_KEY": "app_key",
        "SUPERSONIC_TIMEOUT": "timeout",
        "SUPERSONIC_ENABLE_ASYNC": "enable_async",
        "SUPERSONIC_LOG_LEVEL": "log_level",
        "SUPERSONIC_MAX_RETRIES": "max_retries",
    }

    result: dict[str, Any] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")

        if key not in env_to_key:
            continue
        flat_key = env_to_key[key]
        if flat_key == "enable_async":
            result[flat_key] = value.lower() == "true"
        elif flat_key == "timeout":
            result[flat_key] = float(value)
        elif flat_key == "max_retries":
            result.setdefault("retry", {})["max_retries"] = int(value)
        else:
            result[flat_key] = value

    return result


def load_config_file(
    config: Path | None,
    env_file: Path | None,
) -> dict[str, Any]:
    """Load config file based on priority: --config > --env-file > default path.

    --config and --env-file are mutually exclusive.
    Returns flat dict (not validated yet).
    """
    if config and env_file:
        raise typer.BadParameter(
            "--config and --env-file are mutually exclusive.",
        )

    if config is not None:
        if not config.exists():
            raise typer.BadParameter(f"Config file not found: {config}")
        return _load_toml(config)

    if env_file is not None:
        if not env_file.exists():
            raise typer.BadParameter(f"Env file not found: {env_file}")
        return _load_dotenv(env_file)

    default_path = Path.home() / ".supersonic" / "config.toml"
    if default_path.exists():
        return _load_toml(default_path)

    return {}


def validate_config_dict(data: dict[str, Any]) -> CliConfig:
    """Validate raw dict via CliConfig pydantic model."""
    return CliConfig.model_validate(data)


def merge_priority(
    cli_args: dict[str, Any],
    env_vars: dict[str, str],
    file_config: dict[str, Any],
) -> dict[str, Any]:
    """Merge config sources by priority: CLI > env > file > default.

    Returns flat dict ready for CliConfig.model_validate.
    """
    env_mapping = {
        "SUPERSONIC_HOST": "host",
        "SUPERSONIC_TOKEN": "token",
        "SUPERSONIC_APP_KEY": "app_key",
        "SUPERSONIC_TIMEOUT": "timeout",
        "SUPERSONIC_ENABLE_ASYNC": "enable_async",
        "SUPERSONIC_LOG_LEVEL": "log_level",
        "SUPERSONIC_MAX_RETRIES": "max_retries",
    }

    parsed_env: dict[str, Any] = {}
    for env_key, flat_key in env_mapping.items():
        if env_key not in env_vars:
            continue
        raw = env_vars[env_key]
        if flat_key == "enable_async":
            parsed_env[flat_key] = raw.lower() == "true"
        elif flat_key == "timeout":
            parsed_env[flat_key] = float(raw)
        elif flat_key == "max_retries":
            parsed_env.setdefault("retry", {})["max_retries"] = int(raw)
        else:
            parsed_env[flat_key] = raw

    merged: dict[str, Any] = {}
    merged.update(file_config)
    merged.update(parsed_env)
    for k, v in cli_args.items():
        if v is not None:
            merged[k] = v

    return merged
