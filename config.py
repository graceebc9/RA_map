# Configuration file for the Streamlit Mapbox app

# Mapbox style options
MAPBOX_STYLES = {
    "Streets": "mapbox://styles/mapbox/streets-v11",
    "Outdoors": "mapbox://styles/mapbox/outdoors-v11", 
    "Light": "mapbox://styles/mapbox/light-v10",
    "Dark": "mapbox://styles/mapbox/dark-v10",
    "Satellite": "mapbox://styles/mapbox/satellite-v9",
    "Satellite Streets": "mapbox://styles/mapbox/satellite-streets-v11"
}

# Default map center (San Francisco)
DEFAULT_CENTER = {
    "lat": 37.7749,
    "lon": -122.4194
}

# Color schemes for different data categories
COLOR_SCHEMES = {
    "category_a": "#FF6B6B",
    "category_b": "#4ECDC4", 
    "category_c": "#45B7D1",
    "category_d": "#96CEB4",
    "category_e": "#FFEAA7"
}

# Data file paths
DATA_PATHS = {
    "neb_data": "/Users/gracecolverd/NebulaDataset/final_dataset/NEBULA_englandwales_domestic_filtered.csv",
    "pc_shapefiles": "/Volumes/T9/2024_Data_downloads/codepoint_polygons_edina/Download_all_postcodes_2378998/codepoint-poly_5267291",
    "geojson_data": "data/geojson_data.json"
}