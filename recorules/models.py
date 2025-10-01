"""Data models for attendance and planning."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from recorules.duration import Duration


class WorkplaceType(str, Enum):
    """Type of workplace."""

    OFFICE = "HF Bldg."
    WFH = "WFH"


class DayType(str, Enum):
    """Type of day."""

    WORKING_DAY = "working_day"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    PAID_LEAVE = "paid_leave"
    UNPAID_LEAVE = "unpaid_leave"


@dataclass
class WorkEntry:
    """A single work entry (clock-in/clock-out pair)."""

    workplace: WorkplaceType
    clock_in: Duration | None
    clock_out: Duration | None
    duration: Duration
    category: str


@dataclass
class DayRecord:
    """Record for a single day."""

    date: date
    day_type: DayType
    entries: list[WorkEntry]
    memo: str = ""

    @property
    def office_minutes(self) -> int:
        """Total office minutes for this day (excluding leave)."""
        return sum(
            entry.duration.minutes
            for entry in self.entries
            if entry.workplace == WorkplaceType.OFFICE and not self._is_leave_entry(entry)
        )

    @property
    def remote_minutes(self) -> int:
        """Total remote (WFH) minutes for this day (excluding leave)."""
        return sum(
            entry.duration.minutes
            for entry in self.entries
            if entry.workplace == WorkplaceType.WFH and not self._is_leave_entry(entry)
        )

    def _is_leave_entry(self, entry: WorkEntry) -> bool:
        """Check if entry is a leave entry."""
        return "leave" in entry.category.lower() or "holiday" in entry.category.lower()

    @property
    def total_minutes(self) -> int:
        """Total work minutes for this day."""
        return sum(entry.duration.minutes for entry in self.entries)

    @property
    def expected_minutes(self) -> int:
        """Expected work minutes for this day based on day type."""
        if self.day_type == DayType.WORKING_DAY:
            return 8 * 60  # 8 hours
        if self.day_type == DayType.UNPAID_LEAVE:
            return 8 * 60  # Unpaid leave: hours still due
        if self.day_type == DayType.PAID_LEAVE:
            return 0  # Paid leave: no hours due
        return 0  # Weekend/holiday


@dataclass
class PlannedDay:
    """A planned future day."""

    date: date
    office_minutes: int
    remote_minutes: int
    is_paid_leave: bool = False
    note: str = ""


@dataclass
class MonthStats:
    """Statistics for a month."""

    year: int
    month: int
    working_days: int
    total_required_hours: float
    wfh_quota_hours: float
    office_required_hours: float
    actual_office_hours: float
    actual_wfh_hours: float
    planned_office_hours: float
    planned_wfh_hours: float
    paid_leave_days: int
    balance_minutes: int

    @property
    def total_office_hours(self) -> float:
        """Total office hours (actual + planned)."""
        return self.actual_office_hours + self.planned_office_hours

    @property
    def total_wfh_hours(self) -> float:
        """Total WFH hours (actual + planned)."""
        return self.actual_wfh_hours + self.planned_wfh_hours

    @property
    def wfh_over_quota(self) -> float:
        """How much WFH hours are over quota (negative if under)."""
        return self.total_wfh_hours - self.wfh_quota_hours

    @property
    def office_deficit(self) -> float:
        """How much office hours are under required (negative if over)."""
        return self.office_required_hours - self.total_office_hours

    @property
    def total_deficit(self) -> float:
        """
        Total hours deficit at end of month.

        This is the actual shortfall considering:
        - Total required hours
        - WFH can only contribute up to quota
        - Any extra WFH doesn't count toward requirement
        """
        # Cap WFH contribution at quota
        wfh_contribution = min(self.total_wfh_hours, self.wfh_quota_hours)
        total_worked = self.total_office_hours + wfh_contribution
        return self.total_required_hours - total_worked
