"""Tests for database operations."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from recorules.database import PlanningDatabase
from recorules.models import PlannedDay


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db = PlanningDatabase(db_path)
    yield db

    # Cleanup
    db_path.unlink(missing_ok=True)


def test_save_and_get_planned_day(temp_db):
    """Test saving and retrieving a planned day."""
    planned = PlannedDay(
        date=date(2025, 9, 15),
        office_minutes=0,
        remote_minutes=480,
        is_paid_leave=False,
        note="WFH day",
    )

    temp_db.save_planned_day(planned)
    retrieved = temp_db.get_planned_day(date(2025, 9, 15))

    assert retrieved is not None
    assert retrieved.date == planned.date
    assert retrieved.office_minutes == planned.office_minutes
    assert retrieved.remote_minutes == planned.remote_minutes
    assert retrieved.is_paid_leave == planned.is_paid_leave
    assert retrieved.note == planned.note


def test_update_planned_day(temp_db):
    """Test updating an existing planned day."""
    planned1 = PlannedDay(date=date(2025, 9, 15), office_minutes=480, remote_minutes=0)
    temp_db.save_planned_day(planned1)

    # Update
    planned2 = PlannedDay(
        date=date(2025, 9, 15), office_minutes=0, remote_minutes=480, note="Changed to WFH"
    )
    temp_db.save_planned_day(planned2)

    retrieved = temp_db.get_planned_day(date(2025, 9, 15))
    assert retrieved.office_minutes == 0
    assert retrieved.remote_minutes == 480
    assert retrieved.note == "Changed to WFH"


def test_get_nonexistent_planned_day(temp_db):
    """Test getting a planned day that doesn't exist."""
    retrieved = temp_db.get_planned_day(date(2025, 9, 15))
    assert retrieved is None


def test_get_planned_days_for_month(temp_db):
    """Test retrieving all planned days for a month."""
    # Add planned days in September and October
    temp_db.save_planned_day(
        PlannedDay(date=date(2025, 9, 15), office_minutes=480, remote_minutes=0)
    )
    temp_db.save_planned_day(
        PlannedDay(date=date(2025, 9, 20), office_minutes=0, remote_minutes=480)
    )
    temp_db.save_planned_day(
        PlannedDay(date=date(2025, 10, 5), office_minutes=480, remote_minutes=0)
    )

    # Get September days
    september_days = temp_db.get_planned_days_for_month(2025, 9)

    assert len(september_days) == 2
    assert september_days[0].date == date(2025, 9, 15)
    assert september_days[1].date == date(2025, 9, 20)

    # Get October days
    october_days = temp_db.get_planned_days_for_month(2025, 10)
    assert len(october_days) == 1
    assert october_days[0].date == date(2025, 10, 5)


def test_delete_planned_day(temp_db):
    """Test deleting a planned day."""
    planned = PlannedDay(date=date(2025, 9, 15), office_minutes=480, remote_minutes=0)
    temp_db.save_planned_day(planned)

    # Verify it exists
    assert temp_db.get_planned_day(date(2025, 9, 15)) is not None

    # Delete
    temp_db.delete_planned_day(date(2025, 9, 15))

    # Verify it's gone
    assert temp_db.get_planned_day(date(2025, 9, 15)) is None


def test_paid_leave(temp_db):
    """Test paid leave flag."""
    planned = PlannedDay(
        date=date(2025, 9, 22), office_minutes=0, remote_minutes=0, is_paid_leave=True, note="PTO"
    )
    temp_db.save_planned_day(planned)

    retrieved = temp_db.get_planned_day(date(2025, 9, 22))
    assert retrieved.is_paid_leave is True
    assert retrieved.note == "PTO"
