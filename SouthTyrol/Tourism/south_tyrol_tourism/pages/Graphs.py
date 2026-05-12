import pandas as pd
import streamlit as st
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import PuBu
from bokeh.plotting import figure
from bokeh.transform import dodge
from streamlit_bokeh import streamlit_bokeh

from south_tyrol_tourism.config import settings

_RATING_COLS = ["Rating_1", "Rating_2", "Rating_3", "Rating_3S", "Rating_4", "Rating_4S", "Rating_5"]
_RATING_LABELS = ["1", "2", "3", "3S", "4", "4S", "5"]
_TYPES = ["Hotels", "Apartments", "Farms"]
_COLORS_4 = PuBu[6][2:]   # 4 mid-to-dark blue shades, skipping the two lightest
_COLORS_3 = _COLORS_4[:3]  # same first 3 shades for grouped chart consistency


@st.cache_resource
def _accommodation_data() -> pd.DataFrame:
    return pd.read_parquet(settings.prepared_accommodation_file)


def _type_bar_chart(type_df: pd.DataFrame) -> figure:
    total = type_df["count"].sum()
    source = ColumnDataSource({
        "label": type_df["label"].tolist(),
        "pct": (type_df["count"] / total * 100).tolist(),
        "color": list(_COLORS_4),
    })
    p = figure(
        x_range=type_df["label"].tolist(),
        height=250,
        toolbar_location=None,
        tools="hover",
        tooltips=[("", "@label"), ("Share", "@pct{0.1f}%")],
        y_axis_label="Share (%)",
    )
    p.vbar(x="label", top="pct", width=0.6, source=source, color="color")
    p.y_range.start = 0
    p.xgrid.grid_line_color = None
    p.outline_line_color = None
    p.sizing_mode = "stretch_width"
    return p


def _rating_grouped_bar_chart(df: pd.DataFrame) -> figure:
    type_masks = {
        "Hotels": df["Type_Hotel"],
        "Apartments": df["Type_Apartment"],
        "Farms": df["Type_Farm"],
    }
    data: dict[str, list] = {"ratings": _RATING_LABELS}
    for type_name, mask in type_masks.items():
        counts = [int(df.loc[mask, r].sum()) for r in _RATING_COLS]
        total = sum(counts)
        data[type_name] = [c / total * 100 if total else 0.0 for c in counts]

    source = ColumnDataSource(data)
    p = figure(
        x_range=_RATING_LABELS,
        height=250,
        toolbar_location=None,
        x_axis_label="Rating",
        y_axis_label="Share within type (%)",
    )
    offsets = [-0.25, 0.0, 0.25]
    for type_name, offset, color in zip(_TYPES, offsets, _COLORS_3):
        r = p.vbar(
            x=dodge("ratings", offset, range=p.x_range),
            top=type_name,
            width=0.2,
            source=source,
            color=color,
            legend_label=type_name,
        )
        p.add_tools(HoverTool(
            renderers=[r],
            tooltips=[("Type", type_name), ("Rating", "@ratings"), ("Share", f"@{type_name}{{0.1f}}%")],
        ))
    p.y_range.start = 0
    p.xgrid.grid_line_color = None
    p.outline_line_color = None
    p.legend.location = "top_right"
    p.sizing_mode = "stretch_width"
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
streamlit_bokeh(_type_bar_chart(type_df), use_container_width=True)

# --- Section 2: Ratings per type ---
st.subheader("Rating Distribution by Type")
streamlit_bokeh(_rating_grouped_bar_chart(df), use_container_width=True)