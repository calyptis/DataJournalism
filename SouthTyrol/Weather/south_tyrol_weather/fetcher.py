#!/usr/bin/env python3
"""
Download max daily air temperature for all South Tyrol weather stations
via the Open Meteo Data API (http://daten.buergernetz.bz.it/services/meteo/v1/).

When multiple stations share the same geographic location, keeps the one with
the most complete LT (Lufttemperatur) timeseries.

Output: data/max_daily_temp.csv
Columns: date, <SCODE>, <SCODE>, ...  (one column per station)
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests

BASE_URL = "http://daten.buergernetz.bz.it/services/meteo/v1"
SENSOR = "LT"
DATE_FROM = "19800101"
DATE_TO = date.today().strftime("%Y%m%d")
LOCATION_PRECISION = 3  # ~100 m grouping
MAX_WORKERS = 12
OUTPUT_PATH = "data/max_daily_temp.csv"
TIMEOUT = 60


def get_stations() -> pd.DataFrame:
    r = requests.get(
        f"{BASE_URL}/stations",
        params={"output_format": "CSV"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return pd.read_csv(pd.io.common.StringIO(r.text))


def has_lt_sensor(scode: str) -> bool:
    """Return True if this station reports LT measurements."""
    r = requests.get(
        f"{BASE_URL}/sensors",
        params={"station_code": scode, "output_format": "CSV"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200 or not r.text.strip():
        return False
    try:
        df = pd.read_csv(pd.io.common.StringIO(r.text))
        return SENSOR in df["TYPE"].values
    except Exception:
        return False


def fetch_timeseries(scode: str) -> pd.Series:
    """Fetch the full LT timeseries and return a daily-max Series indexed by date."""
    r = requests.get(
        f"{BASE_URL}/timeseries",
        params={
            "station_code": scode,
            "sensor_code": SENSOR,
            "output_format": "CSV",
            "date_from": DATE_FROM,
            "date_to": DATE_TO,
        },
        timeout=TIMEOUT,
    )
    if r.status_code != 200 or not r.text.strip():
        return pd.Series(dtype=float, name=scode)
    try:
        df = pd.read_csv(pd.io.common.StringIO(r.text))
        df["DATE"] = pd.to_datetime(df["DATE"], utc=True)
        df["date"] = df["DATE"].dt.normalize().dt.tz_localize(None)
        daily_max = df.groupby("date")["VALUE"].max()
        daily_max.name = scode
        return daily_max
    except Exception:
        return pd.Series(dtype=float, name=scode)


def location_key(row) -> tuple:
    return (round(row["LAT"], LOCATION_PRECISION), round(row["LONG"], LOCATION_PRECISION))


def main():
    print("Fetching station list…")
    stations = get_stations()
    print(f"  {len(stations)} stations found")

    # Filter to stations that have an LT sensor
    print("Checking which stations have LT sensor (parallel)…")
    lt_stations = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(has_lt_sensor, row["SCODE"]): row for _, row in stations.iterrows()}
        for i, fut in enumerate(as_completed(futures), 1):
            row = futures[fut]
            if fut.result():
                lt_stations.append(row)
            if i % 20 == 0 or i == len(futures):
                print(f"  checked {i}/{len(futures)} stations, {len(lt_stations)} with LT so far")

    lt_df = pd.DataFrame(lt_stations).reset_index(drop=True)
    print(f"\n{len(lt_df)} stations have LT sensor")

    # Group by location, resolve duplicates by fetching all timeseries
    lt_df["_loc"] = lt_df.apply(location_key, axis=1)
    loc_groups = lt_df.groupby("_loc")["SCODE"].apply(list)
    multi_loc = loc_groups[loc_groups.apply(len) > 1]
    single_loc = loc_groups[loc_groups.apply(len) == 1]

    print(f"  {len(single_loc)} unique locations, {len(multi_loc)} locations with multiple stations")

    # Stations at unique locations — fetch directly
    unique_scodes = [codes[0] for codes in single_loc]

    # For multi-station locations we need to compare completeness — also fetch them all
    multi_scodes = [scode for codes in multi_loc for scode in codes]

    all_scodes_to_fetch = unique_scodes + multi_scodes
    print(f"\nDownloading timeseries for {len(all_scodes_to_fetch)} stations…")

    series_map: dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_timeseries, s): s for s in all_scodes_to_fetch}
        for i, fut in enumerate(as_completed(futures), 1):
            scode = futures[fut]
            series_map[scode] = fut.result()
            if i % 10 == 0 or i == len(futures):
                print(f"  downloaded {i}/{len(futures)}")

    # For each multi-station location pick the one with most non-null records
    winner_scodes = list(unique_scodes)
    for loc, codes in multi_loc.items():
        best = max(codes, key=lambda s: series_map[s].count())
        counts = {s: series_map[s].count() for s in codes}
        print(f"  Location {loc}: {counts} → keeping {best}")
        winner_scodes.append(best)

    print(f"\nMerging {len(winner_scodes)} timeseries…")
    combined = pd.concat(
        [series_map[s] for s in winner_scodes if not series_map[s].empty],
        axis=1,
    )
    combined.index.name = "date"
    combined.sort_index(inplace=True)

    # Attach station metadata as column-level info via a comment header
    meta = lt_df.set_index("SCODE")[["NAME_D", "ALT", "LAT", "LONG"]]

    combined.to_csv(OUTPUT_PATH)
    print(f"Saved {combined.shape} (days × stations) to {OUTPUT_PATH}")

    # Also write a station metadata sidecar
    meta_path = OUTPUT_PATH.replace(".csv", "_stations.csv")
    meta.loc[meta.index.isin(winner_scodes)].to_csv(meta_path)
    print(f"Station metadata saved to {meta_path}")


if __name__ == "__main__":
    main()
