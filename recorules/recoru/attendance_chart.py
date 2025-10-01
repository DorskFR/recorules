"""Attendance chart data structures."""

import re
from enum import Enum

from bs4 import Tag


class ChartColumn(str, Enum):
    """Column names in the attendance chart."""

    DATE = "日付"
    WORKPLACE = "作業場所"
    CATEGORY = "勤務区分"
    START = "開始"
    END = "終了"
    WORK_TIME = "労働時間"
    MEMO = "メモ"


class ChartHeader:
    """Header of the attendance chart."""

    def __init__(self, tag: Tag) -> None:
        self._column_indices: dict[str, int] = {
            ChartCell(column).text.strip(): i
            for i, column in enumerate(tag.find_all("td", recursive=False))
        }

    def get_column_index(self, column: ChartColumn) -> int:
        """Get the index of a column."""
        return self._column_indices[column]

    def has_column(self, column: ChartColumn) -> bool:
        """Check if a column exists."""
        return column in self._column_indices


class ChartCell:
    """Single cell of the attendance chart."""

    def __init__(self, tag: Tag) -> None:
        self._tag = tag

    @property
    def text(self) -> str:
        """Get the text content of the cell."""
        return self._tag.text.strip()

    @property
    def color(self) -> str:
        """Get the color style of the cell."""
        label = self._tag.find("label", recursive=False)
        if not label or not hasattr(label, "attrs"):
            return ""
        style_val = label.attrs.get("style", "")
        if isinstance(style_val, list):
            style_val = " ".join(str(s) for s in style_val)
        return str(style_val).removeprefix("color: ").removesuffix(";")


class ChartRowEntry:
    """Sub-row of the attendance chart."""

    def __init__(self, header: ChartHeader, tag: Tag) -> None:
        self._header = header
        self._tag = tag

    def __getitem__(self, column: ChartColumn) -> ChartCell:
        column_index = self._header.get_column_index(column)
        column_tag = self._tag.select_one(f"td:nth-child({column_index + 1})")
        if not column_tag:
            msg = f"Could not find column {column}"
            raise ValueError(msg)
        return ChartCell(column_tag)

    @property
    def day(self) -> ChartCell:
        """Get the date cell."""
        return self[ChartColumn.DATE]

    @property
    def workplace(self) -> str:
        """Get the workplace name."""
        return self[ChartColumn.WORKPLACE].text

    @property
    def category(self) -> str:
        """Get the work category."""
        return self[ChartColumn.CATEGORY].text

    @property
    def clock_in_time(self) -> str:
        """Get the clock-in time."""
        return self[ChartColumn.START].text

    @property
    def clock_out_time(self) -> str:
        """Get the clock-out time."""
        return self[ChartColumn.END].text

    @property
    def work_time(self) -> str:
        """Get the work time."""
        return self[ChartColumn.WORK_TIME].text

    @property
    def memo(self) -> str:
        """Get the memo text."""
        return self[ChartColumn.MEMO].text


class ChartRow:
    """Row of the attendance chart."""

    _date_regex = re.compile(r"^(\d{1,2})\/(\d{1,2})\(.\)$")

    def __init__(self, entries: list[ChartRowEntry]) -> None:
        if not entries:
            msg = "Empty ChartRow"
            raise ValueError(msg)
        self._entries = entries

    @property
    def entries(self) -> list[ChartRowEntry]:
        """Get all entries in this row."""
        return self._entries

    @property
    def day(self) -> ChartCell:
        """Get the date cell."""
        return self._entries[0][ChartColumn.DATE]

    @property
    def day_of_month(self) -> int:
        """Extract the day of month from the date string."""
        match = ChartRow._date_regex.match(self._entries[0].day.text)
        if not match:
            return 0
        return int(match.group(2))

    @property
    def memo(self) -> str:
        """Get the memo text."""
        return self._entries[0][ChartColumn.MEMO].text


type AttendanceChart = list[ChartRow]
