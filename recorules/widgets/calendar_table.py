"""Calendar table widget showing daily records."""

from datetime import date as date_type
from datetime import datetime

from rich.text import Text
from textual.widgets import DataTable

from recorules.calculator import JST
from recorules.models import DayRecord, DayType


class CalendarTable(DataTable):
    """Table displaying the monthly calendar with work records."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.show_cursor = True
        self.zebra_stripes = True
        self.can_focus = True

    def on_mount(self) -> None:
        """Set up the table columns."""
        # Set reasonable fixed widths (flexible columns not yet implemented in Textual)
        # Date format is "MM/DD (Day)" = 13 chars
        self.add_column("Date", width=13)
        self.add_column("Office", width=8)
        self.add_column("Remote", width=8)
        self.add_column("Expected", width=10)
        self.add_column("Balance", width=10)
        self.add_column("Note")  # No width = auto-size to remaining space

    def load_records(self, records: list[DayRecord], today: date_type | None = None) -> None:
        """Load day records into the table."""
        self.clear()
        if today is None:
            today = datetime.now(JST).date()

        running_balance = 0
        today_row_index = None

        for idx, record in enumerate(records):
            # Calculate balance (use office + remote to exclude leave entries)
            worked_minutes = record.office_minutes + record.remote_minutes
            expected_minutes = record.expected_minutes
            daily_balance = worked_minutes - expected_minutes
            running_balance += daily_balance

            # Format values
            date_str = record.date.strftime("%m/%d")
            day_name = record.date.strftime("(%a)")[0:3]  # (Mon), (Tue), etc.
            date_display = f"{date_str} {day_name}"

            office_str = self._format_minutes(record.office_minutes)
            remote_str = self._format_minutes(record.remote_minutes)
            expected_str = self._format_minutes(expected_minutes)
            balance_str = self._format_balance(running_balance)

            # Collect notes
            note = record.memo if record.memo else ""
            if record.day_type == DayType.PAID_LEAVE:
                note = "PTO" if not note else f"PTO | {note}"
            elif record.day_type == DayType.UNPAID_LEAVE:
                note = "Unpaid Leave" if not note else f"Unpaid Leave | {note}"

            # Determine row style (check day_type before future dimming)
            if record.date == today:
                style = "bold yellow"
                today_row_index = idx
            elif record.day_type == DayType.UNPAID_LEAVE:
                style = "yellow"
            elif record.day_type == DayType.WEEKEND:
                style = "blue"
            elif record.day_type == DayType.HOLIDAY:
                style = "red"
            elif record.day_type == DayType.PAID_LEAVE:
                style = "cyan"
            elif record.date > today:
                # Dim future working days (with planned work)
                style = "dim"
            else:
                style = None

            # Apply styling to each cell using Rich Text
            if style:
                self.add_row(
                    Text(date_display, style=style),
                    Text(office_str, style=style),
                    Text(remote_str, style=style),
                    Text(expected_str, style=style),
                    Text(balance_str, style=style),
                    Text(note, style=style),
                    key=record.date.isoformat(),
                )
            else:
                self.add_row(
                    date_display,
                    office_str,
                    remote_str,
                    expected_str,
                    balance_str,
                    note,
                    key=record.date.isoformat(),
                )

        # Move cursor to today's row if found
        if today_row_index is not None and len(self.rows) > 0:
            self.move_cursor(row=today_row_index)

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        """Format minutes as HH:MM."""
        if minutes == 0:
            return "--"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def _format_balance(balance_minutes: int) -> str:
        """Format balance with sign."""
        sign = "+" if balance_minutes >= 0 else ""
        hours = abs(balance_minutes) // 60
        mins = abs(balance_minutes) % 60
        return (
            f"{sign}{hours:02d}:{mins:02d}" if balance_minutes >= 0 else f"-{hours:02d}:{mins:02d}"
        )
