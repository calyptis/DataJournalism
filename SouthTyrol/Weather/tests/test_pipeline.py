"""
Integration test for the full pipeline — hits live API, writes to a temp DuckDB.
"""
import os
from unittest.mock import patch

import pytest

from south_tyrol_weather.pipeline import run


def test_run_creates_database(tmp_path):
    db = str(tmp_path / "test.duckdb")
    with patch("south_tyrol_weather.pipeline.DB_PATH", db):
        run(full=False)
    assert os.path.exists(db)


def test_run_populates_stations(tmp_path):
    import duckdb
    db = str(tmp_path / "test.duckdb")
    with patch("south_tyrol_weather.pipeline.DB_PATH", db):
        run(full=False)
    con = duckdb.connect(db)
    count = con.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    con.close()
    assert count > 0


def test_run_populates_measurements(tmp_path):
    import duckdb
    db = str(tmp_path / "test.duckdb")
    with patch("south_tyrol_weather.pipeline.DB_PATH", db):
        run(full=False)
    con = duckdb.connect(db)
    count = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    con.close()
    assert count > 0
