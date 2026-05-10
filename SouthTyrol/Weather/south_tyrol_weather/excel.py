"""
Scrape and parse the South Tyrol historical weather Excel files.
Source: https://wetter.provinz.bz.it/de/download-messdaten
"""
import io

import pandas as pd
import requests
from bs4 import BeautifulSoup

from south_tyrol_weather.config import EXCEL_PAGE_URL, TIMEOUT

# Excel layout (0-indexed rows, columns)
_ROW_NAME = 7
_ROW_SCODE = 8
_ROW_ELEVATION = 9
_COL_NAME = 2
_COL_SCODE = 2
_COL_ELEVATION = 7
_DATA_START_ROW = 14
_COL_DATE = 2
_COL_PRECIP = 3
_COL_TEMP_MIN = 4
_COL_TEMP_MAX = 5


def get_excel_urls() -> list[str]:
    """Return all .xlsx download hrefs from the provincial weather download page."""
    r = requests.get(EXCEL_PAGE_URL, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        a["href"]
        for a in soup.find_all("a", class_="download")
        if a.get("href", "").endswith(".xlsx")
    ]


def scode_from_url(url: str) -> str:
    """Extract station code from the Excel filename (e.g. '47400MS' from the URL path)."""
    filename = url.split("/")[-1]
    return filename.split("-")[0]


def parse_excel(url: str, api_stations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download and parse one station Excel file.

    Returns (station_df, measurements_df) where measurements_df is in long
    format (scode, sensor, date, daily_max, daily_min).
    """
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()

    raw = pd.read_excel(io.BytesIO(r.content), header=None, engine="openpyxl")
    scode = scode_from_url(url)

    station_df = _build_station_row(raw, scode, api_stations)
    measurements_df = _parse_measurements(raw, scode)

    return station_df, measurements_df


def _build_station_row(raw: pd.DataFrame, scode: str, api_stations: pd.DataFrame) -> pd.DataFrame:
    name = str(raw.iloc[_ROW_NAME, _COL_NAME]).strip()

    api_row = api_stations[api_stations["SCODE"] == scode]
    if not api_row.empty:
        r = api_row.iloc[0]
        altitude, lat, lon = float(r["ALT"]), float(r["LAT"]), float(r["LONG"])
    else:
        try:
            altitude = float(str(raw.iloc[_ROW_ELEVATION, _COL_ELEVATION]).strip())
        except ValueError:
            altitude = None
        lat = lon = None

    return pd.DataFrame([{"scode": scode, "name": name, "altitude": altitude, "lat": lat, "lon": lon}])


def _parse_measurements(raw: pd.DataFrame, scode: str) -> pd.DataFrame:
    data = raw.iloc[_DATA_START_ROW:, [_COL_DATE, _COL_PRECIP, _COL_TEMP_MIN, _COL_TEMP_MAX]].copy()
    data.columns = ["date", "precip_sum", "temp_min", "temp_max"]

    # Drop footer / non-date rows
    data = data[data["date"].notna()]
    data = data[~data["date"].astype(str).str.match(r"^[a-zA-Z]")]

    data["date"] = pd.to_datetime(data["date"], format="%d.%m.%Y", errors="coerce").dt.date
    data = data.dropna(subset=["date"])

    for col in ("precip_sum", "temp_min", "temp_max"):
        data[col] = pd.to_numeric(data[col].replace("---", None), errors="coerce")

    records: list[pd.DataFrame] = []

    lt = data[data["temp_max"].notna() | data["temp_min"].notna()].copy()
    if not lt.empty:
        records.append(pd.DataFrame({
            "scode": scode,
            "sensor": "LT",
            "date": lt["date"].values,
            "daily_max": lt["temp_max"].values,
            "daily_min": lt["temp_min"].values,
        }))

    n = data[data["precip_sum"].notna()].copy()
    if not n.empty:
        records.append(pd.DataFrame({
            "scode": scode,
            "sensor": "N",
            "date": n["date"].values,
            "daily_max": n["precip_sum"].values,
            "daily_min": None,
        }))

    return pd.concat(records, ignore_index=True) if records else pd.DataFrame(
        columns=["scode", "sensor", "date", "daily_max", "daily_min"]
    )
