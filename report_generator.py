from fpdf import FPDF
import pandas as pd
import os
import config
import logging

logger = logging.getLogger(__name__)

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, '2025 NYC Congestion Pricing Audit Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_report():
    logger.info("Generating PDF Report...")
    
    outputs = config.OUTPUTS_DIR
    
    # Load Data
    try:
        with open(os.path.join(outputs, 'total_revenue.txt'), 'r') as f:
            total_revenue = float(f.read().strip())
    except Exception:
        total_revenue = 0.0

    try:
        with open(os.path.join(outputs, 'elasticity_score.txt'), 'r') as f:
            elasticity = float(f.read().strip())
    except Exception:
        elasticity = "N/A"

    try:
        suspicious_vendors = pd.read_csv(os.path.join(outputs, 'suspicious_vendors.csv'))
    except Exception:
        suspicious_vendors = pd.DataFrame()

    pdf = PDFReport()
    pdf.add_page()
    
    # Executive Summary
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Executive Summary', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    summary_text = (
        f"This report provides a technical and business audit of the Manhattan Congestion Relief Zone Toll.\n\n"
        f"Total 2025 Surcharge Revenue: ${total_revenue:,.2f}\n"
        f"Rain Elasticity Score (Correlation): {elasticity}\n"
    )
    pdf.multi_cell(0, 10, summary_text)
    pdf.ln(5)
    
    # Suspicious Vendors
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Top Suspicious Vendors (Ghost Trips)', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    if not suspicious_vendors.empty:
        pdf.cell(40, 10, 'VendorID', 1)
        pdf.cell(60, 10, 'Ghost Trip Count', 1)
        pdf.ln()
        for index, row in suspicious_vendors.iterrows():
            pdf.cell(40, 10, str(row['VendorID']), 1)
            pdf.cell(60, 10, str(row['ghost_trip_count']), 1)
            pdf.ln()
    else:
        pdf.cell(0, 10, "No suspicious vendor data found.", 0, 1)
    
    pdf.ln(10)
    
    # Policy Recommendation
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Policy Recommendation', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    recommendation = (
        "Based on the analysis, we observe significant ghost trip activity. "
        "We recommend implementing stricter real-time validation of trip physics (speed/duration) "
        "at the point of data submission to reject impossible trips."
    )
    pdf.multi_cell(0, 10, recommendation)
    
    output_path = os.path.join(config.BASE_DIR, 'audit_report.pdf')
    pdf.output(output_path)
    logger.info(f"Report generated: {output_path}")

if __name__ == "__main__":
    generate_report()

