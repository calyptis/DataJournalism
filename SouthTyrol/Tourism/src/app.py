import streamlit as st
import holoviews as hv
import pickle
from utils import (
    define_municipality_map,
    define_density_map,
)
from config import (
    VARIABLES_INV,
    MUNICIPALITY_FILE,
    DENSITY_FILE,
)


def get_data(selection):
    # Note: In docker image => these files already exist
    if selection == "by Municipality":
        return pickle.load(open(MUNICIPALITY_FILE, "rb"))
    elif selection == "by GPS":
        return pickle.load(open(DENSITY_FILE, "rb"))


app_title = 'Tourism in South Tyrol'
st.set_page_config(page_title=app_title, layout="wide")

# --------- Side Bar
# Map type
select_map_type = st.sidebar.selectbox(
    "Please choose the granularity of the visualisation: ",
    ["by Municipality", "by GPS"]
)
# KPI to visualise
text = "Please choose the metric to visualise: "
if select_map_type == "by Municipality":
    select_kpi = st.sidebar.selectbox(
        text,
        [i for i in VARIABLES_INV.keys() if i not in ["Municipality (de)", "Municipality (it)"]]
    )
else:
    select_kpi = st.sidebar.selectbox(text, ["Number of Tourism Establishments"])
kpi_col_name = VARIABLES_INV[select_kpi]
# Visualisation options:
if select_map_type == "by Municipality":
    select_all_kpis_tooltip = st.sidebar.radio("Include all available KPIs in tooltip: ", [True, False])
else:
    select_all_kpis_tooltip = None
# --------- Generate Visualisations
tourism_data = get_data(select_map_type)
if select_map_type == "by Municipality":
    visualisation = define_municipality_map(
        data=tourism_data,
        color_col=kpi_col_name,
        title=select_kpi + " " + select_map_type,
        clabel=select_kpi,
        tooltip_all_kpis=select_all_kpis_tooltip
    )
elif select_map_type == "by GPS":
    visualisation = define_density_map(**tourism_data)
else:
    raise NotImplementedError()

# --------- Main Page
st.title('Tourism in South Tyrol')
st.bokeh_chart(hv.render(visualisation, backend='bokeh'))
