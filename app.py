import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_regional_data, load_geojson_data, get_available_regions
from utils.map_helpers import create_mapbox_fig, get_mapbox_styles
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
    default_metrics = ['PPI', 'energy_consumption', 'cost_savings', 'carbon_reduction', 'property_value']
    
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
        available_metrics = [col for col in numeric_cols if col not in ['latitude', 'longitude', 'lat', 'lon']]
        
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
            help="Metric used for color coding points"
        ) if available_metrics else None
        
        size_metric = st.sidebar.selectbox(
            "Size Metric", 
            options=['None'] + available_metrics,
            index=1 if len(available_metrics) > 1 else 0,
            help="Metric used for sizing points"
        ) if available_metrics else None
        
        if size_metric == 'None':
            size_metric = None
        
        # Additional metrics for hover
        hover_metrics = st.sidebar.multiselect(
            "Additional Hover Metrics",
            options=[col for col in combined_df.columns if col not in ['geometry', 'POSTCODE', color_metric, size_metric]],
            default=[col for col in ['PPI', 'energy_consumption', 'property_value'] if col in combined_df.columns and col not in [color_metric, size_metric]][:3],
            help="Additional metrics to show on hover"
        )
        
        # Layer controls
        st.sidebar.subheader("Display Options")
        show_points = st.sidebar.checkbox("Show Data Points", value=True)
        show_choropleth = st.sidebar.checkbox("Show Postcode Boundaries", value=False)
        
        # Filter data to only records with geometry
        plot_df = combined_df[combined_df['geometry'].notna()].copy()
        
        if plot_df.empty:
            st.error("No geographic data available for visualization")
            return
        
        # Extract coordinates from geometry
        if 'lat' not in plot_df.columns:
            # Calculate centroids
            gdf = gpd.GeoDataFrame(plot_df)
            centroids = gdf.geometry.centroid
            plot_df['lat'] = centroids.y
            plot_df['lon'] = centroids.x
        
        # Create the map
        fig = go.Figure()
        
        # Add point layer
        if show_points:
            # Prepare hover data
            hover_data = ['POSTCODE'] if 'POSTCODE' in plot_df.columns else []
            hover_data.extend(hover_metrics)
            
            if color_metric and size_metric:
                point_fig = px.scatter_mapbox(
                    plot_df,
                    lat="lat",
                    lon="lon",
                    color=color_metric,
                    size=size_metric,
                    hover_data=hover_data,
                    color_continuous_scale="viridis",
                    size_max=20,
                    title=f"{region_name} - {color_metric} (Color) & {size_metric} (Size)"
                )
            elif color_metric:
                point_fig = px.scatter_mapbox(
                    plot_df,
                    lat="lat", 
                    lon="lon",
                    color=color_metric,
                    hover_data=hover_data,
                    color_continuous_scale="viridis",
                    title=f"{region_name} - {color_metric} Distribution"
                )
            else:
                point_fig = px.scatter_mapbox(
                    plot_df,
                    lat="lat",
                    lon="lon",
                    hover_data=hover_data,
                    title=f"{region_name} - Postcode Distribution"
                )
            
            for trace in point_fig.data:
                fig.add_trace(trace)
        
        # Add choropleth layer (postcode boundaries)
        if show_choropleth and geo_df is not None:
            # Convert to GeoJSON for choropleth
            geojson_data = json.loads(geo_df.to_json())
            
            if color_metric:
                # Merge color data with geo data
                choropleth_data = geo_df.merge(
                    combined_df[['POSTCODE', color_metric]].dropna(), 
                    on='POSTCODE', 
                    how='left'
                )
                
                choropleth_fig = px.choropleth_mapbox(
                    choropleth_data,
                    geojson=geojson_data,
                    locations='POSTCODE',
                    color=color_metric,
                    hover_name='POSTCODE',
                    color_continuous_scale="viridis",
                    opacity=0.6
                )
                
                for trace in choropleth_fig.data:
                    fig.add_trace(trace)
        
        # Update layout
        center_lat = plot_df['lat'].mean()
        center_lon = plot_df['lon'].mean()
        
        fig.update_layout(
            mapbox=dict(
                style=MAPBOX_STYLES[map_style],
                center=dict(lat=center_lat, lon=center_lon),
                zoom=10,
                accesstoken=st.secrets["mapbox"]["token"] if "mapbox" in st.secrets else None
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
            geo_match_rate = len(plot_df) / len(combined_df) * 100
            st.metric("Geographic Match", f"{geo_match_rate:.1f}%")
        
        with col3:
            if color_metric:
                avg_value = plot_df[color_metric].mean()
                st.metric(f"Avg {color_metric}", f"{avg_value:.2f}")
            else:
                st.metric("Active Layers", sum([show_points, show_choropleth]))
        
        with col4:
            if 'PPI' in plot_df.columns:
                ppi_avg = plot_df['PPI'].mean()
                st.metric("Avg PPI", f"{ppi_avg:.2f}")
            else:
                unique_postcodes = plot_df['POSTCODE'].nunique() if 'POSTCODE' in plot_df.columns else 0
                st.metric("Unique Postcodes", unique_postcodes)
        
        # Metric analysis
        if color_metric and color_metric in plot_df.columns:
            st.subheader(f"{color_metric} Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Distribution histogram
                hist_fig = px.histogram(
                    plot_df, 
                    x=color_metric, 
                    title=f"{color_metric} Distribution",
                    nbins=20
                )
                st.plotly_chart(hist_fig, use_container_width=True)
            
            with col2:
                # Top/bottom performers
                st.write("**Top 10 Postcodes**")
                top_performers = plot_df.nlargest(10, color_metric)[['POSTCODE', color_metric]]
                st.dataframe(top_performers, hide_index=True)
        
        # Data filters
        st.sidebar.subheader("Data Filters")
        
        if color_metric:
            metric_min = float(plot_df[color_metric].min())
            metric_max = float(plot_df[color_metric].max())
            
            filter_range = st.sidebar.slider(
                f"Filter by {color_metric}",
                min_value=metric_min,
                max_value=metric_max,
                value=(metric_min, metric_max),
                help=f"Filter data points by {color_metric} range"
            )
            
            # Apply filter
            filtered_df = plot_df[
                (plot_df[color_metric] >= filter_range[0]) & 
                (plot_df[color_metric] <= filter_range[1])
            ]
            
            if len(filtered_df) != len(plot_df):
                st.info(f"Filter applied: showing {len(filtered_df)} of {len(plot_df)} points")
        
        # Raw data table (expandable)
        with st.expander("View Raw Data"):
            display_columns = ['POSTCODE'] + available_metrics[:5] if available_metrics else list(combined_df.columns)[:10]
            st.dataframe(
                combined_df[display_columns].head(100),
                hide_index=True
            )
            
            if len(combined_df) > 100:
                st.info(f"Showing first 100 of {len(combined_df)} records")
    
    except Exception as e:
        st.error(f"Error loading regional data: {str(e)}")
        st.info("Please check your data paths and Mapbox configuration.")
        
        # Show debug info
        with st.expander("Debug Information"):
            st.write("Available regions:", get_available_regions())
            st.write("Error details:", str(e))

if __name__ == "__main__":
    main()