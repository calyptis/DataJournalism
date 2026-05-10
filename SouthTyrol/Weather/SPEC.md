# Spec: south-tyrol-weather (v2)

## 1. Objective

Fetch daily weather measurements from the South Tyrol Open Data API
(`http://daten.buergernetz.bz.it/services/meteo/v1`) and persist them in a
local DuckDB database (`data/weather.duckdb`) with a schema designed for fast
station-metadata + measurement joins from notebooks.

The pipeline runs incrementally: on subsequent runs it only downloads records
newer than what is already stored, so re-running is cheap.

---

## 2. Commands

| Command | Description |
|---|---|
| `poetry install` | Install all dependencies |
| `poetry run weather download` | Incremental fetch; updates `data/weather.duckdb` |
| `poetry run weather download --full` | Force full re-fetch from `DATE_FROM` |
| `poetry run pytest` | Run integration tests (hits live API) |

---

## 3. Project Structure

```
south_tyrol_weather/
  __init__.py
  config.py       # constants: URLs, sensors, paths, worker count
  api.py          # pure HTTP calls → DataFrames (no I/O side effects)
  store.py        # DuckDB schema init, upsert helpers, last-date queries
  pipeline.py     # orchestrates api + store; drives incremental logic
  cli.py          # `weather` CLI entry point

tests/
  test_api.py     # integration tests: live API calls, shape/type checks
  test_store.py   # unit tests: schema, upsert idempotency (in-memory DuckDB)

data/
  weather.duckdb  # generated; gitignored
```

---

## 4. DuckDB Schema

### `stations` table

| Column | Type | Notes |
|---|---|---|
| `scode` | VARCHAR PRIMARY KEY | Station code (e.g. `"BZO"`) |
| `name` | VARCHAR | German station name (`NAME_D`) |
| `altitude` | DOUBLE | Metres above sea level |
| `lat` | DOUBLE | WGS-84 latitude |
| `lon` | DOUBLE | WGS-84 longitude |

### `measurements` table

| Column | Type | Notes |
|---|---|---|
| `scode` | VARCHAR | FK → stations.scode |
| `sensor` | VARCHAR | Sensor type code (e.g. `"LT"`) |
| `date` | DATE | Local date (tz-stripped after UTC normalise) |
| `daily_max` | DOUBLE | Max value across all intraday readings |
| PRIMARY KEY | `(scode, sensor, date)` | Ensures upsert idempotency |

Rationale: long/tall layout means adding new sensors later requires no schema
change. Joining with stations is always a single `JOIN stations USING (scode)`.

---

## 5. Module Responsibilities

### `config.py`
```python
API_BASE      = "http://daten.buergernetz.bz.it/services/meteo/v1"
SENSORS       = ["LT"]          # extend here to add more sensors
DATE_FROM     = "19800101"      # earliest date for full fetch
DB_PATH       = "data/weather.duckdb"
MAX_WORKERS   = 12
TIMEOUT       = 60
LOCATION_PRECISION = 3          # decimal places for duplicate-station grouping
```

### `api.py`
- `get_stations() -> pd.DataFrame`: GET `/stations?output_format=CSV`
- `get_sensors(scode: str) -> list[str]`: GET `/sensors?station_code=…` → list of TYPE values
- `get_timeseries(scode: str, sensor: str, date_from: str, date_to: str) -> pd.Series`:
  GET `/timeseries?…` → daily-max Series indexed by date, named `scode`
- No side effects; raises on HTTP error

### `store.py`
- `init_db(path: str) -> duckdb.DuckDBPyConnection`: create tables if not exist
- `upsert_stations(con, df: pd.DataFrame) -> None`: INSERT OR REPLACE into stations
- `upsert_measurements(con, records: pd.DataFrame) -> None`: INSERT OR REPLACE into measurements
- `last_dates(con, scodes: list[str], sensor: str) -> dict[str, date | None]`:
  return `{scode: max(date)}` for each scode; `None` if no rows exist yet

### `pipeline.py`
- `run(full: bool = False) -> None`
  1. Open DuckDB via `store.init_db`
  2. Fetch station list via `api.get_stations`
  3. Filter to stations that have each sensor in `SENSORS` (parallel, `ThreadPoolExecutor`)
  4. Resolve duplicate locations (same lat/lon rounded to `LOCATION_PRECISION`):
     fetch timeseries for all duplicates, keep the one with the most non-null records
  5. `store.upsert_stations` with the winner set
  6. For each sensor in `SENSORS`:
     - Query `store.last_dates` for all winners
     - If `full`, set `date_from = DATE_FROM` for all
     - Otherwise set `date_from = last_date + 1 day` (or `DATE_FROM` if None)
     - Skip stations already up-to-date (last_date == today)
     - Fetch timeseries in parallel for the stations that need updating
     - `store.upsert_measurements` after each batch

### `cli.py`
- `main()`: `argparse` with `download` subcommand + `--full` flag
- Calls `pipeline.run(full=...)`

---

## 6. Tech Stack

| Dependency | Role |
|---|---|
| Python ≥ 3.11 | runtime |
| pandas ≥ 2.0 | DataFrame manipulation |
| requests ≥ 2.28 | HTTP client |
| duckdb ≥ 0.10 | embedded analytical DB |
| pytest (dev) | testing |

Remove: `openpyxl`, `beautifulsoup4` (no longer needed).

---

## 7. Notebook Usage Pattern

```python
import duckdb
con = duckdb.connect("data/weather.duckdb")

# All LT measurements with station name and altitude
df = con.execute("""
    SELECT m.date, s.name, s.altitude, s.lat, s.lon, m.daily_max
    FROM measurements m
    JOIN stations s USING (scode)
    WHERE m.sensor = 'LT'
    ORDER BY m.date, s.name
""").df()
```

---

## 8. Testing Strategy

### `test_api.py` (integration, hits live API)
1. `get_stations()` returns a DataFrame with expected columns and > 0 rows
2. `get_sensors("BZO")` returns a non-empty list containing `"LT"`
3. `get_timeseries("BZO", "LT", "20240101", "20240131")` returns a Series with
   a DatetimeIndex and float values

### `test_store.py` (unit, in-memory DuckDB)
1. `init_db(":memory:")` creates both tables with the correct schema
2. `upsert_stations` is idempotent: inserting the same rows twice leaves one copy
3. `upsert_measurements` is idempotent: same (scode, sensor, date) updates in place
4. `last_dates` returns `None` for unknown stations and the correct date for known ones

---

## 9. Boundaries

| Category | Rule |
|---|---|
| Always | All API calls go through `api.py`; no `requests` calls elsewhere |
| Always | All DB access goes through `store.py`; no raw DuckDB calls in `pipeline.py` |
| Always | `SENSORS` list in `config.py` controls which sensor types are fetched |
| Always | Upserts must be idempotent — re-running never creates duplicate rows |
| Ask first | Adding new sensor types beyond `SENSORS` |
| Ask first | Changing DB_PATH or output format |
| Never | Drop or truncate the measurements table during an incremental run |
| Never | Hardcode station codes, sensor types, or date strings outside `config.py` |