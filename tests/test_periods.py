from datetime import date

from energy_pipeline.periods import Month, iso_minute, last_complete_month, month_range, windows


def test_month_range_crosses_year():
    labels = [m.label for m in month_range(Month.parse("2025-11"), Month.parse("2026-02"))]
    assert labels == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_month_end_is_exclusive_next_month():
    assert Month.parse("2024-02").end == date(2024, 3, 1)
    assert Month.parse("2024-12").end == date(2025, 1, 1)


def test_windows_cover_range_without_overlap():
    w = windows(date(2026, 1, 1), date(2026, 2, 1), 14)
    assert w[0] == (date(2026, 1, 1), date(2026, 1, 15))
    assert w[-1][1] == date(2026, 2, 1)
    assert all(a[1] == b[0] for a, b in zip(w, w[1:]))
    assert all((e - s).days <= 14 for s, e in w)


def test_last_complete_month():
    assert last_complete_month(date(2026, 11, 20)).label == "2026-10"
    assert last_complete_month(date(2026, 1, 3)).label == "2025-12"


def test_iso_minute_format():
    assert iso_minute(date(2026, 3, 29)) == "2026-03-29T00:00Z"
