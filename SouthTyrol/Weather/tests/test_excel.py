"""
Tests for excel.py — integration tests hit the live provincial website.
"""
import pandas as pd
import pytest

from south_tyrol_weather.excel import get_excel_urls, parse_excel, scode_from_url

SAMPLE_URL = (
    "https://static-wetter.provinz.bz.it/web-data/measurment-data/"
    "47400MS-Antholz%20-%20Obertal-Anterselva%20di%20Sopra"
    "-multiannual-LT-N-daily-temperature-precipitation.xlsx"
)


@pytest.fixture(scope="session")
def excel_urls() -> list[str]:
    return get_excel_urls()


@pytest.fixture(scope="session")
def api_stations() -> pd.DataFrame:
    from south_tyrol_weather.api import get_stations
    return get_stations()


@pytest.fixture(scope="session")
def parsed(api_stations):
    return parse_excel(SAMPLE_URL, api_stations)


# --- get_excel_urls ---

def test_get_excel_urls_nonempty(excel_urls):
    assert len(excel_urls) > 0


def test_get_excel_urls_all_xlsx(excel_urls):
    assert all(u.endswith(".xlsx") for u in excel_urls)


def test_get_excel_urls_contains_sample(excel_urls):
    scodes = [scode_from_url(u) for u in excel_urls]
    assert "47400MS" in scodes


# --- scode_from_url ---

def test_scode_from_url():
    assert scode_from_url(SAMPLE_URL) == "47400MS"


# --- parse_excel ---

def test_parse_excel_returns_station_df(parsed):
    station_df, _ = parsed
    assert isinstance(station_df, pd.DataFrame)
    assert len(station_df) == 1
    assert "scode" in station_df.columns
    assert station_df.iloc[0]["scode"] == "47400MS"


def test_parse_excel_station_has_coordinates(parsed):
    station_df, _ = parsed
    row = station_df.iloc[0]
    assert row["lat"] is not None and row["lon"] is not None
    assert 46.0 < row["lat"] < 47.5   # South Tyrol latitude range
    assert 10.0 < row["lon"] < 12.5   # South Tyrol longitude range


def test_parse_excel_returns_measurements_df(parsed):
    _, meas = parsed
    assert isinstance(meas, pd.DataFrame)
    assert len(meas) > 0


def test_parse_excel_measurements_has_required_columns(parsed):
    _, meas = parsed
    for col in ("scode", "sensor", "date", "daily_max", "daily_min"):
        assert col in meas.columns


def test_parse_excel_contains_lt_sensor(parsed):
    _, meas = parsed
    assert "LT" in meas["sensor"].values


def test_parse_excel_contains_n_sensor(parsed):
    _, meas = parsed
    assert "N" in meas["sensor"].values


def test_parse_excel_lt_daily_max_is_numeric(parsed):
    _, meas = parsed
    lt = meas[meas["sensor"] == "LT"]["daily_max"].dropna()
    assert pd.api.types.is_float_dtype(lt)
    assert lt.between(-50, 50).all()   # plausible temperature range


def test_parse_excel_n_daily_max_is_nonnegative(parsed):
    _, meas = parsed
    n = meas[meas["sensor"] == "N"]["daily_max"].dropna()
    assert (n >= 0).all()


def test_parse_excel_dates_are_valid(parsed):
    _, meas = parsed
    dates = pd.to_datetime(meas["date"])
    assert dates.min().year >= 1980
    assert dates.max().year <= 2030


# --- store integration: daily_min is stored ---

def test_store_persists_daily_min(parsed, tmp_path):
    import duckdb
    from south_tyrol_weather.store import init_db, upsert_measurements, upsert_stations

    station_df, meas = parsed
    db = str(tmp_path / "t.duckdb")
    con = init_db(db)
    upsert_stations(con, station_df)
    upsert_measurements(con, meas)

    lt = con.execute(
        "SELECT daily_min FROM measurements WHERE sensor='LT' AND daily_min IS NOT NULL LIMIT 5"
    ).fetchall()
    assert len(lt) > 0
    con.close()
