"""Task Butler - A task management tool that helps prioritize and recommend actions."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("markdown-task-butler")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Development mode
