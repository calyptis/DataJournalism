import geopandas as gpd
import streamlit as st

from south_tyrol_tourism.config import settings

_RATING_SUFFIXES = ["1", "2", "3", "3s", "4", "4s", "5"]
_RATING_LABELS = ["1", "2", "3", "3S", "4", "4S", "5"]

_PCT = "%.1f"

_COLUMN_CONFIG = {
    "NAME_D": st.column_config.TextColumn("Municipality (DE)"),
    "NAME_I": st.column_config.TextColumn("Municipality (IT)"),
    "nr_establishments": st.column_config.NumberColumn("# Establishments", format="%d"),
    "nr_establishments_per_thousand_pop": st.column_config.NumberColumn(
        "# per 1,000 pop", format="%.1f"
    ),
    "share_hotels": st.column_config.NumberColumn("Hotels %", format=_PCT),
    "share_apartments": st.column_config.NumberColumn("Apartments %", format=_PCT),
    "share_farms": st.column_config.NumberColumn("Farms %", format=_PCT),
    **{
        f"share_hotel_rating_{r}": st.column_config.NumberColumn(
            f"Hotel Rating {l} %", format=_PCT
        )
        for r, l in zip(_RATING_SUFFIXES, _RATING_LABELS)
    },
    **{
        f"share_apartment_rating_{r}": st.column_config.NumberColumn(
            f"Apt Rating {l} %", format=_PCT
        )
        for r, l in zip(_RATING_SUFFIXES, _RATING_LABELS)
    },
    **{
        f"share_farm_rating_{r}": st.column_config.NumberColumn(
            f"Farm Rating {l} %", format=_PCT
        )
        for r, l in zip(_RATING_SUFFIXES, _RATING_LABELS)
    },
}

_GENERAL_COLS = ["NAME_D", "NAME_I", "nr_establishments", "nr_establishments_per_thousand_pop"]
_HOTEL_COLS = ["NAME_D", "share_hotels", *(f"share_hotel_rating_{r}" for r in _RATING_SUFFIXES)]
_APARTMENT_COLS = ["NAME_D", "share_apartments", *(f"share_apartment_rating_{r}" for r in _RATING_SUFFIXES)]
_FARM_COLS = ["NAME_D", "share_farms", *(f"share_farm_rating_{r}" for r in _RATING_SUFFIXES)]


@st.cache_resource
def _municipality_data() -> gpd.GeoDataFrame:
    return gpd.read_parquet(settings.municipality_file)


st.title("Municipality KPIs")

data = _municipality_data()

query = st.text_input("Search municipality…", "")
if query:
    mask = data["NAME_D"].str.contains(query, case=False, na=False) | data[
        "NAME_I"
    ].str.contains(query, case=False, na=False)
    data = data[mask]

tab_general, tab_hotels, tab_apartments, tab_farms = st.tabs(
    ["General", "Hotels", "Apartments", "Farms"]
)

with tab_general:
    st.dataframe(data[_GENERAL_COLS], column_config=_COLUMN_CONFIG, width='stretch')

with tab_hotels:
    st.dataframe(data[_HOTEL_COLS], column_config=_COLUMN_CONFIG, width='stretch')

with tab_apartments:
    st.dataframe(data[_APARTMENT_COLS], column_config=_COLUMN_CONFIG, width='stretch')

with tab_farms:
    st.dataframe(data[_FARM_COLS], column_config=_COLUMN_CONFIG, width='stretch')
