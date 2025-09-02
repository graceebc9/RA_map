import streamlit as st
import numpy as np 
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_regional_data, load_geojson_data, get_available_regions
from utils.map_helpers import create_mapbox_fig, get_mapbox_styles
from utils.checks import check_chloropleth_data 
from config import MAPBOX_STYLES, DEFAULT_CENTER
import json
import geopandas as gpd

# Page configuration
st.set_page_config(
    page_title="Regional PPI Map Dashboard",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🗺️ Regional PPI Map Dashboard")
    st.markdown("### Explore regional data with postcode-level metrics")
    
    # Sidebar controls
    st.sidebar.header("Regional Controls")
    
    # Region selection
    available_regions = get_available_regions()
    if "EE" not in available_regions and available_regions:
        default_region = available_regions[0]
    else:
        default_region = "EE"
    
    region_name = st.sidebar.selectbox(
        "Select Region",
        options=available_regions if available_regions else ["EE"],
        index=available_regions.index(default_region) if default_region in available_regions else 0
    )
    
    # Map style selection
    map_style = st.sidebar.selectbox(
        "Select Map Style",
        options=list(MAPBOX_STYLES.keys()),
        index=0
    )
    
    # Default metrics with PPI focus
    default_metrics = [ 'num_meters_gas',
                    'total_gas',
                    'avg_gas',
                    'median_gas',
                    'num_meters_elec',
                    'total_elec',
                    'avg_elec',
                    'median_elec',
                    'gas_EUI_GIA',
                    'elec_EUI_GIA' ]
    
    # Load data
    try:
        with st.spinner(f"Loading data for region: {region_name}"):
            combined_df, geo_df, success = load_regional_data(
                region_name=region_name,
                metric_cols=default_metrics
            )
            
            if not success or combined_df is None:
                st.warning(f"Could not load data for region {region_name}")
                st.info("Please check if the region exists or contact support")
                return
        
        # Get available metric columns
        numeric_cols = combined_df.select_dtypes(include=['number']).columns.tolist()
        available_metrics = [col for col in numeric_cols if col not in ['latitude', 'longitude', 'lat', 'lon'] and col in  default_metrics]
        
        # Prioritize PPI if available
        if 'PPI' in available_metrics:
            default_color_metric = 'PPI'
        elif available_metrics:
            default_color_metric = available_metrics[0]
        else:
            default_color_metric = None
        
        # Metric selection controls
        st.sidebar.subheader("Metric Controls")
        
        color_metric = st.sidebar.selectbox(
            "Color Metric",
            options=available_metrics,
            index=available_metrics.index(default_color_metric) if default_color_metric in available_metrics else 0,
            help="Metric used for color coding postcode boundaries"
        ) if available_metrics else None
        
        # Additional metrics for hover
        hover_metrics = st.sidebar.multiselect(
            "Additional Hover Metrics",
            options=[col for col in combined_df.columns if col not in ['geometry', 'POSTCODE', color_metric]],
            default=[col for col in ['PPI', 'energy_consumption', 'property_value'] if col in combined_df.columns and col != color_metric][:3],
            help="Additional metrics to show on hover"
        )
        
        # Ensure we have geo_df for choropleth
        if geo_df is None:
            st.error("No geographic data available for visualization. The GeoJSON file for this region could not be loaded.")
            return
        geo_df.to_crs('EPSG:4326', inplace=True)

        # Merge color data with geo data for choropleth
        choropleth_data = geo_df.merge(
            combined_df[['POSTCODE', color_metric] + hover_metrics].dropna(subset=[color_metric]), 
            on='POSTCODE', 
            how='left'
        )
        check_chloropleth_data(combined_df, geo_df , choropleth_data, color_metric)
        
        print('geo_df data')
        print(geo_df.columns.tolist() )
        print(geo_df.crs )


        # First, extract centroids for scatter plot
        choropleth_data_with_coords = choropleth_data.copy()
        centroids = choropleth_data_with_coords.geometry.centroid
        choropleth_data_with_coords['lat'] = centroids.y
        choropleth_data_with_coords['lon'] = centroids.x

        print(f"Coordinate ranges:")
        print(f"Lat range: {choropleth_data_with_coords['lat'].min():.4f} to {choropleth_data_with_coords['lat'].max():.4f}")
        print(f"Lon range: {choropleth_data_with_coords['lon'].min():.4f} to {choropleth_data_with_coords['lon'].max():.4f}")

        # Sample a subset for testing (to avoid overwhelming the map)
        sample_size = min(500, len(choropleth_data_with_coords))
        sample_data = choropleth_data_with_coords.sample(n=sample_size, random_state=42)
        print(f"Using {sample_size} points for scatter test")


        
        # Create the choropleth map
        fig = px.choropleth_mapbox(
            choropleth_data,
            geojson=json.loads(choropleth_data.to_json()),
            locations='POSTCODE',
            color=color_metric,
            hover_name='POSTCODE',
            featureidkey='properties.POSTCODE',
            hover_data={**{m: True for m in hover_metrics}, 'POSTCODE': False}, # Hide POSTCODE from the hover data since it's the hover_name
            color_continuous_scale="viridis",
            opacity=0.9,
            title=f"{region_name} - {color_metric} Distribution by Postcode"
        )

               
        # scatter_trace = px.scatter_mapbox(
        #     sample_data,
        #     lat='lat',
        #     lon='lon',
        #     color=color_metric,
        #     hover_name='POSTCODE',
        #     hover_data=hover_metrics,
        #     color_continuous_scale="plasma",  # Different color scale to distinguish
        #     size_max=8,
        #     opacity=0.8
        # )
        
        # Add the scatter trace to the choropleth figure
        # for trace in scatter_trace.data:
        #     trace.name = "Scatter Points"
        #     trace.showlegend = True
        #     fig.add_trace(trace)

        # # Update layout to center on a default postcode (CB3 0DG)
        # fig.update_layout(
        #     mapbox=dict(
        #         style=MAPBOX_STYLES[map_style],
        #         center=dict(lat=52.2104, lon=0.0934), # Coordinates for CB3 0DG
        #         zoom=13,
        #         accesstoken=st.secrets["mapbox"]["token"] if "mapbox" in st.secrets else None
        #     ),
        #     height=700,
        #     margin={"r": 0, "t": 50, "l": 0, "b": 0},
        #     showlegend=True
        # )
        

                # Update layout
        fig.update_layout(
            mapbox=dict(
                style=MAPBOX_STYLES[map_style],
                center=dict(lat=52.2104, lon=0.0934),
                zoom=13,
                accesstoken=st.secrets["mapbox"]["token"]
            ),
            height=700,
            margin={"r": 0, "t": 50, "l": 0, "b": 0},
            showlegend=True
        )

        # Display map
        st.plotly_chart(fig, use_container_width=True)
        
        # Data summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Records", len(combined_df))
        
        with col2:
            st.metric("Geometries Displayed", len(choropleth_data))
        
        with col3:
            if color_metric:
                avg_value = choropleth_data[color_metric].mean()
                st.metric(f"Avg {color_metric}", f"{avg_value:.2f}")
            else:
                st.metric("Color Metric", "Not Selected")
        
        with col4:
            if 'PPI' in combined_df.columns:
                ppi_avg = combined_df['PPI'].mean()
                st.metric("Avg PPI", f"{ppi_avg:.2f}")
            else:
                st.metric("Unique Postcodes", combined_df['POSTCODE'].nunique() if 'POSTCODE' in combined_df.columns else 0)
        
        # Metric analysis
        if color_metric and color_metric in combined_df.columns:
            st.subheader(f"{color_metric} Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Distribution histogram
                hist_fig = px.histogram(
                    combined_df, 
                    x=color_metric, 
                    title=f"{color_metric} Distribution",
                    nbins=20
                )
                st.plotly_chart(hist_fig, use_container_width=True)
            
            with col2:
                # Top/bottom performers
                st.write("**Top 10 Postcodes**")
                top_performers = combined_df.nlargest(10, color_metric)[['POSTCODE', color_metric]]
                st.dataframe(top_performers, hide_index=True)
        
        # Data filters
        st.sidebar.subheader("Data Filters")
        
        if color_metric:
            metric_min = float(combined_df[color_metric].min())
            metric_max = float(combined_df[color_metric].max())
            
            filter_range = st.sidebar.slider(
                f"Filter by {color_metric}",
                min_value=metric_min,
                max_value=metric_max,
                value=(metric_min, metric_max),
                help=f"Filter data for display by {color_metric} range"
            )
            
            # Note: Filters are applied to the data before visualization for metrics but not on the map display itself in this script.
            
    
    
    except Exception as e:
        st.error(f"Error loading regional data: {str(e)}")
        st.info("Please check your data paths and Mapbox configuration.")
        
        # Show debug info
        with st.expander("Debug Information"):
            st.write("Available regions:", get_available_regions())
            st.write("Error details:", str(e))

if __name__ == "__main__":
    main()