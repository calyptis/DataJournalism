import streamlit as st
import streamlit.components.v1 as components
import os
from utils import (
    load_municipality_data, define_municipality_map,
    load_density_data, define_density_map, save_map
)
from config import PLOT_DIR, VARIABLES_INV


def get_data(selection):
    # TODO: How can streamlit cache dict instead of pd.DataFrames?
    if selection == "by Municipality":
        return load_municipality_data()
    elif selection == "by GPS":
        return load_density_data()


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
    select_kpi = st.sidebar.selectbox(text, set(VARIABLES_INV.keys()) - {"Municipality"})
else:
    select_kpi = st.sidebar.selectbox(text, ["Number of Tourism Establishments"])
kpi_col_name = VARIABLES_INV[select_kpi]
# Visualisation options:
if select_map_type == "by Municipality":
    select_all_kpis_tooltip = st.sidebar.radio("Include all available KPIs in tooltip: ", [True, False])
else:
    select_all_kpis_tooltip = None

# --------- Generate Visualisations
# For now Streamlit does not support Bokeh plots (dependency issues)
# Therefore save plot as HTML
filename = os.path.join(PLOT_DIR, f"{select_map_type} - {select_kpi}")
if not os.path.exists(filename + ".html"):

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

    save_map(visualisation, filename, filetype="html")

# --------- Main Page
st.title('Tourism in South Tyrol')
# st.bokeh_chart(hv.render(visualisation, backend='bokeh'))
components.html(open(filename + ".html", "r").read(), width=1000, height=800)
