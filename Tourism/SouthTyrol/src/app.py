import streamlit as st
import streamlit.components.v1 as components
import os
import pickle
from .utils import (
    load_municipality_data, define_municipality_map,
    load_density_data, define_density_map, save_map
)
from .config import PLOT_DIR, VARIABLES_INV, MUNICIPALITY_FILE, DENSITY_FILE


def get_data(selection):
    # Note: In docker image => these files already exist
    if selection == "by Municipality":
        if not os.path.exists(MUNICIPALITY_FILE):
            df_municipality = load_municipality_data()
            pickle.dump(df_municipality, open(MUNICIPALITY_FILE, "wb"))
            return df_municipality
        else:
            return pickle.load(open(MUNICIPALITY_FILE, "rb"))
    elif selection == "by GPS":
        if not os.path.exists(DENSITY_FILE):
            d_density = load_density_data()
            pickle.dump(d_density, open(DENSITY_FILE, "wb"))
            return d_density
        else:
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
# For now Streamlit does not support Bokeh plots (dependency issues)
# Therefore save plot as HTML
filename = os.path.join(PLOT_DIR, f"{select_map_type} - {select_kpi} - {str(select_all_kpis_tooltip)}")
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
