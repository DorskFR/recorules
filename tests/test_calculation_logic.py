"""Comprehensive tests for calculate_month_stats logic."""

from datetime import date

from recorules.calculator import calculate_month_stats
from recorules.duration import Duration
from recorules.models import DayRecord, DayType, WorkEntry, WorkplaceType


def test_paid_leave_reduces_requirements():
    """Paid leave should reduce required hours but not count as worked."""
    # 2 working days: 1 normal work, 1 paid leave
    records = [
        DayRecord(
            date=date(2025, 9, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),  # 8h
                    category="Attendance/Work",
                )
            ],
            memo="",
        ),
        DayRecord(
            date=date(2025, 9, 2),
            day_type=DayType.PAID_LEAVE,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),  # Leave entry has 8h but filtered by _is_leave_entry
                    category="Paid Leave",
                )
            ],
            memo="",
        ),
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Working days = 2 (both count as working days in calendar)
    assert stats.working_days == 2
    # Paid leave days = 1
    assert stats.paid_leave_days == 1
    # Required = (2 - 1) * 8 = 8 hours
    assert stats.total_required_hours == 8.0
    # Office worked = 8h (leave entry filtered out)
    assert stats.actual_office_hours == 8.0
    # Balance = 8 - 8 = 0
    assert stats.balance_minutes == 0


def test_unpaid_leave_still_required():
    """Unpaid leave should NOT reduce required hours."""
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
        ),
        DayRecord(
            date=date(2025, 9, 2),
            day_type=DayType.UNPAID_LEAVE,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),  # Filtered out
                    category="Unpaid Leave",
                )
            ],
            memo="",
        ),
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Working days = 2 (unpaid leave counts as working day)
    assert stats.working_days == 2
    # Paid leave days = 0
    assert stats.paid_leave_days == 0
    # Required = 2 * 8 = 16 hours (unpaid leave doesn't reduce it)
    assert stats.total_required_hours == 16.0
    # Worked = 8h (unpaid leave entry filtered out)
    assert stats.actual_office_hours == 8.0
    # Balance = 8 - 16 = -8h = -480 min
    assert stats.balance_minutes == -480


def test_wfh_quota_not_reduced_by_leave():
    """WFH quota is based on working days, not reduced by paid leave."""
    # 20 working days total, 1 paid leave
    records = [
        # 19 normal working days with 8h each
        *[
            DayRecord(
                date=date(2025, 9, day),
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
            for day in range(1, 20)
        ],
        # 1 paid leave
        DayRecord(
            date=date(2025, 9, 20),
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
        ),
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Working days = 20
    assert stats.working_days == 20
    # Required hours = (20 - 1) * 8 = 152
    assert stats.total_required_hours == 152.0
    # WFH quota = 20 * 1 = 20 (NOT 19!)
    assert stats.wfh_quota_hours == 20.0
    # Office required = 152 - 20 = 132
    assert stats.office_required_hours == 132.0


def test_wfh_over_quota_capped_in_balance():
    """Balance and total_deficit both cap WFH at quota."""
    # Realistic: 20 working days, need 160h
    # Work exactly 160h: 136h office (17 days) + 24h WFH (3 days)
    # WFH quota: 20h (only 2.5 days allowed)
    # Both balance and deficit show shortage due to WFH cap (only 20h of the 24h WFH counts)
    records = [
        # 17 days office (136h)
        *[
            DayRecord(
                date=date(2025, 9, day),
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
            for day in range(1, 18)
        ],
        # 3 days WFH (24h total)
        *[
            DayRecord(
                date=date(2025, 9, day),
                day_type=DayType.WORKING_DAY,
                entries=[
                    WorkEntry(
                        workplace=WorkplaceType.WFH,
                        clock_in=None,
                        clock_out=None,
                        duration=Duration(480),
                        category="Attendance/Work",
                    )
                ],
                memo="",
            )
            for day in range(18, 21)
        ],
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Working days = 20
    assert stats.working_days == 20
    # Required = 20 * 8 = 160h
    assert stats.total_required_hours == 160.0
    # Office = 136h
    assert stats.actual_office_hours == 136.0
    # WFH = 24h (3 full days)
    assert stats.actual_wfh_hours == 24.0
    # WFH quota = 20h
    assert stats.wfh_quota_hours == 20.0
    # WFH over quota = 24 - 20 = 4h
    assert stats.wfh_over_quota == 4.0
    # Balance (capped): worked (136h + 20h capped WFH) - required (160h) = -4h = -240min
    assert stats.balance_minutes == -240
    # total_deficit (capped) also shows: (136 + 20 capped) - 160 = -4h
    assert stats.total_deficit == 4.0


def test_weekend_not_counted_as_working_day():
    """Weekends should not count as working days."""
    records = [
        DayRecord(
            date=date(2025, 10, 4),  # Saturday
            day_type=DayType.WEEKEND,
            entries=[],
            memo="",
        ),
        DayRecord(
            date=date(2025, 10, 5),  # Sunday
            day_type=DayType.WEEKEND,
            entries=[],
            memo="",
        ),
    ]

    stats, _ = calculate_month_stats(2025, 10, records)

    assert stats.working_days == 0
    assert stats.total_required_hours == 0.0


def test_balance_calculation():
    """Test balance calculation is correct."""
    # Work 10h on one day, need 8h
    records = [
        DayRecord(
            date=date(2025, 9, 1),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(600),  # 10h
                    category="Attendance/Work",
                )
            ],
            memo="",
        )
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Working days = 1, required = 8h, worked = 10h
    # Balance = 10h - 8h = 2h = 120min
    assert stats.balance_minutes == 120


def test_leave_entries_filtered_from_worked_time():
    """Leave entries should be filtered from office/remote minutes."""
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
        ),
        DayRecord(
            date=date(2025, 9, 2),
            day_type=DayType.PAID_LEAVE,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),
                    category="Paid Leave",  # Should be filtered
                )
            ],
            memo="",
        ),
    ]

    stats, _ = calculate_month_stats(2025, 9, records)

    # Only the first day's 8h should count
    assert stats.actual_office_hours == 8.0
    # Leave entry should NOT add to office hours
    # Total worked = 8h, required = (2 - 1) * 8 = 8h, balance = 0
    assert stats.balance_minutes == 0


def test_planned_entries_counted():
    """Entries with category='Planned' should be counted."""
    records = [
        DayRecord(
            date=date(2025, 10, 15),
            day_type=DayType.WORKING_DAY,
            entries=[
                WorkEntry(
                    workplace=WorkplaceType.OFFICE,
                    clock_in=None,
                    clock_out=None,
                    duration=Duration(480),
                    category="Planned",  # Should be counted
                )
            ],
            memo="",
        )
    ]

    stats, _ = calculate_month_stats(2025, 10, records)

    # Planned entries should count as worked time
    assert stats.actual_office_hours == 8.0
