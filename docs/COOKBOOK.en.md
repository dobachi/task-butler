# Task Butler Cookbook

[日本語](COOKBOOK.md)

A recipe-style guide for common Task Butler workflows.

## Table of Contents

- [Basic Workflow](#basic-workflow)
- [Task Organization](#task-organization)
- [Obsidian Integration](#obsidian-integration)
- [Recurring Tasks](#recurring-tasks)
- [Advanced Usage](#advanced-usage)

---

## Basic Workflow

### Recipe: Add a New Task

**When**: A new piece of work comes up

**Steps**:
```bash
# Simple task
task-butler add "Update documentation"

# With due date and priority
task-butler add "Fix bug" --due 2025-02-01 --priority high

# With project and tags
task-butler add "API design" --project backend --tags "design,important"
```

**Tips**:
- Due dates accept `today`, `tomorrow`, or `YYYY-MM-DD` format
- Priority levels: `lowest`, `low`, `medium`, `high`, `urgent`

---

### Recipe: View Task List

**When**: You want to see what needs to be done

**Steps**:
```bash
# List open tasks
task-butler list

# Table format
task-butler list --table

# Tree format (shows hierarchy)
task-butler list --tree

# High priority only
task-butler list --priority high

# Specific project
task-butler list --project backend
```

**Tips**:
- `task-butler ls` is an alias for `list`
- Use `--all` to include completed tasks

---

### Recipe: Start and Complete a Task

**When**: You're working on a task and finishing it

**Steps**:
```bash
# Check task list for ID
task-butler list

# Start task (status becomes in_progress)
task-butler start abc12345

# Add a note while working
task-butler note abc12345 "Decided on API response format"

# Complete the task
task-butler done abc12345

# Complete with time logged
task-butler done abc12345 --hours 2.5
```

**Tips**:
- Task IDs can be shortened to the first few characters
- If a short ID matches multiple tasks, you'll see a list to choose from

---

### Recipe: View Task Details

**When**: You need full information about a task

**Steps**:
```bash
task-butler show abc12345
```

**Tips**:
- Shows description, notes, created/updated timestamps, and more

---

## Task Organization

### Recipe: Organize by Priority

**When**: You need to identify and focus on important tasks

**Steps**:
```bash
# View urgent tasks
task-butler list --priority urgent

# View high priority and above
task-butler list --priority high
```

**Tips**:
- Priority order: `urgent` > `high` > `medium` > `low` > `lowest`
- Default priority is `medium` if not specified

---

### Recipe: Manage by Project

**When**: You're working on multiple projects simultaneously

**Steps**:
```bash
# List all projects
task-butler projects

# Show tasks for a specific project
task-butler list --project backend

# Add task to a project
task-butler add "DB design" --project backend
```

**Tips**:
- Project names are free-form
- Use consistent names to group related tasks

---

### Recipe: Classify with Tags

**When**: You want to categorize tasks across projects

**Steps**:
```bash
# List all tags
task-butler tags

# Show tasks with a specific tag
task-butler list --tag important

# Add task with multiple tags
task-butler add "Security audit" --tags "security,important,Q1"
```

**Tips**:
- Multiple tags can be specified with commas
- Combine with projects for flexible organization

---

## Obsidian Integration

### Recipe: Start Managing Tasks in Obsidian Vault

**When**: You want to use Obsidian as your main note app alongside Task Butler

**Steps**:
```bash
# 1. Set storage to Vault location
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# 2. Make it permanent (add to .bashrc or .zshrc)
echo 'export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks' >> ~/.bashrc

# 3. Add a task (saved in Vault)
task-butler add "Test Obsidian integration" --due tomorrow
```

**Tips**:
- Can also be configured in `~/.task-butler/config.toml`
- Any folder in the Vault works (e.g., `Tasks/`, `GTD/`)

---

### Recipe: Use Hybrid Format for Obsidian Compatibility

**When**: You want task files to display properly with Obsidian Tasks plugin

**Steps**:
```bash
# Add task in hybrid format
task-butler --format hybrid add "Meeting prep" --due 2025-02-01 --priority high

# Make it permanent via config
cat >> ~/.task-butler/config.toml << 'EOF'
[storage]
format = "hybrid"
EOF
```

**Tips**:
- Hybrid format includes both YAML frontmatter and Obsidian Tasks line
- Tasks are directly viewable and editable in Obsidian Tasks plugin

---

### Recipe: Import Tasks from Daily Notes

**When**: You've written tasks in Obsidian daily notes and want to import them

**Steps**:
```bash
# Import from a single file
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-31.md

# Import from a directory
task-butler obsidian import ~/Documents/MyVault/daily/

# Preview (don't actually create)
task-butler obsidian import ~/Documents/MyVault/daily/ --dry-run

# Update existing duplicates
task-butler obsidian import ~/Documents/MyVault/daily/ --update
```

**Tips**:
- Lines starting with `- [ ]` or `- [x]` are recognized as tasks
- Use `--link` to replace imported lines with wiki links

---

### Recipe: Export Tasks to Daily Notes

**When**: You want to output Task Butler tasks for daily notes

**Steps**:
```bash
# Display all tasks in Obsidian Tasks format
task-butler obsidian export

# Output to file
task-butler obsidian export --output ~/Documents/MyVault/Tasks/all-tasks.md

# Include completed tasks
task-butler obsidian export --include-done
```

**Tips**:
- Export output is compatible with Obsidian Tasks plugin
- Useful for daily/weekly review summaries

---

### Recipe: Detect and Resolve Conflicts

**When**: You've edited tasks in both Obsidian and Task Butler

**Steps**:
```bash
# Detect conflicts
task-butler obsidian check

# Resolve using YAML frontmatter as source of truth
task-butler obsidian resolve --strategy frontmatter

# Resolve using Obsidian Tasks line as source of truth
task-butler obsidian resolve --strategy obsidian

# Preview changes
task-butler obsidian resolve --dry-run
```

**Tips**:
- Run `obsidian check` weekly to catch conflicts early
- Choose which edits to prioritize when conflicts are found

---

## Recurring Tasks

### Recipe: Set Up Weekly Tasks

**When**: You have regular weekly tasks

**Steps**:
```bash
# Weekly review
task-butler add "Weekly review" --recur weekly --priority high

# Bi-weekly task
task-butler add "Bi-weekly meeting prep" --recur "every 2 weeks"
```

**Tips**:
- When a recurring task is completed, the next occurrence is auto-generated
- Supports `daily`, `weekly`, `monthly`, `yearly`

---

### Recipe: Create Periodic Review Tasks

**When**: You need monthly or quarterly review tasks

**Steps**:
```bash
# Monthly report
task-butler add "Monthly report" --recur monthly --priority high --project reports

# Quarterly review
task-butler add "Q1 review" --recur "every 3 months" --tags "review,important"
```

**Tips**:
- Combine with `--due` to fix the start date

---

## Advanced Usage

### Recipe: Manage Task Dependencies

**When**: Task B cannot start until Task A is complete

**Steps**:
```bash
# Create the prerequisite task
task-butler add "Database design"
# → ID: abc12345

# Create the dependent task
task-butler add "API implementation" --depends abc12345
```

**Tips**:
- Dependent tasks show as "blocked" when prerequisites are incomplete
- Multiple dependencies can be specified with commas

---

### Recipe: Break Down Work with Subtasks

**When**: You want to split a large task into smaller pieces

**Steps**:
```bash
# Create parent task
task-butler add "Release preparation"
# → ID: abc12345

# Create subtasks
task-butler add "Run tests" --parent abc12345
task-butler add "Update documentation" --parent abc12345
task-butler add "Deploy" --parent abc12345

# View in tree format
task-butler list --tree
```

**Tips**:
- Subtasks appear hierarchically under the parent
- Subtasks can be completed independently of the parent

---

## Related Documentation

- [README](../README.md) - Basic Task Butler usage
- [Obsidian Integration Guide](OBSIDIAN.en.md) - Detailed Obsidian integration
- [Design Document](DESIGN.en.md) - Internal design details
