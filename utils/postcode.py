import re 
import os 
import geopandas as gpd 
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def process_regional_data(region_name, neb_data_path, geo_save_folder='./geo_files', 
                         path_to_pc_shp_folder='/Volumes/T9/2024_Data_downloads/codepoint_polygons_edina/Download_all_postcodes_2378998/codepoint-poly_5267291',
                         mapbox_token=None, show_map=True, save_geo=True, metric_cols=None):
    """
    Process regional data: check for existing geo file, load/create geo data, visualize on mapbox
    
    Args:
        region_name (str): Name of the region (used for file naming)
        neb_data_path (str): Path to the NEB data file
        geo_save_folder (str): Folder to save/load geo files
        path_to_pc_shp_folder (str): Path to postcode shapefiles
        mapbox_token (str): Mapbox access token for visualization
        show_map (bool): Whether to display the map
        save_geo (bool): Whether to save the geo file
        metric_cols (list): List of column names to include in map hover data and color coding
        
    Returns:
        tuple: (combined_df, geo_df, fig) - Combined data, geo data, and plotly figure
    """
    
    # Create geo save folder if it doesn't exist
    os.makedirs(geo_save_folder, exist_ok=True)
    
    # Generate geo file path
    geo_file_path = os.path.join(geo_save_folder, f"{region_name}_postcodes.geojson")
    
    print(f"Processing region: {region_name}")
    print(f"Looking for existing geo file: {geo_file_path}")
    
    # Check if geo file for this region exists
    if os.path.exists(geo_file_path):
        print("✓ Existing geo file found. Loading...")
        try:
            geo_df = gpd.read_file(geo_file_path)
            print(f"Loaded {len(geo_df)} postcode geometries from existing file")
        except Exception as e:
            print(f"Error loading existing geo file: {e}")
            print("Proceeding to create new geo file...")
            geo_df = None
    else:
        print("✗ No existing geo file found")
        geo_df = None
    
    # Load NEB data
    print(f"Loading NEB data from: {neb_data_path}")
    try:
        if neb_data_path.endswith('.csv'):
            neb_df = pd.read_csv(neb_data_path)
        elif neb_data_path.endswith(('.xlsx', '.xls')):
            neb_df = pd.read_excel(neb_data_path)
        else:
            # Try to infer format
            neb_df = pd.read_csv(neb_data_path)
        
        print(f"Loaded NEB data: {len(neb_df)} records")
        
        # Check if postcode column exists
        postcode_cols = [col for col in neb_df.columns if 'postcode' in col.lower()]
        if not postcode_cols:
            raise ValueError("No postcode column found in NEB data. Please ensure column contains 'postcode' in the name.")
        
        postcode_col = postcode_cols[0]
        print(f"Using postcode column: {postcode_col}")
        
    except Exception as e:
        print(f"Error loading NEB data: {e}")
        return None, None, None
    
    # If geo file doesn't exist, create it
    if geo_df is None:
        print("Creating geo data from postcodes...")
        
        # Get unique postcodes, removing any NaN values
        unique_postcodes = neb_df[postcode_col].dropna().unique().tolist()
        print(f"Found {len(unique_postcodes)} unique postcodes")
        
        if len(unique_postcodes) == 0:
            print("No valid postcodes found in data")
            return neb_df, None, None
        
        # Get geo data using the postcode shapefile function
        geo_df = get_postcode_shapefile(unique_postcodes, path_to_pc_shp_folder)
        
        if geo_df.empty:
            print("No geometric data found for postcodes")
            return neb_df, None, None
        
        print(f"Retrieved geometric data for {len(geo_df)} postcodes")
        
        # Save geo file if requested
        if save_geo:
            try:
                geo_df.to_file(geo_file_path, driver='GeoJSON')
                print(f"✓ Saved geo data to: {geo_file_path}")
            except Exception as e:
                print(f"Warning: Could not save geo file: {e}")
    
    # Combine NEB data with geo data
    print("Combining NEB data with geographic data...")
    combined_df = neb_df.merge(geo_df, left_on=postcode_col, right_on='POSTCODE', how='left')
    
    # Count how many records have geometry
    geo_matched = combined_df['geometry'].notna().sum()
    print(f"Geographic match rate: {geo_matched}/{len(combined_df)} ({geo_matched/len(combined_df)*100:.1f}%)")
    
    # Create mapbox visualization
    fig = None
    if show_map and geo_matched > 0:
        print("Creating mapbox visualization...")
        
        # Convert to GeoDataFrame for easier plotting
        combined_gdf = gpd.GeoDataFrame(combined_df[combined_df['geometry'].notna()])
        
        # Calculate centroids for point plotting
        combined_gdf['centroid'] = combined_gdf.geometry.centroid
        combined_gdf['lat'] = combined_gdf.centroid.y
        combined_gdf['lon'] = combined_gdf.centroid.x
        
        # Prepare hover data and color column
        hover_data = [postcode_col]
        color_col = None
        size_col = None
        
        if metric_cols:
            # Validate metric columns exist in the data
            available_metrics = []
            for col in metric_cols:
                if col in combined_gdf.columns:
                    available_metrics.append(col)
                    hover_data.append(col)
                else:
                    print(f"Warning: Metric column '{col}' not found in data")
            
            if available_metrics:
                print(f"Using metric columns for visualization: {available_metrics}")
                
                # Use first numeric metric for color coding
                for col in available_metrics:
                    if pd.api.types.is_numeric_dtype(combined_gdf[col]):
                        color_col = col
                        print(f"Using '{col}' for color coding")
                        break
                
                # Use second numeric metric for size (if available)
                numeric_metrics = [col for col in available_metrics if pd.api.types.is_numeric_dtype(combined_gdf[col])]
                if len(numeric_metrics) > 1:
                    size_col = numeric_metrics[1]
                    print(f"Using '{size_col}' for point sizing")
        
        # Create the mapbox plot
        if color_col and size_col:
            # Color and size based on metrics
            fig = px.scatter_mapbox(
                combined_gdf,
                lat='lat',
                lon='lon',
                color=color_col,
                size=size_col,
                hover_data=hover_data,
                title=f"{region_name} - {color_col} (Color) & {size_col} (Size)",
                zoom=8,
                height=600,
                mapbox_style="open-street-map",
                color_continuous_scale="viridis"
            )
        elif color_col:
            # Color based on metric
            fig = px.scatter_mapbox(
                combined_gdf,
                lat='lat',
                lon='lon',
                color=color_col,
                hover_data=hover_data,
                title=f"{region_name} - {color_col} Distribution",
                zoom=8,
                height=600,
                mapbox_style="open-street-map",
                color_continuous_scale="viridis"
            )
        else:
            # Basic scatter plot
            fig = px.scatter_mapbox(
                combined_gdf,
                lat='lat',
                lon='lon',
                hover_data=hover_data,
                title=f"{region_name} - Postcode Distribution",
                zoom=8,
                height=600,
                mapbox_style="open-street-map"
            )
        
        # Set mapbox token if provided
        if mapbox_token:
            fig.update_layout(mapbox_accesstoken=mapbox_token)
            fig.update_layout(mapbox_style="satellite-streets")
        
        # Update layout
        fig.update_layout(
            title_x=0.5,
            showlegend=True if color_col else False
        )
        
        # Add custom hover template if metrics are present
        if metric_cols and available_metrics:
            hover_template = f"<b>{postcode_col}</b>: %{{customdata[0]}}<br>"
            for i, col in enumerate(available_metrics):
                hover_template += f"<b>{col}</b>: %{{customdata[{i+1}]}}<br>"
            hover_template += "<extra></extra>"
            
            fig.update_traces(
                customdata=combined_gdf[hover_data].values,
                hovertemplate=hover_template
            )
        
        if show_map:
            fig.show()
    
    return combined_df, geo_df, fig


