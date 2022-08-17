import os
import pathlib


# Directories
# -----------
# Project directory
MAIN_DIR = os.path.split(pathlib.Path(__file__).parent.resolve())[0]

# Directory where data will be stored
DATA_DIR = os.path.join(MAIN_DIR, "data")

# Directory where downloaded, i.e. source data, will be stored
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw_data")

# Directory where results from API calls will be stored
RAW_DATA_API_DIR = os.path.join(RAW_DATA_DIR, "api_calls")

# Directory where results from main API calls are stored
RAW_DATA_MAIN_API_CALL_DIR = os.path.join(RAW_DATA_API_DIR, "main_call")

# Directory where results from the room API calls are stored
RAW_DATA_ROOM_API_CALL_DIR = os.path.join(RAW_DATA_API_DIR, "room_info")

# Directory where edited, i.e. prepared data, will be stored
PREPARED_DATA_DIR = os.path.join(DATA_DIR, "prepared_data")

# Directory where pickle files for the dashboard are stored
DASHBOARD_DATA_DIR = os.path.join(DATA_DIR, "dashboard_data")

# Directory where plots will be stored
PLOT_DIR = os.path.join(MAIN_DIR, "plots")

# Bundle all directories (in the right order)
DIRS = [
    # Root directories
    DATA_DIR,
    PLOT_DIR,
    # Subdirectories
    RAW_DATA_DIR,
    PREPARED_DATA_DIR,
    # Sub-subdirectories
    RAW_DATA_API_DIR,
    RAW_DATA_MAIN_API_CALL_DIR,
    RAW_DATA_ROOM_API_CALL_DIR
]

# Raw files
# ---------
POPULATION_SHAPEFILE = os.path.join(*[
    RAW_DATA_DIR,
    "shapefiles",
    "FME_14060355_1660760091426_63496"
    "DownloadService"
    "OfficialResidentPopulation_polygon.shp"
])

# Prepared files
# --------------
PARSED_ACCOMM_FILE = os.path.join(PREPARED_DATA_DIR, "accommodations_parsed.csv")
PREPARED_ACCOMM_FILE = os.path.join(PREPARED_DATA_DIR, "accommodations_cleaned.csv")
ROOM_INFO_FILE = os.path.join(PREPARED_DATA_DIR, "accommodation_rooms.csv")

# Dashboard files
# ---------------
MUNICIPALITY_FILE = os.path.join(DASHBOARD_DATA_DIR, "municipality.pickle")
DENSITY_FILE = os.path.join(DASHBOARD_DATA_DIR, "density.pickle")

# Variables
# ---------
VARIABLES_INFO = {
    # KPI: (Name, Format)
    "nr_establishments": ("Number of Tourism Establishments", "{,}"),
    "nr_establishments_per_thousand_pop": ("Number of Tourism Establishments per 1,000 Inhabitants", "{,}"),
    "total_occupancy": ("Total Occupancy", "{,}"),
    "total_nr_rooms": ("Total Number of Rooms", "{,}"),
    "total_nr_rooms_per_thousand_pop": ("Number of Rooms per 1,000 Inhabitants", "{,}"),
    "avg_occupancy": ("Mean Occupancy of Tourism Establishments", "{0.1f}"),
    "total_occupancy_per_thousand_pop": ("Total Occupancy per 1,000 Inhabitants", "{,}"),
    "NAME_D": ("Municipality (de)", ""),
    "NAME_I": ("Municipality (it)", ""),
    "share_1_rating": ("Share of Establishments with Rating 1", "{0.2f}%"),
    "share_2_rating": ("Share of Establishments with Rating 2", "{0.2f}%"),
    "share_3_rating": ("Share of Establishments with Rating 3", "{0.2f}%"),
    "share_3s_rating": ("Share of Establishments with Rating 3S", "{0.2f}%"),
    "share_4_rating": ("Share of Establishments with Rating 4", "{0.2f}%"),
    "share_4s_rating": ("Share of Establishments with Rating 4S", "{0.2f}%"),
    "share_5_rating": ("Share of Establishments with Rating 5", "{0.2f}%"),
    "share_stars": ("Share of Stars Establishments", "{0.2f}%"),
    "share_suns": ("Share of Suns Establishments", "{0.2f}%"),
    "share_flowers": ("Share of Flowers Establishments", "{0.2f}%")
}
# KPI: Name mapping to be used when creating visualisations
# Allow KPIs to be rendered with nicely formatted names
VARIABLES_PRETTY = {k: v[0] for k, v in VARIABLES_INFO.items()}
# Name: KPI mapping to be used in the streamlit app
# Allow users to select KPI using nicely formatted names
VARIABLES_INV = {v[0]: k for k, v in VARIABLES_INFO.items()}

MAPPING_CATEGORY_SINGULAR_PLURAL = {
    "flower": "flowers",
    "star": "stars",
    "sun": "suns"
}
