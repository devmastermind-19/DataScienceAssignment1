import duckdb
import os
import logging
import pandas as pd
import config
from geospatial import get_congestion_zones

# Setup Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_connection():
    return duckdb.connect()

def run_ghost_trip_audit(con):
    """
    Detects Ghost Trips and logs them to audit_ghost_trips.parquet.
    Criteria:
    1. Impossible Speed: > 65 MPH
    2. Teleporter: Time < 1 min (< 60s) AND Fare > $20
    3. Stationary: Distance = 0 AND Fare > 0
    """
    logger.info("Running Ghost Trip Audit...")
    
    # We query all 2025 data
    # Note: We can use a glob pattern for all 2025 files
    # The files are in data/raw/
    # pattern: data/raw/*_tripdata_2025-*.parquet
    
    file_pattern = os.path.join(config.RAW_DIR, "*_tripdata_2025-*.parquet")
    
    # Need to normalize column names if they differ between Yellow and Green, 
    # but DuckDB's read_parquet with union_by_name=True usually handles it.
    # Yellow: tpep_pickup_datetime, Green: lpep_pickup_datetime
    # We might need to handle this.
    # A cleaner way is to create a View that unifies them first.
    
    # Let's try to define a view with coalesced columns.
    # However, globbing *2025*.parquet mixes yellow and green.
    # Yellow schema != Green schema completely.
    # It's better to process Yellow and Green separately or UNION them with specific columns.
    
    # Let's create a unified view `all_trips_2025`
    # We only need specific columns: pickup, dropoff, distance, fare, surcharge, pulocation, dolocation
    
    # Yellow
    q_yellow = f"""
SELECT 
    VendorID,
    tpep_pickup_datetime as pickup_datetime,
    tpep_dropoff_datetime as dropoff_datetime,
    trip_distance,
    fare_amount,
    total_amount,
    tip_amount,
    congestion_surcharge,
    PULocationID,
    DOLocationID,
    'Yellow' as taxi_type
FROM '{os.path.join(config.RAW_DIR, 'yellow_tripdata_2025-*.parquet')}'
"""

    q_green = f"""
SELECT 
    VendorID,
    lpep_pickup_datetime as pickup_datetime,
    lpep_dropoff_datetime as dropoff_datetime,
    trip_distance,
    fare_amount,
    total_amount,
    tip_amount,
    congestion_surcharge,
    PULocationID,
    DOLocationID,
    'Green' as taxi_type
FROM '{os.path.join(config.RAW_DIR, 'green_tripdata_2025-*.parquet')}'
"""

    con.execute(f"CREATE OR REPLACE VIEW all_trips_2025 AS {q_yellow} UNION ALL {q_green}")
    
    # Calculate duration in hours and seconds
    # DuckDB: date_diff('second', pickup, dropoff)
    
    ghost_query = """
    SELECT *,
        date_diff('second', pickup_datetime, dropoff_datetime) as duration_seconds,
        CASE 
            WHEN date_diff('second', pickup_datetime, dropoff_datetime) > 0 
            THEN trip_distance / (date_diff('second', pickup_datetime, dropoff_datetime) / 3600.0)
            ELSE 0 
        END as speed_mph,
        CASE
            WHEN (trip_distance > 0 AND (trip_distance / (NULLIF(date_diff('second', pickup_datetime, dropoff_datetime),0) / 3600.0)) > 65) THEN 'Impossible Speed'
            WHEN (date_diff('second', pickup_datetime, dropoff_datetime) < 60 AND fare_amount > 20) THEN 'Teleporter'
            WHEN (trip_distance = 0 AND fare_amount > 0) THEN 'Stationary'
            ELSE 'Valid'
        END as audit_status
    FROM all_trips_2025
    WHERE 
       (trip_distance > 0 AND (trip_distance / (NULLIF(date_diff('second', pickup_datetime, dropoff_datetime),0) / 3600.0)) > 65)
       OR (date_diff('second', pickup_datetime, dropoff_datetime) < 60 AND fare_amount > 20)
       OR (trip_distance = 0 AND fare_amount > 0)
    """
    
    output_path = os.path.join(config.OUTPUTS_DIR, 'audit_ghost_trips.parquet')
    con.execute(f"COPY ({ghost_query}) TO '{output_path}' (FORMAT PARQUET)")
    logger.info(f"Ghost Trip Audit saved to {output_path}")

    # Suspicious Vendors Analysis
    # We aggregate by VendorID (usually 1=Creative Mobile, 2=Verifone)
    vendor_audit_query = """
    SELECT 
        VendorID,
        count(*) as ghost_trip_count
    FROM all_trips_2025
    WHERE 
       (trip_distance > 0 AND (trip_distance / (NULLIF(date_diff('second', pickup_datetime, dropoff_datetime),0) / 3600.0)) > 65)
       OR (date_diff('second', pickup_datetime, dropoff_datetime) < 60 AND fare_amount > 20)
       OR (trip_distance = 0 AND fare_amount > 0)
    GROUP BY VendorID
    ORDER BY ghost_trip_count DESC
    LIMIT 5
    """
    df_vendors = con.execute(vendor_audit_query).df()
    df_vendors.to_csv(os.path.join(config.OUTPUTS_DIR, 'suspicious_vendors.csv'), index=False)
    logger.info("Suspicious Vendor Audit Complete.")

