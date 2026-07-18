"""Dimension subcommand group: list/get/create/update/delete + query-values."""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.dimension import DimensionCreateReq

app = typer.Typer(name="dimension", help="Dimension CRUD + query values.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    model_id: int = typer.Option(..., "--model-id", help="Model ID (required)"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List dimensions by model."""
    client = get_client(ctx)
    result = client.dimensions.list(model_id=model_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Get a dimension by ID."""
    client = get_client(ctx)
    result = client.dimensions.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    model_id: int = typer.Option(..., "--model-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    type: str = typer.Option(..., "--type", help="Data type: VARCHAR/NUMBER/DATE/..."),
    expr: str | None = typer.Option(None, "--expr"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new dimension."""
    client = get_client(ctx)
    req = DimensionCreateReq(
        model_id=model_id, name=name, biz_name=biz_name,
        type=type, expr=expr, description=description,
    )
    result = client.dimensions.create(req)
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
    type: str | None = typer.Option(None, "--type"),
    expr: str | None = typer.Option(None, "--expr"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a dimension."""
    client = get_client(ctx)
    req = DimensionCreateReq(
        model_id=0,
        name=name or "", biz_name=biz_name or "", type=type or "",
        expr=expr, description=description,
    )
    result = client.dimensions.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    """Delete a dimension."""
    client = get_client(ctx)
    client.dimensions.delete(id)
    typer.echo(f"Deleted dimension {id}")


@app.command(name="query-values")
def query_values_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Dimension ID"),
) -> None:
    """Query distinct values of a dimension."""
    client = get_client(ctx)
    result = client.dimensions.query_values(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
