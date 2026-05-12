import streamlit as st

st.set_page_config(page_title="Tourism in South Tyrol", layout="wide")

pg = st.navigation(
    [
        st.Page("south_tyrol_tourism/pages/Maps.py", title="Maps", icon="📍"),
        st.Page("south_tyrol_tourism/pages/Tables.py", title="Tables", icon="📊"),
        st.Page("south_tyrol_tourism/pages/Graphs.py", title="Graphs", icon="📈"),
    ]
)
pg.run()