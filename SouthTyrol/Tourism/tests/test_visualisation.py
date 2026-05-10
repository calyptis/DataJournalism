import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from south_tyrol_tourism.visualisation import get_kernel_density


@pytest.fixture
def accommodation_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Latitude": [46.67, 46.49, 46.72, 46.80, 46.57],
            "Longitude": [11.16, 11.34, 11.66, 11.94, 11.68],
        }
    )


def test_get_kernel_density_returns_three_arrays(
    accommodation_df: pd.DataFrame, sample_basemap: gpd.GeoDataFrame
) -> None:
    y_grid, x_grid, z_grid_masked = get_kernel_density(accommodation_df, sample_basemap)
    assert isinstance(y_grid, np.ndarray)
    assert isinstance(x_grid, np.ndarray)
    assert isinstance(z_grid_masked, np.ndarray)


def test_get_kernel_density_output_shapes_match(
    accommodation_df: pd.DataFrame, sample_basemap: gpd.GeoDataFrame
) -> None:
    y_grid, x_grid, z_grid_masked = get_kernel_density(accommodation_df, sample_basemap)
    assert y_grid.shape == x_grid.shape == z_grid_masked.shape


def test_get_kernel_density_has_non_nan_values_inside_basemap(
    accommodation_df: pd.DataFrame, sample_basemap: gpd.GeoDataFrame
) -> None:
    _, _, z = get_kernel_density(accommodation_df, sample_basemap)
    assert not np.all(np.isnan(z)), "All KDE values are NaN — basemap may not overlap data"


def test_get_kernel_density_uses_nan_not_zero_for_outside(
    accommodation_df: pd.DataFrame, sample_basemap: gpd.GeoDataFrame
) -> None:
    _, _, z = get_kernel_density(accommodation_df, sample_basemap)
    assert np.any(np.isnan(z)) or not np.any(z == 0), (
        "Outside-basemap values should be NaN, not zero"
    )
