import geopandas as gpd
import holoviews as hv
import streamlit as st
from streamlit_bokeh import streamlit_bokeh

from south_tyrol_tourism.config import settings
from south_tyrol_tourism.dashboard_data import load_density_data
from south_tyrol_tourism.visualisation import define_density_map, define_municipality_map

hv.extension("bokeh")


@st.cache_resource
def _municipality_data() -> gpd.GeoDataFrame:
    return gpd.read_parquet(settings.municipality_file)


@st.cache_resource
def _density_data() -> dict[str, object]:
    return load_density_data()


st.title("Tourism in South Tyrol")

data = _municipality_data()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Number of Establishments")
    viz = define_municipality_map(
        data=data,
        color_col="nr_establishments",
        title="",
        clabel="Establishments",
        frame_width=550,
    )
    streamlit_bokeh(hv.render(viz, backend="bokeh"), use_container_width=False)

with col2:
    st.subheader("Establishments per 1,000 Inhabitants")
    viz = define_municipality_map(
        data=data,
        color_col="nr_establishments_per_thousand_pop",
        title="",
        clabel="Estab. / 1k pop",
        frame_width=550,
    )
    streamlit_bokeh(hv.render(viz, backend="bokeh"), use_container_width=False)

st.subheader("Spatial Density of Tourism Establishments")
viz = define_density_map(**_density_data())
streamlit_bokeh(hv.render(viz, backend="bokeh"), use_container_width=False)
