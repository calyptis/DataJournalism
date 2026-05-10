"""
Unit tests for store.py — use in-memory DuckDB, no file I/O.
"""
from datetime import date

import pandas as pd
import pytest

from south_tyrol_weather.store import init_db, last_dates, upsert_measurements, upsert_stations


@pytest.fixture
def con():
    c = init_db(":memory:")
    yield c
    c.close()


def _stations_df(**overrides) -> pd.DataFrame:
    row = {"scode": "BZO", "name": "Bozen", "altitude": 262.0, "lat": 46.49, "lon": 11.33}
    row.update(overrides)
    return pd.DataFrame([row])


def _measurements_df(**overrides) -> pd.DataFrame:
    row = {"scode": "BZO", "sensor": "LT", "date": date(2024, 1, 15), "daily_max": 8.5}
    row.update(overrides)
    return pd.DataFrame([row])


# --- schema ---

def test_init_creates_stations_table(con):
    result = con.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'stations'").fetchall()
    assert len(result) == 1


def test_init_creates_measurements_table(con):
    result = con.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'measurements'").fetchall()
    assert len(result) == 1


# --- upsert_stations ---

def test_upsert_stations_inserts_row(con):
    upsert_stations(con, _stations_df())
    count = con.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    assert count == 1


def test_upsert_stations_is_idempotent(con):
    upsert_stations(con, _stations_df())
    upsert_stations(con, _stations_df())
    count = con.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    assert count == 1


def test_upsert_stations_updates_existing(con):
    upsert_stations(con, _stations_df(name="Old Name"))
    upsert_stations(con, _stations_df(name="New Name"))
    name = con.execute("SELECT name FROM stations WHERE scode = 'BZO'").fetchone()[0]
    assert name == "New Name"


# --- upsert_measurements ---

def test_upsert_measurements_inserts_row(con):
    upsert_stations(con, _stations_df())
    upsert_measurements(con, _measurements_df())
    count = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    assert count == 1


def test_upsert_measurements_is_idempotent(con):
    upsert_stations(con, _stations_df())
    upsert_measurements(con, _measurements_df())
    upsert_measurements(con, _measurements_df())
    count = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    assert count == 1


def test_upsert_measurements_updates_value(con):
    upsert_stations(con, _stations_df())
    upsert_measurements(con, _measurements_df(daily_max=5.0))
    upsert_measurements(con, _measurements_df(daily_max=9.9))
    val = con.execute("SELECT daily_max FROM measurements WHERE scode='BZO'").fetchone()[0]
    assert val == pytest.approx(9.9)


# --- last_dates ---

def test_last_dates_returns_none_for_unknown_station(con):
    result = last_dates(con, ["BZO"], "LT")
    assert result["BZO"] is None


def test_last_dates_returns_correct_date(con):
    upsert_stations(con, _stations_df())
    upsert_measurements(con, _measurements_df(date=date(2024, 3, 10)))
    upsert_measurements(con, _measurements_df(date=date(2024, 3, 11)))
    result = last_dates(con, ["BZO"], "LT")
    assert result["BZO"] == date(2024, 3, 11)


def test_last_dates_ignores_other_sensors(con):
    upsert_stations(con, _stations_df())
    upsert_measurements(con, _measurements_df(sensor="N", date=date(2024, 6, 1)))
    result = last_dates(con, ["BZO"], "LT")
    assert result["BZO"] is None
