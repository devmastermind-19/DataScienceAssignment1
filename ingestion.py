import os
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import duckdb
import config

# Setup Logging
logging.basicConfig(
    filename=os.path.join(config.LOGS_DIR, 'ingestion.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

def download_file(url, dest_path, retries=3):
    """Downloads a file with retries."""
    if os.path.exists(dest_path):
        logging.info(f"File already exists: {dest_path}")
        return True

    for attempt in range(retries):
        try:
            logging.info(f"Downloading {url} (Attempt {attempt + 1})")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Successfully downloaded {dest_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to download {url}: {e}")
            time.sleep(2 * (attempt + 1))
    
    return False

def generate_urls(year, months, taxi_types):
    """Generates a list of (url, dest_path) tuples."""
    tasks = []
    for taxi in taxi_types:
        for month in months:
            filename = f"{taxi}_tripdata_{year}-{month:02d}.parquet"
            url = f"{config.TLC_BASE_URL}/{filename}"
            dest = os.path.join(config.RAW_DIR, filename)
            tasks.append((url, dest))
    return tasks

def impute_december_2025():
    """Imputes Dec 2025 data if missing, using weighted sampling from Dec 2023 and Dec 2024."""
    # Check if Dec 2025 exists
    target_files = [
        os.path.join(config.RAW_DIR, f"yellow_tripdata_2025-12.parquet"),
        os.path.join(config.RAW_DIR, f"green_tripdata_2025-12.parquet")
    ]
    
    missing = [f for f in target_files if not os.path.exists(f)]
    
    if not missing:
        logging.info("December 2025 data already exists. Skipping imputation.")
        return

    logging.info("Imputing missing December 2025 data...")
    
    con = duckdb.connect()
    
    for taxi in config.TAXI_TYPES:
        target_file = os.path.join(config.RAW_DIR, f"{taxi}_tripdata_2025-12.parquet")
        if os.path.exists(target_file):
            continue
            
        logging.info(f"Generating {target_file}...")
        
        # Download source files if not present (Dec 2023, Dec 2024)
        sources = {
            '2023-12': f"{taxi}_tripdata_2023-12.parquet",
            '2024-12': f"{taxi}_tripdata_2024-12.parquet"
        }
        
        source_paths = {}
        for key, filename in sources.items():
            url = f"{config.TLC_BASE_URL}/{filename}"
            dest = os.path.join(config.RAW_DIR, filename)
            if not os.path.exists(dest):
                download_file(url, dest)
            source_paths[key] = dest
            
        # DuckDB Imputation Logic
        # We want to create a dataset that has volume = Weighted Sum of volumes?
        # Or just sample rows? Use UNION ALL with weights?
        # The requirement says: "Impute December 2025 using: December 2023 weight=30%, December 2024 weight=70%"
        # Implies we mix records. 
        # Strategy: detailed sampling might be complex in SQL.
        # Simpler approach: Take 30% of Dec 2023 and 70% of Dec 2024 (random sample).
        # And shift dates to 2025? The prompt doesn't explicitly say to shift dates, but "Impute Dec 2025" implies dates should be Dec 2025.
        
        try:
            # Create a table from 2023
            con.execute(f"CREATE OR REPLACE VIEW src_2023 AS SELECT * FROM '{source_paths['2023-12']}'")
            # Create a table from 2024
            con.execute(f"CREATE OR REPLACE VIEW src_2024 AS SELECT * FROM '{source_paths['2024-12']}'")
            
            # Sample
            # DuckDB SAMPLE is reasonably fast.
            query = f"""
            COPY (
                SELECT * REPLACE (date_add(pickup_datetime, INTERVAL 2 YEAR) AS pickup_datetime, 
                                  date_add(dropoff_datetime, INTERVAL 2 YEAR) AS dropoff_datetime) 
                FROM src_2023 USING SAMPLE 30%
                UNION ALL
                SELECT * REPLACE (date_add(pickup_datetime, INTERVAL 1 YEAR) AS pickup_datetime, 
                                  date_add(dropoff_datetime, INTERVAL 1 YEAR) AS dropoff_datetime)
                FROM src_2024 USING SAMPLE 70%
            ) TO '{target_file}' (FORMAT PARQUET);
            """
            # Note: date_add might need adjustment if schema column names differ (tpep_pickup_datetime vs lpep_pickup_datetime).
            # Yellow: tpep_pickup_datetime, Green: lpep_pickup_datetime
            
            # Detect column names first
            cols_2024 = con.execute("DESCRIBE src_2024").fetchall()
            col_names = [c[0] for c in cols_2024]
            
            pu_col = 'tpep_pickup_datetime' if 'tpep_pickup_datetime' in col_names else 'lpep_pickup_datetime'
            do_col = 'tpep_dropoff_datetime' if 'tpep_dropoff_datetime' in col_names else 'lpep_dropoff_datetime'
            
            # Revised Query with dynamic column names using standard interval syntax
            query = f"""
            COPY (
                SELECT * REPLACE ({pu_col} + INTERVAL 2 YEAR AS {pu_col}, 
                                  {do_col} + INTERVAL 2 YEAR AS {do_col}) 
                FROM src_2023 USING SAMPLE 30%
                UNION ALL
                SELECT * REPLACE ({pu_col} + INTERVAL 1 YEAR AS {pu_col}, 
                                  {do_col} + INTERVAL 1 YEAR AS {do_col})
                FROM src_2024 USING SAMPLE 70%
            ) TO '{target_file}' (FORMAT PARQUET);
            """
            
            con.execute(query)
            logging.info(f"Created {target_file} via imputation.")
            
        except Exception as e:
            logging.error(f"Imputation failed for {taxi}: {e}")
            
    con.close()

def run_ingestion():
    logging.info("Starting Ingestion Phase...")
    
    # 1. Download 2025 Data (Jan to Nov)
    # The prompt says "download ... for all available months of 2025".
    # Assuming Dec is missing, we download Jan-Nov.
    # Note: If we are in Jan 2026, Dec 2025 might be available or not.
    # We'll try to download all 12 months. Any failure in Dec triggers imputation.
    
    months = config.MONTHS # 1..12
    tasks = generate_urls(config.YEAR_2025, months, config.TAXI_TYPES)
    
    # Also need Q1 2024 for comparison (Jan, Feb, Mar 2024)
    tasks_2024 = generate_urls(config.YEAR_2024, [1, 2, 3], config.TAXI_TYPES)
    tasks.extend(tasks_2024)
    
    # Execute Downloads
    # We can use ThreadPoolExecutor for parallel downloads
    # But be mindful of rate limits or connection issues.
    # Sequential might be safer or small batch.
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_file, url, dest) for url, dest in tasks]
        for f in futures:
            f.result() # Wait for completion
            
    # 2. Impute December if needed
    impute_december_2025()
    
    logging.info("Ingestion Phase Complete.")

if __name__ == "__main__":
    run_ingestion()

