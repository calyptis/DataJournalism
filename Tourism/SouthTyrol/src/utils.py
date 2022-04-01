from typing import Tuple
import os
import pandas as pd
import geopandas as gpd
import geoviews as gv
from bokeh.models import HoverTool
import numpy as np
from sklearn.neighbors import KernelDensity
from src.config import RAW_DATA_DIR, PREPARED_ACCOMM_FILE, VARIABLES_INFO


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
    df_geo = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")

    # Load population data
    population = gpd.read_file(
        os.path.join(
            RAW_DATA_DIR,
            "shapefiles/FME_12060355_1631560092259_118556/DownloadService/OfficialResidentPopulation_polygon.shp"
        ),
        crs="EPSG:4326"
    )
    population = population.to_crs("EPSG:4326")
    population.drop_duplicates(subset=["NAME_D"], inplace=True)

    # Merge data sources
    df_merged = gpd.sjoin(df_geo, population[["NAME_D", "NAME_I", "geometry"]], how="left", op="within")

    # Aggregate information on municipality level
    tourism_df = (
        df_merged
        .groupby(["NAME_D", "NAME_I"])
        .agg(
            nr_establishments=("Id", "count"),
            total_occupancy=("MaxOccupancy", "sum"),
            total_nr_rooms=("TotalRooms", "sum"),
            avg_occupancy=("MaxOccupancy", "mean")
        )
        .reset_index()
        .merge(population[["NAME_D", "geometry", "BW_WOHNBEV"]], on="NAME_D", how="left")
        .assign(
            nr_establishments_per_thousand_pop=lambda x: x.nr_establishments / (x.BW_WOHNBEV / 1_000),
            total_occupancy_per_thousand_pop=lambda x: x.total_occupancy / (x.BW_WOHNBEV / 1_000)
        )
    )
    assert tourism_df.NAME_D.nunique() == len(tourism_df)

    # Ensure dataframe is a geo-dataframe
    tourism_df = gpd.GeoDataFrame(tourism_df, geometry=tourism_df["geometry"])

    return tourism_df


def define_municipality_map(
        data: pd.DataFrame, color_col: str, title: str, clabel: str, tooltip_all_kpis: bool = False
) -> gv.Polygons:
    """
    Plots a choropleth using bokeh for a selected tourism related summary metric at municipality level.

    Parameters
    ----------
    data: Tourism data summarised at the municipality level. See output of src.utils.load_municipality_data().
    color_col: Variable to plot as colour in the resulting choropleth.
    title: The title to add to the Bokeh plot.
    clabel: The label to give to the color bar of the Bokeh plot.
    tooltip_all_kpis: Whether to include all tourism related variables in the tooltip or just the one selected by
                      the `color_col` variable.

    Returns
    -------
    visualisation: Bokeh choropleth map at municipality level with the colouring defined by the `color_col` variable.
    """

    if tooltip_all_kpis:
        v = VARIABLES_INFO[color_col]
        tooltips = [(v[0], "@" + color_col + v[1])]
    else:
        tooltips = [
            (v[0], "@" + k + v[1]) for k, v in VARIABLES_INFO.items()
        ]

    hover = HoverTool(tooltips=tooltips)
    # TODO: Cap cmap at 95th percentile
    visualisation = (
        gv.Polygons(
            data,
            vdims=list(VARIABLES_INFO.keys())
        )
        .opts(
            tools=[hover], width=900, height=600, color=color_col,
            colorbar=True, toolbar="below", xaxis=None, yaxis=None,
            title=title,
            cmap="Blues", clabel=clabel
        )
    )

    return visualisation


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


