import geopandas as gpd
import geoviews as gv
import pandas as pd
from loguru import logger

from south_tyrol_tourism.config import settings
from south_tyrol_tourism.visualisation import get_kernel_density


def load_municipality_data() -> gpd.GeoDataFrame:
    """Aggregates accommodation data to municipality level and returns a GeoDataFrame of KPIs."""
    df = pd.read_parquet(settings.prepared_accommodation_file)

    population = gpd.read_file(settings.population_shapefile).to_crs(settings.crs)
    population = population.drop_duplicates(subset=["NAME_D"])

    tourism_df = (
        df.groupby(["NAME_D", "NAME_I"])
        .agg(
            nr_establishments=("Id", "count"),
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
            nr_establishments_per_thousand_pop=lambda x: (
                x["nr_establishments"] / (x["BW_WOHNBEV"] / 1_000)
            ),
        )
    )

    share_cols = [c for c in tourism_df.columns if c.startswith("share_")]
    for col in share_cols:
        tourism_df[col] = tourism_df[col] / tourism_df["nr_establishments"] * 100

    assert tourism_df["NAME_D"].nunique() == len(tourism_df)

    return gpd.GeoDataFrame(tourism_df, geometry=tourism_df["geometry"])


def load_density_data() -> dict[str, object]:
    """Loads accommodation coordinates and computes KDE inputs for the density map."""
    df = pd.read_parquet(settings.prepared_accommodation_file)

    province_shape = gpd.read_file(settings.province_shapefile).to_crs(settings.crs)
    south_tyrol = province_shape.query("SIGLA == 'BZ'")

    establishments = (
        gv.Dataset(df, kdims=["City", "Latitude", "Longitude"])
        .to(gv.Points, ["Longitude", "Latitude"], ["City"])
    )
    basemap = gv.Polygons(south_tyrol)
    y_grid, x_grid, z_grid_masked = get_kernel_density(df, south_tyrol)

    return {
        "establishments": establishments,
        "basemap": basemap,
        "y_grid": y_grid,
        "x_grid": x_grid,
        "z_grid_masked": z_grid_masked,
    }


def main() -> None:
    """Precomputes and persists municipality data for the dashboard."""
    logger.info("Preparing dashboard data")
    settings.dashboard_data_dir.mkdir(parents=True, exist_ok=True)
    df_municipality = load_municipality_data()
    df_municipality.to_parquet(settings.municipality_file)
    logger.info(f"Municipality data saved → {settings.municipality_file}")


if __name__ == "__main__":
    main()
