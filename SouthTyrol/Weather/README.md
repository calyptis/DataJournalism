# South Tyrol Weather

Downloads historical weather measurements from the [South Tyrol Open Data API](http://daten.buergernetz.bz.it/services/meteo/v1/) and stores them in a local DuckDB database optimised for notebook analysis.

## Setup

```bash
poetry install
```

## Usage

```bash
# Incremental fetch — only downloads records newer than what's already stored
poetry run weather download

# Force full re-fetch from 1980
poetry run weather download --full
```

The database is written to `data/weather.duckdb`.

## Database schema

Two tables, joined on `scode`:

**`stations`** — one row per station

| Column | Type | Description |
|---|---|---|
| `scode` | VARCHAR (PK) | Station code |
| `name` | VARCHAR | German station name |
| `altitude` | DOUBLE | Metres above sea level |
| `lat` | DOUBLE | WGS-84 latitude |
| `lon` | DOUBLE | WGS-84 longitude |

**`measurements`** — one row per station × sensor × day

| Column | Type | Description |
|---|---|---|
| `scode` | VARCHAR | Station code |
| `sensor` | VARCHAR | Sensor type (`LT` = air temperature) |
| `date` | DATE | Local date |
| `daily_max` | DOUBLE | Daily maximum reading |

## Querying from a notebook

```python
import duckdb

con = duckdb.connect("data/weather.duckdb")

df = con.execute("""
    SELECT m.date, s.name, s.altitude, s.lat, s.lon, m.daily_max
    FROM measurements m
    JOIN stations s USING (scode)
    WHERE m.sensor = 'LT'
    ORDER BY m.date, s.name
""").df()
```

## Project structure

```
south_tyrol_weather/
  config.py     # constants: API URL, sensors, DB path, worker count
  api.py        # HTTP calls → DataFrames (no side effects)
  store.py      # DuckDB schema init and idempotent upserts
  pipeline.py   # incremental orchestration (api + store)
  cli.py        # `weather` CLI entry point

tests/
  test_api.py       # integration tests (live API)
  test_store.py     # unit tests (in-memory DuckDB)
  test_pipeline.py  # end-to-end integration test
```

## Running tests

```bash
poetry run pytest
```

The API and pipeline tests hit the live South Tyrol API.
