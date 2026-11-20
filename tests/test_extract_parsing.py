from datetime import date
from pathlib import Path

from energy_pipeline import extract
from energy_pipeline.periods import Month

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_settlement_date_handles_all_formats():
    assert extract.parse_settlement_date("2024-01-31") == date(2024, 1, 31)
    assert extract.parse_settlement_date("2024-01-31T00:00:00") == date(2024, 1, 31)
    assert extract.parse_settlement_date("01-FEB-2024") == date(2024, 2, 1)
    assert extract.parse_settlement_date("1-Feb-2024") == date(2024, 2, 1)
    assert extract.parse_settlement_date("31/01/2024") == date(2024, 1, 31)
    assert extract.parse_settlement_date("rubbish") is None


def test_split_neso_csv_keeps_raw_text_and_adds_missing_columns():
    parts, seen = extract.split_neso_csv((FIXTURES / "neso_sample.csv").read_text())
    assert set(parts) == {"2024-01", "2024-02", "unparsed"}
    jan = parts["2024-01"]
    assert len(jan) == 2
    assert jan.loc[0, "ND"] == "25000"                # still text, not converted
    assert parts["2024-02"].loc[0, "SETTLEMENT_DATE"] == "01-FEB-2024"  # raw format kept
    assert "GREENLINK_FLOW" in jan.columns and jan["GREENLINK_FLOW"].eq("").all()
    assert "GREENLINK_FLOW" not in seen


def test_pick_year_resources_finds_yearly_csvs():
    package = {"result": {"resources": [
        {"name": "Historic Demand Data 2025", "format": "CSV", "url": "https://x/download/demanddata_2025.csv"},
        {"name": "Historic Demand Data 2024", "format": "CSV", "url": "https://x/download/demanddata_2024.csv"},
        {"name": "Data description", "format": "PDF", "url": "https://x/download/description.pdf"},
    ]}}
    found = extract.pick_year_resources(package, {2024, 2025, 2026})
    assert found == {2024: "https://x/download/demanddata_2024.csv", 2025: "https://x/download/demanddata_2025.csv"}


def test_flatten_intensity_and_generation():
    rows = extract.flatten_intensity({"data": [
        {"from": "2026-01-01T00:00Z", "to": "2026-01-01T00:30Z", "intensity": {"forecast": 150, "actual": 140, "index": "moderate"}}]})
    assert rows == [{"from": "2026-01-01T00:00Z", "to": "2026-01-01T00:30Z", "forecast": 150, "actual": 140, "index": "moderate"}]
    gen = extract.flatten_generation({"data": [{"from": "2026-01-01T00:00Z", "to": "2026-01-01T00:30Z",
                                                "generationmix": [{"fuel": "wind", "perc": 40.5}, {"fuel": "gas", "perc": 30}]}]})
    assert gen[0]["wind_perc"] == 40.5 and gen[0]["gas_perc"] == 30 and gen[0]["coal_perc"] is None


def test_flatten_regional_one_row_per_region():
    payload = {"data": [{"from": "2026-01-01T00:00Z", "to": "2026-01-01T00:30Z", "regions": [
        {"regionid": 1, "shortname": "North Scotland", "dnoregion": "SSE", "intensity": {"forecast": 20, "index": "very low"},
         "generationmix": [{"fuel": "wind", "perc": 80}]},
        {"regionid": 13, "shortname": "London", "dnoregion": "UKPN", "intensity": {"forecast": 180, "index": "moderate"},
         "generationmix": [{"fuel": "gas", "perc": 50}]}]}]}
    rows = extract.flatten_regional(payload)
    assert [r["regionid"] for r in rows] == [1, 13]
    assert rows[0]["wind_perc"] == 80 and rows[1]["gas_perc"] == 50


def test_keep_month_trims_edges_and_repeats():
    rows = [{"from": "2026-01-31T23:30Z", "v": 1}, {"from": "2026-02-01T00:00Z", "v": 2},
            {"from": "2026-02-01T00:00Z", "v": 3}, {"from": "2026-03-01T00:00Z", "v": 4}]
    df = extract._keep_month(rows, Month.parse("2026-02"), ["from"])
    assert df["from"].tolist() == ["2026-02-01T00:00Z"]
    assert df["v"].tolist() == [3]  # the later copy wins


def test_flatten_bank_holidays_and_weather():
    hol = extract.flatten_bank_holidays({"england-and-wales": {"division": "england-and-wales", "events": [
        {"title": "Christmas Day", "date": "2026-12-25", "notes": "", "bunting": True}]}})
    assert hol.to_dict("records") == [{"division": "england-and-wales", "date": "2026-12-25", "title": "Christmas Day", "notes": ""}]
    w = extract.flatten_open_meteo({"hourly": {"time": ["2026-01-01T00:00"], "temperature_2m": [4.2]}}, "Leeds")
    assert list(w.columns) == ["time", "city", "temperature_2m"] and w.loc[0, "city"] == "Leeds"
