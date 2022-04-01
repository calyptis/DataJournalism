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

# Directory where edited, i.e. prepared data, will be stored
PREPARED_DATA_DIR = os.path.join(DATA_DIR, "prepared_data")

# Directory where plots will be stored
PLOT_DIR = os.path.join(MAIN_DIR, "plots")

# Prepared files
# --------------
PARSED_ACCOMM_FILE = os.path.join(PREPARED_DATA_DIR, "accommodations_parsed.csv")
PREPARED_ACCOMM_FILE = os.path.join(PREPARED_DATA_DIR, "accommodations_cleaned.csv")
ROOM_INFO_FILE = os.path.join(PREPARED_DATA_DIR, "accommodation_rooms.csv")

# Variables
# ---------
VARIABLES_INFO = {
    # KPI: (Name, Format)
    "nr_establishments": ("Number of Tourism Establishments", "{,}"),
    "nr_establishments_per_thousand_pop": ("Number of Tourism Establishments per 1,000 Inhabitants", "{,}"),
    "total_occupancy": ("Total Occupancy", "{,}"),
    "total_nr_rooms": ("Total Number of Rooms", "{,}"),
    "avg_occupancy": ("Mean Occupancy of Tourism Establishments", "{0.1f}"),
    "total_occupancy_per_thousand_pop": ("Total Occupancy per 1,000 Inhabitants", "{,}"),
    "NAME_D": ("Municipality (de)", ""),
    "NAME_I": ("Municipality (it)", "")
}
# KPI: Name mapping to be used when creating visualisations
# Allow KPIs to be rendered with nicely formatted names
VARIABLES_PRETTY = {k: v[0] for k, v in VARIABLES_INFO.items()}
# Name: KPI mapping to be used in the streamlit app
# Allow users to select KPI using nicely formatted names
VARIABLES_INV = {v[0]: k for k, v in VARIABLES_INFO.items()}
