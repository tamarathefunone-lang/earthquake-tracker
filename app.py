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
            st.session_state['min_mag'] = 2
        if 'days_back' not in st.session_state:
            st.session_state['days_back'] = 7
        if 'keyword' not in st.session_state:
            st.session_state['keyword'] = "San Ramon"
        if "show_map" not in st.session_state:
            st.session_state["show_map"] = True

        min_mag = st.slider("Minimum magnitude", min_value=0.0, max_value=10.0, step=0.1, key='min_mag')
        days_back = st.radio("Days Prior", options=[1, 7, 30], key='days_back')
        keyword = st.text_input("Location (optional)", key='keyword')
        show_map = st.checkbox("Show map", key="show_map")


    try:
        df = cached_fetch(days_back=days_back)
    except Exception as e:
        st.error(f"Failed to fetch data from USGS: {e}")
        return

    # Display last refresh time
    # ensure there's a stored refresh timestamp
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = time.time()

    last_refresh = time.time()
    st.caption(
        f"Last refresh: {datetime.fromtimestamp(last_refresh).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    filtered = filter_earthquakes(df, min_mag=min_mag, days_back=days_back, keyword=keyword)
    results_message = f"**{len(filtered)}** Earthquakes Shown"
    #st.write(results_message)
    # Show current filters
    kw_display = (keyword or "").strip()
    kw_display = f"'{kw_display}'" if kw_display else "(none)"
    filter_message = f"Filters Applied:   Minimum magnitude ≥ {min_mag},   Days Prior = {days_back},   Main Location = {kw_display}"
    st.write(results_message)
    st.write(filter_message)

    if filtered.empty:
        st.warning("No earthquakes match your filters. Try lowering the magnitude or increasing days back.")
        return

    # Results table
    display_df = filtered[["time", "magnitude", "place"]].copy()
    display_df["time"] = display_df["time"].apply(lambda t: t.strftime("%m/%d/%Y %I:%M %p") if pd.notnull(t) else "")
    display_df["magnitude"] = display_df["magnitude"].apply(lambda m: "" if pd.isna(m) else f"{m:.1f}")
    display_df["place"] = display_df["place"].astype(str).apply(lambda s: s if len(s) <= 120 else s[:117] + "…")
    st.markdown(
        """
        <style>
        .stDataFrame table { table-layout: fixed !important; width: 100% !important; }
        .stDataFrame td, .stTable td { overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; }
        .stDataFrame, .stTable, .stDeckGlJson { overflow-x: hidden !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "time": st.column_config.TextColumn("Time (Local)"),
            "magnitude": st.column_config.TextColumn("Magnitude"),
            "place": st.column_config.TextColumn("Location"),
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
            st.map(map_df, zoom=10)

       
    st.markdown(
    """
    <style>
    html, body, .stApp, .main, .block-container {
        max-width: 100vw !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }
    .stDataFrame, .stTable, .stDeckGlJson {
        width: 100vw !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }
    .stDataFrame td, .stTable td {
        word-break: break-word !important;
        text-overflow: ellipsis !important;
        max-width: 120px !important;
        overflow-x: hidden !important;
    }
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
    </style>
    """,
    unsafe_allow_html=True
)
    

if __name__ == "__main__":
    main()