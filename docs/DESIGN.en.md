# Task Butler - Design Document

[日本語](DESIGN.md) | English

## Overview

A "butler" tool that helps users manage tasks, prioritize work, and suggest recommended actions.

## Decisions

| Item | Decision |
|------|----------|
| Project Name | task-butler |
| Input Method | CLI dialog + Markdown file editing |
| AI Method | llama-cpp-python + auto model download on first run (Phase 2) |
| Language | Python 3.11+ (uv managed, uvx execution supported) |
| Hierarchy | Free hierarchical structure (recursive parent-child relationships) |
| Dependencies | Explicitly managed in data model |
| Recurring Tasks | Implemented from Phase 1 |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      User Interface                      │
├─────────────────┬───────────────────────────────────────┤
│   CLI (typer)   │   Markdown File Watcher (Phase 3)     │
└────────┬────────┴───────────────────┬───────────────────┘
         │                            │
         ▼                            ▼
┌─────────────────────────────────────────────────────────┐
│                     Core Engine                          │
├─────────────────────────────────────────────────────────┤
│  TaskManager  │  RecurrenceGenerator  │  (AI Phase 2)   │
└───────────────┴─────────┬─────────────┴─────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│   Repository    │ │MarkdownStore│ │ Data Models  │
│   (CRUD API)    │ │ (File I/O)  │ │  (Pydantic)  │
└─────────────────┘ └──────────────┘ └──────────────┘
```

## Directory Structure

```
task-butler/
├── pyproject.toml          # Project config & dependencies
├── README.md               # Usage guide
├── src/
│   └── task_butler/
│       ├── __init__.py     # Version info
│       ├── models/         # Data models
│       │   ├── task.py     # Task, Note, RecurrenceRule
│       │   └── enums.py    # Status, Priority, Frequency
│       ├── storage/        # Storage layer
│       │   ├── markdown.py # Markdown file I/O
│       │   └── repository.py # CRUD operations
│       ├── core/           # Business logic
│       │   ├── task_manager.py # Task management
│       │   └── recurrence.py   # Recurring task generation
│       ├── cli/            # CLI interface
│       │   ├── main.py     # Entry point
│       │   └── commands/   # Command implementations
│       └── ai/             # AI features (Phase 2)
├── tests/                  # Test code
└── docs/                   # Documentation
    └── DESIGN.md          # This design doc
```

## Data Models

### Task

```python
class Task(BaseModel):
    id: str                          # UUID
    title: str                       # Task name
    description: str = ""            # Detailed description
    status: Status = "pending"       # pending/in_progress/done/cancelled
    priority: Priority = "medium"    # low/medium/high/urgent

    # Time-related
    due_date: datetime | None        # Due date
    estimated_hours: float | None    # Estimated hours
    actual_hours: float | None       # Actual hours

    # Classification
    tags: list[str] = []             # Tags
    project: str | None              # Project name

    # Hierarchy & Dependencies
    parent_id: str | None            # Parent task ID
    dependencies: list[str] = []     # Dependent task IDs

    # Recurrence
    recurrence: RecurrenceRule | None # Recurrence rule
    recurrence_parent_id: str | None  # Source task ID for recurrence

    # Metadata
    created_at: datetime
    updated_at: datetime
    notes: list[Note] = []
```

### RecurrenceRule

```python
class RecurrenceRule(BaseModel):
    frequency: Frequency    # daily/weekly/monthly/yearly
    interval: int = 1       # Interval (2 = every other week, etc.)
    days_of_week: list[int] | None  # 0=Monday to 6=Sunday
    day_of_month: int | None        # Day of month
    end_date: datetime | None       # End date
```

## Markdown Format

Tasks are saved as Markdown files with YAML frontmatter:

```markdown
---
id: abc12345-1234-5678-9abc-def012345678
title: Implement API endpoint
status: pending
priority: high
created_at: 2025-01-25T10:00:00
updated_at: 2025-01-25T10:00:00
due_date: 2025-02-01T00:00:00
tags:
  - development
  - backend
project: my-project
estimated_hours: 4
---

Implement user authentication API.

## Notes

- [2025-01-25 10:30] Initial research complete. Planning to use JWT.
- [2025-01-25 14:00] Endpoint design complete.
```

## CLI Commands

### Basic Operations

```bash
# Add task
task-butler add "New task" --priority high --due 2025-02-01
task-butler add "Subtask" --parent <parent-id>
task-butler add "Dependent task" --depends <task-id>
task-butler add "Weekly review" --recur weekly

# List tasks
task-butler list                    # Open tasks only
task-butler list --all              # Include completed
task-butler list --priority high    # Filter by priority
task-butler list --project myproj   # Filter by project
task-butler list --table            # Table format
task-butler list --tree             # Tree format (hierarchy)

# Show task details
task-butler show <task-id>

# Change status
task-butler start <task-id>         # Start work
task-butler done <task-id>          # Complete
task-butler done <task-id> -h 2.5   # Log actual hours
task-butler cancel <task-id>        # Cancel

# Add note
task-butler note <task-id> "Progress note"

# Delete
task-butler delete <task-id>        # With confirmation
task-butler delete <task-id> -f     # Force delete

# Search
task-butler search "keyword"

# Others
task-butler projects                # List projects
task-butler tags                    # List tags
task-butler version                 # Show version
```

### Aliases

- Can be run as `task-butler` or `tb`

## Dependency Management

- Tasks can depend on other tasks (`--depends` option)
- A task cannot be started until its dependencies are completed
- Tasks with dependents cannot be deleted

## Recurring Tasks

- Set recurrence rules with `--recur` option
- Supported patterns: `daily`, `weekly`, `monthly`, `yearly`, `every N days/weeks/months`
- Next instance is auto-generated when an instance is completed

## Implementation Status

### Phase 1: Foundation (MVP) ✅

- [x] Data model implementation
- [x] Markdown storage implementation
- [x] Basic CLI (add, list, show, start, done, cancel, delete, note)
- [x] Hierarchical structure (parent-child)
- [x] Dependency management
- [x] Recurring tasks
- [x] uvx execution support
- [x] Test implementation

### Phase 2: AI Integration (Not Implemented)

- [ ] llama-cpp-python + auto model download
- [ ] Task analysis (analyze)
- [ ] Suggestion feature (suggest)
- [ ] Planning feature (plan)

### Phase 3: Advanced Features (Not Implemented)

- [ ] File watching (watchdog)
- [ ] Export (JSON, CSV)
- [ ] Interactive mode (chat)

### Phase 4: Distribution (Not Implemented)

- [ ] Executable packaging (PyInstaller/Nuitka)
- [ ] Extended documentation

## Technology Stack

| Area | Technology | Reason |
|------|------------|--------|
| Language | Python 3.11+ | Wide compatibility |
| Package Manager | uv | Fast, modern |
| CLI | typer | Type-safe, auto-complete, help generation |
| Data Validation | pydantic | Robust validation |
| Output Formatting | rich | Beautiful terminal output |
| Storage | Markdown + YAML frontmatter | Human-readable, Git-friendly |
| Testing | pytest | Standard Python testing framework |
