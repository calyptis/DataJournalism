from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd

from south_tyrol_weather.api import get_sensors, get_stations, get_timeseries
from south_tyrol_weather.config import (
    DATE_FROM,
    DB_PATH,
    LOCATION_PRECISION,
    MAX_WORKERS,
    SENSORS,
)
from south_tyrol_weather.excel import get_excel_urls, parse_excel, scode_from_url
from south_tyrol_weather.store import init_db, last_dates, upsert_measurements, upsert_stations


def _location_key(row) -> tuple:
    return (round(row["LAT"], LOCATION_PRECISION), round(row["LONG"], LOCATION_PRECISION))


def _filter_stations_by_sensor(stations: pd.DataFrame, sensor: str) -> pd.DataFrame:
    """Return subset of stations that have the given sensor (parallel checks)."""
    matching = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(get_sensors, row["SCODE"]): row
            for _, row in stations.iterrows()
        }
        total = len(futures)
        done = 0
        for fut in as_completed(futures):
            row = futures[fut]
            done += 1
            if sensor in fut.result():
                matching.append(row)
            if done % 20 == 0 or done == total:
                print(f"  sensor check: {done}/{total}, {len(matching)} with {sensor}")
    return pd.DataFrame(matching).reset_index(drop=True)


def _resolve_duplicates(df: pd.DataFrame, sensor: str) -> list[str]:
    """For stations sharing the same location, keep the one with the most records."""
    df = df.copy()
    df["_loc"] = df.apply(_location_key, axis=1)
    loc_groups = df.groupby("_loc")["SCODE"].apply(list)

    unique_scodes = [codes[0] for codes in loc_groups if len(codes) == 1]
    multi_groups = [codes for codes in loc_groups if len(codes) > 1]

    if not multi_groups:
        return unique_scodes

    multi_scodes = [s for codes in multi_groups for s in codes]
    today = date.today().strftime("%Y%m%d")
    print(f"  resolving {len(multi_groups)} duplicate locations ({len(multi_scodes)} stations)…")

    series_map: dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(get_timeseries, s, sensor, DATE_FROM, today): s for s in multi_scodes}
        for fut in as_completed(futures):
            scode = futures[fut]
            series_map[scode] = fut.result()

    winners = list(unique_scodes)
    for codes in multi_groups:
        best = max(codes, key=lambda s: series_map[s].count())
        winners.append(best)
    return winners


def run(full: bool = False) -> None:
    con = init_db(DB_PATH)
    today = date.today().strftime("%Y%m%d")

    print("Fetching station list…")
    stations = get_stations()
    print(f"  {len(stations)} stations found")

    for sensor in SENSORS:
        print(f"\nProcessing sensor: {sensor}")
        sensor_stations = _filter_stations_by_sensor(stations, sensor)
        print(f"  {len(sensor_stations)} stations have sensor {sensor}")

        winner_scodes = _resolve_duplicates(sensor_stations, sensor)
        winner_meta = sensor_stations[sensor_stations["SCODE"].isin(winner_scodes)].copy()
        winner_meta = winner_meta.rename(
            columns={"NAME_D": "name", "ALT": "altitude", "LAT": "lat", "LONG": "lon", "SCODE": "scode"}
        )[["scode", "name", "altitude", "lat", "lon"]]
        upsert_stations(con, winner_meta)
        print(f"  {len(winner_scodes)} winner stations stored")

        if full:
            date_from_map = {s: DATE_FROM for s in winner_scodes}
        else:
            known = last_dates(con, winner_scodes, sensor)
            date_from_map = {
                s: (
                    DATE_FROM if known[s] is None
                    else (known[s] + timedelta(days=1)).strftime("%Y%m%d")
                )
                for s in winner_scodes
            }

        to_fetch = {s: d for s, d in date_from_map.items() if d <= today}
        print(f"  fetching timeseries for {len(to_fetch)} stations…")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(get_timeseries, s, sensor, date_from_map[s], today): s
                for s in to_fetch
            }
            done = 0
            total = len(futures)
            for fut in as_completed(futures):
                scode = futures[fut]
                series = fut.result()
                done += 1
                if series.empty:
                    if done % 20 == 0 or done == total:
                        print(f"  downloaded {done}/{total}")
                    continue
                records = pd.DataFrame({
                    "scode": scode,
                    "sensor": sensor,
                    "date": series.index,
                    "daily_max": series.values,
                })
                upsert_measurements(con, records)
                if done % 20 == 0 or done == total:
                    print(f"  downloaded {done}/{total}")

    con.close()
    print(f"\nDone. Database: {DB_PATH}")


def run_excel(full: bool = False) -> None:
    """Ingest historical data from the provincial Excel download page into DuckDB."""
    con = init_db(DB_PATH)

    print("Fetching station list from REST API (for coordinates)…")
    api_stations = get_stations()

    print("Fetching Excel file list…")
    urls = get_excel_urls()
    print(f"  {len(urls)} Excel files found")

    total = len(urls)
    for i, url in enumerate(urls, 1):
        scode = scode_from_url(url)
        print(f"[{i}/{total}] {scode}", end="", flush=True)

        if not full:
            known = last_dates(con, [scode], "LT")
            last_lt = known.get(scode)
            today = date.today()
            if last_lt is not None and last_lt >= today:
                print(" — up to date, skipped")
                continue

        try:
            station_df, measurements = parse_excel(url, api_stations)
            upsert_stations(con, station_df)

            if not measurements.empty:
                if not full:
                    known = last_dates(con, [scode], "LT")
                    last_lt = known.get(scode)
                    if last_lt is not None:
                        cutoff = pd.Timestamp(last_lt).date()
                        measurements = measurements[
                            pd.to_datetime(measurements["date"]).dt.date > cutoff
                        ]

                if not measurements.empty:
                    upsert_measurements(con, measurements)
                    print(f" — {len(measurements)} rows")
                else:
                    print(" — no new rows")
            else:
                print(" — no data")

        except Exception as e:
            print(f" — ERROR: {e}")

    con.close()
    print(f"\nDone. Database: {DB_PATH}")
