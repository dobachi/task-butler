# Obsidian Integration Guide

[日本語](OBSIDIAN.md)

This guide explains how to integrate Task Butler with the Obsidian Tasks plugin.

## Table of Contents

- [Overview](#overview)
- [Obsidian Tasks Format](#obsidian-tasks-format)
- [Basic Usage](#basic-usage)
- [Storage Format Option (--format)](#storage-format-option---format)
- [Command Reference](#command-reference)
- [Date Fields](#date-fields)
- [Priority Levels](#priority-levels)
- [Conflict Detection and Resolution](#conflict-detection-and-resolution)
- [Workflow Examples](#workflow-examples)
- [Troubleshooting](#troubleshooting)

## Overview

Task Butler supports a format compatible with the [Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks) plugin. This enables:

- **Bidirectional Integration**: Export from Task Butler to Obsidian format, import from Obsidian to Task Butler
- **Emoji-based Metadata**: Express priority, dates, and recurrence using emojis
- **Conflict Detection**: Detect and fix inconsistencies between YAML frontmatter and Obsidian Tasks lines

## Obsidian Tasks Format

The Obsidian Tasks plugin adds metadata to Markdown checkboxes using emojis:

```markdown
- [ ] Task name 🔺 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-15 🔁 every week #work #important
- [x] Completed task ✅ 2025-01-20
```

### Emoji Meanings

| Emoji | Meaning | Description |
|-------|---------|-------------|
| 📅 | Due Date | Task deadline |
| ⏳ | Scheduled Date | Day planned to work on the task |
| 🛫 | Start Date | Day when work can begin |
| ➕ | Created Date | Day task was created |
| ✅ | Done Date | Day task was completed |
| 🔁 | Recurrence | Recurrence rule |

### Priority Emojis

| Emoji | Obsidian Tasks | Task Butler |
|-------|---------------|-------------|
| 🔺 | Highest | urgent |
| ⏫ | High | high |
| 🔼 | Medium | medium |
| 🔽 | Low | low |
| ⏬ | Lowest | lowest |

## Basic Usage

### Using Obsidian Vault as Storage

Set Task Butler's storage directory inside your Obsidian Vault to access tasks from both tools:

```bash
# Set via environment variable (recommended)
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# Or specify with option each time
task-butler --storage-dir ~/Documents/MyVault/Tasks list
```

### Creating Tasks (with new date fields)

```bash
# Create task with due, scheduled, and start dates
task-butler add "Prepare for important meeting" \
  --due 2025-02-01 \
  --scheduled 2025-01-25 \
  --start 2025-01-20 \
  --priority high \
  --tags "work,meeting"
```

Output:
```
✓ Created task: Prepare for important meeting
  ID: abc12345
  Due: 2025-02-01
  Scheduled: 2025-01-25
  Start: 2025-01-20
```

### Export to Obsidian Format

```bash
# Display all tasks in Obsidian Tasks format
task-butler obsidian export

# Output to file
task-butler obsidian export --output tasks.md

# Include completed tasks
task-butler obsidian export --include-done
```

Example output:
```markdown
- [ ] Prepare for important meeting ⏫ 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-25 #work #meeting
- [ ] Write weekly report 🔼 📅 2025-01-31 🔁 every week #work
- [x] Fix bug ✅ 2025-01-24 #dev
```

### Display Single Task in Obsidian Format

```bash
# Display a task in Obsidian format by ID
task-butler obsidian format abc12345
```

Copy and paste into your Obsidian notes.

### Import from Obsidian

```bash
# Import from a single file
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-25.md

# Bulk import from directory
task-butler obsidian import ~/Documents/MyVault/daily/

# Recursive import including subdirectories
task-butler obsidian import ~/Documents/MyVault/ --recursive

# Preview (don't actually create)
task-butler obsidian import ~/Documents/MyVault/daily/ --dry-run

# Update existing tasks on duplicate
task-butler obsidian import ~/Documents/MyVault/daily/ --update

# Interactive duplicate handling
task-butler obsidian import ~/Documents/MyVault/daily/ --interactive

# Replace source lines with wiki links
task-butler obsidian import ~/Documents/MyVault/daily/ --link

# Use embed format for links
task-butler obsidian import ~/Documents/MyVault/daily/ --link --link-format embed
```

## Storage Format Option (--format)

### Overview

The `--format` option controls the **storage format** of task files.

```bash
# Save in hybrid format (YAML frontmatter + Obsidian Tasks line)
task-butler --format hybrid add "Task name"

# Save in frontmatter format (default, YAML frontmatter only)
task-butler --format frontmatter add "Task name"
```

### Important: Impact on Reading and Display

The `--format` option only affects **write operations**:

| Operation | --format Impact |
|-----------|----------------|
| **Save (add, done, start, etc.)** | ✅ Affected |
| **Read (list, show, etc.)** | ❌ Not affected |
| **Display format** | ❌ Not affected |

Read behavior:
- Data is always read from **YAML frontmatter** (source of truth)
- Obsidian Tasks lines in the file body are stripped to prevent duplication
- Using `--format hybrid` does NOT change the display format of `list` or `show`

### Displaying in Obsidian Format

If you need Obsidian Tasks format output from `list` or `show`, use the dedicated commands:

```bash
# Display all tasks in Obsidian format
task-butler obsidian export

# Display a single task in Obsidian format
task-butler obsidian format abc12345
```

### Configuration

Storage format is determined in the following order of precedence:

1. **CLI option**: `--format hybrid`
2. **Environment variable**: `TASK_BUTLER_FORMAT=hybrid`
3. **Config file**: `~/.task-butler/config.toml`

```toml
# ~/.task-butler/config.toml
[storage]
format = "hybrid"  # "frontmatter" or "hybrid"
```

## Command Reference

### New Options for `task-butler add`

```bash
task-butler add "task name" [options]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--due` | `-d` | Due date (📅) |
| `--scheduled` | `-s` | Scheduled date (⏳) - when to work on it |
| `--start` | - | Start date (🛫) - when work can begin |
| `--priority` | `-p` | Priority (lowest, low, medium, high, urgent) |

### `task-butler obsidian` Subcommands

#### `obsidian export`

Export tasks in Obsidian Tasks format.

```bash
task-butler obsidian export [options]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--format` | `-f` | Output format: `tasks` (default) or `frontmatter` |
| `--output` | `-o` | Output file path (stdout if omitted) |
| `--include-done` | - | Include completed tasks |

#### `obsidian import`

Import tasks from an Obsidian Markdown file or directory to Task Butler.

```bash
task-butler obsidian import <path> [options]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--recursive` | `-r` | Include subdirectories (when path is a directory) |
| `--pattern` | `-p` | File pattern (default: `*.md`) |
| `--skip` | - | Skip duplicate tasks (default) |
| `--update` | - | Update existing tasks on duplicate |
| `--force` | - | Create new task even if duplicate exists |
| `--interactive` | `-i` | Prompt for each duplicate |
| `--dry-run` | `-n` | Preview only, don't actually create |
| `--link` | `-l` | Replace source lines with wiki links |
| `--link-format` | - | Link format: `wiki` (default) or `embed` |

**About Link Replacement Mode:**

When using the `--link` option, the original task lines in your Obsidian notes are replaced with wiki links after import. This prevents duplicate display in the Obsidian Tasks plugin and enables centralized task management.

Before import:
```markdown
- [ ] Meeting prep 📅 2025-02-01
```

After import (with `--link`):
```markdown
- [[Tasks/abc12345_Meeting_prep|Meeting prep]]
```

**Notes:**
- Must be run inside an Obsidian Vault (where `.obsidian` directory exists)
- If Task Butler storage (`--storage-dir`) is outside the vault, links may not work correctly
- Use `--link-format embed` to generate embed links (`![[...]]`)

**About Duplicate Detection:**

Task duplication is determined by the combination of "title" and "due date". When a task with the same title and due date already exists, it is handled according to the specified option.

- `--skip` (default): Skip the duplicate and proceed to the next task
- `--update`: Update the existing task's priority, dates, and tags
- `--force`: Ignore duplicate and create as a new task
- `--interactive`: Choose `[s]kip, [u]pdate, [f]orce, [a]ll skip, [A]ll update` for each duplicate

**Directory Import Examples:**

```bash
# Import all md files in the daily directory
task-butler obsidian import ~/Vault/daily/

# Only files matching daily-*.md pattern
task-butler obsidian import ~/Vault/daily/ --pattern "daily-*.md"

# Recursively import entire Vault (preview)
task-butler obsidian import ~/Vault/ --recursive --dry-run
```

#### `obsidian check`

Detect conflicts between YAML frontmatter and Obsidian Tasks lines.

```bash
task-butler obsidian check
```

Example output:
```
⚠ Conflict in task abc12345: Prepare for important meeting
  status: frontmatter=pending, obsidian_line=done
  priority: frontmatter=high, obsidian_line=urgent

Found 1 task(s) with conflicts
Use 'task-butler obsidian resolve' to fix conflicts
```

#### `obsidian resolve`

Resolve detected conflicts.

```bash
task-butler obsidian resolve [options]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--strategy` | `-s` | Resolution strategy: `frontmatter` (default) or `obsidian` |
| `--task` | `-t` | Resolve only specific task ID |
| `--dry-run` | `-n` | Preview only, don't actually change |

Resolution strategies:
- `frontmatter`: Use YAML frontmatter values as source of truth, update Obsidian Tasks line
- `obsidian`: Use Obsidian Tasks line values as source of truth, update frontmatter

#### `obsidian format`

Display a single task in Obsidian Tasks format.

```bash
task-butler obsidian format <task-id>
```

## Date Fields

Task Butler supports four types of date fields:

### Due Date 📅

The task deadline. The task must be completed by this date.

```bash
task-butler add "Submit report" --due 2025-02-01
```

### Scheduled Date ⏳

The day you plan to work on the task. "I'll do this on this day."

```bash
task-butler add "Create materials" --scheduled 2025-01-25
```

### Start Date 🛫

The day when work can begin. Used for tasks that cannot (or should not) be started before this date.

```bash
task-butler add "Implement new feature" --start 2025-01-20
```

### Completed At ✅

Automatically set when the task is completed. No manual setting required.

```bash
task-butler done abc12345
# → completed_at is automatically set to current datetime
```

### Date Combination Example

```bash
# Can start Jan 20, scheduled for Jan 25, due Feb 1
task-butler add "Write project plan" \
  --start 2025-01-20 \
  --scheduled 2025-01-25 \
  --due 2025-02-01
```

Obsidian format:
```markdown
- [ ] Write project plan 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-25
```

## Priority Levels

Task Butler supports 5 priority levels:

| Level | CLI Value | Emoji | Description |
|-------|-----------|-------|-------------|
| Highest | `urgent` | 🔺 | Needs immediate attention |
| High | `high` | ⏫ | Priority handling |
| Medium | `medium` | 🔼 | Normal priority (default) |
| Low | `low` | 🔽 | When you have time |
| Lowest | `lowest` | ⏬ | Someday/maybe |

```bash
# Lowest priority task
task-butler add "Someday idea" --priority lowest
```

**Note**: `medium` priority omits the emoji in Obsidian format (as it's the default).

## Conflict Detection and Resolution

### Why Conflicts Occur

Task Butler saves tasks as Markdown files with YAML frontmatter. When using hybrid format, the file body may also contain an Obsidian Tasks format line:

```markdown
---
id: abc12345
title: Meeting prep
status: pending
priority: high
due_date: 2025-02-01T00:00:00
---

- [ ] Meeting prep ⏫ 📅 2025-02-01

Detailed description...
```

When you edit a task directly in Obsidian (clicking the checkbox, etc.), the Obsidian Tasks line is updated but the YAML frontmatter is not. This causes conflicts.

### Check for Conflicts

```bash
task-butler obsidian check
```

### Resolve Conflicts

```bash
# Use YAML frontmatter as source of truth (recommended)
task-butler obsidian resolve --strategy frontmatter

# Use Obsidian Tasks line as source of truth
task-butler obsidian resolve --strategy obsidian

# Resolve only specific task
task-butler obsidian resolve --task abc12345 --strategy frontmatter

# Preview
task-butler obsidian resolve --dry-run
```

## Workflow Examples

### Workflow 1: Task Butler-Centric Operation

1. Set Task Butler storage inside Obsidian Vault
2. Manage tasks with Task Butler CLI
3. View and add notes in Obsidian
4. Periodically generate Obsidian Tasks format summaries

```bash
# Setup
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# Daily operations
task-butler add "Implement new feature" --due 2025-02-01 --priority high
task-butler list
task-butler start abc12345
task-butler done abc12345

# Weekly: Generate summary
task-butler obsidian export --output ~/Documents/MyVault/Tasks/summary.md
```

### Workflow 2: Obsidian-Centric Operation

1. Record tasks in Obsidian daily notes (Obsidian Tasks format)
2. Periodically import to Task Butler
3. Use Task Butler for analysis and reporting

```bash
# Bulk import from daily notes directory (skip duplicates)
task-butler obsidian import ~/Documents/MyVault/daily/

# Or import specific file only
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-25.md

# Update existing tasks instead of skipping
task-butler obsidian import ~/Documents/MyVault/daily/ --update

# View task list
task-butler list

# View by project
task-butler list --project my-project
```

### Workflow 3: Hybrid Operation

1. Edit tasks from both tools
2. Periodically check for conflicts
3. Resolve as needed

```bash
# Check conflicts (daily)
task-butler obsidian check

# Resolve if any
task-butler obsidian resolve --strategy frontmatter
```

## Troubleshooting

### Q: Some tasks aren't imported

**A**: Lines must start with `- [ ]` or `- [x]` to be recognized as Obsidian Tasks format.

Correct format:
```markdown
- [ ] Task name
- [x] Completed task
```

Not recognized:
```markdown
* [ ] Task name    # Use - not *
- [] Task name     # Space required
  - [ ] Task name  # Indented is OK (but hierarchy info is lost)
```

### Q: Priority isn't converted correctly

**A**: Task Butler's 5-level priority maps to Obsidian Tasks as follows:

- `urgent` ↔ 🔺 (Highest)
- `high` ↔ ⏫ (High)
- `medium` ↔ 🔼 (Medium) *optional
- `low` ↔ 🔽 (Low)
- `lowest` ↔ ⏬ (Lowest)

### Q: Recurring tasks don't work properly

**A**: Currently supported recurrence formats:

- `daily`, `weekly`, `monthly`, `yearly`
- `every day`, `every week`, `every month`, `every year`
- `every N days`, `every N weeks`, `every N months`, `every N years`

Complex recurrence (like "every Monday") is not currently supported.

### Q: Edits in Obsidian not reflected in Task Butler

**A**: When editing directly in Obsidian, YAML frontmatter is not updated. Sync with these steps:

```bash
# Check conflicts
task-butler obsidian check

# Apply Obsidian edits
task-butler obsidian resolve --strategy obsidian
```

### Q: File encoding error

**A**: Task Butler uses UTF-8 encoding. Make sure your files are saved as UTF-8.

## Related Documentation

- [README](../README.md) - Basic Task Butler usage
- [DESIGN](DESIGN.en.md) - Design documentation
- [Obsidian Tasks Official Documentation](https://publish.obsidian.md/tasks/)
