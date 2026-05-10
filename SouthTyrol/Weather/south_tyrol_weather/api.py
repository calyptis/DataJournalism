from datetime import date

import pandas as pd
import requests

from south_tyrol_weather.config import API_BASE, TIMEOUT


def get_stations() -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/stations", params={"output_format": "CSV"}, timeout=TIMEOUT)
    r.raise_for_status()
    return pd.read_csv(pd.io.common.StringIO(r.text))


def get_sensors(scode: str) -> list[str]:
    r = requests.get(
        f"{API_BASE}/sensors",
        params={"station_code": scode, "output_format": "CSV"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200 or not r.text.strip():
        return []
    try:
        df = pd.read_csv(pd.io.common.StringIO(r.text))
        return df["TYPE"].tolist()
    except Exception:
        return []


def get_timeseries(scode: str, sensor: str, date_from: str, date_to: str) -> pd.Series:
    """Return a daily-max Series indexed by date (tz-naive). Empty on any error."""
    r = requests.get(
        f"{API_BASE}/timeseries",
        params={
            "station_code": scode,
            "sensor_code": sensor,
            "output_format": "CSV",
            "date_from": date_from,
            "date_to": date_to,
        },
        timeout=TIMEOUT,
    )
    if r.status_code != 200 or not r.text.strip():
        return pd.Series(dtype=float, name=scode)
    try:
        df = pd.read_csv(pd.io.common.StringIO(r.text))
        # Strip trailing timezone abbreviations like "CET" / "CEST" before parsing
        df["DATE"] = pd.to_datetime(
            df["DATE"].str.replace(r"[A-Z]{2,4}$", "", regex=True),
            format="%Y-%m-%dT%H:%M:%S",
        )
        df["date"] = df["DATE"].dt.normalize()
        daily_max = df.groupby("date")["VALUE"].max().rename(scode)
        return daily_max
    except Exception:
        return pd.Series(dtype=float, name=scode)