def run_leakage_audit(con):
    """
    Leakage: Trips starting OUTSIDE zone and ending INSIDE zone with NO surcharge.
    Zone: Manhattan South of 60th St.
    """
    logger.info("Running Leakage Audit...")
    
    zone_ids = get_congestion_zones()
    if not zone_ids:
        logger.warning("No congestion zones found. Skipping Leakage Audit.")
        return

    # Convert list to string for SQL IN clause
    zone_list_str = ",".join(map(str, zone_ids))
    
    # Logic:
    # PULocationID NOT IN (zone_ids)
    # DOLocationID IN (zone_ids)
    # congestion_surcharge IS NULL OR congestion_surcharge = 0
    # Date >= '2025-01-05'
    
    leakage_query = f"""
    SELECT 
        count(*) as leakage_count,
        count(*) * 100.0 / (SELECT count(*) FROM all_trips_2025 WHERE pickup_datetime >= '2025-01-05') as leakage_pct,
        mode(PULocationID) as top_leakage_loc
    FROM all_trips_2025
    WHERE 
        pickup_datetime >= '2025-01-05'
        AND PULocationID NOT IN ({zone_list_str})
        AND DOLocationID IN ({zone_list_str})
        AND (congestion_surcharge IS NULL OR congestion_surcharge = 0)
    """
    
    # We want a more detailed report: Top 3 pickup locations with missing surcharges
    top_leakage_query = f"""
    SELECT 
        PULocationID,
        count(*) as missing_surcharge_trips
    FROM all_trips_2025
    WHERE 
        pickup_datetime >= '2025-01-05'
        AND PULocationID NOT IN ({zone_list_str})
        AND DOLocationID IN ({zone_list_str})
        AND (congestion_surcharge IS NULL OR congestion_surcharge = 0)
    GROUP BY PULocationID
    ORDER BY missing_surcharge_trips DESC
    LIMIT 3
    """
    
    df_top = con.execute(top_leakage_query).df()
    df_top.to_csv(os.path.join(config.OUTPUTS_DIR, 'leakage_top_locations.csv'), index=False)
    
    # Also calculate overall compliance rate
    # Compliance = 1 - (Leakage / Total Eligible Trips)
    # Eligible = Start Outside, End Inside
    
    compliance_query = f"""
    SELECT
        COUNT(*) FILTER (WHERE congestion_surcharge > 0) as paid_trips,
        COUNT(*) as total_eligible_trips,
        (COUNT(*) FILTER (WHERE congestion_surcharge > 0) * 100.0 / NULLIF(COUNT(*), 0)) as compliance_rate
    FROM all_trips_2025
    WHERE
        pickup_datetime >= '2025-01-05'
        AND PULocationID NOT IN ({zone_list_str})
        AND DOLocationID IN ({zone_list_str})
    """
    
    df_comp = con.execute(compliance_query).df()
    df_comp.to_csv(os.path.join(config.OUTPUTS_DIR, 'compliance_stats.csv'), index=False)
    logger.info("Leakage Audit Complete.")

