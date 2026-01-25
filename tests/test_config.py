"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest

from task_butler.config import Config, get_config


class TestConfig:
    """Tests for Config class."""

    @pytest.fixture
    def config_dir(self, tmp_path):
        """Create a temporary config directory."""
        return tmp_path / ".task-butler"

    @pytest.fixture
    def config(self, config_dir, monkeypatch):
        """Create a Config instance with temporary directory."""
        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_dir / "config.toml")
        return Config()

    def test_default_format(self, config):
        """Test default format is frontmatter."""
        assert config.get_format() == "frontmatter"

    def test_cli_format_takes_precedence(self, config, monkeypatch):
        """Test CLI format takes precedence over other sources."""
        # Set environment variable
        monkeypatch.setenv("TASK_BUTLER_FORMAT", "frontmatter")

        # CLI option should win
        assert config.get_format(cli_format="hybrid") == "hybrid"

    def test_env_format_precedence(self, config, monkeypatch):
        """Test environment variable format precedence."""
        monkeypatch.setenv("TASK_BUTLER_FORMAT", "hybrid")

        assert config.get_format() == "hybrid"

    def test_file_config_format(self, config_dir, monkeypatch):
        """Test file config format."""
        # Create config file
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text('[storage]\nformat = "hybrid"\n')

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_path)

        # Clear environment variable
        monkeypatch.delenv("TASK_BUTLER_FORMAT", raising=False)

        new_config = Config()
        assert new_config.get_format() == "hybrid"

    def test_invalid_format_fallback(self, config, monkeypatch):
        """Test invalid format falls back to default."""
        monkeypatch.setenv("TASK_BUTLER_FORMAT", "invalid")

        # Should fall back to default
        assert config.get_format() == "frontmatter"

    def test_cli_invalid_format_fallback(self, config, monkeypatch):
        """Test invalid CLI format falls back to env or default."""
        monkeypatch.setenv("TASK_BUTLER_FORMAT", "hybrid")

        # Invalid CLI format should fall back to env
        assert config.get_format(cli_format="invalid") == "hybrid"

    def test_storage_dir_default(self, config):
        """Test default storage directory."""
        storage_dir = config.get_storage_dir()
        assert storage_dir == config.CONFIG_DIR / "tasks"

    def test_storage_dir_cli(self, config, tmp_path):
        """Test CLI storage directory takes precedence."""
        cli_dir = tmp_path / "custom"
        storage_dir = config.get_storage_dir(cli_dir=cli_dir)
        assert storage_dir == cli_dir

    def test_storage_dir_env(self, config, tmp_path, monkeypatch):
        """Test environment variable storage directory."""
        env_dir = tmp_path / "env-dir"
        monkeypatch.setenv("TASK_BUTLER_DIR", str(env_dir))

        storage_dir = config.get_storage_dir()
        assert storage_dir == env_dir

    def test_config_file_not_exists(self, config_dir, monkeypatch):
        """Test config with non-existent file."""
        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_dir / "config.toml")
        monkeypatch.delenv("TASK_BUTLER_FORMAT", raising=False)

        new_config = Config()
        assert new_config.get_format() == "frontmatter"

    def test_config_file_invalid_toml(self, config_dir, monkeypatch):
        """Test config with invalid TOML file."""
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text("invalid toml [[[")

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_path)
        monkeypatch.delenv("TASK_BUTLER_FORMAT", raising=False)

        # Should not raise, just use defaults
        new_config = Config()
        assert new_config.get_format() == "frontmatter"


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_returns_config(self, monkeypatch):
        """Test get_config returns a Config instance."""
        # Reset global config
        import task_butler.config
        monkeypatch.setattr(task_butler.config, "_config", None)

        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_singleton(self, monkeypatch):
        """Test get_config returns the same instance."""
        import task_butler.config
        monkeypatch.setattr(task_butler.config, "_config", None)

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
