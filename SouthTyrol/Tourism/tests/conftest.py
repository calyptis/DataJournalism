import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon


@pytest.fixture
def sample_api_entry() -> dict:
    return {
        "Id": "ABC123",
        "AccoCategoryId": "3stars",
        "HasApartment": False,
        "IsGastronomy": False,
        "LocationInfo": {"RegionInfo": {"Name": {"de": "Meran"}}},
        "Altitude": 300,
        "Latitude": 46.67,
        "Longitude": 11.16,
        "AccoDetail": {"de": {"Name": "Hotel Test", "City": "Merano"}},
    }


@pytest.fixture
def sample_accommodation_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Id": ["ABC123", "DEF456"],
            "Name": ["Hotel A", "Hotel B"],
            "City": ["Merano", "Bolzano"],
            "Latitude": [46.67, 46.49],
            "Longitude": [11.16, 11.34],
            "NAME_D": ["Meran", "Bozen"],
            "NAME_I": ["Merano", "Bolzano"],
        }
    )


@pytest.fixture
def sample_basemap() -> gpd.GeoDataFrame:
    poly = Polygon([(10.5, 46.2), (12.5, 46.2), (12.5, 47.1), (10.5, 47.1)])
    return gpd.GeoDataFrame({"geometry": [poly]}, crs="EPSG:4326")
