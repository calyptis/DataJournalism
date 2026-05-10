"""
Integration tests for api.py — hit the live South Tyrol API.
Run with: poetry run pytest tests/test_api.py
"""
import pandas as pd
import pytest

from south_tyrol_weather.api import get_sensors, get_stations, get_timeseries

KNOWN_STATION = "83200MS"  # Bozen/Bolzano main station


@pytest.fixture(scope="session")
def stations() -> pd.DataFrame:
    return get_stations()


def test_get_stations_returns_nonempty_dataframe(stations):
    assert isinstance(stations, pd.DataFrame)
    assert len(stations) > 0


def test_get_stations_has_required_columns(stations):
    for col in ("SCODE", "NAME_D", "ALT", "LAT", "LONG"):
        assert col in stations.columns


def test_get_sensors_returns_list(stations):
    sensors = get_sensors(KNOWN_STATION)
    assert isinstance(sensors, list)
    assert len(sensors) > 0


def test_get_sensors_includes_lt(stations):
    assert "LT" in get_sensors(KNOWN_STATION)


def test_get_timeseries_returns_series():
    s = get_timeseries(KNOWN_STATION, "LT", "20240101", "20240131")
    assert isinstance(s, pd.Series)
    assert len(s) > 0


def test_get_timeseries_has_date_index():
    s = get_timeseries(KNOWN_STATION, "LT", "20240101", "20240131")
    assert pd.api.types.is_datetime64_any_dtype(s.index)


def test_get_timeseries_values_are_numeric():
    s = get_timeseries(KNOWN_STATION, "LT", "20240101", "20240131")
    assert pd.api.types.is_float_dtype(s)


def test_get_timeseries_returns_empty_series_for_unknown_station():
    s = get_timeseries("DOESNOTEXIST999", "LT", "20240101", "20240131")
    assert isinstance(s, pd.Series)
    assert len(s) == 0
