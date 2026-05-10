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
            PRIMARY KEY (scode, sensor, date)
        )
    """)
    return con


def upsert_stations(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    con.execute("""
        INSERT OR REPLACE INTO stations (scode, name, altitude, lat, lon)
        SELECT scode, name, altitude, lat, lon FROM df
    """)


def upsert_measurements(con: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    con.execute("""
        INSERT OR REPLACE INTO measurements (scode, sensor, date, daily_max)
        SELECT scode, sensor, date, daily_max FROM df
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
