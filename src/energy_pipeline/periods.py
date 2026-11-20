"""Small date helpers shared by the extract scripts.

Raw files are stored one per calendar month (data/raw/<source>/YYYY-MM.csv.gz)
so a refresh only needs to re-download the newest months.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class Month:
    year: int
    month: int

    @classmethod
    def parse(cls, text: str) -> "Month":
        y, m = text.split("-")
        return cls(int(y), int(m))

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        """First day of the next month (exclusive end)."""
        return self.next().start

    def next(self) -> "Month":
        return Month(self.year + (self.month == 12), 1 if self.month == 12 else self.month + 1)

    def __lt__(self, other: "Month") -> bool:
        return (self.year, self.month) < (other.year, other.month)

    def __le__(self, other: "Month") -> bool:
        return (self.year, self.month) <= (other.year, other.month)


def month_range(first: Month, last: Month) -> list[Month]:
    """All months from first to last, inclusive."""
    out, m = [], first
    while m <= last:
        out.append(m)
        m = m.next()
    return out


def last_complete_month(today: date | None = None) -> Month:
    today = today or datetime.now(timezone.utc).date()
    first_of_this = date(today.year, today.month, 1)
    prev = first_of_this - timedelta(days=1)
    return Month(prev.year, prev.month)


def current_month(today: date | None = None) -> Month:
    today = today or datetime.now(timezone.utc).date()
    return Month(today.year, today.month)


def windows(start: date, end: date, days: int) -> list[tuple[date, date]]:
    """Split [start, end) into consecutive windows of at most `days` days."""
    out, s = [], start
    while s < end:
        e = min(s + timedelta(days=days), end)
        out.append((s, e))
        s = e
    return out


def iso_minute(d: date) -> str:
    """Format a date as the UTC minute string the Carbon Intensity API expects."""
    return f"{d.isoformat()}T00:00Z"
