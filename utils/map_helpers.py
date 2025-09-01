import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from config import MAPBOX_STYLES, COLOR_SCHEMES

def create_mapbox_fig(df, map_style="Streets", layer_type="scatter"):
    """
    Create a Mapbox figure with specified layer type
    
    Args:
        df: DataFrame with latitude, longitude columns
        map_style: Style name from MAPBOX_STYLES
        layer_type: 'scatter', 'heatmap', or 'choropleth'
    """
    if layer_type == "scatter":
        return create_scatter_map(df, map_style)
    elif layer_type == "heatmap": 
        return create_heatmap(df, map_style)
    else:
        raise ValueError("Unsupported layer type")

def create_scatter_map(df, map_style="Streets"):
    """Create scatter plot on map"""
    fig = px.scatter_mapbox(
        df,
        lat="latitude",
        lon="longitude", 
        hover_name="name" if "name" in df.columns else None,
        hover_data={col: True for col in df.columns if col not in ['latitude', 'longitude']},
        color="category" if "category" in df.columns else None,
        size="value" if "value" in df.columns else None,
        size_max=20,
        zoom=10,
        height=600
    )
    
    fig.update_layout(
        mapbox_style=MAPBOX_STYLES.get(map_style, MAPBOX_STYLES["Streets"]),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    
    return fig

def create_heatmap(df, map_style="Streets"):
    """Create density heatmap"""
    if "value" not in df.columns:
        # If no value column, create one based on point density
        df = df.copy()
        df['value'] = 1
    
    fig = px.density_mapbox(
        df,
        lat="latitude",
        lon="longitude",
        z="value",
        radius=15,
        zoom=10,
        height=600
    )
    
    fig.update_layout(
        mapbox_style=MAPBOX_STYLES.get(map_style, MAPBOX_STYLES["Streets"]),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    
    return fig

def create_choropleth_map(geojson, data_df, map_style="Streets"):
    """Create choropleth map with GeoJSON boundaries"""
    fig = px.choropleth_mapbox(
        data_df,
        geojson=geojson,
        locations='region_id',
        color='value',
        hover_name='name' if 'name' in data_df.columns else None,
        color_continuous_scale="Viridis",
        zoom=10,
        height=600
    )
    
    fig.update_layout(
        mapbox_style=MAPBOX_STYLES.get(map_style, MAPBOX_STYLES["Streets"]),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    
    return fig

def create_multi_layer_map(layers_data, map_style="Streets"):
    """
    Create map with multiple layers
    
    Args:
        layers_data: dict with layer names as keys and data as values
        map_style: Map style to use
    """
    fig = go.Figure()
    
    for layer_name, layer_config in layers_data.items():
        if layer_config['type'] == 'scatter':
            scatter_trace = create_scatter_trace(
                layer_config['data'], 
                layer_name
            )
            fig.add_trace(scatter_trace)
        elif layer_config['type'] == 'heatmap':
            # Note: Plotly doesn't support adding heatmap as trace easily
            # This would need custom implementation
            pass
    
    fig.update_layout(
        mapbox=dict(
            style=MAPBOX_STYLES.get(map_style, MAPBOX_STYLES["Streets"]),
            center=dict(
                lat=layers_data[list(layers_data.keys())[0]]['data']['latitude'].mean(),
                lon=layers_data[list(layers_data.keys())[0]]['data']['longitude'].mean()
            ),
            zoom=10
        ),
        height=600,
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    
    return fig

def create_scatter_trace(df, name):
    """Create scatter trace for multi-layer maps"""
    return go.Scattermapbox(
        lat=df['latitude'],
        lon=df['longitude'],
        mode='markers',
        marker=dict(
            size=df.get('value', [10] * len(df)) if 'value' in df.columns else 10,
            color=df.get('category', 'blue'),
            sizemode='diameter',
            sizemin=4,
            sizemax=20
        ),
        text=df.get('name', ''),
        hovertemplate='<b>%{text}</b><br>Lat: %{lat}<br>Lon: %{lon}<extra></extra>',
        name=name
    )

def get_mapbox_styles():
    """Return available Mapbox styles"""
    return list(MAPBOX_STYLES.keys())

def calculate_map_bounds(df):
    """Calculate appropriate map bounds for data"""
    if df.empty:
        return None
    
    lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
    lon_min, lon_max = df['longitude'].min(), df['longitude'].max()
    
    # Add padding
    lat_padding = (lat_max - lat_min) * 0.1
    lon_padding = (lon_max - lon_min) * 0.1
    
    return {
        'lat_min': lat_min - lat_padding,
        'lat_max': lat_max + lat_padding, 
        'lon_min': lon_min - lon_padding,
        'lon_max': lon_max + lon_padding
    }

def filter_data_by_bounds(df, bounds):
    """Filter dataframe by geographic bounds"""
    return df[
        (df['latitude'] >= bounds['lat_min']) & 
        (df['latitude'] <= bounds['lat_max']) &
        (df['longitude'] >= bounds['lon_min']) & 
        (df['longitude'] <= bounds['lon_max'])
    ]