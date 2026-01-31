"""Config command for Task Butler."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

config_app = typer.Typer(
    name="config",
    help="Manage configuration settings",
    no_args_is_help=True,
)

console = Console()


@config_app.command(name="show")
def config_show() -> None:
    """Show all configuration settings."""
    from ...config import get_config

    config = get_config()
    all_config = config.get_all()

    if not all_config:
        console.print("[dim]No configuration set. Using defaults.[/dim]")
        console.print(f"  storage.format = {config.DEFAULT_FORMAT}")
        console.print(f"  storage.dir = {config.CONFIG_DIR / 'tasks'}")
        return

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for section, values in sorted(all_config.items()):
        if isinstance(values, dict):
            for key, value in sorted(values.items()):
                table.add_row(f"{section}.{key}", str(value))

    console.print(table)


@config_app.command(name="get")
def config_get(
    key: str = typer.Argument(..., help="Config key (e.g., storage.format)"),
) -> None:
    """Get a configuration value."""
    from ...config import get_config

    config = get_config()
    value = config.get_value(key)

    if value is None:
        console.print(f"[yellow]Key '{key}' not set[/yellow]")
        raise typer.Exit(1)

    console.print(value)


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., storage.format)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    from ...config import get_config

    config = get_config()

    try:
        config.set_value(key, value)
        config.save()
        console.print(f"[green]Set {key} = {value}[/green]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
