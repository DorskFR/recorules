"""SQLite database for storing future planning data."""

import sqlite3
from datetime import date
from pathlib import Path

from recorules.models import PlannedDay

DEFAULT_DB_PATH = Path.home() / ".config" / "recorules" / "planning.db"


class PlanningDatabase:
    """Database for storing and retrieving planned days."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS planned_days (
                    date TEXT PRIMARY KEY,
                    office_minutes INTEGER NOT NULL,
                    remote_minutes INTEGER NOT NULL,
                    is_paid_leave INTEGER NOT NULL,
                    note TEXT
                )
            """)
            conn.commit()

    def save_planned_day(self, planned: PlannedDay) -> None:
        """Save or update a planned day."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO planned_days
                (date, office_minutes, remote_minutes, is_paid_leave, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    planned.date.isoformat(),
                    planned.office_minutes,
                    planned.remote_minutes,
                    1 if planned.is_paid_leave else 0,
                    planned.note,
                ),
            )
            conn.commit()

    def get_planned_day(self, target_date: date) -> PlannedDay | None:
        """Get a planned day by date."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT date, office_minutes, remote_minutes, is_paid_leave, note "
                "FROM planned_days WHERE date = ?",
                (target_date.isoformat(),),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return PlannedDay(
                date=date.fromisoformat(row[0]),
                office_minutes=row[1],
                remote_minutes=row[2],
                is_paid_leave=bool(row[3]),
                note=row[4] or "",
            )

    def get_planned_days_for_month(self, year: int, month: int) -> list[PlannedDay]:
        """Get all planned days for a specific month."""
        start_date = date(year, month, 1)
        # Handle December edge case
        end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT date, office_minutes, remote_minutes, is_paid_leave, note "
                "FROM planned_days WHERE date >= ? AND date < ? ORDER BY date",
                (start_date.isoformat(), end_date.isoformat()),
            )

            planned_days = []
            for row in cursor:
                planned_days.append(
                    PlannedDay(
                        date=date.fromisoformat(row[0]),
                        office_minutes=row[1],
                        remote_minutes=row[2],
                        is_paid_leave=bool(row[3]),
                        note=row[4] or "",
                    )
                )

            return planned_days

    def delete_planned_day(self, target_date: date) -> None:
        """Delete a planned day."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM planned_days WHERE date = ?", (target_date.isoformat(),))
            conn.commit()

    def clear_all(self) -> None:
        """Clear all planned days (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM planned_days")
            conn.commit()
