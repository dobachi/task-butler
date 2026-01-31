"""Tests for configuration module."""

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

    def test_get_value(self, config_dir, monkeypatch):
        """Test get_value method."""
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text('[storage]\nformat = "hybrid"\n')

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_path)

        new_config = Config()
        assert new_config.get_value("storage.format") == "hybrid"
        assert new_config.get_value("storage.dir") is None
        assert new_config.get_value("invalid") is None

    def test_set_value_format(self, config):
        """Test setting format value."""
        config.set_value("storage.format", "hybrid")
        assert config.get_value("storage.format") == "hybrid"

    def test_set_value_dir(self, config):
        """Test setting dir value."""
        config.set_value("storage.dir", "/custom/path")
        assert config.get_value("storage.dir") == "/custom/path"

    def test_set_value_invalid_format(self, config):
        """Test setting invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid format"):
            config.set_value("storage.format", "invalid")

    def test_set_value_invalid_key(self, config):
        """Test setting invalid key raises error."""
        with pytest.raises(ValueError, match="Unknown section"):
            config.set_value("invalid.key", "value")

    def test_set_value_unknown_storage_key(self, config):
        """Test setting unknown storage key raises error."""
        with pytest.raises(ValueError, match="Unknown storage key"):
            config.set_value("storage.unknown", "value")

    def test_set_value_invalid_key_format(self, config):
        """Test setting key with wrong format raises error."""
        with pytest.raises(ValueError, match="Invalid key"):
            config.set_value("notsection", "value")

    def test_get_all(self, config):
        """Test get_all method."""
        config.set_value("storage.format", "hybrid")
        config.set_value("storage.dir", "/path")

        all_config = config.get_all()
        assert all_config == {"storage": {"format": "hybrid", "dir": "/path"}}

    def test_save_and_reload(self, config_dir, monkeypatch):
        """Test saving and reloading config."""
        config_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_dir / "config.toml")

        config = Config()
        config.set_value("storage.format", "hybrid")
        config.save()

        # Verify file was created
        assert (config_dir / "config.toml").exists()

        # Reload
        config2 = Config()
        assert config2.get_value("storage.format") == "hybrid"

    def test_storage_dir_from_file(self, config_dir, monkeypatch):
        """Test storage dir from file config."""
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text('[storage]\ndir = "/custom/tasks"\n')

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_path)
        monkeypatch.delenv("TASK_BUTLER_DIR", raising=False)

        from pathlib import Path

        new_config = Config()
        assert new_config.get_storage_dir() == Path("/custom/tasks")

    def test_set_value_vault_root(self, config):
        """Test setting vault_root value."""
        config.set_value("obsidian.vault_root", "/path/to/vault")
        assert config.get_value("obsidian.vault_root") == "/path/to/vault"

    def test_set_value_unknown_obsidian_key(self, config):
        """Test setting unknown obsidian key raises error."""
        with pytest.raises(ValueError, match="Unknown obsidian key"):
            config.set_value("obsidian.unknown", "value")

    def test_get_vault_root_cli(self, config):
        """Test CLI vault root takes precedence."""
        from pathlib import Path

        config.set_value("obsidian.vault_root", "/config/vault")
        cli_path = Path("/cli/vault")
        assert config.get_vault_root(cli_path) == cli_path

    def test_get_vault_root_from_file(self, config_dir, monkeypatch):
        """Test vault root from file config."""
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
        config_path.write_text('[obsidian]\nvault_root = "/my/vault"\n')

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_path)

        from pathlib import Path

        new_config = Config()
        assert new_config.get_vault_root() == Path("/my/vault")

    def test_get_vault_root_none(self, config):
        """Test vault root returns None when not set."""
        assert config.get_vault_root() is None


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
