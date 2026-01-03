"""Backend logic for the Earthquake Tracker app.

This module contains:
- USGS feed fetching
- parsing GeoJSON into a DataFrame
- filtering utilities

It is intentionally Streamlit-agnostic (no UI code).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

USGS_FEEDS = {
    1: "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    7: "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    30: "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
}


def fetch_earthquakes(days_back: int = 1, timeout_s: int = 20) -> pd.DataFrame:
    """Fetch earthquake data from the appropriate USGS GeoJSON feed based on days_back."""
    url = USGS_FEEDS.get(days_back, USGS_FEEDS[1])
    resp = requests.get(url, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()

    rows: list[dict] = []
    for f in data.get("features", []):
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates", [None, None, None])  # [lon, lat, depth]

        rows.append(
            {
                "time": props.get("time"),
                "place": props.get("place"),
                "magnitude": props.get("mag"),
                "url": props.get("url"),
                "longitude": coords[0],
                "latitude": coords[1],
            }
        )

    df = pd.DataFrame(rows)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True, errors="coerce")

    if "time" in df.columns and pd.api.types.is_datetime64_any_dtype(df["time"]):
        try:
            df["time"] = df["time"].dt.tz_convert("America/Los_Angeles")
        except TypeError:
            # If naive, assume UTC then convert
            df["time"] = df["time"].dt.tz_localize("UTC").dt.tz_convert("America/Los_Angeles")


    # Ensure expected columns exist even if empty
    for col in ["time", "place", "magnitude", "url", "latitude", "longitude"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df


def filter_earthquakes(df: pd.DataFrame, min_mag: float, days_back: int, keyword: str) -> pd.DataFrame:
    """Filter earthquakes by:
    - minimum magnitude (>= min_mag)
    - time window (within the last `days_back` days)
    - optional case-insensitive keyword match against `place`

    Returns a new DataFrame sorted by most recent first.
    """
    out = df.copy()

    # Magnitude filter
    out = out[out["magnitude"].fillna(-999) >= min_mag]

    # Days-back filter
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    out = out[out["time"].notna() & (out["time"] >= cutoff)]

    # Keyword filter (case-insensitive)
    kw = (keyword or "").strip().lower()
    if kw:
        out = out[out["place"].fillna("").str.lower().str.contains(kw)]

    # Sort newest first
    out = out.sort_values("time", ascending=False)

    # Prettier time for display (naive local-ish)
    # Convert UTC times to Pacific Time (PST/PDT)
    if "time" in out.columns and pd.api.types.is_datetime64_any_dtype(out["time"]):
        try:
            out["time"] = out["time"].dt.tz_convert("America/Los_Angeles")
        except TypeError:
            # If naive, assume UTC then convert
            out["time"] = out["time"].dt.tz_localize("UTC").dt.tz_convert("America/Los_Angeles")


    return out
