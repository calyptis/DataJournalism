from pathlib import Path

import geopandas as gpd
import geoviews as gv
import holoviews as hv
import numpy as np
import pandas as pd
from bokeh.models import HoverTool
from loguru import logger
from sklearn.neighbors import KernelDensity

from south_tyrol_tourism.config import VARIABLES_INFO


def define_municipality_map(
    data: gpd.GeoDataFrame,
    color_col: str,
    title: str,
    clabel: str,
    tooltip_all_kpis: bool = False,
) -> gv.Polygons:
    """Returns a choropleth of the selected tourism KPI at municipality level."""
    if tooltip_all_kpis:
        tooltips = [(v[0], "@" + k + v[1]) for k, v in VARIABLES_INFO.items() if k in data.columns]
    else:
        col_info = VARIABLES_INFO[color_col]
        municipality_info = {k: v for k, v in VARIABLES_INFO.items() if k in ("NAME_D", "NAME_I")}
        tooltips = [(col_info[0], "@" + color_col + col_info[1])]
        tooltips += [(v[0], "@" + k + v[1]) for k, v in municipality_info.items()]

    vdims = [k for k in VARIABLES_INFO if k in data.columns]
    hover = HoverTool(tooltips=tooltips)
    return (
        gv.Polygons(data, vdims=vdims)
        .opts(
            tools=[hover],
            responsive=True,
            aspect="equal",
            color=color_col,
            colorbar=True,
            toolbar="below",
            xaxis=None,
            yaxis=None,
            title=title,
            cmap="Blues",
            clabel=clabel,
        )
    )


def define_density_map(
    establishments: gv.Points,
    basemap: gv.Polygons,
    y_grid: np.ndarray,
    x_grid: np.ndarray,
    z_grid_masked: np.ndarray,
) -> hv.Overlay:
    """Combines basemap and kernel density heatmap into a single geoviews overlay."""
    reference_df = pd.DataFrame(
        [
            ("Merano", 46.669877, 11.164477),
            ("Bolzano", 46.490620, 11.338833),
            ("Ortisei", 46.572632, 11.676449),
            ("Bressanone", 46.714856, 11.656111),
            ("Brunico", 46.795319, 11.938820),
            ("Vipiteno", 46.892434, 11.430226),
            ("Silandro", 46.628023, 10.771166),
            ("Curon", 46.807447, 10.539065),
            ("San\nCandido", 46.731986, 12.281373),
        ],
        columns=["City", "Latitude", "Longitude"],
    )
    reference_points = gv.Points(reference_df, ["Longitude", "Latitude"], ["City"])
    reference_labels_df = reference_df.copy()
    reference_labels_df["Latitude"] += -0.03
    reference_labels = gv.Labels(reference_labels_df, ["Longitude", "Latitude"], ["City"])

    return (
        basemap.opts(
            colorbar=False,
            fill_color="rgba(255, 255, 255, 0.3)",
            color_index=None,
            line_color="black",
            tools=[],
        )
        * establishments.opts(size=10, marker="dot", tools=[])
        * gv.FilledContours((y_grid, x_grid, z_grid_masked)).opts(
            cmap="PuBu",
            fill_alpha=0.8,
            line_color=None,
            tools=[],
        )
        * reference_points.opts(size=10, tools=[], color="black")
        * reference_labels.opts(text_color="white")
    ).opts(
        responsive=True,
        aspect="equal",
        xaxis=None,
        yaxis=None,
        toolbar="below",
        title="Spatial Density of Tourism Establishments",
    )


def save_map(figure: gv.Polygons | hv.Overlay, path: Path, filetype: str = "html") -> None:
    """Saves a geoviews figure to disk as HTML or PNG (Bokeh backend)."""
    logger.info(f"Saving {path}")
    if filetype == "html":
        gv.save(figure, filename=f"{path}.html")
    elif filetype == "bokeh":
        gv.save(figure, filename=f"{path}.png", backend="bokeh", toolbar=False)
    else:
        raise ValueError(f"Unsupported file type: {filetype!r}")


def get_kernel_density(
    df: pd.DataFrame,
    basemap: gpd.GeoDataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fits a KDE on establishment GPS coordinates; masks estimates outside the basemap."""
    n_samples = 200j
    ymin, xmin, ymax, xmax = basemap.geometry.iloc[0].bounds
    x_grid, y_grid = np.mgrid[xmin:xmax:n_samples, ymin:ymax:n_samples]
    grid = np.vstack([x_grid.ravel(), y_grid.ravel()])

    lat_long = df[["Latitude", "Longitude"]].values
    kde = KernelDensity(bandwidth=0.03)
    kde.fit(lat_long)
    z_grid = kde.score_samples(grid.T).reshape(x_grid.shape)

    coords_arr = np.vstack([x_grid.flatten(), y_grid.flatten(), z_grid.flatten()]).T
    coords_gdf = gpd.GeoDataFrame(
        coords_arr,
        columns=["Latitude", "Longitude", "Z"],
        geometry=gpd.points_from_xy(coords_arr[:, 1], coords_arr[:, 0]),
    )
    inside = coords_gdf.geometry.apply(lambda p: basemap.geometry.contains(p).any())
    z_grid_masked = np.where(inside, coords_gdf["Z"], np.nan).reshape(z_grid.shape)

    return y_grid, x_grid, z_grid_masked
