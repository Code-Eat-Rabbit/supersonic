"""CLI shared utilities: client construction, output formatting, exit code mapping.

Review spec: shared tools (common.py).
"""
from __future__ import annotations

import json
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from supersonic.client import SupersonicClient
from supersonic.common.pagination import Page
from supersonic.config import RetryConfig
from supersonic.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)
from supersonic.exceptions import (
    ConnectionError as SupersonicConnectionError,
)
from supersonic.models.query import QueryResult
from supersonic.utils.format import format_result_table


def get_client(ctx: typer.Context) -> SupersonicClient:
    """Build SupersonicClient from ctx.obj (merged config).

    ctx.obj is populated by main.py's global callback before any subcommand runs.
    """
    config: dict[str, Any] = ctx.obj or {}
    host = config.get("host")
    token = config.get("token")
    if not host or not token:
        raise typer.BadParameter(
            "host and token are required. Provide via --host/--token, "
            "env vars SUPERSONIC_HOST/SUPERSONIC_TOKEN, or config file."
        )

    retry_dict = config.get("retry") or {}
    retry = RetryConfig(**retry_dict) if retry_dict else RetryConfig()

    return SupersonicClient(
        host=host,
        token=token,
        app_key=config.get("app_key", "supersonic"),
        timeout=config.get("timeout", 30.0),
        retry=retry,
        log_level=config.get("log_level", "WARNING"),
    )


def format_output(
    obj: Any,
    *,
    as_json: bool,
    no_color: bool,
    columns: list[str] | None = None,
) -> None:
    """Unified output formatting.

    - as_json=True: pydantic model_dump_json or json.dumps
    - as_json=False: rich Table (or format_result_table for QueryResult)
    """
    if as_json:
        if isinstance(obj, BaseModel):
            typer.echo(obj.model_dump_json(indent=2))
        else:
            typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
        return

    console = Console(no_color=no_color)

    if isinstance(obj, QueryResult):
        typer.echo(format_result_table(obj))
    elif isinstance(obj, Page):
        _render_page_table(console, obj, columns)
    elif isinstance(obj, BaseModel):
        _render_kv_table(console, obj)
    elif isinstance(obj, list):
        _render_list_table(console, obj, columns)
    else:
        typer.echo(str(obj))


def _render_page_table(
    console: Console,
    page: Page[BaseModel],
    columns: list[str] | None,
) -> None:
    """Render Page[T] as rich table with footer 'Total: N . Page X/Y'."""
    if not page.items:
        typer.echo("(no items)")
        return

    sample = page.items[0]
    headers = columns or list(sample.model_dump(by_alias=False).keys())

    table = Table(show_header=True, header_style="bold")
    for h in headers:
        table.add_column(str(h))

    for item in page.items:
        data = item.model_dump(by_alias=False)
        table.add_row(*[str(data.get(h, "")) for h in headers])

    console.print(table)
    total_pages = (
        (page.total + page.page_size - 1) // page.page_size if page.page_size else 1
    )
    typer.echo(f"\nTotal: {page.total} . Page {page.page}/{total_pages}")


def _render_kv_table(console: Console, model: BaseModel) -> None:
    """Render single pydantic model as key-value two-column table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")

    data = model.model_dump(by_alias=False)
    for k, v in data.items():
        table.add_row(str(k), str(v) if v is not None else "")

    console.print(table)


def _render_list_table(
    console: Console,
    items: list[BaseModel],
    columns: list[str] | None,
) -> None:
    """Render list of pydantic models as rich table."""
    if not items:
        typer.echo("(empty)")
        return

    sample = items[0]
    if not isinstance(sample, BaseModel):
        for i in items:
            typer.echo(str(i))
        return

    headers = columns or list(sample.model_dump(by_alias=False).keys())

    table = Table(show_header=True, header_style="bold")
    for h in headers:
        table.add_column(str(h))

    for item in items:
        if isinstance(item, BaseModel):
            data = item.model_dump(by_alias=False)
            table.add_row(*[str(data.get(h, "")) for h in headers])
        else:
            table.add_row(str(item))

    console.print(table)


def exit_code_for(exc: Exception) -> int:
    """Map exception to semantic exit code.

    0: success (not handled here)
    1: generic client error / unknown SupersonicError
    2: AuthenticationError (401)
    3: ResourceNotFoundError (404)
    4: ValidationError (400)
    5: ServerError / ConnectionError (5xx / network)
    """
    if isinstance(exc, AuthenticationError):
        return 2
    if isinstance(exc, ResourceNotFoundError):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, (ServerError, SupersonicConnectionError)):
        return 5
    return 1
