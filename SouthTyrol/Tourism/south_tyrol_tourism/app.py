import geopandas as gpd
import holoviews as hv
import streamlit as st

from south_tyrol_tourism.config import VARIABLES_INV, settings
from south_tyrol_tourism.dashboard_data import load_density_data
from south_tyrol_tourism.visualisation import define_density_map, define_municipality_map

_APP_TITLE = "Tourism in South Tyrol"
st.set_page_config(page_title=_APP_TITLE, layout="wide")


@st.cache_resource
def _municipality_data() -> gpd.GeoDataFrame:
    return gpd.read_parquet(settings.municipality_file)


@st.cache_resource
def _density_data() -> dict[str, object]:
    return load_density_data()


map_type: str = st.sidebar.selectbox(
    "Please choose the granularity of the visualisation:",
    ["by Municipality", "by GPS"],
)

if map_type == "by Municipality":
    kpi_label: str = st.sidebar.selectbox(
        "Please choose the metric to visualise:",
        [k for k in VARIABLES_INV if k not in ("Municipality (de)", "Municipality (it)")],
    )
    show_all_kpis: bool | None = st.sidebar.radio(
        "Include all available KPIs in tooltip:", [True, False]
    )
else:
    kpi_label = st.sidebar.selectbox(
        "Please choose the metric to visualise:",
        ["Number of Tourism Establishments"],
    )
    show_all_kpis = None

kpi_col = VARIABLES_INV[kpi_label]

if map_type == "by Municipality":
    viz = define_municipality_map(
        data=_municipality_data(),
        color_col=kpi_col,
        title=f"{kpi_label} {map_type}",
        clabel=kpi_label,
        tooltip_all_kpis=bool(show_all_kpis),
    )
elif map_type == "by GPS":
    viz = define_density_map(**_density_data())
else:
    raise NotImplementedError(f"Unknown map type: {map_type!r}")

st.title(_APP_TITLE)
st.bokeh_chart(hv.render(viz, backend="bokeh"))
