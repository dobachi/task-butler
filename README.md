# Task Butler

[日本語](README.ja.md) | English

Your digital butler for task management. A CLI tool that helps you manage tasks, prioritize work, and stay organized.

## Features

- **Simple CLI**: Intuitive commands for managing tasks
- **Markdown Storage**: Tasks stored as human-readable Markdown files with YAML frontmatter
- **Hierarchical Tasks**: Create parent/child relationships between tasks
- **Dependencies**: Define task dependencies to track blocking work
- **Recurring Tasks**: Set up daily, weekly, monthly, or yearly recurring tasks
- **Rich Output**: Beautiful terminal output with colors and formatting
- **Git Friendly**: All data stored in plain text, easy to version control

## Installation

### Using uvx from GitHub (Recommended)

```bash
uvx --from git+https://github.com/dobachi/task-butler.git task-butler
```

### From Source

```bash
git clone https://github.com/dobachi/task-butler.git
cd task-butler
uv sync
uv run task-butler
```

## Quick Start

```bash
# Add a task
task-butler add "Write documentation"

# Add a high-priority task with due date
task-butler add "Fix critical bug" --priority urgent --due 2025-01-30

# List all tasks
task-butler list

# Start working on a task
task-butler start abc123

# Mark a task as done
task-butler done abc123
```

## Commands

### Adding Tasks

```bash
# Basic task
task-butler add "Task title"

# With options
task-butler add "Task title" \
  --priority high \           # low, medium, high, urgent
  --due 2025-02-01 \         # Due date (YYYY-MM-DD, today, tomorrow)
  --project "my-project" \   # Project name
  --tags "work,important" \  # Comma-separated tags
  --hours 4 \                # Estimated hours
  --desc "Description"       # Task description

# Subtask (child of another task)
task-butler add "Subtask" --parent abc123

# Task with dependencies
task-butler add "Deploy" --depends abc123,def456

# Recurring task
task-butler add "Weekly review" --recur weekly
task-butler add "Biweekly sync" --recur "every 2 weeks"
```

### Listing Tasks

```bash
# List open tasks (default)
task-butler list

# Include completed tasks
task-butler list --all

# Filter by priority
task-butler list --priority high

# Filter by project
task-butler list --project my-project

# Filter by tag
task-butler list --tag important

# Table format
task-butler list --table

# Tree format (shows hierarchy)
task-butler list --tree

# Alias
task-butler ls
```

### Viewing Task Details

```bash
task-butler show abc123
```

### Changing Task Status

```bash
# Start working on a task
task-butler start abc123

# Mark as done
task-butler done abc123

# Mark as done with time logged
task-butler done abc123 --hours 2.5

# Cancel a task
task-butler cancel abc123
```

### Managing Tasks

```bash
# Add a note
task-butler note abc123 "Progress update: API complete"

# Delete a task
task-butler delete abc123

# Force delete (skip confirmation)
task-butler delete abc123 --force
```

### Other Commands

```bash
# Search tasks
task-butler search "bug"

# List all projects
task-butler projects

# List all tags
task-butler tags

# Show version
task-butler version

# Help
task-butler --help
task-butler add --help
```

## Data Storage

Tasks are stored in `~/.task-butler/tasks/` as Markdown files with YAML frontmatter:

```markdown
---
id: abc12345-1234-5678-9abc-def012345678
title: Implement authentication
status: in_progress
priority: high
created_at: 2025-01-25T10:00:00
updated_at: 2025-01-25T14:30:00
due_date: 2025-02-01T00:00:00
tags:
  - backend
  - security
project: api-v2
estimated_hours: 8
---

Implement JWT-based authentication for the API.

## Notes

- [2025-01-25 10:30] Started research
- [2025-01-25 14:30] JWT library selected
```

### Custom Storage Location

Set via environment variable:
```bash
export TASK_BUTLER_DIR=/path/to/tasks
```

Or via command-line option:
```bash
task-butler --storage-dir /path/to/tasks list
```

## Development

### Setup

```bash
git clone https://github.com/dobachi/task-butler.git
cd task-butler
uv sync --dev
```

### Running Tests

```bash
uv run pytest
```

### Running Tests with Coverage

```bash
uv run pytest --cov=task_butler
```

## Roadmap

- [x] **Phase 1**: Core functionality (MVP)
  - Task CRUD operations
  - Hierarchical tasks
  - Dependencies
  - Recurring tasks
  - CLI interface

- [ ] **Phase 2**: AI Integration
  - Task analysis and prioritization
  - Smart suggestions
  - Daily planning assistance

- [ ] **Phase 3**: Obsidian Integration
  - Use Obsidian vault as storage directory
  - Obsidian Tasks plugin compatibility
  - Bidirectional sync with Obsidian notes

- [ ] **Phase 4**: Advanced Features
  - File watching (auto-import from Markdown)
  - Export (JSON, CSV)
  - Interactive chat mode

- [ ] **Phase 5**: Distribution
  - PyPI publication (`pip install task-butler`, `uvx task-butler`)
  - Standalone executables
  - Extended documentation

## Obsidian Integration (Planned)

Task Butler is designed to work with [Obsidian](https://obsidian.md/) vaults:

### Basic Usage with Obsidian

```bash
# Use Obsidian vault as storage
task-butler --storage-dir ~/Documents/MyVault/Tasks list

# Or set via environment variable
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks
task-butler list
```

### Obsidian Tasks Plugin Compatibility (Planned)

Future versions will support [Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks) format:

```markdown
- [ ] Task name 📅 2025-02-01 ⏳ 2025-01-25 🔺
```

Features planned:
- Export tasks in Obsidian Tasks format
- Import tasks from Obsidian Tasks format
- Emoji-based priority and date indicators

## License

MIT

## Author

dobachi
