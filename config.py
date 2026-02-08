import os

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
OUTPUTS_DIR = os.path.join(DATA_DIR, 'outputs')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist
for d in [RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# TLC Data URLs
# Base URL pattern: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

# Shapefile URL
SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

# Years to process
YEAR_2025 = 2025
YEAR_2024 = 2024

# Files to download
MONTHS = range(1, 13)
TAXI_TYPES = ['yellow', 'green']

# Schema for Unification
UNIFIED_SCHEMA = [
    'pickup_datetime',
    'dropoff_datetime',
    'PULocationID',
    'DOLocationID',
    'trip_distance',
    'fare_amount',
    'total_amount',
    'congestion_surcharge'
]

# Missing Month Imputation Weights for Dec 2025
IMPUTATION_WEIGHTS = {
    '2023-12': 0.3, # source year-month: weight
    '2024-12': 0.7
}

# Congestion Zone
# Lat/Lon boundary is approx 60th St in Manhattan.
# We will use specific LocationIDs from the shapefile or a lat/lon cutoff.
# For simplicity in Phase 1, we can list known Manhattan zones South of 60th St if needed,
# but we will rely on shapefile intersection in geospatial.py.
MANHATTAN_BOROUGH = "Manhattan"

