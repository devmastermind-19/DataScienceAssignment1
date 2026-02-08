import os
import sys
import logging
import argparse
import config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ingestion
import geospatial
import analytics
import weather
import report_generator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOGS_DIR, 'pipeline.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Pipeline")

def main():
    logger.info("Starting NYC Congestion Pricing Audit Pipeline...")
    
    try:
        # Phase 1: Ingestion
        logger.info("=== Phase 1: Data Ingestion ===")
        ingestion.run_ingestion()
        
        # Phase 2: Geospatial & Analytics
        logger.info("=== Phase 2: Analytics & Processing ===")
        analytics.main()
        weather.fetch_weather_data()
        con = analytics.create_connection()
        analytics.setup_global_views(con) # Re-create views
        weather.calculate_elasticity(con)
        con.close()
        
        # Phase 3: Reporting
        logger.info("=== Phase 3: Reporting_Generator ===")
        report_generator.generate_report()
        
        logger.info("Pipeline Execution Complete Successfully.")
        print("\n\nPipeline Complete!")
        print(f"Report available at: {os.path.join(config.BASE_DIR, 'audit_report.pdf')}")
        print("To view the dashboard, run: streamlit run dashboard.py\n")
        
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

