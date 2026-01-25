"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
