import streamlit as st

st.set_page_config(page_title="Tourism in South Tyrol", layout="wide")

pg = st.navigation(
    [
        st.Page("pages/Maps.py", title="Maps", icon="📍"),
        st.Page("pages/Tables.py", title="Tables", icon="📊"),
        st.Page("pages/Graphs.py", title="Graphs", icon="📈"),
    ]
)
pg.run()
