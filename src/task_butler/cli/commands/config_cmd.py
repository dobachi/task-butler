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


@config_app.command(name="init")
def config_init() -> None:
    """Initialize configuration with interactive wizard."""
    from ...config import get_config

    config = get_config()

    console.print("[bold]Task Butler Configuration Wizard[/bold]\n")

    # Check if config already exists
    if config.get_all():
        overwrite = typer.confirm("Configuration already exists. Overwrite?", default=False)
        if not overwrite:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    # Storage format
    console.print("[cyan]Storage Format:[/cyan]")
    console.print("  1. frontmatter - YAML frontmatter only (default)")
    console.print("  2. hybrid - YAML frontmatter + Obsidian Tasks line")
    format_choice = typer.prompt(
        "Choose format",
        default="1",
        show_choices=False,
    )
    storage_format = "hybrid" if format_choice == "2" else "frontmatter"

    # Storage directory
    console.print("\n[cyan]Storage Directory:[/cyan]")
    default_dir = str(config.CONFIG_DIR / "tasks")
    storage_dir = typer.prompt(
        "Task storage directory",
        default=default_dir,
    )

    # Obsidian vault root (optional)
    console.print("\n[cyan]Obsidian Vault Root (optional):[/cyan]")
    console.print("[dim]Set this if you use Obsidian integration[/dim]")
    vault_root = typer.prompt(
        "Vault root path",
        default="",
        show_default=False,
    )

    # Organization method
    console.print("\n[cyan]Task Organization Method:[/cyan]")
    console.print("  1. flat - All tasks in one directory (default)")
    console.print(
        "  2. kanban - Status-based subdirectories (Backlog, InProgress, Done, Cancelled)"
    )
    org_choice = typer.prompt(
        "Choose organization method",
        default="1",
        show_choices=False,
    )
    organization_method = "kanban" if org_choice == "2" else "flat"

    # Apply settings
    config.set_value("storage.format", storage_format)
    if storage_dir != default_dir:
        config.set_value("storage.dir", storage_dir)
    if vault_root:
        config.set_value("obsidian.vault_root", vault_root)
    if organization_method != "flat":
        config.set_value("organization.method", organization_method)
    config.save()

    console.print("\n[green]✓ Configuration saved![/green]")
    console.print(f"  storage.format = {storage_format}")
    console.print(f"  storage.dir = {storage_dir}")
    if vault_root:
        console.print(f"  obsidian.vault_root = {vault_root}")
    if organization_method != "flat":
        console.print(f"  organization.method = {organization_method}")
    console.print(f"\nConfig file: {config.CONFIG_PATH}")
