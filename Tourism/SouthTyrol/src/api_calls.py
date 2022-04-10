from typing import Union, Tuple
import json
import urllib.request
import glob
import pandas as pd
import os
import numpy as np
from scipy import stats
import geopandas as gpd
import logging
from .config import (
    RAW_DATA_ROOM_API_CALL_DIR,
    RAW_DATA_MAIN_API_CALL_DIR,
    PARSED_ACCOMM_FILE,
    PREPARED_ACCOMM_FILE,
    ROOM_INFO_FILE,
    DIRS,
    MAPPING_CATEGORY_SINGULAR_PLURAL,
    RAW_DATA_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

MSG = "\n{}\n========"


def download_data():
    """
    Downloads accommodation data from the open data hub of South Tyrol.
    Saves paginated API results as JSON to disk.
    """
    logging.info(MSG.format("Downloading tourism data"))
    page = "https://tourism.api.opendatahub.bz.it/v1/Accommodation"
    counter = 0
    while True:
        if counter == 0:
            logging.info(
                "{:,} results broken into {:,} pages"
                .format(data.get("TotalResults"), data.get("TotalPages"))
            )
        if counter % 10 == 0:
            logging.info(f"Page number {counter + 1:,}")
        with urllib.request.urlopen(page) as response:
            data = json.loads(response.read())
            page = data.get("NextPage")
            json.dump(data, open(os.path.join(RAW_DATA_MAIN_API_CALL_DIR, f"page_{counter}.json"), "w"))
            counter += 1
            if not page:
                break


def parse_data():
    """
    Parses paginated API results and saves information in a single file.
    """
    logging.info(MSG.format("Parsing tourism data"))
    files = glob.glob(os.path.join(RAW_DATA_MAIN_API_CALL_DIR, "*.json"))
    parsed_data = []
    for file in files:
        entries = json.load(open(file, "r")).get("Items")
        for entry in entries:
            parsed_data.append(_parse_entry(entry, file))
    df = pd.DataFrame(parsed_data)
    df.to_csv(PARSED_ACCOMM_FILE, index=False)


def _parse_entry(entry: dict, file: str = None) -> dict:
    """
    Selects only most relevant information from an original API return object.

    Parameters
    ----------
    entry: API return object.
    file: Filename where entry is from, if known.

    Returns
    -------
    parsed_entry: Parsed API return object, which includes only relevant attributes.
    """
    of_interest = [
        "AccoDetail",
        "AccoCategoryId",
        "AccoRoomInfo",
        "HasApartment",
        "IsGastronomy",
        "LocationInfo",
        "Altitude",
        "Latitude",
        "Longitude",
        "Id"
    ]

    parsed_entry = {}
    for attribute in of_interest:
        attribute_value = entry.get(attribute)
        if (attribute in ["AccoDetail", "LocationInfo"]) & (attribute_value is not None):
            if attribute == "AccoDetail":
                attribute_value_lang = attribute_value.get("de")
                for c in ["Name", "City"]:
                    parsed_entry[c] = attribute_value_lang.get(c)
            elif attribute == "LocationInfo":
                try:
                    attribute_value_lang = attribute_value.get("RegionInfo").get("Name").get("de")
                except KeyError:
                    attribute_value_lang = None
                parsed_entry[attribute] = attribute_value_lang
            else:
                pass
        else:
            if attribute == "AccoRoomInfo":
                parsed_entry[attribute] = len(attribute_value) if attribute_value is not None else None
            else:
                parsed_entry[attribute] = attribute_value
    parsed_entry["file"] = file
    return parsed_entry


def prepare_data():
    """
    Cleans the dataframe containing the information from parsed API calls on tourism establishments,
    by filtering out duplicates and entries without valid GPS coordinates.
    In addition, room information is added.
    """
    logging.info(MSG.format("Preparing data"))
    # Main file
    df = pd.read_csv(PARSED_ACCOMM_FILE)
    # File containing room and max occupancy info
    room_info = pd.read_csv(ROOM_INFO_FILE)
    dupl_cols = list(df.columns.difference(["file"]))
    # Remove duplicates
    logging.info(f"Number of duplicates: {df[dupl_cols].duplicated().sum():,}")
    df.drop_duplicates(subset=dupl_cols, inplace=True)
    # Remove outliers in terms of GPS coordinates (e.g. those with Lat or Long equal to zero)
    mask = (np.abs(stats.zscore(df[["Latitude", "Longitude"]])) >= 0.5).all(axis=1)
    logging.info(f"Number of invalid GPS coordinates: {mask.sum():,}")
    df = df.loc[~mask].copy()
    # Parse category information
    df["AccoCategoryRating"] = (
        df
        .AccoCategoryId
        .apply(lambda x: _parse_category(x)[0])
        .str
        .title()
    )
    df["AccoCategoryType"] = (
        df
        .AccoCategoryId
        .apply(lambda x: _parse_category(x)[1])
        .replace(MAPPING_CATEGORY_SINGULAR_PLURAL)
        .str.title()
    )
    # Get OHE
    n = len(df)
    df = (
        df
        .merge(
            pd.get_dummies(
                df[["Id", "AccoCategoryType", "AccoCategoryRating"]],
                columns=["AccoCategoryType", "AccoCategoryRating"]
            ),
            on="Id",
            how="inner"
        )
    )
    assert len(df) == n
    # Add municipality info
    n = len(df)
    df_geo = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")
    population = gpd.read_file(
        os.path.join(
            RAW_DATA_DIR,
            "shapefiles/FME_12060355_1631560092259_118556/DownloadService/OfficialResidentPopulation_polygon.shp"
        ),
        crs="EPSG:4326"
    )
    population = population.to_crs("EPSG:4326")
    population.drop_duplicates(subset=["NAME_D"], inplace=True)
    df = gpd.sjoin(df_geo, population[["NAME_D", "NAME_I", "geometry"]], how="left", op="within")
    assert len(df) == n
    # Merge with room info
    n = len(df)
    df["Id"] = df["Id"].str.rstrip("_REDUCED")  # New IDs end with "_REDUCED"
    df = df.merge(room_info, on="Id", how="left")
    assert len(df) == n
    df.to_csv(PREPARED_ACCOMM_FILE, index=False)


def download_room_info():
    """
    Makes API calls to obtain information on rooms of tourism establishments.
    """
    logging.info(MSG.format("Downloading room information"))

    api_calls = 0
    if os.path.exists(PREPARED_ACCOMM_FILE):
        # Use merged data to see which cleaned establishments ones we already have
        accommodation_ids = set(pd.read_csv(PREPARED_ACCOMM_FILE).Id.str.rstrip("_REDUCED").unique())
    else:
        # Otherwise, start with the full list of establishments
        accommodation_ids = set(pd.read_csv(PARSED_ACCOMM_FILE).Id.str.rstrip("_REDUCED").unique())
    new_ids = accommodation_ids
    if os.path.exists(ROOM_INFO_FILE):
        # If we have already made some room info API calls, remove them from the set of calls to make
        existing_ids = set(pd.read_csv(ROOM_INFO_FILE).Id.unique())
        new_ids = accommodation_ids - existing_ids
    logging.info(f"API calls to make: {len(new_ids):,}")
    results = []
    for i, accomm_id in enumerate(new_ids):
        results.append(_get_rooms(accomm_id))
        api_calls += 1
        if (api_calls % 200 == 0) | (i == len(new_ids) - 1):
            results_df = pd.DataFrame(results, columns=["Id", "TotalRooms", "MaxOccupancy"])
            results_df.to_csv(
                os.path.join(RAW_DATA_ROOM_API_CALL_DIR, f"accommodations_nr_rooms_{api_calls}_{accomm_id}.csv"),
                index=False
            )
            results = []
            logging.info(f"Made {api_calls} room info API calls")

    csv_files = glob.glob(os.path.join(RAW_DATA_ROOM_API_CALL_DIR, "accommodations_nr_rooms_*.csv"))
    results_dfs = pd.concat([pd.read_csv(i) for i in csv_files])
    results_dfs.drop_duplicates(subset=["Id"], inplace=True)
    if not os.path.exists(ROOM_INFO_FILE):
        results_dfs.to_csv(ROOM_INFO_FILE, index=False, mode="a", header=False)
    else:
        results_dfs.to_csv(ROOM_INFO_FILE, index=False)


def _get_rooms(accommodation_id: str, debug: bool = False) -> Union[dict, tuple]:
    """
    Obtains room information for a given tourism establishment.

    Parameters
    ----------
    accommodation_id: ID of the tourism establishment
    debug: Whether to enter debug mode and return the results of the API call as-is.

    Returns
    -------
    accommodation_info: Tuple containing the accommodation ID (see input), the total rooms of the establishment
                        and its total maximum occupancy.
    """
    url_main = f"https://tourism.api.opendatahub.bz.it/v1/AccommodationRoom?accoid={accommodation_id}&"
    url_settings = "idsource=lts&getall=true&language=de&removenullvalues=true"
    url = url_main + url_settings
    with urllib.request.urlopen(url) as response:
        content = response.read()
        data = json.loads(content)
        if debug:
            return data
        nr_rooms = np.array([d["RoomQuantity"] for d in data])
        max_occupancy = np.array([d["Roommax"] for d in data])
        total_rooms = int(nr_rooms.sum())
        total_max_occupancy = int((nr_rooms * max_occupancy).sum())
        accommodation_info = tuple([accommodation_id, total_rooms, total_max_occupancy])
        return accommodation_info


def _parse_category(x: str) -> Tuple[Union[str, None], Union[str, None]]:
    """

    Parameters
    ----------
    x: Category, such as "3sstars"

    Returns
    -------
    Category rank and type, e.g. (3s, stars)
    """
    if x != "Not categorized":
        if "ss" in x:
            # 4s or 3s hotels
            return x[:2], x[2:]
        else:
            return x[:1], x[1:]
    else:
        return None, None


def prepare_dirs():
    """
    Creates directories defined in the config file.
    """
    for _dir in DIRS:
        if not os.path.exists(_dir):
            os.mkdir(_dir)


if __name__ == '__main__':
    prepare_dirs()
    # download_data()
    parse_data()
    download_room_info()
    prepare_data()
