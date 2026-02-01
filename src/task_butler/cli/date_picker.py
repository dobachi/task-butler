"""Date picker using text input."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

console = Console()

# 日本語相対日付パターン
RELATIVE_DATE_PATTERNS = [
    # N日後
    (re.compile(r"^(\d+)日後$"), lambda m: timedelta(days=int(m.group(1)))),
    # N週間後
    (re.compile(r"^(\d+)週間?後$"), lambda m: timedelta(weeks=int(m.group(1)))),
    # Nヶ月後 (簡易: 30日 * N)
    (re.compile(r"^(\d+)[ヶか]?月後$"), lambda m: timedelta(days=30 * int(m.group(1)))),
    # 明後日
    (re.compile(r"^明後日$"), lambda m: timedelta(days=2)),
    # 来週
    (re.compile(r"^来週$"), lambda m: timedelta(weeks=1)),
    # 再来週
    (re.compile(r"^再来週$"), lambda m: timedelta(weeks=2)),
]


def parse_relative_japanese(value: str) -> Optional[datetime]:
    """Parse Japanese relative date expressions."""
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

    # マジックワード省略形を展開
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

    # 日本語相対日付を試行
    result = parse_relative_japanese(value)
    if result:
        return result

    try:
        return parse_due_date(value)
    except Exception:
        return None


def pick_date(title: str = "日付選択") -> Optional[date]:
    """Prompt for date input and return selected date or None."""
    while True:
        date_str = Prompt.ask(
            f"[cyan]{title}[/cyan] (YYYY-MM-DD, t=today, 3日後, 空でスキップ)",
            default="",
        )
        if not date_str.strip():
            return None

        dt = parse_date_input(date_str)
        if dt:
            return dt.date()

        console.print("[red]無効な日付形式です。再入力してください。[/red]")
