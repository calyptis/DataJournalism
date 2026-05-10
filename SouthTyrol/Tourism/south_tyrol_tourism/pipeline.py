import json
import urllib.request
from pathlib import Path

from loguru import logger

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

from south_tyrol_tourism.config import (
    MAPPING_CATEGORY_SINGULAR_PLURAL,
    settings,
    ACCOMMODATION_API,
    ACCOMMODATION_ROOM_API
)
from south_tyrol_tourism.exceptions import APIError, DataError


def prepare_dirs(dirs: list[Path] | None = None) -> None:
    """Creates all data directories. Pass ``dirs`` explicitly in tests."""
    for directory in dirs or settings.dirs:
        directory.mkdir(parents=True, exist_ok=True)


def download_accommodations() -> None:
    """Downloads accommodation data from the Open Data Hub.

    Pages are written to ``main_call_dir`` during download, then consolidated
    into a single ``accommodations_raw.json`` and the page files are deleted.
    """
    logger.info("Downloading accommodations")
    page: str | None = ACCOMMODATION_API
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
    """Merge all files matching ``pattern`` in ``src_dir`` into ``dest``, then delete them."""
    files = list(src_dir.glob(pattern))
    if not files:
        return
    if dest.suffix == ".json":
        files = sorted(files, key=lambda p: int(p.stem.split("_")[1]))
        items = [item for f in files for item in json.loads(f.read_text()).get("Items", [])]
        dest.write_text(json.dumps(items))
        logger.info(f"Merged {len(files)} pages → {len(items):,} entries")
    else:
        df = pd.concat([pd.read_parquet(f) for f in files]).drop_duplicates("Id")
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
    room_info = entry.get("AccoRoomInfo")
    return {
        "Name": detail.get("Name"),
        "City": detail.get("City"),
        "LocationInfo": region,
        "AccoRoomInfo": len(room_info) if room_info else None,  # type: ignore[arg-type]
        **{f: entry.get(f) for f in (
            "AccoCategoryId", "HasApartment", "IsGastronomy",
            "Altitude", "Latitude", "Longitude", "Id",
        )},
    }


def prepare_data() -> None:
    """Cleans parsed data, adds category OHE columns and municipality via spatial join."""
    logger.info("Preparing data")
    df = pd.read_parquet(settings.parsed_accommodation_file)
    room_info = pd.read_parquet(settings.room_info_file)

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
    df_geo = df_geo.merge(room_info, on="Id", how="left").drop(columns=["index_right", "geometry"])
    pd.DataFrame(df_geo).to_parquet(settings.prepared_accommodation_file, index=False)


def download_room_info() -> None:
    """Makes API calls for room/occupancy info.

    Batches of 200 are checkpointed to ``room_call_dir`` as Parquet. At the
    end, all batches are consolidated into ``room_info_file`` and deleted.
    """
    logger.info("Downloading information on rooms of accommodations")
    source = (
        settings.prepared_accommodation_file
        if settings.prepared_accommodation_file.exists()
        else settings.parsed_accommodation_file
    )
    if not source.exists():
        raise DataError(f"Source file not found: {source}")

    accommodation_ids: set[str] = set(
        pd.read_parquet(source)["Id"].str.removesuffix("_REDUCED").unique()
    )
    existing_ids: set[str] = (
        set(pd.read_parquet(settings.room_info_file)["Id"].unique())
        if settings.room_info_file.exists()
        else set()
    )
    ids = list(accommodation_ids - existing_ids)
    logger.info(f"API calls to make: {len(ids):,}")

    results: list[tuple[str, int, int]] = []
    for i, accomm_id in enumerate(ids, 1):
        results.append(_get_rooms(accomm_id))
        if i % 200 == 0 or i == len(ids):
            pd.DataFrame(results, columns=["Id", "TotalRooms", "MaxOccupancy"]).to_parquet(
                settings.room_call_dir / f"room_batch_{i}.parquet", index=False
            )
            results = []
            logger.info(f"Made {i:,} room info API calls")

    _consolidate(settings.room_call_dir, "room_batch_*.parquet", settings.room_info_file)


def _get_rooms(accommodation_id: str) -> tuple[str, int, int]:
    url = (
        f"{ACCOMMODATION_ROOM_API}?accoid={accommodation_id}"
        "&idsource=lts&getall=true&language=de&removenullvalues=true"
    )
    try:
        with urllib.request.urlopen(url) as response:
            data: list[dict] = json.loads(response.read())
    except Exception as exc:
        raise APIError(f"Failed to fetch room info for {accommodation_id!r}") from exc
    rooms = [(d["RoomQuantity"], d["Roommax"]) for d in data]
    return accommodation_id, sum(r for r, _ in rooms), sum(r * m for r, m in rooms)


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
