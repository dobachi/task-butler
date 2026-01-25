"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def tmp_path():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
