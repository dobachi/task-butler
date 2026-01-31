#!/bin/bash
# Bash completion for task-butler with task title display
# Install: source this file or add to ~/.bashrc

_task_butler_get_tasks() {
    # Get task list with IDs and titles
    task-butler list --all 2>/dev/null | grep -E '^\s*[○◐●✗]' | sed 's/^[[:space:]]*//' || true
}

_task_butler_get_open_tasks() {
    # Get only open (pending/in_progress) tasks
    task-butler list 2>/dev/null | grep -E '^\s*[○◐]' | sed 's/^[[:space:]]*//' || true
}

_task_butler_complete_task_id() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local tasks="$1"

    if [[ -z "$tasks" ]]; then
        return
    fi

    # Extract task IDs for completion (8-char hex IDs)
    local ids=$(echo "$tasks" | grep -oE '[a-f0-9]{8}')

    # Build completion with "ID -- Title" format for display
    local completions=()
    while IFS= read -r line; do
        local id=$(echo "$line" | grep -oE '[a-f0-9]{8}')
        local title=$(echo "$line" | sed 's/^[○◐●✗] · [a-f0-9]\{8\} //')
        if [[ -n "$id" ]]; then
            completions+=("$id")
        fi
    done <<< "$tasks"

    COMPREPLY=($(compgen -W "${completions[*]}" -- "$cur"))

    # Show task list once when no input yet (use COMP_TYPE to detect first TAB)
    # COMP_TYPE: 9=normal, 33=list (show-all), 37=menu, 63=list (partial), 64=list
    if [[ -z "$cur" && ${#COMPREPLY[@]} -gt 0 && $COMP_TYPE -eq 63 ]]; then
        echo >&2
        echo "$tasks" >&2
    fi
}

_task_butler_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local cmd=""

    # Find the subcommand
    for ((i=1; i < COMP_CWORD; i++)); do
        case "${COMP_WORDS[i]}" in
            -*)
                # Skip options
                ;;
            *)
                cmd="${COMP_WORDS[i]}"
                break
                ;;
        esac
    done

    # Commands that need open task IDs
    case "$cmd" in
        start|done|cancel)
            _task_butler_complete_task_id "$(_task_butler_get_open_tasks)"
            return
            ;;
        show|delete|note)
            _task_butler_complete_task_id "$(_task_butler_get_tasks)"
            return
            ;;
    esac

    # Handle --parent and --depends options
    case "$prev" in
        --parent|--depends)
            _task_butler_complete_task_id "$(_task_butler_get_tasks)"
            return
            ;;
    esac

    # Default: use Typer's built-in completion for commands and options
    local IFS=$'\n'
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _TASK_BUTLER_COMPLETE=complete_bash task-butler 2>/dev/null ) )
}

complete -o default -F _task_butler_completion task-butler
complete -o default -F _task_butler_completion tb
