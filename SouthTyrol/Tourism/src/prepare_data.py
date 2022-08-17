import os
import pickle

import pandas as pd
import geopandas as gpd
import geoviews as gv

from config import (
    RAW_DATA_DIR,
    PREPARED_ACCOMM_FILE,
    DENSITY_FILE,
    MUNICIPALITY_FILE,
    POPULATION_SHAPEFILE
)
from utils import get_kernel_density


def load_municipality_data() -> pd.DataFrame:
    """
    Merged accommodation data at GPS level with population data at municipality level using a geo-join.
    At the municipality level, calculate a variety of KPIs, which are listed in src.config.VARIABLES_INFO.

    Returns
    -------
    tourism_df: A dataframe with one row per municipality in South Tyrol and one column for each supported KPI.
                See src.config.VARIABLES_INFO for a list of variables available.
    """

    # Load accommodation data
    df = pd.read_csv(PREPARED_ACCOMM_FILE)
    df_geo = gpd.GeoDataFrame(df, crs="EPSG:4326")

    # Load population data
    population = gpd.read_file(POPULATION_SHAPEFILE, crs="EPSG:4326")
    population = population.to_crs("EPSG:4326")
    population.drop_duplicates(subset=["NAME_D"], inplace=True)

    # Aggregate information on municipality level
    tourism_df = (
        df_geo
        .groupby(["NAME_D", "NAME_I"])
        .agg(
            nr_establishments=("Id", "count"),
            total_occupancy=("MaxOccupancy", "sum"),
            total_nr_rooms=("TotalRooms", "sum"),
            avg_occupancy=("MaxOccupancy", "mean"),
            # Add shares for category rating & type
            share_1_rating=("AccoCategoryRating_1", "sum"),
            share_2_rating=("AccoCategoryRating_2", "sum"),
            share_3_rating=("AccoCategoryRating_3", "sum"),
            share_3s_rating=("AccoCategoryRating_3S", "sum"),
            share_4_rating=("AccoCategoryRating_4", "sum"),
            share_4s_rating=("AccoCategoryRating_4S", "sum"),
            share_5_rating=("AccoCategoryRating_5", "sum"),
            share_stars=("AccoCategoryType_Stars", "sum"),
            share_suns=("AccoCategoryType_Suns", "sum"),
            share_flowers=("AccoCategoryType_Flowers", "sum"),
        )
        .reset_index()
        .merge(population[["NAME_D", "BW_WOHNBEV", "geometry"]], on="NAME_D", how="left")
        .assign(
            nr_establishments_per_thousand_pop=lambda x: x.nr_establishments / (x.BW_WOHNBEV / 1_000),
            total_occupancy_per_thousand_pop=lambda x: x.total_occupancy / (x.BW_WOHNBEV / 1_000),
            total_nr_rooms_per_thousand_pop=lambda x: x.total_nr_rooms / (x.BW_WOHNBEV / 1_000)
        )
    )
    # Make sure share columns are actually in percentages
    share_cols = [i for i in tourism_df.columns if i.startswith("share_")]
    for c in share_cols:
        tourism_df[c] = tourism_df[c] / tourism_df.nr_establishments * 100
    assert tourism_df.NAME_D.nunique() == len(tourism_df)

    # Ensure dataframe is a geo-dataframe
    tourism_df = gpd.GeoDataFrame(tourism_df, geometry=tourism_df["geometry"])

    return tourism_df


def load_density_data() -> dict:
    """
    Transforms dataframe containing coordinates of tourism establishments into a geo-dataframe.
    From this dataframe, kernel density estimation is applied to measure the density of tourism establishments
    across South Tyrol. In order to visualise this map later, a basemap outlining the province is read in.
    All information is packaged in a dictionary for later use in `define_density_map()`

    Returns
    -------
    out_dict: A dictionary containing all necessary variables to create a density plot.
    """
    # Load accommodation data
    df = pd.read_csv(PREPARED_ACCOMM_FILE)

    # Read in province shapefiles
    province_shape = gpd.read_file(
        os.path.join(RAW_DATA_DIR, "shapefiles/Limiti01012021_g/ProvCM01012021_g/ProvCM01012021_g_WGS84.shp"),
        crs="EPSG:4326"
    )
    province_shape_projected = province_shape.to_crs('EPSG:4326')
    south_tyrol = province_shape_projected.query("SIGLA == 'BZ'")

    establishments = gv.Dataset(df, kdims=['City', 'Latitude', 'Longitude'])
    establishments = establishments.to(gv.Points, ['Longitude', 'Latitude'], ['City'])
    basemap = gv.Polygons(south_tyrol)

    y_grid, x_grid, z_grid_masked = get_kernel_density(df, south_tyrol)

    out_dict = {
        "establishments": establishments,
        "basemap": basemap,
        "y_grid": y_grid,
        "x_grid": x_grid,
        "z_grid_masked": z_grid_masked
    }

    return out_dict


if __name__ == '__main__':
    d_density = load_density_data()
    df_municipality = load_municipality_data()
    pickle.dump(d_density, open(DENSITY_FILE, "wb"))
    pickle.dump(df_municipality, open(MUNICIPALITY_FILE, "wb"))
