"""Date picker using npyscreen calendar widget."""

from __future__ import annotations

from datetime import date
from typing import Optional

import npyscreen


class DatePickerForm(npyscreen.ActionFormMinimal):
    """Simple form with a date picker."""

    def create(self):
        self.date_widget = self.add(
            npyscreen.TitleDateCombo,
            name="日付を選択 (Enter で確定, Esc でキャンセル):",
        )

    def on_ok(self):
        self.editing = False

    def on_cancel(self):
        self.date_widget.value = None
        self.editing = False


class DatePickerApp(npyscreen.NPSAppManaged):
    """App wrapper for date picker."""

    def __init__(self, title: str = "日付選択"):
        super().__init__()
        self.title = title
        self.selected_date: Optional[date] = None

    def onStart(self):
        self.form = self.addForm("MAIN", DatePickerForm, name=self.title)

    def onCleanExit(self):
        if self.form.date_widget.value:
            self.selected_date = self.form.date_widget.value


def pick_date(title: str = "日付選択") -> Optional[date]:
    """Open date picker and return selected date or None if cancelled."""
    app = DatePickerApp(title)
    app.run()
    return app.selected_date
