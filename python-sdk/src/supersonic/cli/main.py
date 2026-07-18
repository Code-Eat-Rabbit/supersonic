"""CLI main entry: typer app + global callback + cli_main wrapper.

Review spec: command structure + error handling.

Key design: subcommand registration is deferred to cli_main() to allow
main.py to be imported standalone (for testing common.py and config_schema.py
before subcommand modules exist).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import typer

from supersonic import __version__
from supersonic.cli.config_schema import (
    load_config_file,
    merge_priority,
    validate_config_dict,
)
from supersonic.common.logging import configure_logging
from supersonic.exceptions import SupersonicError, ValidationError

app = typer.Typer(
    name="supersonic",
    help="SuperSonic Python SDK CLI - query and manage semantic models.",
    no_args_is_help=True,
    add_completion=True,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    host: str | None = typer.Option(None, "--host", help="SuperSonic service URL"),
    token: str | None = typer.Option(None, "--token", help="JWT auth token"),
    app_key: str | None = typer.Option(None, "--app-key", help="App-Key header value"),
    timeout: float | None = typer.Option(None, "--timeout", help="HTTP timeout in seconds"),
    config: Path | None = typer.Option(None, "--config", help="TOML config file path"),  # noqa: B008
    env_file: Path | None = typer.Option(None, "--env-file", help="dotenv file path"),  # noqa: B008
    json_output: bool = typer.Option(False, "--json", help="Output JSON instead of table"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    verbose: bool = typer.Option(False, "--verbose", "--debug", help="Verbose logging"),
    quiet: bool = typer.Option(False, "--quiet", help="Error-only logging"),
    show_version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit"
    ),
) -> None:
    """SuperSonic CLI - manage semantic models and run queries."""
    if show_version:
        typer.echo(f"supersonic-sdk {__version__}")
        raise typer.Exit(0)

    if verbose and quiet:
        raise typer.BadParameter("--verbose and --quiet are mutually exclusive.")

    if verbose:
        log_level = "DEBUG"
    elif quiet:
        log_level = "ERROR"
    else:
        log_level = "WARNING"
    configure_logging(log_level)

    file_config = load_config_file(config, env_file)

    cli_args: dict[str, Any] = {
        "host": host,
        "token": token,
        "app_key": app_key,
        "timeout": timeout,
        "log_level": log_level if (verbose or quiet) else None,
    }

    merged = merge_priority(cli_args, dict(os.environ), file_config)
    validated = validate_config_dict(merged)
    flat = validated.to_flat_dict()
    flat.setdefault("log_level", log_level)

    ctx.obj = flat
    ctx.obj["__json"] = json_output
    ctx.obj["__no_color"] = no_color


def _register_subcommands() -> None:
    """Register all subcommand groups. Called from cli_main() to defer imports."""
    from supersonic.cli.config_cmd import app as config_app  # type: ignore[import-not-found]
    from supersonic.cli.database import app as database_app  # type: ignore[import-not-found]
    from supersonic.cli.dataset import app as dataset_app  # type: ignore[import-not-found]
    from supersonic.cli.dimension import app as dimension_app  # type: ignore[import-not-found]
    from supersonic.cli.domain import app as domain_app  # type: ignore[import-not-found]
    from supersonic.cli.metric import app as metric_app  # type: ignore[import-not-found]
    from supersonic.cli.model import app as model_app  # type: ignore[import-not-found]
    from supersonic.cli.query import app as query_app  # type: ignore[import-not-found]

    app.add_typer(query_app, name="query", help="Query the semantic layer (sql/metric/chat)")
    app.add_typer(domain_app, name="domain", help="Domain CRUD")
    app.add_typer(model_app, name="model", help="Model CRUD")
    app.add_typer(dimension_app, name="dimension", help="Dimension CRUD")
    app.add_typer(metric_app, name="metric", help="Metric CRUD + publish/unpublish")
    app.add_typer(database_app, name="database", help="Database CRUD + test-connect")
    app.add_typer(dataset_app, name="dataset", help="Dataset read")
    app.add_typer(config_app, name="config", help="Configuration utilities")


_subcommands_registered = False


def cli_main() -> None:
    """CLI entry point referenced by pyproject.toml [project.scripts]."""
    global _subcommands_registered
    if not _subcommands_registered:
        _register_subcommands()
        _subcommands_registered = True

    try:
        app()
    except SupersonicError as e:
        from supersonic.cli.common import exit_code_for

        exit_code = exit_code_for(e)
        typer.echo(
            f"Error: {e.message} (status={e.status_code})",
            err=True,
        )
        if isinstance(e, ValidationError) and e.field_errors:
            for fe in e.field_errors:
                typer.echo(f"  - {fe.field}: {fe.message}", err=True)
        raise typer.Exit(exit_code) from e
    except typer.Exit:
        raise
    except Exception as e:
        logging.getLogger("supersonic").exception("Unexpected CLI error")
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    cli_main()
