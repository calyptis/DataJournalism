import math

import pandas as pd
import streamlit as st
from bokeh.palettes import PuBu
from bokeh.plotting import figure
from bokeh.transform import cumsum
from streamlit_bokeh import streamlit_bokeh

from south_tyrol_tourism.config import settings

_RATING_COLS = ["Rating_1", "Rating_2", "Rating_3", "Rating_3S", "Rating_4", "Rating_4S", "Rating_5"]
_RATING_LABELS = ["1", "2", "3", "3S", "4", "4S", "5"]

# Spectral[7] runs blue→red; reverse so Rating 5 (best) = deep blue, Rating 1 (lowest) = red
_RATING_PALETTE = tuple(reversed(PuBu[7]))


@st.cache_resource
def _accommodation_data() -> pd.DataFrame:
    return pd.read_parquet(settings.prepared_accommodation_file)


def _pie_chart(
    df: pd.DataFrame,
    title: str,
    palette: tuple,
    width: int = 180,
    height: int = 180,
) -> figure:
    """df: 'label' and 'count' columns. Zero-count slices are dropped."""
    df = df[df["count"] > 0].copy().reset_index(drop=True)
    total = df["count"].sum()
    df["angle"] = df["count"] / total * 2 * math.pi
    df["pct"] = df["count"] / total * 100
    df["color"] = list(palette[: len(df)])

    p = figure(
        height=height,
        width=width,
        title=title,
        toolbar_location=None,
        tools="hover",
        tooltips="@label: @pct{0.1f}%",
    )
    p.wedge(
        x=0,
        y=1,
        radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend_field="label",
        source=df,
    )
    p.axis.visible = False
    p.grid.grid_line_color = None
    p.outline_line_color = None
    p.legend.location = "bottom_left"
    p.legend.label_text_font_size = "10px"
    p.legend.spacing = 2
    p.legend.padding = 4
    p.sizing_mode = "scale_width"
    return p


st.title("South Tyrol — Overview")

df = _accommodation_data()

# --- Section 1: Type breakdown ---
st.subheader("Accommodation Types")

other_mask = ~df["Type_Hotel"] & ~df["Type_Apartment"] & ~df["Type_Farm"]
type_df = pd.DataFrame({
    "label": ["Hotels", "Apartments", "Farms", "Other"],
    "count": [
        int(df["Type_Hotel"].sum()),
        int(df["Type_Apartment"].sum()),
        int(df["Type_Farm"].sum()),
        int(other_mask.sum()),
    ],
})

_, center_col, _ = st.columns([1, 1, 1])
with center_col:
    streamlit_bokeh(_pie_chart(type_df, "Share of Accommodation Types", PuBu[4], width=290, height=300), use_container_width=True)

# --- Section 2: Ratings per type ---
st.subheader("Rating Distribution by Type")

type_filters = {
    "Hotels":     df["Type_Hotel"],
    "Apartments": df["Type_Apartment"],
    "Farms":      df["Type_Farm"],
}

col1, col2, col3 = st.columns(3)
for col, (type_name, mask) in zip([col1, col2, col3], type_filters.items()):
    subset = df[mask]
    rating_df = pd.DataFrame({
        "label": _RATING_LABELS,
        "count": [int(subset[r].sum()) for r in _RATING_COLS],
    })
    with col:
        streamlit_bokeh(_pie_chart(rating_df, type_name, _RATING_PALETTE), use_container_width=True)
