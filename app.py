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
import time

USGS_ALL_DAY = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


@st.cache_data(ttl=300)
def cached_fetch(days_back: int) -> pd.DataFrame:
    from earthquake_backend import fetch_earthquakes

    return fetch_earthquakes(days_back=days_back)



def main() -> None:
    st.title("Track recent earthquakes 🌎")

    #st.markdown(
    #        """
    #        <meta http-equiv="refresh" content="20">
    #        """,
    #        unsafe_allow_html=True
    #    )

    
    with st.sidebar:
        st.subheader("Filters")
        if 'min_mag' not in st.session_state:
            st.session_state['min_mag'] = 1
        if 'days_back' not in st.session_state:
            st.session_state['days_back'] = 7
        if 'keyword' not in st.session_state:
            st.session_state['keyword'] = "California"

        min_mag = st.slider("Minimum magnitude", min_value=0.0, max_value=10.0, step=0.1, key='min_mag')
        days_back = st.selectbox("Days back", options=[1, 7, 30], key='days_back')
        keyword = st.text_input("Keyword / location (optional)", key='keyword')


    try:
        df = cached_fetch(days_back=days_back)
    except Exception as e:
        st.error(f"Failed to fetch data from USGS: {e}")
        return

    # Display last refresh time
    # ensure there's a stored refresh timestamp
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = time.time()

    # show caption and the map toggle side-by-side, giving the caption more width
    col_caption, col_toggle = st.columns([4, 1])
    last_refresh = st.session_state.get("last_refresh", time.time())
    col_caption.caption(
        f"Last refresh: {datetime.fromtimestamp(last_refresh).strftime('%Y-%m-%d %H:%M:%S')}"
    )

    if "show_map" not in st.session_state:
        st.session_state["show_map"] = True
    with col_toggle:
        show_map =st.checkbox("Show map", key="show_map")

    # ensure the row uses the full available width
    st.markdown(
        """
        <style>
        .stColumns, .stColumn {
            max-width: 100vw !important;
            width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    
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
        filtered["time"] = filtered["time"]



    # Results table
    display_df = filtered[["time", "place", "magnitude"]].copy()
    # Format time as human-readable (e.g., 4:30 AM, 5:30 PM)

    # If there are more than 5 rows, constrain the dataframe's height so it becomes scrollable.
    if len(display_df) > 5:
        # approximate row height (px) and cap visible rows to 5
        row_px = 50
        max_rows_visible = 5
        max_height = row_px * max_rows_visible
        st.markdown(
            f"<style>.stDataFrame > div {{ max-height: {max_height}px; overflow-y: auto; }}</style>",
            unsafe_allow_html=True,
        )
    display_df["time"] = display_df["time"].apply(lambda t: t.strftime("%m/%d/%Y %I:%M %p") if pd.notnull(t) else "")
    # Show magnitude as text so it's left-aligned
    display_df["magnitude"] = display_df["magnitude"].apply(lambda m: "" if pd.isna(m) else f"{m:.1f}")
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "time": st.column_config.TextColumn("Time (Local)"),
            "place": st.column_config.TextColumn("Location"),
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
