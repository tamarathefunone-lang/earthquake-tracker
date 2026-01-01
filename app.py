"""Earthquake Tracker (Streamlit)

A simple dashboard that pulls recent earthquake data from the USGS GeoJSON feeds,
lets users filter results, and displays them in a table (and optionally on a map).

Notes on Streamlit state:
- Streamlit reruns the script top-to-bottom whenever a widget value changes.
- Sidebar widgets (slider/selectbox/text_input) keep their values automatically.
- st.cache_data is used to avoid calling the API on every rerun.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from earthquake_backend import filter_earthquakes

import pandas as pd
import requests
import streamlit as st


USGS_ALL_DAY = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


@st.cache_data(ttl=300)
def cached_fetch(days_back: int) -> pd.DataFrame:
    from earthquake_backend import fetch_earthquakes

    return fetch_earthquakes(days_back=days_back)



def main() -> None:
    st.title("Earthquake Tracker")
    st.header("Track recent earthquakes 🌎")

    with st.sidebar:
        st.subheader("Filters")
        min_mag = st.slider("Minimum magnitude", min_value=0.0, max_value=10.0, value=2.5, step=0.1)
        days_back = st.selectbox("Days back", options=[1, 7, 30], index=2)
        keyword = st.text_input("Keyword / location (optional)", value="San Ramon")
        num_results = st.slider("Number of results", min_value=1, max_value=100, value=5, step=1)
        show_map = st.checkbox("Show map", value=True)

    try:
        df = cached_fetch(days_back=days_back)
    except Exception as e:
        st.error(f"Failed to fetch data from USGS: {e}")
        return

    filtered = filter_earthquakes(df, min_mag=min_mag, days_back=days_back, keyword=keyword)

    st.write(f"Showing **{len(filtered)}** earthquakes")

    if filtered.empty:
        st.warning("No earthquakes match your filters. Try lowering the magnitude or increasing days back.")
        return


    
    # Build masks for magnitude and recency
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=days_back)

    mag_mask = df["magnitude"].fillna(-999) >= min_mag
    time_mask = df["time"].notna() & (df["time"] >= cutoff)

    mask = mag_mask & time_mask

    # Optional keyword (case-insensitive) on the place column
    kw = (keyword or "").strip().lower()
    if kw:
        place_series = df["place"].fillna("").str.lower()
        mask &= place_series.str.contains(kw)

    # Apply filters and sort newest first
    filtered = df.loc[mask].sort_values(by="time", ascending=False).copy()

    # Make times nicer for display (drop tz info)
    if "time" in filtered.columns:
        filtered["time"] = filtered["time"].dt.tz_convert(None)

    # Limit number of results
    filtered = filtered.head(num_results)

    # Results table
    display_df = filtered[["time", "place", "magnitude"]].copy()
    # Show magnitude as text so it's left-aligned
    display_df["magnitude"] = display_df["magnitude"].apply(lambda m: "" if pd.isna(m) else f"{m:.1f}")
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "magnitude": st.column_config.TextColumn("Magnitude")
        }
    )

    # Optional map
    if show_map:
        # Prepare a DataFrame with valid latitude/longitude for st.map
        if {"latitude", "longitude"}.issubset(filtered.columns):
            coords = filtered[["latitude", "longitude"]].copy()
            coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
            coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
            map_df = coords.dropna(subset=["latitude", "longitude"])
        else:
            map_df = pd.DataFrame(columns=["latitude", "longitude"])

        if map_df.empty:
            st.info("No latitude/longitude available to show on the map.")
        else:
            st.map(map_df)


    st.markdown(
    """
    <style>
    /* Responsive font sizes and layout for mobile */
    @media (max-width: 600px) {
        .stApp, .main, .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }
        .stSidebar {
            width: 80vw !important;
            min-width: 120px !important;
        }
        h1, .stTitle { font-size: 1.5em !important; }
        h2, .stHeader { font-size: 1.1em !important; }
        .stDataFrame, .stTable { font-size: 0.9em !important; }
        .stButton>button { font-size: 1.1em !important; }
    }
    /* Always use full width for tables and maps */
    .stDataFrame, .stTable, .stDeckGlJson { width: 100vw !important; max-width: 100vw !important; }
    </style>
    """,
    unsafe_allow_html=True
)
    

if __name__ == "__main__":
    main()
