"""Main Textual application."""

from datetime import date, datetime
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, LoadingIndicator

from recorules.calculator import (
    JST,
    calculate_month_stats,
    merge_actual_and_planned,
    parse_attendance_chart,
)
from recorules.config import Config
from recorules.database import PlanningDatabase
from recorules.errors import ConfigNotFoundError
from recorules.models import DayRecord, MonthStats, PlannedDay
from recorules.recoru import RecoruSession
from recorules.widgets import CalendarTable, StatsPanel
from recorules.widgets.plan_dialog import PlanDialog


class RecoRulesApp(App):
    """RecoRules TUI application."""

    CSS = """
    #main-container {
        height: 100%;
    }

    Vertical {
        height: 100%;
    }

    #loading-indicator {
        layer: overlay;
        offset: 50% 50%;
        width: auto;
        height: auto;
        display: none;
    }

    #loading-indicator.visible {
        display: block;
    }

    #stats-panel {
        height: 1fr;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    #stats-row {
        height: 100%;
        width: 100%;
    }

    .stat-box {
        width: 1fr;
        padding: 0 1;
    }

    #calendar-table {
        height: 4fr;
        border: solid $primary;
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("p", "plan", "Plan Future"),
        ("c", "current_month", "Current Month"),
        ("n", "next_month", "Next Month"),
        ("b", "prev_month", "Prev Month"),
        ("?", "help", "Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        # Use JST timezone to match Recoru
        self.today = datetime.now(JST).date()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.db = PlanningDatabase()
        self.config: Config | None = None
        self.day_records: list[DayRecord] = []
        self.planned_days: list[PlannedDay] = []

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        with Container(id="main-container"), Vertical():
            yield LoadingIndicator(id="loading-indicator")
            yield StatsPanel(id="stats-panel")
            yield CalendarTable(id="calendar-table")
        yield Footer()

    def on_mount(self) -> None:
        """Load data when the app starts."""
        self.title = f"RecoRules - {self.current_year}/{self.current_month:02d}"
        self.load_data_async()

    def load_data_async(self) -> None:
        """Start async data loading."""
        loading = self.query_one("#loading-indicator", LoadingIndicator)
        loading.add_class("visible")
        self.run_worker(self._fetch_and_update, exclusive=True, thread=True)

    def _fetch_and_update(self) -> None:
        """Load attendance data from Recoru and merge with planned days."""
        # Load config
        self.config = Config.from_env() or Config.load()
        if not self.config:
            self.notify(
                "No configuration found. Please run 'recorules config' first.", severity="error"
            )
            raise ConfigNotFoundError

        # Calculate period_point offset from current JST month
        now_jst = datetime.now(JST).date()
        current_jst_year = now_jst.year
        current_jst_month = now_jst.month

        # Calculate month difference
        period_point = (self.current_year - current_jst_year) * 12 + (
            self.current_month - current_jst_month
        )

        # Fetch from Recoru
        try:
            with RecoruSession(
                contract_id=self.config.recoru_contract_id,
                auth_id=self.config.recoru_auth_id,
                password=self.config.recoru_password,
            ) as session:
                attendance_chart = session.get_attendance_chart(period_point)
        except (OSError, ValueError) as e:
            self.notify(f"Failed to fetch data from Recoru: {e}", severity="error")
            return

        # Parse attendance chart
        self.day_records = parse_attendance_chart(
            attendance_chart, self.current_year, self.current_month
        )

        # Get planned days
        self.planned_days = self.db.get_planned_days_for_month(
            self.current_year, self.current_month
        )

        # Merge actual and planned (with auto-generated defaults for future working days)
        merged_records = merge_actual_and_planned(
            self.day_records, self.planned_days, self.current_year, self.current_month, self.today
        )

        # Calculate stats from merged records (single source of truth)
        stats = calculate_month_stats(self.current_year, self.current_month, merged_records)

        # Update UI on main thread
        self.call_from_thread(self._update_ui, stats, merged_records)

    def _update_ui(self, stats: MonthStats, merged_records: list[DayRecord]) -> None:
        """Update UI components (must run on main thread)."""
        # Update stats panel
        stats_panel = self.query_one("#stats-panel", StatsPanel)
        stats_panel.update_stats(stats)

        # Update calendar table
        calendar_table = self.query_one("#calendar-table", CalendarTable)
        calendar_table.load_records(merged_records, self.today)

        # Hide loading indicator
        loading = self.query_one("#loading-indicator", LoadingIndicator)
        loading.remove_class("visible")

        # Focus the table so it can receive keyboard input
        calendar_table.focus()

        self.notify("Data loaded successfully", severity="information")

    def action_refresh(self) -> None:
        """Refresh data from Recoru."""
        self.notify("Refreshing data...", severity="information")
        self.load_data_async()

    def action_next_month(self) -> None:
        """Navigate to next month."""
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.title = f"RecoRules - {self.current_year}/{self.current_month:02d}"
        self.load_data_async()

    def action_prev_month(self) -> None:
        """Navigate to previous month."""
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.title = f"RecoRules - {self.current_year}/{self.current_month:02d}"
        self.load_data_async()

    def action_current_month(self) -> None:
        """Navigate to current month (JST timezone)."""
        now = datetime.now(JST).date()
        self.current_year = now.year
        self.current_month = now.month
        self.title = f"RecoRules - {self.current_year}/{self.current_month:02d}"
        self.load_data_async()

    def action_plan(self) -> None:
        """Open planning dialog for selected date."""
        calendar_table = self.query_one("#calendar-table", CalendarTable)

        # Get currently selected row using coordinate_to_cell_key
        if calendar_table.cursor_coordinate is None:
            self.notify("Please select a date first", severity="warning")
            return

        # Get the row key from the cursor coordinate
        try:
            row_key, _ = calendar_table.coordinate_to_cell_key(calendar_table.cursor_coordinate)
            # The row key's value is the ISO date string
            target_date = date.fromisoformat(row_key.value or "")
        except (AttributeError, ValueError, IndexError) as e:
            self.notify(f"Invalid row selected: {e}", severity="warning")
            return

        # Can only plan future dates
        if target_date < self.today:
            self.notify("Cannot plan past dates", severity="warning")
            return

        self.push_screen(PlanDialog(target_date), self.handle_plan_result)

    def handle_plan_result(self, result: dict | None) -> None:
        """Handle the result from the planning dialog."""
        if result is None:
            return

        if result["action"] == "delete":
            self.db.delete_planned_day(result["date"])
            self.notify(f"Deleted plan for {result['date']}", severity="information")
            self.load_data_async()
        elif result["action"] == "save":
            planned = PlannedDay(
                date=result["date"],
                office_minutes=result["office_minutes"],
                remote_minutes=result["remote_minutes"],
                is_paid_leave=result["is_paid_leave"],
                note=result["note"],
            )
            self.db.save_planned_day(planned)
            self.notify(f"Saved plan for {result['date']}", severity="information")
            self.load_data_async()

    def action_help(self) -> None:
        """Show help message."""
        help_text = """
        [bold]RecoRules - Keyboard Shortcuts[/bold]

        [cyan]q[/cyan] - Quit application
        [cyan]r[/cyan] - Refresh data from Recoru
        [cyan]p[/cyan] - Plan future days
        [cyan]?[/cyan] - Show this help

        [bold]Workplace Rules:[/bold]
        • 8 hours required per working day
        • 1 hour WFH quota per working day
        • Office hours = Total hours - WFH quota
        """
        self.notify(help_text, title="Help", timeout=10)
