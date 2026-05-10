from datetime import date

import duckdb
import pandas as pd


def init_db(path: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            scode    VARCHAR PRIMARY KEY,
            name     VARCHAR,
            altitude DOUBLE,
            lat      DOUBLE,
            lon      DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            scode     VARCHAR,
            sensor    VARCHAR,
            date      DATE,
            daily_max DOUBLE,
            daily_min DOUBLE,
            PRIMARY KEY (scode, sensor, date)
        )
    """)
    # Safe migration: add daily_min if this DB was created before v0.2
    existing = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'measurements'"
    ).fetchall()}
    if "daily_min" not in existing:
        con.execute("ALTER TABLE measurements ADD COLUMN daily_min DOUBLE")
    return con


def upsert_stations(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    con.execute("""
        INSERT OR REPLACE INTO stations (scode, name, altitude, lat, lon)
        SELECT scode, name, altitude, lat, lon FROM df
    """)


def upsert_measurements(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    if "daily_min" not in df.columns:
        df = df.copy()
        df["daily_min"] = None
    con.execute("""
        INSERT OR REPLACE INTO measurements (scode, sensor, date, daily_max, daily_min)
        SELECT scode, sensor, date, daily_max, daily_min FROM df
    """)


def last_dates(
    con: duckdb.DuckDBPyConnection, scodes: list[str], sensor: str
) -> dict[str, date | None]:
    if not scodes:
        return {}
    rows = con.execute("""
        SELECT scode, MAX(date)::DATE AS last_date
        FROM measurements
        WHERE sensor = ? AND scode IN (SELECT unnest(?))
        GROUP BY scode
    """, [sensor, scodes]).fetchall()
    result = {s: None for s in scodes}
    for scode, last in rows:
        result[scode] = last
    return result
