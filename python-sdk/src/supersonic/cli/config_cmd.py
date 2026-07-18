"""Config subcommand group: show effective configuration."""
from __future__ import annotations

from typing import Any

import typer

app = typer.Typer(name="config", help="Configuration utilities.")


@app.command(name="show")
def show_cmd(ctx: typer.Context) -> None:
    """Show effective configuration (token masked)."""
    config: dict[str, Any] = ctx.obj or {}

    typer.echo("Effective configuration:")
    typer.echo(f"  host:      {config.get('host', '(not set)')}")
    typer.echo(f"  token:     {_mask(config.get('token'))}")
    typer.echo(f"  app_key:   {config.get('app_key', 'supersonic')}")
    typer.echo(f"  timeout:   {config.get('timeout', 30.0)}")
    typer.echo(f"  log_level: {config.get('log_level', 'WARNING')}")

    retry = config.get("retry") or {}
    if retry:
        typer.echo("  retry:")
        for k, v in retry.items():
            typer.echo(f"    {k}: {v}")


def _mask(token: str | None) -> str:
    """Mask token, showing only first 4 and last 4 characters."""
    if not token:
        return "(not set)"
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"
