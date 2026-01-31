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
    COMPREPLY=($(compgen -W "$ids" -- "$cur"))

    # Show task list only once per command line (track via temp file)
    local cache_key=$(echo "$COMP_LINE" | md5sum | cut -d' ' -f1)
    local cache_file="/tmp/.tb_comp_$cache_key"

    if [[ -z "$cur" && ${#COMPREPLY[@]} -gt 1 && ! -f "$cache_file" ]]; then
        touch "$cache_file"
        # Clean up old cache files
        find /tmp -name '.tb_comp_*' -mmin +1 -delete 2>/dev/null
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
