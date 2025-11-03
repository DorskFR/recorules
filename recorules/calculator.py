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
    today: date | None = None,
) -> tuple[MonthStats, dict[date, int]]:
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

    Args:
        today: If provided, balance will be calculated only for past/today records
    """
    from datetime import datetime, timedelta

    if today is None:
        today = datetime.now(JST).date()

    # Count working days and paid leave from ALL records (for month-end projections)
    working_days = 0
    paid_leave_days = 0
    total_office_minutes = 0
    total_wfh_minutes = 0

    # Track daily balances (cumulative, WITH WFH capping)
    daily_balances: dict[date, int] = {}
    running_balance_minutes = 0

    # Today's balance specifically
    current_balance_minutes = 0

    # Track WFH quota consumption chronologically
    # We need to count working days first to know total quota
    total_wfh_quota_minutes = 0
    for record in merged_records:
        if record.day_type in (DayType.WORKING_DAY, DayType.UNPAID_LEAVE, DayType.PAID_LEAVE):
            total_wfh_quota_minutes += WFH_QUOTA_PER_DAY * 60

    remaining_wfh_quota_minutes = total_wfh_quota_minutes

    for record in merged_records:
        is_past_or_today = record.date <= today

        # Count working days (all days that would be work days in the calendar)
        if record.day_type in (DayType.WORKING_DAY, DayType.UNPAID_LEAVE, DayType.PAID_LEAVE):
            working_days += 1

        # Count paid leave separately (to reduce requirements)
        if record.day_type == DayType.PAID_LEAVE:
            paid_leave_days += 1

        # Aggregate hours (uncapped, for display purposes)
        total_office_minutes += record.office_minutes
        total_wfh_minutes += record.remote_minutes

        # Calculate daily balance with WFH capping
        # Only count WFH up to remaining quota
        capped_wfh_minutes = min(record.remote_minutes, remaining_wfh_quota_minutes)
        remaining_wfh_quota_minutes = max(0, remaining_wfh_quota_minutes - record.remote_minutes)

        worked_minutes = record.office_minutes + capped_wfh_minutes
        expected_minutes = record.expected_minutes
        daily_balance = worked_minutes - expected_minutes
        running_balance_minutes += daily_balance

        # Store cumulative balance for this day
        daily_balances[record.date] = running_balance_minutes

        if is_past_or_today:
            current_balance_minutes = running_balance_minutes

    # Calculate requirements
    actual_working_days = working_days - paid_leave_days
    total_required_hours = actual_working_days * HOURS_PER_DAY
    wfh_quota_hours = working_days * WFH_QUOTA_PER_DAY
    office_required_hours = total_required_hours - wfh_quota_hours

    # Calculate suggested clock-out time for today
    suggested_clockout_time = None
    today_record = next((r for r in merged_records if r.date == today), None)

    if today_record and today_record.day_type == DayType.WORKING_DAY:
        # Get yesterday's balance (already capped)
        from datetime import timedelta

        yesterday = today - timedelta(days=1)
        yesterday_balance = daily_balances.get(yesterday, 0)

        # Minutes needed today to reach neutral balance
        # yesterday_balance + (today_worked - today_required) = 0
        # today_worked = today_required - yesterday_balance
        today_required = HOURS_PER_DAY * 60  # 480 minutes
        minutes_needed_today = today_required - yesterday_balance

        # Calculate how much WFH quota was available for today
        # Recalculate remaining quota up to yesterday
        remaining_quota_before_today = total_wfh_quota_minutes
        for record in merged_records:
            if record.date >= today:
                break
            remaining_quota_before_today = max(
                0, remaining_quota_before_today - record.remote_minutes
            )

        # How much worked today so far (with WFH capping)
        capped_today_wfh = min(today_record.remote_minutes, remaining_quota_before_today)
        today_worked = today_record.office_minutes + capped_today_wfh

        # Remaining minutes to reach neutral
        remaining_minutes = minutes_needed_today - today_worked

        if remaining_minutes <= 0:
            suggested_clockout_time = "Done ✓"
        else:
            # Calculate clock-out time
            from datetime import datetime

            current_time = datetime.now(JST)

            # The remaining work time is net work time (breaks already handled)
            # Simply add the remaining minutes to current time
            clockout_time = current_time + timedelta(minutes=remaining_minutes)

            suggested_clockout_time = clockout_time.strftime("%H:%M")

    stats = MonthStats(
        year=year,
        month=month,
        working_days=working_days,
        total_required_hours=total_required_hours,
        wfh_quota_hours=wfh_quota_hours,
        office_required_hours=office_required_hours,
        actual_office_hours=total_office_minutes / 60,
        actual_wfh_hours=total_wfh_minutes / 60,
        planned_office_hours=0,  # Deprecated
        planned_wfh_hours=0,  # Deprecated
        paid_leave_days=paid_leave_days,
        balance_minutes=current_balance_minutes,
        suggested_clockout_time=suggested_clockout_time,
    )

    return stats, daily_balances


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

        # For past/today: always use actual data if available
        if target_date <= today and target_date in actual_by_date:
            result.append(actual_by_date[target_date])
        # For future: use actual only if it has meaningful data (entries or special day type)
        elif target_date in actual_by_date:
            actual = actual_by_date[target_date]
            # Check if entries have meaningful duration (> 0)
            has_meaningful_entries = any(entry.duration.minutes > 0 for entry in actual.entries)
            # Use if has meaningful entries OR is special day (leave/holiday/weekend)
            if has_meaningful_entries or actual.day_type != DayType.WORKING_DAY:
                result.append(actual)
            # Empty future working day: check for plans or auto-generate
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
                    DayRecord(
                        date=target_date, day_type=day_type, entries=entries, memo=planned.note
                    )
                )
            # No plan: auto-generate default for working days
            elif day_record.day_type == DayType.WORKING_DAY:
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
                    DayRecord(
                        date=target_date, day_type=day_record.day_type, entries=entries, memo=""
                    )
                )
            else:
                # Weekend/holiday with no data
                result.append(actual)
        # No actual data: check for planned data
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
