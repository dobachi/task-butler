"""AI-related CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

console = Console()

ai_app = typer.Typer(
    name="ai",
    help="AI model management commands",
    no_args_is_help=True,
)


@ai_app.command(name="status")
def ai_status() -> None:
    """Show AI provider status and configuration."""
    from ...ai.model_manager import ModelManager
    from ...ai.providers.llama import is_llama_available
    from ...config import get_config

    config = get_config()
    ai_config = config.get_ai_config()
    provider_name = ai_config.get("provider", "rule_based")

    console.print("[bold]AI Configuration[/bold]")
    console.print()
    console.print(f"  Provider: [cyan]{provider_name}[/cyan]")
    console.print(
        f"  llama-cpp-python: {'[green]installed[/green]' if is_llama_available() else '[dim]not installed[/dim]'}"
    )

    if provider_name == "llama":
        llama_config = ai_config.get("llama", {})
        console.print()
        console.print("[bold]Llama Configuration[/bold]")
        console.print(f"  Model: {llama_config.get('model_name', 'tinyllama-1.1b')}")
        console.print(f"  Context size: {llama_config.get('n_ctx', 2048)}")
        console.print(f"  GPU layers: {llama_config.get('n_gpu_layers', 0)}")

        # Check if model is downloaded
        manager = ModelManager()
        model_name = llama_config.get("model_name", "tinyllama-1.1b")
        if manager.is_model_available(model_name):
            model_path = manager.get_model_path(model_name)
            console.print(f"  Model path: [green]{model_path}[/green]")
        else:
            console.print("  Model path: [yellow]not downloaded[/yellow]")
            console.print()
            console.print("[dim]Run 'tb ai download' to download the model[/dim]")


@ai_app.command(name="models")
def list_models() -> None:
    """List available AI models."""
    from ...ai.model_manager import ModelManager

    manager = ModelManager()
    models = manager.list_models()

    table = Table(title="Available Models")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Size")
    table.add_column("Status")

    for model in models:
        status = "[green]installed[/green]" if model["installed"] else "[dim]not installed[/dim]"
        table.add_row(
            model["name"],
            model["description"],
            f"{model['size_mb']} MB",
            status,
        )

    console.print(table)
    console.print()
    console.print("[dim]Use 'tb ai download <model>' to download a model[/dim]")


@ai_app.command(name="download")
def download_model(
    model_name: str = typer.Argument("tinyllama-1.1b", help="Model name to download"),
) -> None:
    """Download an AI model for local inference."""
    from ...ai.model_manager import AVAILABLE_MODELS, ModelManager

    if model_name not in AVAILABLE_MODELS:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        console.print(f"Available models: {', '.join(AVAILABLE_MODELS.keys())}")
        raise typer.Exit(1)

    manager = ModelManager()

    if manager.is_model_available(model_name):
        model_path = manager.get_model_path(model_name)
        console.print(f"[green]Model already downloaded: {model_path}[/green]")
        return

    try:
        model_path = manager.download_model(model_name)
        console.print()
        console.print("[green]✓[/green] Model ready for use")
        console.print()
        console.print("To enable LLM-based analysis, run:")
        console.print("  [cyan]tb config set ai.provider llama[/cyan]")
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise typer.Exit(1)


@ai_app.command(name="delete")
def delete_model(
    model_name: str = typer.Argument(..., help="Model name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a downloaded AI model."""
    from ...ai.model_manager import ModelManager

    manager = ModelManager()

    if not manager.is_model_available(model_name):
        console.print(f"[yellow]Model not found: {model_name}[/yellow]")
        raise typer.Exit(0)

    if not force:
        confirm = typer.confirm(f"Delete model '{model_name}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    if manager.delete_model(model_name):
        console.print(f"[green]✓[/green] Deleted: {model_name}")
    else:
        console.print(f"[red]Failed to delete: {model_name}[/red]")
        raise typer.Exit(1)


@ai_app.command(name="prompts")
def show_prompts(
    key: str = typer.Argument(None, help="Specific prompt key to show"),
    show_placeholders: bool = typer.Option(
        False, "--show-placeholders", "-p", help="Show placeholder information"
    ),
    language: str = typer.Option(None, "--language", "-l", help="Language (en/ja)"),
    show_default: bool = typer.Option(
        False, "--default", "-d", help="Show default prompt (ignore customizations)"
    ),
) -> None:
    """Show AI prompts and their placeholders.

    Examples:
        tb ai prompts                    # List all prompts
        tb ai prompts analyze_system     # Show specific prompt
        tb ai prompts -p                 # Show all placeholders
        tb ai prompts analyze_user -p    # Show placeholders for a prompt
    """
    from ...ai.prompts import (
        DEFAULT_PROMPTS,
        PLACEHOLDER_DOCS,
        PROMPT_CATEGORIES,
        PromptManager,
    )
    from ...config import get_config

    # Determine language
    if language is None:
        language = get_config().get_ai_language()
    if language not in ("en", "ja"):
        language = "ja"

    manager = PromptManager(language)

    # Show placeholder documentation
    if show_placeholders and key is None:
        table = Table(title="Available Placeholders")
        table.add_column("Placeholder", style="cyan")
        table.add_column("Description")

        for name, info in PLACEHOLDER_DOCS.items():
            desc_key = f"description_{language}"
            desc = info.get(desc_key, info.get("description_ja", ""))
            table.add_row(f"{{{name}}}", desc)

        console.print(table)
        console.print()
        console.print("[dim]Use placeholders in your custom prompts in config.toml[/dim]")
        return

    # Show specific prompt
    if key:
        if key not in manager.list_keys():
            console.print(f"[red]Unknown prompt key: {key}[/red]")
            console.print()
            console.print("Available keys:")
            for k in manager.list_keys():
                console.print(f"  - {k}")
            raise typer.Exit(1)

        if show_default:
            prompt_text = PromptManager.get_default_prompt(key, language)
            console.print(f"[bold]Default prompt: {key}[/bold] [dim](language: {language})[/dim]")
        else:
            prompt_text = manager.get(key)
            is_custom = manager.is_customized(key)
            status = "[yellow](customized)[/yellow]" if is_custom else "[dim](default)[/dim]"
            console.print(f"[bold]Prompt: {key}[/bold] {status}")

        console.print()
        console.print(prompt_text)

        if show_placeholders:
            placeholders = manager.list_placeholders(key)
            if placeholders:
                console.print()
                console.print("[bold]Placeholders:[/bold]")
                for ph in placeholders:
                    desc = PromptManager.get_placeholder_info(ph, language)
                    console.print(f"  {{{ph}}}: {desc}")
        return

    # Show all prompts grouped by category
    console.print(f"[bold]AI Prompts[/bold] [dim](language: {language})[/dim]")
    console.print()

    for category_key, category in PROMPT_CATEGORIES.items():
        desc_key = f"description_{language}"
        category_desc = category.get(desc_key, category.get("description_ja", ""))
        console.print(f"[bold cyan]{category_desc}[/bold cyan]")

        for prompt_key in category["keys"]:
            is_custom = manager.is_customized(prompt_key)
            status = " [yellow]*[/yellow]" if is_custom else ""
            prompt_text = manager.get(prompt_key)
            # Truncate long prompts
            if len(prompt_text) > 60:
                prompt_text = prompt_text[:57] + "..."
            # Replace newlines for display
            prompt_text = prompt_text.replace("\n", "\\n")
            console.print(f"  [cyan]{prompt_key}[/cyan]{status}: {prompt_text}")

        console.print()

    console.print("[dim]* = customized in config.toml[/dim]")
    console.print()
    console.print("[dim]Use 'tb ai prompts <key>' to see full prompt[/dim]")
    console.print("[dim]Use 'tb ai prompts -p' to see available placeholders[/dim]")
