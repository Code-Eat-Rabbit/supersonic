"""Domain subcommand group: list/get/create/update/delete.

Review spec: 命令清单 -> 元数据 CRUD.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.domain import DomainCreateReq, DomainUpdateReq

app = typer.Typer(name="domain", help="Domain CRUD.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List domains."""
    client = get_client(ctx)
    result = client.domains.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Domain ID"),
) -> None:
    """Get a domain by ID."""
    client = get_client(ctx)
    result = client.domains.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    parent_domain_id: int | None = typer.Option(None, "--parent-domain-id"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new domain."""
    client = get_client(ctx)
    req = DomainCreateReq(
        name=name,
        biz_name=biz_name,
        parent_domain_id=parent_domain_id,
        description=description,
    )
    result = client.domains.create(req)
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
    parent_domain_id: int | None = typer.Option(None, "--parent-domain-id"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a domain."""
    client = get_client(ctx)
    req = DomainUpdateReq(
        id=id,
        name=name,
        biz_name=biz_name,
        parent_domain_id=parent_domain_id,
        description=description,
    )
    result = client.domains.update(id, req)
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
    """Delete a domain."""
    client = get_client(ctx)
    client.domains.delete(id)
    typer.echo(f"Deleted domain {id}")
