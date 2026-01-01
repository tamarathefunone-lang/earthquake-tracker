# Earthquake Tracker

A simple Streamlit web app to track recent earthquakes using the USGS public API. Filter by magnitude, time window, location keyword, and number of results. View results in a table and on an interactive map.

## Features
- Filter earthquakes by minimum magnitude, days back (1, 7, 30), and location keyword
- Limit the number of results shown (default: 5)
- View results in a sortable table
- See earthquake locations on a map, colored by magnitude
- Mobile-friendly responsive UI
- Data is cached for fast performance

## Setup

1. **Clone the repo and navigate to the project folder:**
   ```bash
   cd /Users/tammu162/copilot-projects/earthquake-tracker
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv dev
   source dev/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the app:**
   ```bash
   streamlit run app.py
   ```
2. **Open your browser** (if it doesn't open automatically) and go to the provided local URL.
3. **Adjust filters** in the sidebar to explore recent earthquakes.

## Data Source
- [USGS Earthquake Hazards Program - GeoJSON Feeds](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)

## File Structure
- `app.py` — Streamlit frontend (UI)
- `earthquake_backend.py` — Backend logic for fetching and filtering earthquake data

## License
MIT
