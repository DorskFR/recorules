"""Recoru session management and data fetching."""

from typing import Self

import requests
from bs4 import BeautifulSoup

from recorules.errors import InvalidRecoruLoginError
from recorules.recoru.attendance_chart import (
    AttendanceChart,
    ChartHeader,
    ChartRow,
    ChartRowEntry,
)


class RecoruSession:
    """Session for interacting with Recoru API."""

    def __init__(self, contract_id: str, auth_id: str, password: str) -> None:
        self._contract_id: str = contract_id
        self._auth_id: str = auth_id
        self._password: str = password
        self._session: requests.Session | None = None

    def __enter__(self) -> Self:
        self._session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            self._session.close()
        self._session = None

    @property
    def session(self) -> requests.Session:
        """Get the active session."""
        if not self._session:
            msg = "RecoruSession should be used as a context manager"
            raise RuntimeError(msg)
        return self._session

    def get_attendance_chart(self, period_point: int = 0) -> AttendanceChart:
        """
        Fetch and parse the attendance chart.

        Args:
            period_point: Month offset from current month (0=current, -1=previous, 1=next)
        """
        self._login()
        response = self.session.post(
            "https://app.recoru.in/ap/home/loadAttendanceChartGadget",
            data={"periodPoint": period_point},
        )
        response.raise_for_status()
        return self._parse_attendance_chart(response.text)

    def _login(self) -> None:
        """Login to Recoru."""
        # Get a session ID
        self.session.get("https://app.recoru.in/ap/")

        url = "https://app.recoru.in/ap/login"
        form_data = {
            "contractId": self._contract_id,
            "authId": self._auth_id,
            "password": self._password,
        }
        response = self.session.post(url, data=form_data)
        response.raise_for_status()
        if "message-err" in response.text:
            raise InvalidRecoruLoginError

    @staticmethod
    def _parse_attendance_chart(text: str) -> AttendanceChart:
        """Parse HTML text into an AttendanceChart."""
        soup = BeautifulSoup(text, "html.parser")
        table = soup.select_one("#ID-attendanceChartGadgetTable")
        if not table:
            msg = "Could not find attendance chart table"
            raise ValueError(msg)

        table_header = table.select_one("thead > tr")
        if not table_header:
            msg = "Could not find table header"
            raise ValueError(msg)
        header = ChartHeader(table_header)

        from bs4 import Tag as BS4Tag

        chart_rows: list[ChartRow] = []
        current_row_entries: list[ChartRowEntry] = []
        table_body = table.find("tbody")
        if not table_body or not isinstance(table_body, BS4Tag):
            return chart_rows

        rows = table_body.find_all("tr")
        for row_elem in rows:
            if not isinstance(row_elem, BS4Tag):
                continue
            entry = ChartRowEntry(header, row_elem)
            if entry.day.text:  # New row
                # Append previous row
                if current_row_entries:
                    chart_rows.append(ChartRow(current_row_entries))
                current_row_entries = [entry]
            else:  # Row with multiple entries
                current_row_entries.append(entry)
        if current_row_entries:
            chart_rows.append(ChartRow(current_row_entries))
        return chart_rows
