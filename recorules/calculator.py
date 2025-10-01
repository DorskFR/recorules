"""Business logic calculator for workplace rules."""

from calendar import monthrange
from datetime import date
from zoneinfo import ZoneInfo

from recorules.duration import Duration
from recorules.holidays import is_working_day
from recorules.models import DayRecord, DayType, MonthStats, PlannedDay, WorkEntry, WorkplaceType
from recorules.recoru import AttendanceChart

# Constants
HOURS_PER_DAY = 8
WFH_QUOTA_PER_DAY = 1  # hours
MANDATORY_BREAK_THRESHOLD = 6 * 60  # minutes
MANDATORY_BREAK_DURATION = 60  # minutes
JST = ZoneInfo("Asia/Tokyo")  # Japan Standard Time timezone


def parse_attendance_chart(
    attendance_chart: AttendanceChart, year: int, month: int
) -> list[DayRecord]:
    """Parse AttendanceChart into DayRecord objects."""
    records = []

    for row in attendance_chart:
        day_of_month = row.day_of_month
        if day_of_month == 0:
            continue

        target_date = date(year, month, day_of_month)

        # Determine day type
        color = row.day.color
        if color in ("blue", "red"):
            day_type = DayType.HOLIDAY if color == "red" else DayType.WEEKEND
        # Unpaid leave: hours still due
        elif any("unpaid" in entry.category.lower() for entry in row.entries):
            day_type = DayType.UNPAID_LEAVE
        elif any("leave" in entry.category.lower() for entry in row.entries):
            day_type = DayType.PAID_LEAVE
        elif is_working_day(target_date):
            day_type = DayType.WORKING_DAY
        else:
            day_type = DayType.HOLIDAY

        # Parse entries
        entries = []
        for entry in row.entries:
            workplace = _parse_workplace(entry.workplace)
            clock_in = Duration.parse(entry.clock_in_time) if entry.clock_in_time else None
            clock_out = Duration.parse(entry.clock_out_time) if entry.clock_out_time else None
            duration = _calculate_entry_duration(entry, clock_in, clock_out)

            entries.append(
                WorkEntry(
                    workplace=workplace,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    duration=duration,
                    category=entry.category,
                )
            )

        records.append(
            DayRecord(date=target_date, day_type=day_type, entries=entries, memo=row.memo)
        )

    return records


def _parse_workplace(workplace_str: str) -> WorkplaceType:
    """Parse workplace string into WorkplaceType, defaulting to OFFICE."""
    if "WFH" in workplace_str or "remote" in workplace_str.lower():
        return WorkplaceType.WFH
    # Default to office (includes "HF Bldg", "office", leave entries, etc.)
    return WorkplaceType.OFFICE


def _calculate_entry_duration(
    entry, clock_in: Duration | None, clock_out: Duration | None
) -> Duration:
    """Calculate duration for a work entry, applying break rules."""
    category = entry.category

    # Handle half-day leave categories (4 hours)
    if any(
        half_day in category
        for half_day in [
            "Half Day Leave AM",
            "Half Day Leave PM",
            "Flexible Holiday AM",
            "Flexible Holiday PM",
        ]
    ):
        return Duration(4 * 60)

    # Handle full-day leave categories (8 hours)
    if any(
        full_day in category
        for full_day in [
            "Paid Leave",
            "Unpaid Leave",
            "GW Substitute Leave",
            "Wedding Leave",
            "Paternity Leave",
            "Condolence Leave",
            "Special Leave",
            "Flexible Holiday",
        ]
    ) or category.endswith(("Leave", "Leagve")):
        return Duration(8 * 60)

    # No clock in time
    if not clock_in:
        return Duration(0)

    # If no clock out, use current time
    if not clock_out:
        clock_out = Duration.now()

    # Handle after midnight
    if clock_out < clock_in:
        clock_out = clock_out + Duration(24 * 60)

    work_time = clock_out - clock_in

    # Apply mandatory break
    if work_time.minutes >= MANDATORY_BREAK_THRESHOLD:
        work_time = work_time - Duration(MANDATORY_BREAK_DURATION)

    return work_time


