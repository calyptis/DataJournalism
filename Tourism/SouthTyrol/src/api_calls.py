import json
import urllib.request
import glob
import pandas as pd
import os
import numpy as np
from scipy import stats
from config import (
    RAW_DATA_API_DIR,
    PARSED_ACCOMM_FILE,
    PREPARED_ACCOMM_FILE,
    ROOM_INFO_FILE
)


def download_data():
    """
    Downloads accommodation data from the open data hub of South Tyrol.
    Saves paginated API results as JSON to disk.
    """
    page = "https://tourism.api.opendatahub.bz.it/v1/Accommodation"
    counter = 0
    while True:
        if counter % 10 == 0:
            print(f"Page number {counter + 1:,}")
        with urllib.request.urlopen(page) as response:
            data = json.loads(response.read())
            page = data.get("NextPage")
            json.dump(data, open(os.path.join(RAW_DATA_API_DIR, f"page_{counter}.json"), "w"))
            if counter == 0:
                print("{:,} results broken into {:,} pages".format(data.get("TotalResults"), data.get("TotalPages")))
            counter += 1
            if not page:
                break


def parse_data():
    """
    Parses paginated API results and saves information in a single file.
    """
    files = glob.glob(os.path.join(RAW_DATA_API_DIR, "main_call/*.json"))
    parsed_data = []
    for file in files:
        entries = json.load(open(file, "r")).get("Items")
        for entry in entries:
            parsed_data.append(parse_entry(entry, file))
    df = pd.DataFrame(parsed_data)
    df.to_csv(PARSED_ACCOMM_FILE, index=False)


def parse_entry(entry: dict, file: str = None) -> dict:
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


def clean_data():
    """
    Cleans the dataframe containing the information from parsed API calls on tourism establishments,
    by filtering out duplicates and entries without valid GPS coordinates.
    """
    # Main file
    df = pd.read_csv(PARSED_ACCOMM_FILE)
    # File containing room and max occupancy info
    room_info = pd.read_csv(ROOM_INFO_FILE)
    dupl_cols = list(df.columns.difference(["file"]))
    # Remove duplicates
    print(f"Number of duplicates: {df[dupl_cols].duplicated().sum():,}")
    df.drop_duplicates(subset=dupl_cols, inplace=True)
    # Remove outliers in terms of GPS coordinates (e.g. those with Lat or Long equal to zero)
    mask = (np.abs(stats.zscore(df[["Latitude", "Longitude"]])) >= 0.5).all(axis=1)
    print(f"Number of invalid GPS coordinates: {mask.sum():,}")
    df = df.loc[~mask].copy()
    # Merge with room info
    n = len(df)
    df = df.merge(room_info, on="Id", how="left")
    assert len(df) == n
    df.to_csv(PREPARED_ACCOMM_FILE, index=False)


def download_room_info(overwrite: bool = False):
    """
    Makes API calls to obtain information on rooms of tourism establishments.

    Parameters
    ----------
    overwrite: Whether to overwrite existing downloaded information.
               Can be useful when API calls are modified.
    """
    api_calls = 0
    accommodation_ids = set(pd.read_csv(PREPARED_ACCOMM_FILE).Id.unique())
    existing_ids = set(pd.read_csv(ROOM_INFO_FILE).Id.unique())
    new_ids = accommodation_ids - existing_ids
    if overwrite:
        new_ids = accommodation_ids
    print(f"API calls to make: {len(new_ids):,}")
    results = []
    for i, accomm_id in enumerate(new_ids):
        results.append(get_rooms(accomm_id))
        api_calls += 1
        if (api_calls % 200 == 0) | (i == len(new_ids) - 1):
            results_df = pd.DataFrame(results, columns=["Id", "TotalRooms", "MaxOccupancy"])
            results_df.to_csv(
                os.path.join(*[RAW_DATA_API_DIR, "room_info", f"accommodations_nr_rooms_{api_calls}.csv"]),
                index=False
            )
            results = []
    csv_files = glob.glob(os.path.join(*[RAW_DATA_API_DIR, "room_info", "accommodations_nr_rooms_*.csv"]))
    results_dfs = pd.concat([pd.read_csv(i) for i in csv_files])
    results_dfs.drop_duplicates(subset=["Id"], inplace=True)
    if overwrite:
        results_dfs.to_csv(ROOM_INFO_FILE, index=False, mode="a", header=False)
    else:
        results_dfs.to_csv(ROOM_INFO_FILE, index=False)


def get_rooms(accommodation_id: str) -> tuple[str | int, ...]:
    """
    Obtains room information for a given tourism establishment.

    Parameters
    ----------
    accommodation_id: ID of the tourism establishment

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
        nr_rooms = np.array([d["RoomQuantity"] for d in data])
        max_occupancy = np.array([d["Roommax"] for d in data])
        total_rooms = int(nr_rooms.sum())
        total_max_occupancy = int((nr_rooms * max_occupancy).sum())
        accommodation_info = tuple([accommodation_id, total_rooms, total_max_occupancy])
        return accommodation_info
