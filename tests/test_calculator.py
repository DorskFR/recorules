"""Tests for calculator business logic."""

from datetime import date

import pytest

from recorules.calculator import calculate_month_stats, generate_month_calendar
from recorules.duration import Duration
from recorules.models import DayRecord, DayType, PlannedDay, WorkEntry, WorkplaceType


def test_generate_month_calendar():
    """Test generating a month calendar."""
    # September 2025 has 30 days
    calendar = generate_month_calendar(2025, 9)

    assert len(calendar) == 30
    assert calendar[0].date == date(2025, 9, 1)
    assert calendar[29].date == date(2025, 9, 30)

    # Check some known dates
    # Sept 1, 2025 is a Monday (working day)
    assert calendar[0].day_type == DayType.WORKING_DAY
    # Sept 6, 2025 is a Saturday
    assert calendar[5].day_type == DayType.WEEKEND
    # Sept 7, 2025 is a Sunday
    assert calendar[6].day_type == DayType.WEEKEND


def test_calculate_month_stats_basic():
    """Test basic month stats calculation."""
    # Create sample data for a month with 20 working days
    # Let's say we worked 10 days with 8 hours each
    records = []
    for day in range(1, 11):
        target_date = date(2025, 9, day)
        entry = WorkEntry(
            workplace=WorkplaceType.OFFICE,
            clock_in=Duration.parse("09:00"),
            clock_out=Duration.parse("18:00"),  # 9 hours, minus 1h break = 8h
            duration=Duration(8 * 60),
            category="Attendance/Work",
        )
        records.append(
            DayRecord(date=target_date, day_type=DayType.WORKING_DAY, entries=[entry], memo="")
        )

    stats = calculate_month_stats(2025, 9, records)

    # September 2025 should have ~22 working days (need to verify)
    assert stats.working_days > 0
    assert stats.total_required_hours == stats.working_days * 8
    assert stats.wfh_quota_hours == stats.working_days * 1
    assert stats.office_required_hours == stats.total_required_hours - stats.wfh_quota_hours
    assert stats.actual_office_hours == 80.0  # 10 days * 8 hours


def test_calculate_month_stats_with_wfh():
    """Test month stats with WFH and office mix."""
    records = [
        DayRecord(
            date=date(2025, 9, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(607),  # 10h 7m
                    category="Attendance/Work",
                )
            ],
            memo="",
        ),
        DayRecord(
            date=date(2025, 9, 2),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(488),  # 8h 8m
                    category="Attendance/Work",
                ),
                WorkEntry(
                    workplace=WorkplaceType.WFH,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(148),  # 2h 28m
                    category="Attendance/Work",
                ),
            ],
            memo="",
        ),
        DayRecord(
            date=date(2025, 9, 3),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.WFH,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(680),  # 11h 20m
                    category="Attendance/Work",
                )
            ],
            memo="WFH",
        ),
    ]

    stats = calculate_month_stats(2025, 9, records)

    # Check office and WFH hours
    assert stats.actual_office_hours == pytest.approx((607 + 488) / 60, rel=0.01)
    assert stats.actual_wfh_hours == pytest.approx((148 + 680) / 60, rel=0.01)


def test_calculate_month_stats_with_planned():
    """Test month stats with planned future days."""
    # One actual day
    records = [
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

    # Two planned days
    planned = [
        PlannedDay(date=date(2025, 9, 15), office_minutes=0, remote_minutes=480, note="WFH"),
        PlannedDay(date=date(2025, 9, 16), office_minutes=480, remote_minutes=0, note=""),
    ]

    stats = calculate_month_stats(2025, 9, records, planned)

    assert stats.actual_office_hours == 8.0
    assert stats.planned_office_hours == 8.0
    assert stats.total_office_hours == 16.0

    assert stats.actual_wfh_hours == 0.0
    assert stats.planned_wfh_hours == 8.0
    assert stats.total_wfh_hours == 8.0


def test_calculate_month_stats_paid_leave():
    """Test that paid leave is counted correctly."""
    records = [
        DayRecord(
            date=date(2025, 9, 22),
            day_type=DayType.PAID_LEAVE,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),  # 8 hours
                    category="Paid Leave",
                )
            ],
            memo="",
        )
    ]

    stats = calculate_month_stats(2025, 9, records)

    assert stats.paid_leave_days == 1


def test_wfh_over_quota():
    """Test calculation of WFH over quota."""
    # If working days = 20, quota = 20 hours
    # If we do 30 hours WFH, we're 10 hours over
    stats = calculate_month_stats(
        2025,
        9,
        [
            DayRecord(
                date=date(2025, 9, 1),
                day_type=DayType.WORKING_DAY,
                entries=[
                    WorkEntry(
                        workplace=WorkplaceType.WFH,
                        clock_in=None,
                        clock_out=None,
                        duration=Duration(30 * 60),  # 30 hours
                        category="Attendance/Work",
                    )
                ],
                memo="",
            )
        ],
    )

    # WFH over quota should be positive if over
    assert stats.wfh_over_quota > 0


def test_office_deficit():
    """Test calculation of office hour deficit."""
    # If we need 140 hours in office but only did 100, deficit is 40
    records = [
        DayRecord(
            date=date(2025, 9, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(100 * 60),  # 100 hours
                    category="Attendance/Work",
                )
            ],
            memo="",
        )
    ]

    stats = calculate_month_stats(2025, 9, records)

    # Office deficit should be positive if under required
    if stats.office_required_hours > 100:
        assert stats.office_deficit > 0
    else:
        assert stats.office_deficit <= 0
