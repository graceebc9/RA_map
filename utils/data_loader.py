import pandas as pd
import numpy as np
import json
import streamlit as st
from config import DATA_PATHS
import os
import geopandas as gpd
import re

# Import the regional processing functions
# from regional_data_processor import process_regional_data, get_postcode_shapefile
from utils.postcode import * 

@st.cache_data
def load_regional_data(region_name="EE", neb_data_path=None, geo_save_folder='./geo_files', 
                      path_to_pc_shp_folder='/Volumes/T9/2024_Data_downloads/codepoint_polygons_edina/Download_all_postcodes_2378998/codepoint-poly_5267291',
                      metric_cols=None):
    """
    Load regional data using the process_regional_data function.
    Defaults to 'EE' region if no region specified.
    
    Args:
        region_name (str): Regional code (default: "EE")
        neb_data_path (str): Path to NEB data file
        geo_save_folder (str): Folder to save/load geo files
        path_to_pc_shp_folder (str): Path to postcode shapefiles
        metric_cols (list): List of metric columns to include
        
    Returns:
        tuple: (combined_df, geo_df, success_flag)
    """
    try:
        if neb_data_path is None:
            if "neb_data" in DATA_PATHS:
                neb_data_path = DATA_PATHS["neb_data"]
            else:
                st.error("No NEB data path provided and no default path configured")
                return None, None, False
        
        # Check if NEB data file exists
        if not os.path.exists(neb_data_path):
            st.error(f"NEB data file not found: {neb_data_path}")
            return None, None, False
        
        # Use the process_regional_data function
        combined_df, geo_df, fig = process_regional_data(
            region_name=region_name,
            neb_data_path=neb_data_path,
            geo_save_folder=geo_save_folder,
            path_to_pc_shp_folder=path_to_pc_shp_folder,
            show_map=False,  # Don't show map in Streamlit context
            save_geo=True,
            metric_cols=metric_cols
        )
        
        if combined_df is not None and not combined_df.empty:
            st.success(f"Successfully loaded regional data for {region_name}")
            st.info(f"Loaded {len(combined_df)} records")
            return combined_df, geo_df, True
        else:
            st.warning(f"No data found for region {region_name}")
            return None, None, False
            
    except Exception as e:
        st.error(f"Error loading regional data: {str(e)}")
        return None, None, False

@st.cache_data
def load_geojson_data(region_name="EE"):
    """
    Load GeoJSON data for choropleth mapping from processed regional data.
    """
    try:
        geo_file_path = os.path.join('./geo_files', f"{region_name}_postcodes.geojson")
        
        if os.path.exists(geo_file_path):
            gdf = gpd.read_file(geo_file_path)
            # Convert to GeoJSON format
            return json.loads(gdf.to_json())
        else:
            st.warning(f"No GeoJSON file found for region {region_name}")
            return None
            
    except Exception as e:
        st.warning(f"Could not load GeoJSON file for {region_name}: {e}")
        return None

def load_user_data(uploaded_file):
    """Load data from user uploaded file"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.json_normalize(data)
        else:
            st.error("Unsupported file format. Please upload CSV, Excel, or JSON.")
            return None
            
        return df
        
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def validate_postcode_data(df):
    """Validate that dataframe contains postcode data"""
    postcode_cols = [col for col in df.columns if 'postcode' in col.lower()]
    
    if not postcode_cols:
        st.error("No postcode column found. Column should contain 'postcode' in the name.")
        return False, None
    
    postcode_col = postcode_cols[0]
    
    # Check for valid UK postcode format
    postcode_pattern = r'^[A-Z]{1,2}[0-9]{1,2}[A-Z]?\s?[0-9][A-Z]{2}$'
    sample_postcodes = df[postcode_col].dropna().head(10)
    
    valid_count = sum(1 for pc in sample_postcodes if re.match(postcode_pattern, str(pc).upper().strip()))
    
    if valid_count < len(sample_postcodes) * 0.5:  # At least 50% should be valid
        st.warning("Postcode format may not be standard UK format")
    
    return True, postcode_col

def get_available_regions(geo_save_folder='./geo_files'):
    """Get list of available regions from saved geo files"""
    try:
        if not os.path.exists(geo_save_folder):
            return []
        
        regions = []
        for filename in os.listdir(geo_save_folder):
            if filename.endswith('_postcodes.geojson'):
                region_name = filename.replace('_postcodes.geojson', '')
                regions.append(region_name)
        
        return sorted(regions)
    except Exception as e:
        st.warning(f"Could not scan for available regions: {e}")
        return []

def create_regional_data_from_upload(uploaded_file, region_name=None):
    """
    Process uploaded data to create regional dataset with postcodes
    
    Args:
        uploaded_file: Streamlit uploaded file object
        region_name (str): Name for the region (auto-generated if None)
        
    Returns:
        tuple: (combined_df, geo_df, region_name)
    """
    try:
        # Load the uploaded data
        df = load_user_data(uploaded_file)
        if df is None:
            return None, None, None
        
        # Validate postcode data
        is_valid, postcode_col = validate_postcode_data(df)
        if not is_valid:
            return None, None, None
        
        # Generate region name if not provided
        if region_name is None:
            region_name = uploaded_file.name.split('.')[0]
        
        # Save temporary file for processing
        temp_path = f"./temp_{region_name}.csv"
        df.to_csv(temp_path, index=False)
        
        try:
            # Process using regional data processor
            combined_df, geo_df, fig = process_regional_data(
                region_name=region_name,
                neb_data_path=temp_path,
                show_map=False,
                save_geo=True
            )
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return combined_df, geo_df, region_name
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        st.error(f"Error processing uploaded regional data: {str(e)}")
        return None, None, None

# Regional data processing functions (copied from previous artifact)
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
    
    return combined_df, geo_df, None

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