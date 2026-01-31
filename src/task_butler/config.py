"""Configuration management for Task Butler."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

StorageFormat = Literal["frontmatter", "hybrid"]
OrganizationMethod = Literal["flat", "kanban"]


class Config:
    """Task Butler configuration.

    Configuration is loaded with the following precedence (highest to lowest):
    1. CLI options (passed directly to methods)
    2. Environment variables (TASK_BUTLER_FORMAT)
    3. Config file (~/.task-butler/config.toml)
    4. Default values
    """

    DEFAULT_FORMAT: StorageFormat = "frontmatter"
    CONFIG_DIR = Path.home() / ".task-butler"
    CONFIG_PATH = CONFIG_DIR / "config.toml"

    def __init__(self) -> None:
        """Initialize configuration."""
        self._file_config = self._load_config_file()

    def _load_config_file(self) -> dict:
        """Load configuration from file if it exists."""
        if not self.CONFIG_PATH.exists():
            return {}
        try:
            with open(self.CONFIG_PATH, "rb") as f:
                return tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def get_format(self, cli_format: str | None = None) -> StorageFormat:
        """Get storage format with precedence: CLI > env > file > default.

        Args:
            cli_format: Format specified via CLI option (highest priority)

        Returns:
            The storage format to use ("frontmatter" or "hybrid")
        """
        # CLI option takes highest priority
        if cli_format:
            if cli_format in ("frontmatter", "hybrid"):
                return cli_format  # type: ignore
            # Invalid format, fall through to other sources

        # Environment variable
        env_format = os.environ.get("TASK_BUTLER_FORMAT")
        if env_format in ("frontmatter", "hybrid"):
            return env_format  # type: ignore

        # Config file
        file_format = self._file_config.get("storage", {}).get("format")
        if file_format in ("frontmatter", "hybrid"):
            return file_format

        return self.DEFAULT_FORMAT

    def get_storage_dir(self, cli_dir: Path | None = None) -> Path:
        """Get storage directory with precedence: CLI > env > file > default.

        Args:
            cli_dir: Directory specified via CLI option (highest priority)

        Returns:
            The storage directory to use
        """
        if cli_dir:
            return cli_dir

        env_dir = os.environ.get("TASK_BUTLER_DIR")
        if env_dir:
            return Path(env_dir)

        # Config file
        file_dir = self._file_config.get("storage", {}).get("dir")
        if file_dir:
            return Path(file_dir)

        return self.CONFIG_DIR / "tasks"

    def get_value(self, key: str) -> str | None:
        """Get a configuration value by key.

        Args:
            key: Config key in dot notation (e.g., "storage.format", "organization.kanban.backlog")

        Returns:
            The value if set, None otherwise
        """
        parts = key.split(".")
        if len(parts) == 2:
            section, name = parts
            return self._file_config.get(section, {}).get(name)
        elif len(parts) == 3:
            section, subsection, name = parts
            return self._file_config.get(section, {}).get(subsection, {}).get(name)
        return None

    def set_value(self, key: str, value: str) -> None:
        """Set a configuration value.

        Args:
            key: Config key in dot notation (e.g., "storage.format", "organization.kanban.backlog")
            value: Value to set

        Raises:
            ValueError: If key is invalid or value is not allowed
        """
        parts = key.split(".")
        if len(parts) not in (2, 3):
            raise ValueError(f"Invalid key: {key}")

        # Validate and set value
        if len(parts) == 2:
            section, name = parts
            self._validate_and_set_2level(section, name, value)
        else:
            section, subsection, name = parts
            self._validate_and_set_3level(section, subsection, name, value)

    def _validate_and_set_2level(self, section: str, name: str, value: str) -> None:
        """Validate and set a 2-level config key."""
        if section == "storage":
            if name == "format":
                if value not in ("frontmatter", "hybrid"):
                    raise ValueError(f"Invalid format: {value}. Must be 'frontmatter' or 'hybrid'")
            elif name == "dir":
                pass  # Any path is valid
            else:
                raise ValueError(f"Unknown storage key: {name}")
        elif section == "obsidian":
            if name == "vault_root":
                pass  # Any path is valid
            else:
                raise ValueError(f"Unknown obsidian key: {name}")
        elif section == "organization":
            if name == "method":
                if value not in ("flat", "kanban"):
                    raise ValueError(f"Invalid method: {value}. Must be 'flat' or 'kanban'")
            else:
                raise ValueError(f"Unknown organization key: {name}")
        else:
            raise ValueError(f"Unknown section: {section}")

        # Update in-memory config
        if section not in self._file_config:
            self._file_config[section] = {}
        self._file_config[section][name] = value

    def _validate_and_set_3level(
        self, section: str, subsection: str, name: str, value: str
    ) -> None:
        """Validate and set a 3-level config key."""
        if section == "organization" and subsection == "kanban":
            if name in ("backlog", "in_progress", "done", "cancelled"):
                pass  # Any directory name is valid
            else:
                raise ValueError(f"Unknown organization.kanban key: {name}")
        else:
            raise ValueError(f"Unknown section: {section}.{subsection}")

        # Update in-memory config
        if section not in self._file_config:
            self._file_config[section] = {}
        if subsection not in self._file_config[section]:
            self._file_config[section][subsection] = {}
        self._file_config[section][subsection][name] = value

    def get_all(self) -> dict:
        """Get all configuration values.

        Returns:
            A copy of the configuration dictionary
        """
        return self._file_config.copy()

    def get_vault_root(self, cli_vault_root: Path | None = None) -> Path | None:
        """Get Obsidian vault root with precedence: CLI > file > None.

        Args:
            cli_vault_root: Vault root specified via CLI option (highest priority)

        Returns:
            The vault root path or None if not set
        """
        if cli_vault_root:
            return cli_vault_root

        file_vault_root = self._file_config.get("obsidian", {}).get("vault_root")
        if file_vault_root:
            return Path(file_vault_root)

        return None

    def get_organization_method(self) -> OrganizationMethod:
        """Get organization method: 'flat' or 'kanban'.

        Returns:
            The organization method to use
        """
        method = self._file_config.get("organization", {}).get("method", "flat")
        if method in ("flat", "kanban"):
            return method  # type: ignore
        return "flat"

    def get_kanban_dirs(self) -> dict[str, str]:
        """Get Kanban directory names.

        Returns:
            Dictionary mapping status to directory name
        """
        defaults = {
            "backlog": "Backlog",
            "in_progress": "InProgress",
            "done": "Done",
            "cancelled": "Cancelled",
        }
        kanban_config = self._file_config.get("organization", {}).get("kanban", {})
        return {**defaults, **kanban_config}

    def save(self) -> None:
        """Save configuration to file."""
        import tomli_w

        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, "wb") as f:
            tomli_w.dump(self._file_config, f)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance (lazy initialization)."""
    global _config
    if _config is None:
        _config = Config()
    return _config
