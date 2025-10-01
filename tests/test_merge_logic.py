"""Tests for merge_actual_and_planned logic."""

from datetime import date

from recorules.calculator import merge_actual_and_planned
from recorules.duration import Duration
from recorules.models import DayRecord, DayType, PlannedDay, WorkEntry, WorkplaceType


def test_merge_past_uses_actual():
    """Past dates should always use actual Recoru data."""
    actual_records = [
        DayRecord(
            date=date(2025, 9, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),
                    category="Attendance/Work",
                )
            ],
            memo="",
        )
    ]
    planned_days = []
    today = date(2025, 9, 15)  # Sept 15 (Sept 1 is in the past)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 9, today)

    # Sept 1 should use actual data
    sept1 = next(r for r in merged if r.date == date(2025, 9, 1))
    assert sept1.office_minutes == 480
    assert len(sept1.entries) == 1


def test_merge_future_empty_actual_uses_plan():
    """Future date with empty Recoru record should use saved plan."""
    # Recoru returns empty record for future
    actual_records = [
        DayRecord(
            date=date(2025, 10, 17),
            day_type=DayType.WORKING_DAY,
            entries=[],  # Empty from Recoru
            memo="",
        )
    ]

    # User saved a plan for Oct 17
    planned_days = [
        PlannedDay(
            date=date(2025, 10, 17),
            office_minutes=0,
            remote_minutes=480,
            is_paid_leave=False,
            note="WFH",
        )
    ]

    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    # Oct 17 should use the plan, not the empty actual
    oct17 = next(r for r in merged if r.date == date(2025, 10, 17))
    assert oct17.remote_minutes == 480
    assert oct17.office_minutes == 0
    assert len(oct17.entries) == 1
    assert oct17.entries[0].category == "Planned"


def test_merge_future_empty_actual_auto_generates():
    """Future working day with no plan should auto-generate 480 min office."""
    # Recoru returns empty record
    actual_records = [
        DayRecord(
            date=date(2025, 10, 15),
            day_type=DayType.WORKING_DAY,
            entries=[],
            memo="",
        )
    ]

    planned_days = []  # No plan saved
    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    # Oct 15 should have auto-generated default
    oct15 = next(r for r in merged if r.date == date(2025, 10, 15))
    assert oct15.office_minutes == 480
    assert oct15.remote_minutes == 0
    assert len(oct15.entries) == 1
    assert oct15.entries[0].category == "Planned"


def test_merge_future_with_leave_uses_actual():
    """Future date with leave in Recoru should use actual leave data."""
    # Recoru shows paid leave for future day
    actual_records = [
        DayRecord(
            date=date(2025, 10, 20),
            day_type=DayType.PAID_LEAVE,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),
                    category="Paid Leave",
                )
            ],
            memo="",
        )
    ]

    planned_days = []
    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    # Oct 20 should use the leave data from Recoru
    oct20 = next(r for r in merged if r.date == date(2025, 10, 20))
    assert oct20.day_type == DayType.PAID_LEAVE
    assert len(oct20.entries) == 1


def test_merge_priority_plan_over_autogen():
    """When both plan and auto-gen are possible, plan should win."""
    # Empty actual record
    actual_records = [
        DayRecord(
            date=date(2025, 10, 10),
            day_type=DayType.WORKING_DAY,
            entries=[],
            memo="",
        )
    ]

    # User has a plan
    planned_days = [
        PlannedDay(
            date=date(2025, 10, 10),
            office_minutes=240,
            remote_minutes=240,
            is_paid_leave=False,
            note="Half day",
        )
    ]

    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    # Should use plan, not auto-gen
    oct10 = next(r for r in merged if r.date == date(2025, 10, 10))
    assert oct10.office_minutes == 240
    assert oct10.remote_minutes == 240


def test_merge_weekend_no_autogen():
    """Weekends should not get auto-generated defaults."""
    actual_records = []  # No Recoru data
    planned_days = []
    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    # Oct 4 is Saturday, Oct 5 is Sunday
    oct4 = next(r for r in merged if r.date == date(2025, 10, 4))
    oct5 = next(r for r in merged if r.date == date(2025, 10, 5))

    assert oct4.day_type == DayType.WEEKEND
    assert len(oct4.entries) == 0
    assert oct5.day_type == DayType.WEEKEND
    assert len(oct5.entries) == 0


def test_merge_full_month():
    """Test merging a full month with various scenarios."""
    # Mix of actual, planned, and empty
    actual_records = [
        # Oct 1: actual work
        DayRecord(
            date=date(2025, 10, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=Duration.parse("09:00"),
                    clock_out=None,  # Still working
                    duration=Duration(240),
                    category="Attendance/Work",
                )
            ],
            memo="",
        ),
        # Oct 2-31: empty from Recoru
        *[
            DayRecord(
                date=date(2025, 10, day),
                day_type=DayType.WORKING_DAY
                if date(2025, 10, day).weekday() < 5
                else DayType.WEEKEND,
                entries=[],
                memo="",
            )
            for day in range(2, 32)
        ],
    ]

    # User has a plan for Oct 17
    planned_days = [
        PlannedDay(
            date=date(2025, 10, 17),
            office_minutes=0,
            remote_minutes=480,
            is_paid_leave=False,
            note="WFH",
        )
    ]

    today = date(2025, 10, 1)

    merged = merge_actual_and_planned(actual_records, planned_days, 2025, 10, today)

    assert len(merged) == 31

    # Oct 1: should have actual data
    oct1 = next(r for r in merged if r.date == date(2025, 10, 1))
    assert oct1.office_minutes == 240

    # Oct 2 (working day): should have auto-gen
    oct2 = next(r for r in merged if r.date == date(2025, 10, 2))
    assert oct2.office_minutes == 480
    assert oct2.entries[0].category == "Planned"

    # Oct 17 (saved plan): should use plan
    oct17 = next(r for r in merged if r.date == date(2025, 10, 17))
    assert oct17.remote_minutes == 480
    assert oct17.office_minutes == 0

    # Oct 4 (Saturday): should be empty
    oct4 = next(r for r in merged if r.date == date(2025, 10, 4))
    assert len(oct4.entries) == 0