def calculate_month_stats(
    year: int,
    month: int,
    merged_records: list[DayRecord],
) -> MonthStats:
    """
    Calculate monthly statistics from merged records (actual + planned + auto-defaults).

    Single source of truth for ALL calculations.

    Rules:
    - 8 hours per working day required
    - 1 hour WFH quota per working day
    - Mandatory in-office = total required - WFH quota
    - Paid leave reduces required hours (not a working day)
    - Unpaid leave is a working day (hours still due)
    - WFH quota is based on total working days (not reduced by paid leave)
    """
    # Count working days and paid leave from ALL records
    working_days = 0
    paid_leave_days = 0
    total_office_minutes = 0
    total_wfh_minutes = 0

    for record in merged_records:
        # Count working days (including unpaid leave which still requires hours)
        if record.day_type in (DayType.WORKING_DAY, DayType.UNPAID_LEAVE):
            working_days += 1
        elif record.day_type == DayType.PAID_LEAVE:
            paid_leave_days += 1

        # Aggregate hours (office_minutes and remote_minutes already exclude leave entries)
        total_office_minutes += record.office_minutes
        total_wfh_minutes += record.remote_minutes

    # Calculate requirements
    actual_working_days = working_days - paid_leave_days  # Paid leave reduces work requirement
    total_required_hours = actual_working_days * HOURS_PER_DAY
    wfh_quota_hours = working_days * WFH_QUOTA_PER_DAY  # Quota based on total working days
    office_required_hours = total_required_hours - wfh_quota_hours

    # Calculate balance (total worked - total required)
    total_worked_minutes = total_office_minutes + total_wfh_minutes
    balance_minutes = total_worked_minutes - (actual_working_days * HOURS_PER_DAY * 60)

    return MonthStats(
        year=year,
        month=month,
        working_days=working_days,
        total_required_hours=total_required_hours,
        wfh_quota_hours=wfh_quota_hours,
        office_required_hours=office_required_hours,
        actual_office_hours=total_office_minutes / 60,  # Now represents TOTAL (not just actual)
        actual_wfh_hours=total_wfh_minutes / 60,  # Now represents TOTAL (not just actual)
        planned_office_hours=0,  # Deprecated: keeping for compatibility
        planned_wfh_hours=0,  # Deprecated: keeping for compatibility
        paid_leave_days=paid_leave_days,
        balance_minutes=balance_minutes,
    )


def generate_month_calendar(year: int, month: int) -> list[DayRecord]:
    """
    Generate a calendar for the entire month with empty DayRecords.

    This creates placeholder records for days that don't have actual data yet.
    """
    _, days_in_month = monthrange(year, month)
    calendar = []

    for day in range(1, days_in_month + 1):
        target_date = date(year, month, day)

        # Determine day type
        if is_working_day(target_date):
            day_type = DayType.WORKING_DAY
        elif target_date.weekday() in (5, 6):
            day_type = DayType.WEEKEND
        else:
            day_type = DayType.HOLIDAY

        calendar.append(DayRecord(date=target_date, day_type=day_type, entries=[], memo=""))

    return calendar


def merge_actual_and_planned(
    actual_records: list[DayRecord],
    planned_days: list[PlannedDay],
    year: int,
    month: int,
    today: date | None = None,
) -> list[DayRecord]:
    """
    Merge actual records with planned days for display.

    For past dates, use actual records.
    For future dates, create records from planned data or auto-generate defaults.
    Future working days without plans default to 8h office work.
    """
    if today is None:
        from datetime import datetime

        today = datetime.now(JST).date()

    # Create a dict of actual records by date
    actual_by_date = {record.date: record for record in actual_records}

    # Create a dict of planned days by date
    planned_by_date = {planned.date: planned for planned in planned_days}

    # Generate full month calendar
    full_calendar = generate_month_calendar(year, month)

    # Merge
    result = []
    for day_record in full_calendar:
        target_date = day_record.date

        # If we have actual data, use it
        if target_date in actual_by_date:
            result.append(actual_by_date[target_date])
        # If we have planned data, convert to DayRecord
        elif target_date in planned_by_date:
            planned = planned_by_date[target_date]
            day_type = DayType.PAID_LEAVE if planned.is_paid_leave else day_record.day_type

            # Create entries for planned office/wfh time
            entries = []
            if planned.office_minutes > 0:
                entries.append(
                    WorkEntry(
                        workplace=WorkplaceType.OFFICE,
                        clock_in=None,
                        clock_out=None,
                        duration=Duration(planned.office_minutes),
                        category="Planned",
                    )
                )
            if planned.remote_minutes > 0:
                entries.append(
                    WorkEntry(
                        workplace=WorkplaceType.WFH,
                        clock_in=None,
                        clock_out=None,
                        duration=Duration(planned.remote_minutes),
                        category="Planned",
                    )
                )

            result.append(
                DayRecord(date=target_date, day_type=day_type, entries=entries, memo=planned.note)
            )
        # For future working days without actual or planned data, auto-generate default plan
        elif target_date > today and day_record.day_type == DayType.WORKING_DAY:
            # Default: 8 hours office work (480 minutes)
            entries = [
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),
                    category="Planned",
                )
            ]
            result.append(
                DayRecord(date=target_date, day_type=day_record.day_type, entries=entries, memo="")
            )
        # Otherwise use empty record (past dates without data, weekends, holidays)
        else:
            result.append(day_record)

    return result
