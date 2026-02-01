"""Date picker using text input."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

console = Console()

# Relative date patterns (Japanese + English)
RELATIVE_DATE_PATTERNS = [
    # Japanese: N日後
    (re.compile(r"^(\d+)日後$"), lambda m: timedelta(days=int(m.group(1)))),
    # Japanese: N週間後
    (re.compile(r"^(\d+)週間?後$"), lambda m: timedelta(weeks=int(m.group(1)))),
    # Japanese: Nヶ月後 (simplified: 30 days * N)
    (re.compile(r"^(\d+)[ヶか]?月後$"), lambda m: timedelta(days=30 * int(m.group(1)))),
    # Japanese: 明後日
    (re.compile(r"^明後日$"), lambda m: timedelta(days=2)),
    # Japanese: 来週
    (re.compile(r"^来週$"), lambda m: timedelta(weeks=1)),
    # Japanese: 再来週
    (re.compile(r"^再来週$"), lambda m: timedelta(weeks=2)),
    # English: in N days
    (re.compile(r"^in\s*(\d+)\s*days?$", re.IGNORECASE), lambda m: timedelta(days=int(m.group(1)))),
    # English: in N weeks
    (
        re.compile(r"^in\s*(\d+)\s*weeks?$", re.IGNORECASE),
        lambda m: timedelta(weeks=int(m.group(1))),
    ),
    # English: +N or +Nd (days)
    (re.compile(r"^\+(\d+)d?$"), lambda m: timedelta(days=int(m.group(1)))),
    # English: +Nw (weeks)
    (re.compile(r"^\+(\d+)w$"), lambda m: timedelta(weeks=int(m.group(1)))),
]


def parse_relative_date(value: str) -> Optional[datetime]:
    """Parse relative date expressions (Japanese and English)."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for pattern, delta_fn in RELATIVE_DATE_PATTERNS:
        match = pattern.match(value.strip())
        if match:
            return today + delta_fn(match)

    return None


def parse_date_input(value: str) -> Optional[datetime]:
    """Parse date from user input."""
    from .commands.add import parse_due_date

    if not value.strip():
        return None

    # Expand abbreviations
    abbrevs = {
        "t": "today",
        "to": "today",
        "tom": "tomorrow",
        "y": "yesterday",
        "nw": "next week",
    }
    value_lower = value.lower().strip()
    if value_lower in abbrevs:
        value = abbrevs[value_lower]

    # Try relative date patterns
    result = parse_relative_date(value)
    if result:
        return result

    try:
        return parse_due_date(value)
    except Exception:
        return None


def show_date_help() -> None:
    """Show available date formats."""
    console.print("\n[bold]Available date formats:[/bold]")
    console.print("  [cyan]YYYY-MM-DD[/cyan]  - e.g., 2025-02-15")
    console.print("  [cyan]MM/DD[/cyan]       - e.g., 2/15 (current year)")
    console.print("  [cyan]t, today[/cyan]   - today")
    console.print("  [cyan]tom[/cyan]        - tomorrow")
    console.print("  [cyan]+N[/cyan]         - in N days (e.g., +3 = in 3 days)")
    console.print("  [cyan]+Nw[/cyan]        - in N weeks (e.g., +2w = in 2 weeks)")
    console.print("  [cyan]nw[/cyan]         - next week")
    console.print("  [cyan]3日後[/cyan]      - in 3 days (Japanese)")
    console.print("  [cyan]来週[/cyan]       - next week (Japanese)")
    console.print()


def pick_date(title: str = "Date") -> Optional[date]:
    """Prompt for date input and return selected date or None."""
    while True:
        date_str = Prompt.ask(
            f"[cyan]{title}[/cyan] (?=help, empty to skip)",
            default="",
        )
        if not date_str.strip():
            return None

        if date_str.strip() == "?":
            show_date_help()
            continue

        dt = parse_date_input(date_str)
        if dt:
            return dt.date()

        console.print("[red]Invalid format. Enter '?' for help.[/red]")