def define_density_map(
        establishments: gv.Points, basemap: gv.Polygons, y_grid: np.array, x_grid, z_grid_masked
) -> gv.Polygons:
    """
    Combines the basemap and the kernel density into one plot to visualise the density of tourism establishments
    in South Tyrol as a heatmap.

    Parameters
    ----------
    establishments: Contains all tourism establishments as GPS coordinates in a gv.Points object.
    basemap: The outline of South Tyrol as a gv.Polygons object.
    y_grid: The y coordinates (or latitude) of the kernel density estimation of tourism establishments.
    x_grid: The y coordinates (or longitude) of the kernel density estimation of tourism establishments.
    z_grid_masked: The z coordinates (or density) of the kernel density estimation of tourism establishments.
                   These values specify the colour of the density heatmap.

    Returns
    -------
    geomap: The final geoviews figure.
    """
    # Define main cities/villages that act as a reference point for the map
    # TODO: Add language support
    reference_locations_df = pd.DataFrame(
        [
            ("Merano", 46.669877, 11.164477),
            ("Bolzano", 46.490620, 11.338833),
            ("Ortisei", 46.572632, 11.676449),
            ("Bressanone", 46.714856, 11.656111),
            ("Brunico", 46.795319, 11.938820),
            ("Vipiteno", 46.892434, 11.430226),
            ("Silandro", 46.628023, 10.771166),
            ("Curon", 46.807447, 10.539065),
            ("San\nCandido", 46.731986, 12.281373)
        ],
        columns=["City", "Latitude", "Longitude"]
    )
    reference_locations = gv.Points(reference_locations_df, ['Longitude', 'Latitude'], ['City'])

    # Offset labels
    reference_locations_labels = reference_locations_df.copy()
    latitude_offset = -0.03
    reference_locations_labels["Latitude"] = reference_locations_labels["Latitude"] + latitude_offset
    reference_locations_labels = gv.Labels(reference_locations_labels, ["Longitude", "Latitude"], ["City"])

    geomap = (
        basemap
        .opts(
            colorbar=False, fill_color="rgba(255, 255, 255, 0.3)",
            color_index=None, line_color="black", tools=[]
        )
        *
        establishments
        .opts(
            size=10,
            marker="dot",
            tools=[]
        )
        *
        gv.FilledContours((y_grid, x_grid, z_grid_masked))
        .opts(
            cmap='PuBu',
            fill_alpha=0.8,
            # levels=levels,
            line_color=None,
            tools=[]
        )
        *
        reference_locations
        .opts(
            size=10,
            tools=[],
            color="black",
        )
        *
        reference_locations_labels
        .opts(
            text_color="white"
        )
    ).opts(
        width=900, height=600, xaxis=None, yaxis=None, toolbar='below',
        title='Spatial Density of Tourism Establishments'
    )

    return geomap


def save_map(figure: gv.Polygons, filename: str, filetype: str = "html"):
    """
    Saves a Bokeh rendering of a geoviews figure at the desired location with the desired file type.

    Parameters
    ----------
    figure: The geoviews figure to save. Note that this figure is rendered using the Bokeh backend.
    filename: The path where the figure should be saved.
    filetype: The type the figure should be saved as.
    """
    print(f"Saving {filename}.")
    if filetype == "html":
        gv.save(figure, filename=f"{filename}.html")
    elif filetype == "bokeh":
        gv.save(
            figure, filename=f"{filename}.png", backend="bokeh",
            toolbar=False
        )
    else:
        raise Exception(f"Saving map as {filetype} is not supported")


def get_kernel_density(df: pd.DataFrame, basemap: gpd.GeoDataFrame) -> Tuple[np.array, np.array, np.array]:
    """
    Performs kernel density estimation on the GPS coordinates of tourism establishments in South Tyrol.

    Parameters
    ----------
    df: Dataframe containing the GPS coordinates for which the density should be estimated.
    basemap: Geo-dataframe describing the border of the GPS coordinates at which density estimations should be stopped.

    Returns
    -------
    kernel_estimates: The y, x, z coordinates of the kernel density estimation.
    """
    # Define grid for on which KDE should be applied
    n_samples = 200j
    # Based on establishments
    # xmin, xmax = df.Latitude.min(), df.Latitude.max()
    # ymin, ymax = df.Longitude.min(), df.Longitude.max()
    # Based on basemap
    ymin, xmin, ymax, xmax = basemap.geometry.iloc[0].bounds
    x_grid, y_grid = np.mgrid[xmin:xmax:n_samples, ymin:ymax:n_samples]
    grid = np.vstack([x_grid.ravel(), y_grid.ravel()])
    # Data on which KDE should be fitted
    lat_long = df[["Latitude", "Longitude"]].values
    # Fit KDE
    kde = KernelDensity(bandwidth=0.03)
    kde.fit(lat_long)
    # Apply KDE on grid
    z_grid = kde.score_samples(grid.T).reshape(x_grid.shape)

    # Alternative:
    # kernel = stats.gaussian_kde(values, bw_method=0.1)
    # z_grid = np.reshape(kernel(grid).T, x_grid.shape)

    # If we only want to plot densities within the basemap's boundaries
    coords = np.vstack([x_grid.flatten(), y_grid.flatten(), z_grid.flatten()]).T
    coords = gpd.GeoDataFrame(coords, geometry=gpd.points_from_xy(coords[:, 1], coords[:, 0]))
    coords.columns = ["Latitude", "Longitude", "Z", "geometry"]
    coords["flag"] = coords.geometry.apply(lambda x: basemap.geometry.contains(x))
    z_grid_masked = np.where(coords.flag, coords.Z, np.NaN).reshape(z_grid.shape)
    kernel_estimates = (y_grid, x_grid, z_grid_masked)
    return kernel_estimates
