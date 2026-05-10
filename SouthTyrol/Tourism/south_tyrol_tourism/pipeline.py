import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from south_tyrol_tourism.config import (
    ACCOMMODATION_API,
    MAPPING_CATEGORY_SINGULAR_PLURAL,
    settings,
)
from south_tyrol_tourism.exceptions import APIError, DataError


def prepare_dirs(dirs: list[Path] | None = None) -> None:
    """Creates all data directories. Pass ``dirs`` explicitly in tests."""
    for directory in dirs or settings.dirs:
        directory.mkdir(parents=True, exist_ok=True)


def download_accommodations() -> None:
    """Downloads accommodation data from the Open Data Hub.

    Resumes from the last saved page if page files already exist in
    ``main_call_dir``. Pages are consolidated into a single
    ``accommodations_raw.json`` at the end and the page files are deleted.
    """
    logger.info("Downloading accommodations")

    existing = sorted(
        settings.main_call_dir.glob("page_*.json"),
        key=lambda p: int(p.stem.split("_")[1]),
    )
    if existing:
        last_data = json.loads(existing[-1].read_text())
        next_page: str | None = last_data.get("NextPage")
        counter = int(existing[-1].stem.split("_")[1]) + 1
        if next_page is None:
            logger.info("All pages already downloaded — consolidating")
            _consolidate(settings.main_call_dir, "page_*.json", settings.raw_accommodation_file)
            return
        logger.info(f"Resuming from page {counter + 1:,}")
        page: str | None = next_page
    else:
        page = ACCOMMODATION_API
        counter = 0

    while page:
        if counter % 10 == 0:
            logger.info(f"Page number {counter + 1:,}")
        try:
            with urllib.request.urlopen(page) as response:
                data: dict = json.loads(response.read())
        except Exception as exc:
            raise APIError(f"Failed to fetch page {counter + 1}: {page}") from exc
        if counter == 0:
            logger.info(
                f"{data.get('TotalResults'):,} results across "
                f"{data.get('TotalPages'):,} pages"
            )
        with (settings.main_call_dir / f"page_{counter}.json").open("w") as fh:
            json.dump(data, fh)
        page = data.get("NextPage")
        counter += 1

    _consolidate(settings.main_call_dir, "page_*.json", settings.raw_accommodation_file)


def _consolidate(src_dir: Path, pattern: str, dest: Path) -> None:
    """Merge all files matching ``pattern`` in ``src_dir`` into ``dest``, then delete them.

    For Parquet destinations the existing ``dest`` file (if any) is included in
    the merge so incremental runs accumulate results rather than overwrite them.
    """
    files = list(src_dir.glob(pattern))
    if not files:
        return
    if dest.suffix == ".json":
        files = sorted(files, key=lambda p: int(p.stem.split("_")[1]))
        items = [item for f in files for item in json.loads(f.read_text()).get("Items", [])]
        dest.write_text(json.dumps(items))
        logger.info(f"Merged {len(files)} pages → {len(items):,} entries")
    else:
        dfs = [pd.read_parquet(f) for f in files]
        if dest.exists():
            dfs.append(pd.read_parquet(dest))
        df = pd.concat(dfs).drop_duplicates("Id")
        df.to_parquet(dest, index=False)
        logger.info(f"Merged {len(files)} batches → {len(df):,} rows")
    for f in files:
        f.unlink()


def parse_accommodations() -> None:
    """Parses the consolidated raw JSON and writes ``accommodations_parsed.parquet``."""
    logger.info("Parsing accommodation data")
    raw_file = settings.raw_accommodation_file
    if not raw_file.exists():
        raise DataError(f"Raw data file not found: {raw_file}")
    with raw_file.open() as fh:
        items: list[dict] = json.load(fh)
    parsed = [_parse_entry(entry) for entry in items]
    pd.DataFrame(parsed).to_parquet(settings.parsed_accommodation_file, index=False)
    logger.info(f"Parsed {len(parsed):,} entries")


def _parse_entry(entry: dict[str, object]) -> dict[str, object]:
    detail = (entry.get("AccoDetail") or {}).get("de") or {}  # type: ignore[union-attr]
    loc = entry.get("LocationInfo") or {}
    try:
        region: str | None = loc["RegionInfo"]["Name"]["de"]  # type: ignore[index]
    except (KeyError, TypeError):
        region = None
    return {
        "Name": detail.get("Name"),
        "City": detail.get("City"),
        "LocationInfo": region,
        **{f: entry.get(f) for f in (
            "AccoCategoryId", "HasApartment", "IsGastronomy",
            "Altitude", "Latitude", "Longitude", "Id",
        )},
    }


def prepare_data() -> None:
    """Cleans parsed data, adds category OHE columns and municipality via spatial join."""
    logger.info("Preparing data")
    df = pd.read_parquet(settings.parsed_accommodation_file)

    n_dupl = int(df.duplicated().sum())
    logger.info(f"Duplicates removed: {n_dupl:,}")
    df = df.drop_duplicates()

    mask = (np.abs(stats.zscore(df[["Latitude", "Longitude"]])) >= 0.5).all(axis=1)
    logger.info(f"Invalid GPS coordinates removed: {int(mask.sum()):,}")
    df = df.loc[~mask].copy()

    df["AccoCategoryRating"] = (
        df["AccoCategoryId"].apply(lambda x: _parse_category(x)[0]).str.title()
    )
    df["AccoCategoryType"] = (
        df["AccoCategoryId"]
        .apply(lambda x: _parse_category(x)[1])
        .replace(MAPPING_CATEGORY_SINGULAR_PLURAL)
        .str.title()
    )

    n = len(df)
    df = df.merge(
        pd.get_dummies(
            df[["Id", "AccoCategoryType", "AccoCategoryRating"]],
            columns=["AccoCategoryType", "AccoCategoryRating"],
        ),
        on="Id",
        how="inner",
    )
    if len(df) != n:
        raise DataError("Row count changed after OHE merge — check for duplicate IDs.")

    population = gpd.read_file(settings.population_shapefile).to_crs(settings.crs)
    population = population.drop_duplicates(subset=["NAME_D"])
    df_geo = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs=settings.crs,
    )
    n = len(df_geo)
    df_geo = gpd.sjoin(
        df_geo,
        population[["NAME_D", "NAME_I", "geometry"]],
        how="left",
        predicate="within",
    )
    if len(df_geo) != n:
        raise DataError("Row count changed after spatial join — check for geometry overlaps.")

    df_geo["Id"] = df_geo["Id"].str.removesuffix("_REDUCED")
    df_geo = df_geo.drop(columns=["index_right", "geometry"])
    pd.DataFrame(df_geo).to_parquet(settings.prepared_accommodation_file, index=False)


def _parse_category(x: str | None) -> tuple[str | None, str | None]:
    if x is None or x == "Not categorized":
        return None, None
    if "ss" in x:
        return x[:2], x[2:]
    return x[:1], x[1:]


if __name__ == "__main__":
    prepare_dirs()
    parse_accommodations()
    prepare_data()
