import os
import requests
import zipfile
import io
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import config
import logging

# Setup Logger
logger = logging.getLogger(__name__)

def download_and_extract_shapefile():
    """Downloads the Taxi Zone Shapefile and extracts it."""
    shape_dir = os.path.join(config.DATA_DIR, 'taxi_zones')
    if not os.path.exists(shape_dir):
        os.makedirs(shape_dir)
    
    shapefile_path = os.path.join(shape_dir, 'taxi_zones.shp')
    if os.path.exists(shapefile_path):
        logger.info("Shapefile already exists.")
        return shapefile_path
    
    logger.info("Downloading Taxi Zone Shapefile...")
    try:
        r = requests.get(config.SHAPEFILE_URL)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(shape_dir)
        logger.info("Shapefile downloaded and extracted.")
    except Exception as e:
        logger.error(f"Failed to download shapefile: {e}")
        raise
        
    return shapefile_path

def get_manhattan_zones():
    """
    Returns a list of LocationIDs that are in Manhattan.
    """
    shape_dir = os.path.join(config.DATA_DIR, 'taxi_zones')
    shapefile_path = os.path.join(shape_dir, 'taxi_zones.shp')
    
    if not os.path.exists(shapefile_path):
        download_and_extract_shapefile()
        
    gdf = gpd.read_file(shapefile_path)
    
    # Filter for Manhattan
    manhattan_zones = gdf[gdf['borough'] == config.MANHATTAN_BOROUGH]
    
    return manhattan_zones

def get_congestion_zones():
    """
    Identifies zones South of 60th St.
    Approximate 60th St Lat is around 40.762? 
    It varies. Better to use a known list or polygon intersection if possible.
    However, for this exercise, we can approximate using centroid latitude or use a static list if known.
    
    Roughly: 60th St crosses Manhattan.
    If we don't have a 60th St line geometry, we can use a hardcoded latitude threshold
    or a list of zone IDs.
    
    Common definition of Congestion Zone (CBD) includes zones south of 60th St.
    
    Let's use a rough latitude cutoff for automation: 40.764 (approx 60th St).
    Zones with centroid.y < 40.764 in Manhattan.
    """
    zones = get_manhattan_zones()
    
    # Calculate centroids
    # The shapefile is usually in EPSG:2263 (NY Long Island) or EPSG:4326.
    # We check crs.
    if zones.crs.to_string() != 'EPSG:4326':
        zones = zones.to_crs('EPSG:4326')
        
    # Latitude Threshold for 60th St (approx)
    # 60th St is roughly 40.764
    LAT_THRESHOLD = 40.764
    
    congestion_zones = zones[zones.geometry.centroid.y < LAT_THRESHOLD]
    
    return congestion_zones['LocationID'].tolist()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ids = get_congestion_zones()
    print(f"Congestion Zone LocationIDs: {ids}")

