import geopandas as gpd
import geoviews as gv
import pandas as pd
from loguru import logger

from south_tyrol_tourism.config import settings
from south_tyrol_tourism.visualisation import get_kernel_density


_RATING_COLS = ["Rating_1", "Rating_2", "Rating_3", "Rating_3S", "Rating_4", "Rating_4S", "Rating_5"]
_TYPE_COLS = ["Hotel", "Apartment", "Farm"]


def load_municipality_data() -> gpd.GeoDataFrame:
    """Aggregates accommodation data to municipality level and returns a GeoDataFrame of KPIs."""
    df = pd.read_parquet(settings.prepared_accommodation_file)

    population = gpd.read_file(settings.population_shapefile).to_crs(settings.crs)
    population = population.drop_duplicates(subset=["NAME_D"])

    for type_ in _TYPE_COLS:
        for rating in _RATING_COLS:
            df[f"Type_{type_}_{rating}"] = df[f"Type_{type_}"] & df[rating]

    type_rating_aggs = {
        f"nr_{type_.lower()}_{rating.lower()}": (f"Type_{type_}_{rating}", "sum")
        for type_ in _TYPE_COLS
        for rating in _RATING_COLS
    }

    tourism_df = (
        df.groupby(["NAME_D", "NAME_I"])
        .agg(
            nr_establishments=("Id", "count"),
            share_1_rating=("Rating_1", "sum"),
            share_2_rating=("Rating_2", "sum"),
            share_3_rating=("Rating_3", "sum"),
            share_3s_rating=("Rating_3S", "sum"),
            share_4_rating=("Rating_4", "sum"),
            share_4s_rating=("Rating_4S", "sum"),
            share_5_rating=("Rating_5", "sum"),
            nr_hotels=("Type_Hotel", "sum"),
            nr_apartments=("Type_Apartment", "sum"),
            nr_farms=("Type_Farm", "sum"),
            **type_rating_aggs,
        )
        .reset_index()
        .merge(population[["NAME_D", "BW_WOHNBEV", "geometry"]], on="NAME_D", how="left")
        .assign(
            nr_establishments_per_thousand_pop=lambda x: (
                x["nr_establishments"] / (x["BW_WOHNBEV"] / 1_000)
            ),
        )
    )

    # Share of each rating across all establishments
    for col in [c for c in tourism_df.columns if c.startswith("share_")]:
        tourism_df[col] = tourism_df[col] / tourism_df["nr_establishments"] * 100

    # Share of each rating within each establishment type (fillna(0) for municipalities with none of that type)
    type_totals = {"hotel": "nr_hotels", "apartment": "nr_apartments", "farm": "nr_farms"}
    for type_, total_col in type_totals.items():
        tourism_df[f"share_{type_}s"] = (
            tourism_df[total_col] / tourism_df["nr_establishments"] * 100
        ).fillna(0)
        for rating in _RATING_COLS:
            tourism_df[f"share_{type_}_{rating.lower()}"] = (
                tourism_df[f"nr_{type_}_{rating.lower()}"] / tourism_df[total_col] * 100
            ).fillna(0)

    assert tourism_df["NAME_D"].nunique() == len(tourism_df)

    return gpd.GeoDataFrame(tourism_df, geometry=tourism_df["geometry"])


def save_south_tyrol_boundary() -> None:
    """Extracts the South Tyrol polygon from the province shapefile and persists it."""
    province_shape = gpd.read_file(settings.province_shapefile).to_crs(settings.crs)
    south_tyrol = province_shape.query("SIGLA == 'BZ'")
    south_tyrol.to_parquet(settings.south_tyrol_boundary_file)
    logger.info(f"South Tyrol boundary saved → {settings.south_tyrol_boundary_file}")


def load_density_data() -> dict[str, object]:
    """Loads accommodation coordinates and computes KDE inputs for the density map."""
    df = pd.read_parquet(settings.prepared_accommodation_file)

    south_tyrol = gpd.read_parquet(settings.south_tyrol_boundary_file)

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
    """Precomputes and persists all dashboard data files."""
    logger.info("Preparing dashboard data")
    settings.dashboard_data_dir.mkdir(parents=True, exist_ok=True)
    df_municipality = load_municipality_data()
    df_municipality.to_parquet(settings.municipality_file)
    logger.info(f"Municipality data saved → {settings.municipality_file}")
    save_south_tyrol_boundary()


if __name__ == "__main__":
    main()