def get_postcode_shapefile(postcodes, path_to_pc_shp_folder='/Volumes/T9/2024_Data_downloads/codepoint_polygons_edina/Download_all_postcodes_2378998/codepoint-poly_5267291'):
    """
    Find postcode shapefiles based on a list of postcodes and return combined GeoDataFrame
    
    Args:
        postcodes (list): List of postcode strings
        path_to_pc_shp_folder (str): Path to the postcode shapefile folder
        
    Returns:
        gpd.GeoDataFrame: Combined GeoDataFrame containing all matching postcodes
    """
    if isinstance(postcodes, str):
        postcodes = [postcodes]  # Convert single postcode to list
    
    all_postcode_data = []
    loaded_shapefiles = {}  # Cache to avoid loading same shapefile multiple times
    
    for pc in postcodes:
        # Regex pattern to extract 1 or 2 letters at the beginning of the string followed by a digit
        pattern = r'^([A-Za-z]{1,2})\d'
        
        # Using re.match() to find the pattern
        match = re.match(pattern, pc)

        # Checking if a match was found and extracting the group
        if match:
            pc_prefix = match.group(1).lower()
            
            # Determine shapefile path based on prefix length
            if len(pc_prefix) == 1:
                pc_path = os.path.join(path_to_pc_shp_folder, f'one_letter_pc_code/{pc_prefix}/{pc_prefix}.shp')
            else:
                pc_path = os.path.join(path_to_pc_shp_folder, f'two_letter_pc_code/{pc_prefix}.shp')
            
            # Load shapefile (use cache if already loaded)
            if pc_path not in loaded_shapefiles:
                try:
                    loaded_shapefiles[pc_path] = gpd.read_file(pc_path)
                except Exception as e:
                    print(f"Warning: Could not load shapefile for postcode {pc}: {e}")
                    continue
            
            pc_shp = loaded_shapefiles[pc_path]
            
            # Filter for the specific postcode
            matching_rows = pc_shp[pc_shp['POSTCODE'] == pc]
            
            if not matching_rows.empty:
                all_postcode_data.append(matching_rows)
            else:
                print(f"Warning: Postcode {pc} not found in shapefile")
        else:
            print(f"Warning: Invalid postcode format: {pc}")
    
    # Combine all results
    if all_postcode_data:
        combined_gdf = gpd.GeoDataFrame(pd.concat(all_postcode_data, ignore_index=True))
        return combined_gdf
    else:
        # Return empty GeoDataFrame with same structure if no data found
        return gpd.GeoDataFrame(columns=['POSTCODE', 'geometry'])