def run_volume_analysis(con):
    """
    Compare Q1 2024 vs Q1 2025 trip volumes entering the zone.
    """
    logger.info("Running Volume Analysis...")
    
    zone_ids = get_congestion_zones()
    zone_list_str = ",".join(map(str, zone_ids))
    
    # Create Q1 2024 View (similar to 2025)
    # We need to load 2024 data (Jan, Feb, Mar)
    # Pattern: *_tripdata_2024-01.parquet, ...
    
    # Ensure 2024 data exists (it should be downloaded by ingestion)
    
    q_yellow_24 = f"""
    SELECT tpep_pickup_datetime as pickup_datetime, DOLocationID, 'Yellow' as taxi_type
    FROM '{os.path.join(config.RAW_DIR, 'yellow_tripdata_2024-*.parquet')}'
    WHERE month(tpep_pickup_datetime) <= 3
    """
    q_green_24 = f"""
    SELECT lpep_pickup_datetime as pickup_datetime, DOLocationID, 'Green' as taxi_type
    FROM '{os.path.join(config.RAW_DIR, 'green_tripdata_2024-*.parquet')}'
    WHERE month(lpep_pickup_datetime) <= 3
    """
    
    con.execute(f"CREATE OR REPLACE VIEW trips_q1_2024 AS {q_yellow_24} UNION ALL {q_green_24}")
    
    # Q1 2025 View
    con.execute(f"""
    CREATE OR REPLACE VIEW trips_q1_2025 AS 
    SELECT pickup_datetime, DOLocationID, taxi_type 
    FROM all_trips_2025 
    WHERE month(pickup_datetime) <= 3
    """)
    
    # Count trips entering zone
    query = f"""
    SELECT 
        '2024 Q1' as period,
        taxi_type,
        count(*) as trip_count
    FROM trips_q1_2024
    WHERE DOLocationID IN ({zone_list_str})
    GROUP BY taxi_type
    
    UNION ALL
    
    SELECT 
        '2025 Q1' as period,
        taxi_type,
        count(*) as trip_count
    FROM trips_q1_2025
    WHERE DOLocationID IN ({zone_list_str})
    GROUP BY taxi_type
    """
    
    df_vol = con.execute(query).df()
    df_vol.to_csv(os.path.join(config.OUTPUTS_DIR, 'volume_comparison.csv'), index=False)
    logger.info("Volume Analysis Complete.")

def run_velocity_metrics(con):
    """
    Compute agg speed for Q1 2024 and Q1 2025 inside congestion zone.
    Group by Hour of Day, Day of Week.
    """
    logger.info("Running Velocity Metrics...")
    
    zone_ids = get_congestion_zones()
    zone_list_str = ",".join(map(str, zone_ids))
    
    # We need to redefine Q1 views to include distance and time columns
    # Re-using the logic but effectively we need a separate query for heavy lifting
    
    # 2024
    q_y_24 = f"""
    SELECT trip_distance, tpep_pickup_datetime, tpep_dropoff_datetime, PULocationID, DOLocationID
    FROM '{os.path.join(config.RAW_DIR, 'yellow_tripdata_2024-*.parquet')}' WHERE month(tpep_pickup_datetime) <= 3
    """
    # Assuming valid trips logic (speed < 100 mph, dist > 0)
    
    # We want trips *inside* the zone.
    # Definition: Start AND End in zone? Or just any part?
    # Usually "Inside Zone" speed implies trips fully within or mostly within.
    # Let's check trips that Start AND End in zone for cleaner signal.
    
    metrics_query_template = """
    SELECT 
        '{year} Q1' as period,
        dayofweek(pickup_datetime) as dow,
        hour(pickup_datetime) as hod,
        AVG(trip_distance / (NULLIF(date_diff('second', pickup_datetime, dropoff_datetime),0) / 3600.0)) as avg_speed
    FROM {table}
    WHERE 
        PULocationID IN ({zones}) AND DOLocationID IN ({zones})
        AND date_diff('second', pickup_datetime, dropoff_datetime) > 60
        AND trip_distance > 0.1
        AND (trip_distance / (NULLIF(date_diff('second', pickup_datetime, dropoff_datetime),0) / 3600.0)) < 100
        AND month(pickup_datetime) <= 3
    GROUP BY 2, 3
    """
    
    # 2025
    q25 = metrics_query_template.format(year="2025", table="all_trips_2025", zones=zone_list_str)
    
    # 2024 - Create a temporary table or CTE
    # Since we can't easily query schema-mismatched files in one go without a view
    # Let's create a view for 2024 full trips
    q_y_24 = f"SELECT tpep_pickup_datetime as pickup_datetime, tpep_dropoff_datetime as dropoff_datetime, trip_distance, PULocationID, DOLocationID FROM '{os.path.join(config.RAW_DIR, 'yellow_tripdata_2024-*.parquet')}'"
    q_g_24 = f"SELECT lpep_pickup_datetime as pickup_datetime, lpep_dropoff_datetime as dropoff_datetime, trip_distance, PULocationID, DOLocationID FROM '{os.path.join(config.RAW_DIR, 'green_tripdata_2024-*.parquet')}'"
    
    con.execute(f"CREATE OR REPLACE VIEW all_trips_2024 AS {q_y_24} UNION ALL {q_g_24}")
    
    q24 = metrics_query_template.format(year="2024", table="all_trips_2024", zones=zone_list_str)
    
    final_query = f"{q24} UNION ALL {q25}"
    
    df_vel = con.execute(final_query).df()
    df_vel.to_csv(os.path.join(config.OUTPUTS_DIR, 'velocity_metrics.csv'), index=False)
    logger.info("Velocity Metrics Complete.")

