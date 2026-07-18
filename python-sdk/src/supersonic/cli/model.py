"""Model subcommand group: list/get/create/update/delete.

Note: model list requires --domain-id (path param in SDK, not query).
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.model import ModelCreateReq, ModelUpdateReq

app = typer.Typer(name="model", help="Model CRUD.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    domain_id: int = typer.Option(..., "--domain-id", help="Domain ID (required)"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List models in a domain."""
    client = get_client(ctx)
    result = client.models.list(domain_id=domain_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
) -> None:
    """Get a model by ID."""
    client = get_client(ctx)
    result = client.models.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    domain_id: int = typer.Option(..., "--domain-id"),
    database_id: int = typer.Option(..., "--database-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    table_name: str | None = typer.Option(None, "--table-name"),
    table_query: str | None = typer.Option(
        None, "--table-query", help="View SQL (alternative to table-name)"
    ),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new model."""
    if not table_name and not table_query:
        raise typer.BadParameter("Either --table-name or --table-query is required.")
    client = get_client(ctx)
    req = ModelCreateReq(
        domain_id=domain_id,
        database_id=database_id,
        name=name,
        biz_name=biz_name,
        table_name=table_name,
        table_query=table_query,
        description=description,
    )
    result = client.models.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    table_name: str | None = typer.Option(None, "--table-name"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a model."""
    client = get_client(ctx)
    req = ModelUpdateReq(
        id=id,
        name=name,
        biz_name=biz_name,
        table_name=table_name,
        description=description,
    )
    result = client.models.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
) -> None:
    """Delete a model."""
    client = get_client(ctx)
    client.models.delete(id)
    typer.echo(f"Deleted model {id}")
