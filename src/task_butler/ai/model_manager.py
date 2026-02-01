"""Model manager for downloading and managing LLM models."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

console = Console()

# Default models - small models suitable for local inference
AVAILABLE_MODELS = {
    "tinyllama-1.1b": {
        "name": "TinyLlama 1.1B Chat",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size_mb": 669,
        "description": "Small and fast, good for basic task analysis",
    },
    "phi-2": {
        "name": "Phi-2",
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "filename": "phi-2.Q4_K_M.gguf",
        "size_mb": 1630,
        "description": "Microsoft's compact model, better reasoning",
    },
}

DEFAULT_MODEL = "tinyllama-1.1b"


class ModelManager:
    """Manages LLM model downloads and paths."""

    def __init__(self, models_dir: Path | None = None):
        """Initialize model manager.

        Args:
            models_dir: Directory to store models. Defaults to ~/.task-butler/models/
        """
        if models_dir is None:
            models_dir = Path.home() / ".task-butler" / "models"
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str = DEFAULT_MODEL) -> Path | None:
        """Get the path to a model file.

        Args:
            model_name: Name of the model (e.g., 'tinyllama-1.1b')

        Returns:
            Path to the model file if it exists, None otherwise
        """
        if model_name not in AVAILABLE_MODELS:
            return None

        model_info = AVAILABLE_MODELS[model_name]
        model_path = self.models_dir / model_info["filename"]

        if model_path.exists():
            return model_path
        return None

    def is_model_available(self, model_name: str = DEFAULT_MODEL) -> bool:
        """Check if a model is downloaded.

        Args:
            model_name: Name of the model

        Returns:
            True if model exists locally
        """
        return self.get_model_path(model_name) is not None

    def download_model(
        self,
        model_name: str = DEFAULT_MODEL,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download a model.

        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates (current, total)

        Returns:
            Path to the downloaded model

        Raises:
            ValueError: If model name is unknown
            RuntimeError: If download fails
        """
        if model_name not in AVAILABLE_MODELS:
            available = ", ".join(AVAILABLE_MODELS.keys())
            raise ValueError(f"Unknown model: {model_name}. Available: {available}")

        model_info = AVAILABLE_MODELS[model_name]
        model_path = self.models_dir / model_info["filename"]

        if model_path.exists():
            return model_path

        url = model_info["url"]
        console.print(f"[blue]Downloading {model_info['name']}...[/blue]")
        console.print(f"[dim]Size: ~{model_info['size_mb']} MB[/dim]")
        console.print(f"[dim]URL: {url}[/dim]")

        # Download with progress
        temp_path = model_path.with_suffix(".tmp")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading...", total=None)

                def reporthook(block_num: int, block_size: int, total_size: int):
                    if total_size > 0:
                        progress.update(task, total=total_size)
                        progress.update(task, completed=block_num * block_size)
                    if progress_callback:
                        progress_callback(block_num * block_size, total_size)

                urllib.request.urlretrieve(url, temp_path, reporthook)

            # Move to final location
            temp_path.rename(model_path)
            console.print(f"[green]✓[/green] Model downloaded: {model_path}")
            return model_path

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to download model: {e}") from e

    def list_models(self) -> list[dict]:
        """List available models with their status.

        Returns:
            List of model info dicts with 'installed' key added
        """
        result = []
        for name, info in AVAILABLE_MODELS.items():
            model_info = {
                "name": name,
                "display_name": info["name"],
                "description": info["description"],
                "size_mb": info["size_mb"],
                "installed": self.is_model_available(name),
            }
            result.append(model_info)
        return result

    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model.

        Args:
            model_name: Name of the model to delete

        Returns:
            True if model was deleted, False if not found
        """
        model_path = self.get_model_path(model_name)
        if model_path and model_path.exists():
            model_path.unlink()
            return True
        return False

    def ensure_model(self, model_name: str = DEFAULT_MODEL) -> Path:
        """Ensure a model is available, downloading if needed.

        Args:
            model_name: Name of the model

        Returns:
            Path to the model file
        """
        model_path = self.get_model_path(model_name)
        if model_path:
            return model_path
        return self.download_model(model_name)