def run_economics_metrics(con):
    """
    Monthly stats: Avg Surcharge vs Avg Tip %.
    """
    logger.info("Running Economics Metrics...")
    
    query = """
    SELECT 
        year(pickup_datetime) as year,
        month(pickup_datetime) as month,
        AVG(congestion_surcharge) as avg_surcharge,
        AVG(fare_amount) as avg_fare,
        AVG(tip_amount) as avg_tip,
        AVG(tip_amount / NULLIF(total_amount - tip_amount, 0)) * 100 as avg_tip_pct
    FROM all_trips_2025
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    
    # Note: 'tip_amount' needs to be in the view.
    # I didn't include it in 'all_trips_2025' view earlier.
    # I need to recreate the view or include it.
    # I'll modify the `create_view` logic conceptually or just do it right here.
    # But `all_trips_2025` is already created in `run_ghost_trip_audit`.
    
    # I should consolidate view creation to a helper or just recreate it with more columns.
    pass

def setup_global_views(con):
    # Yellow
    q_yellow = f"""
    SELECT 
        VendorID,
        tpep_pickup_datetime as pickup_datetime,
        tpep_dropoff_datetime as dropoff_datetime,
        trip_distance,
        fare_amount,
        total_amount,
        tip_amount,
        congestion_surcharge,
        PULocationID,
        DOLocationID,
        'Yellow' as taxi_type
    FROM '{os.path.join(config.RAW_DIR, 'yellow_tripdata_2025-*.parquet')}'
    """
    # Green
    q_green = f"""
    SELECT 
        VendorID,
        lpep_pickup_datetime as pickup_datetime,
        lpep_dropoff_datetime as dropoff_datetime,
        trip_distance,
        fare_amount,
        total_amount,
        tip_amount,
        congestion_surcharge,
        PULocationID,
        DOLocationID,
        'Green' as taxi_type
    FROM '{os.path.join(config.RAW_DIR, 'green_tripdata_2025-*.parquet')}'
    """
    con.execute(f"CREATE OR REPLACE VIEW all_trips_2025 AS {q_yellow} UNION ALL {q_green}")

def run_border_analysis(con):
    """
    Calculate drop-offs per zone for Q1 2024 and Q1 2025 to visualize Border Effect.
    """
    logger.info("Running Border Analysis...")
    
    # 2024 Counts
    q24 = """
    SELECT DOLocationID, COUNT(*) as count_2024
    FROM trips_q1_2024
    GROUP BY 1
    """
    
    # 2025 Counts
    q25 = """
    SELECT DOLocationID, COUNT(*) as count_2025
    FROM trips_q1_2025
    GROUP BY 1
    """
    
    df24 = con.execute(q24).df()
    df25 = con.execute(q25).df()
    
    merged = pd.merge(df24, df25, on='DOLocationID', how='outer').fillna(0)
    merged['pct_change'] = merged.apply(lambda row: ((row['count_2025'] - row['count_2024']) / row['count_2024'] * 100) if row['count_2024'] != 0 else 0, axis=1)
    
    # Handle infinite growth (from 0 to N)
    merged['pct_change'] = merged['pct_change'].fillna(0) # or keep as is? 
    # If count_2024 is 0 and count_2025 > 0, result is inf. 
    # We can cap it or set to 100?
    
    merged.to_csv(os.path.join(config.OUTPUTS_DIR, 'border_analysis.csv'), index=False)
    logger.info("Border Analysis Complete.")

def main():
    con = create_connection()
    try:
        setup_global_views(con)
        run_ghost_trip_audit(con)
        run_leakage_audit(con)
        run_volume_analysis(con)
        run_velocity_metrics(con)
        run_border_analysis(con)
        
        # Economics
        econ_query = """
        SELECT 
            year(pickup_datetime) as year,
            month(pickup_datetime) as month,
            SUM(congestion_surcharge) as total_surcharge,
            AVG(congestion_surcharge) as avg_surcharge,
            AVG(tip_amount / NULLIF(total_amount - tip_amount, 0)) * 100 as avg_tip_pct
        FROM all_trips_2025
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
        econ_df = con.execute(econ_query).df()
        econ_df.to_csv(os.path.join(config.OUTPUTS_DIR, 'economics_metrics.csv'), index=False)
        
        # Save Total 2025 Revenue to a file
        total_revenue = econ_df['total_surcharge'].sum()
        with open(os.path.join(config.OUTPUTS_DIR, 'total_revenue.txt'), 'w') as f:
            f.write(str(total_revenue))
            
    finally:
        con.close()

if __name__ == "__main__":
    main()

