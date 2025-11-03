"""Stats panel widget showing monthly statistics."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static

from recorules.models import MonthStats


class StatsPanel(Container):
    """Panel displaying monthly statistics and quotas."""

    def compose(self) -> ComposeResult:
        """Compose the stats panel."""
        with Horizontal(id="stats-row"):
            with Vertical(classes="stat-box"):
                yield Static("Loading...", id="stat-days")
                yield Static("", id="stat-required")
                yield Static("", id="stat-balance")

            with Vertical(classes="stat-box"):
                yield Static("", id="stat-wfh-used")
                yield Static("", id="stat-wfh-quota")
                yield Static("", id="stat-wfh-status")

            with Vertical(classes="stat-box"):
                yield Static("", id="stat-office")
                yield Static("", id="stat-office-required")
                yield Static("", id="stat-office-status")

    def update_stats(self, stats: MonthStats) -> None:
        """Update the displayed statistics."""

        # Format hours as HH:MM for readability
        def fmt_hours(hours: float) -> str:
            total_minutes = round(hours * 60)
            h = total_minutes // 60
            m = total_minutes % 60
            return f"{h}h {m:02d}m"

        # Determine status indicators
        wfh_status = "⚠️" if stats.wfh_over_quota > 0 else "✓"
        office_status = "⚠️" if stats.total_deficit > 0 else "✓"

        # Update all stat widgets
        self.query_one("#stat-days", Static).update(
            f"[bold]Working Days:[/bold] {stats.working_days}"
        )
        self.query_one("#stat-required", Static).update(
            f"[bold]Required:[/bold] {fmt_hours(stats.total_required_hours)}"
        )
        # Show suggested clock-out time (actionable info)
        if stats.suggested_clockout_time:
            if stats.suggested_clockout_time == "Done ✓":
                self.query_one("#stat-balance", Static).update(
                    f"[bold green]Clock out:[/bold green] {stats.suggested_clockout_time}"
                )
            else:
                self.query_one("#stat-balance", Static).update(
                    f"[bold]Clock out:[/bold] {stats.suggested_clockout_time}"
                )
        else:
            self.query_one("#stat-balance", Static).update("[bold]Clock out:[/bold] --")

        self.query_one("#stat-wfh-used", Static).update(
            f"[bold]WFH Used:[/bold] {fmt_hours(stats.total_wfh_hours)} {wfh_status}"
        )
        self.query_one("#stat-wfh-quota", Static).update(
            f"[bold]WFH Quota:[/bold] {fmt_hours(stats.wfh_quota_hours)}"
        )
        over_quota = stats.wfh_over_quota
        if over_quota > 0:
            self.query_one("#stat-wfh-status", Static).update(
                f"[red][bold]WFH Over:[/bold] {fmt_hours(over_quota)}[/red]"
            )
        else:
            self.query_one("#stat-wfh-status", Static).update(
                f"[green][bold]WFH Left:[/bold] {fmt_hours(-over_quota)}[/green]"
            )

        self.query_one("#stat-office", Static).update(
            f"[bold]Office:[/bold] {fmt_hours(stats.total_office_hours)} {office_status}"
        )
        self.query_one("#stat-office-required", Static).update(
            f"[bold]Required:[/bold] {fmt_hours(stats.office_required_hours)}"
        )
        # Show total deficit (total hours needed), not just office deficit
        deficit = stats.total_deficit
        if deficit > 0:
            self.query_one("#stat-office-status", Static).update(
                f"[red][bold]EoM Deficit:[/bold] {fmt_hours(deficit)}[/red]"
            )
        else:
            self.query_one("#stat-office-status", Static).update(
                f"[green][bold]EoM Surplus:[/bold] {fmt_hours(-deficit)}[/green]"
            )

        # Force refresh of the panel
        self.refresh()
