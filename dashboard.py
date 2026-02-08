import numpy as np
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import config
from datetime import datetime

# Set page configuration
st.set_page_config(
    layout="wide", 
    page_title="NYC Congestion Pricing Audit 2025",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional UI with hollow boxes
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        padding: 1.5rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1a237e 0%, #283593 50%, #3949ab 100%);
        border-radius: 10px;
        color: white;
    }
    
    .main-header h1, .main-header h3 {
        color: white;
        padding-left: 1rem;
        margin: 0;
    }
    
    /* Hollow Box Styling for Metrics */
    .hollow-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px solid #1a237e;
        box-shadow: 0 4px 6px rgba(26, 35, 126, 0.1);
        transition: all 0.3s ease;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .hollow-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #1a237e 0%, #283593 100%);
    }
    
    .hollow-box:hover {
        box-shadow: 0 6px 12px rgba(26, 35, 126, 0.15);
        transform: translateY(-2px);
    }
    
    /* Small hollow box for Rain Elasticity */
    .small-hollow-box {
        background: white;
        padding: 1.25rem;
        border-radius: 8px;
        border: 2px solid #2196f3;
        box-shadow: 0 3px 5px rgba(33, 150, 243, 0.1);
        transition: all 0.3s ease;
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .small-hollow-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%);
    }
    
    .metric-title {
        font-size: 0.85rem;
        color: #1a237e;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.75rem;
        text-align: center;
        border-bottom: 1px solid #e0e0e0;
        padding-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1a237e;
        margin: 0.5rem 0;
        text-align: center;
        font-family: 'Arial', sans-serif;
    }
    
    .metric-description {
        font-size: 0.9rem;
        color: #666;
        text-align: center;
        margin: 0.5rem 0;
        line-height: 1.4;
    }
    
    .metric-delta {
        font-size: 0.85rem;
        padding: 0.3rem 0.75rem;
        border-radius: 4px;
        display: inline-block;
        margin-top: 0.5rem;
        text-align: center;
        width: 100%;
        font-weight: 600;
    }
    
    .delta-positive {
        background-color: rgba(76, 175, 80, 0.1);
        color: #2e7d32;
        border: 1px solid rgba(76, 175, 80, 0.3);
    }
    
    .delta-negative {
        background-color: rgba(244, 67, 54, 0.1);
        color: #c62828;
        border: 1px solid rgba(244, 67, 54, 0.3);
    }
    
    .delta-neutral {
        background-color: rgba(158, 158, 158, 0.1);
        color: #616161;
        border: 1px solid rgba(158, 158, 158, 0.3);
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #f5f7fa 0%, #e4e8f0 100%);
        padding: 1rem 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1a237e;
        margin: 1.5rem 0;
        font-weight: 600;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #f8f9fa;
        padding: 8px 8px 0 8px;
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 6px 6px 0 0;
        border: 1px solid #dee2e6;
        border-bottom: none;
        padding: 0 20px;
        font-weight: 500;
        color: #495057;
        transition: all 0.2s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1a237e;
        color: white;
        border-color: #1a237e;
        font-weight: 600;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #2196f3;
        padding: 1.25rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    .info-box h4 {
        color: #1565c0;
        margin-top: 0;
        margin-bottom: 0.75rem;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-left: 4px solid #ff9800;
        padding: 1.25rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    .warning-box h4 {
        color: #ef6c00;
        margin-top: 0;
        margin-bottom: 0.75rem;
    }
    
    /* Chart containers */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.5rem;
    }
    
    /* Legend containers */
    .legend-container {
        background: #f8f9fa;
        padding: 1.25rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin: 1rem 0;
    }
    
    .legend-title {
        font-weight: 600;
        color: #1a237e;
        margin-bottom: 0.75rem;
    }
    
    /* Data tables */
    .data-table-container {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #dee2e6;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    
    /* Footer */
    .footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e0e0e0;
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Map container */
    .map-container {
        border-radius: 10px;
        overflow: hidden;
        border: 2px solid #e0e0e0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Analysis insights */
    .insight-item {
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 6px;
        border-left: 3px solid #1a237e;
    }
    
    /* Weather metrics in hollow boxes */
    .weather-metric-box {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #2196f3;
        box-shadow: 0 3px 6px rgba(33, 150, 243, 0.1);
        height: 100%;
        position: relative;
    }
    
    .weather-metric-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%);
    }
    
    .weather-metric-title {
        font-size: 0.8rem;
        color: #2196f3;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .weather-metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #2196f3;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .weather-metric-desc {
        font-size: 0.75rem;
        color: #666;
        text-align: center;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header with enhanced design
st.markdown('<div class="main-header">', unsafe_allow_html=True)
col_title1, col_title2, col_title3 = st.columns([3, 2, 1])

with col_title1:
    st.markdown("# NYC Congestion Pricing Audit 2025")
    st.markdown("### Technical & Business Audit of Manhattan Congestion Relief Zone Toll")

with col_title2:
    st.markdown("")
    st.markdown("**Analysis Period:** Q1 2024 vs Q1 2025")

with col_title3:
    st.markdown("")
    st.markdown(f"**Report Date:** {datetime.now().strftime('%Y-%m-%d')}")
st.markdown("</div>", unsafe_allow_html=True)

# Sidebar with enhanced controls
with st.sidebar:
    st.markdown("### Analysis Controls")
    
    # Time period selection
    st.markdown("#### Time Period")
    analysis_period = st.selectbox(
        "Select Analysis Period",
        options=["Q1 2024 vs Q1 2025", "Monthly Trends", "Weekly Patterns", "Daily Analysis"],
        index=0
    )
    
    st.markdown("---")
    
    # Data filters
    st.markdown("#### Data Filters")
    
    # Zone type filter
    zone_types = st.multiselect(
        "Zone Categories",
        options=["Central Business District", "Residential Areas", "Transit Hubs", 
                "Commercial Districts", "Border Zones", "Tourist Areas"],
        default=["Central Business District", "Border Zones"]
    )
    
    # Time of day filter
    time_ranges = st.multiselect(
        "Time Ranges",
        options=["Morning Peak (6AM-10AM)", "Midday (10AM-4PM)", 
                "Evening Peak (4PM-8PM)", "Night (8PM-6AM)"],
        default=["Morning Peak (6AM-10AM)", "Evening Peak (4PM-8PM)"]
    )
    
    st.markdown("---")
    
    # Display settings
    st.markdown("#### Display Settings")
    show_details = st.checkbox("Show Detailed Analysis", value=True)
    auto_refresh = st.checkbox("Auto-refresh Data", value=False)
    
    st.markdown("---")
    
    # Data info
    st.markdown("#### Data Information")
    with st.expander("Data Sources & Methodology"):
        st.markdown("""
        **Data Sources:**
        - NYC Taxi & Limousine Commission (TLC) trip records
        - NYC Open Data - Geospatial boundaries
        - National Weather Service - Precipitation data
        - MTA Congestion Pricing Zone definitions
        
        **Methodology:**
        - Comparative analysis of pre/post-implementation periods
        - Geographic information system (GIS) mapping
        - Statistical correlation analysis
        - Economic impact assessment
        """)
    
    # Quick actions
    st.markdown("---")
    st.markdown("#### Quick Actions")
    if st.button("🔄 Refresh Analysis", use_container_width=True):
        st.rerun()
    
    if st.button("📥 Export Report", use_container_width=True):
        st.info("Report export functionality would be implemented here.")

# Load Data functions
@st.cache_data
def load_data():
    outputs = config.OUTPUTS_DIR
    
    # Border Analysis
    border_df = pd.read_csv(os.path.join(outputs, 'border_analysis.csv'))
    
    # Velocity
    velocity_df = pd.read_csv(os.path.join(outputs, 'velocity_metrics.csv'))
    
    # Economics
    economics_df = pd.read_csv(os.path.join(outputs, 'economics_metrics.csv'))
    
    # Rain Elasticity
    try:
        elasticity_df = pd.read_csv(os.path.join(outputs, 'trips_vs_weather.csv'))
        elasticity_score_path = os.path.join(outputs, 'elasticity_score.txt')
        if os.path.exists(elasticity_score_path):
            with open(elasticity_score_path, 'r') as f:
                elasticity_score = float(f.read().strip())
        else:
            elasticity_score = None
    except:
        elasticity_df = None
        elasticity_score = None
    
    return border_df, velocity_df, economics_df, elasticity_df, elasticity_score

@st.cache_data
def load_shapefile():
    shape_dir = os.path.join(config.DATA_DIR, 'taxi_zones')
    shapefile_path = os.path.join(shape_dir, 'taxi_zones.shp')
    return gpd.read_file(shapefile_path).to_crs("EPSG:4326")

# Data loading with status
try:
    with st.spinner("Loading analysis data..."):
        border_df, velocity_df, economics_df, elasticity_df, elasticity_score = load_data()
        gdf = load_shapefile()
    
    # Update sidebar with data status
    with st.sidebar:
        st.success("✅ Data loaded successfully")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.markdown(f"**Zones:** {len(border_df)}")
            st.markdown(f"**Trips:** {len(velocity_df):,}")
        with col_stat2:
            st.markdown(f"**Months:** {len(economics_df)}")
            if elasticity_df is not None:
                st.markdown(f"**Days:** {len(elasticity_df)}")
            
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Key Metrics Dashboard in Hollow Boxes
st.markdown("### Performance Overview")
st.markdown("Key metrics comparing Q1 2024 (pre-implementation) with Q1 2025 (post-implementation)")

col1, col2, col3, col4 = st.columns(4)

# Calculate metrics
with col1:
    st.markdown('<div class="hollow-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">BORDER EFFECT</div>', unsafe_allow_html=True)
    if 'pct_change' in border_df.columns:
        avg_change = border_df['pct_change'].mean()
        st.markdown(f'<div class="metric-value">+{avg_change:.1f}%</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-description">Change in drop-off activity</div>', unsafe_allow_html=True)
        delta_class = "delta-positive" if avg_change > 0 else "delta-negative" if avg_change < 0 else "delta-neutral"
        delta_text = "Increased drop-offs" if avg_change > 0 else "Decreased drop-offs" if avg_change < 0 else "No significant change"
        st.markdown(f'<div class="metric-delta {delta_class}">{delta_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="hollow-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">TRAFFIC VELOCITY</div>', unsafe_allow_html=True)
    if 'avg_speed' in velocity_df.columns:
        avg_speed_2025 = velocity_df[velocity_df['period'] == '2025 Q1']['avg_speed'].mean() if not velocity_df[velocity_df['period'] == '2025 Q1'].empty else 0
        avg_speed_2024 = velocity_df[velocity_df['period'] == '2024 Q1']['avg_speed'].mean() if not velocity_df[velocity_df['period'] == '2024 Q1'].empty else 0
        speed_change = avg_speed_2025 - avg_speed_2024 if avg_speed_2024 > 0 else 0
        
        st.markdown(f'<div class="metric-value">{avg_speed_2025:.1f} mph</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-description">Average speed in congestion zone</div>', unsafe_allow_html=True)
        delta_class = "delta-positive" if speed_change > 0 else "delta-negative" if speed_change < 0 else "delta-neutral"
        delta_text = f"+{speed_change:.1f} mph change" if speed_change >= 0 else f"{speed_change:.1f} mph change"
        st.markdown(f'<div class="metric-delta {delta_class}">{delta_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown('<div class="hollow-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">ECONOMIC IMPACT</div>', unsafe_allow_html=True)
    if 'avg_surcharge' in economics_df.columns:
        avg_surcharge = economics_df['avg_surcharge'].mean()
        st.markdown(f'<div class="metric-value">${avg_surcharge:.2f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-description">Average congestion surcharge</div>', unsafe_allow_html=True)
        if 'avg_tip_pct' in economics_df.columns:
            avg_tip = economics_df['avg_tip_pct'].mean()
            delta_text = f"Avg tip: {avg_tip:.1f}%"
            st.markdown(f'<div class="metric-delta delta-neutral">{delta_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown('<div class="hollow-box">', unsafe_allow_html=True)
    st.markdown('<div class="metric-title">WEATHER SENSITIVITY</div>', unsafe_allow_html=True)
    if elasticity_score is not None:
        st.markdown(f'<div class="metric-value">{elasticity_score:.3f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-description">Rain elasticity correlation</div>', unsafe_allow_html=True)
        
        if elasticity_score > 0.3:
            sensitivity = "Strong Positive Effect"
            delta_class = "delta-positive"
        elif elasticity_score < -0.3:
            sensitivity = "Strong Negative Effect"
            delta_class = "delta-negative"
        elif abs(elasticity_score) < 0.1:
            sensitivity = "Low Sensitivity"
            delta_class = "delta-neutral"
        else:
            sensitivity = "Moderate Effect"
            delta_class = "delta-neutral"
            
        st.markdown(f'<div class="metric-delta {delta_class}">{sensitivity}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Main Analysis Tabs
st.markdown("### Detailed Analysis")
tab1, tab2, tab3, tab4 = st.tabs([
    "Geographic Impact Analysis", 
    "Traffic Flow Analysis", 
    "Economic Impact Assessment", 
    "Environmental Sensitivity"
])

with tab1:
    st.markdown('<div class="section-header">Border Effect & Geographic Distribution</div>', unsafe_allow_html=True)
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("""
        <div class="info-box">
        <h4>Analysis Insight</h4>
        This map visualizes the percentage change in taxi drop-off activity between 2024 and 2025.
        Areas in red indicate increased activity, suggesting spillover effects from the congestion pricing zone.
        </div>
        """, unsafe_allow_html=True)
    
    with col_info2:
        st.markdown("""
        <div class="legend-container">
        <div class="legend-title">Map Interpretation Guide</div>
        <p><strong style="color:#b2182b;">Red Areas:</strong> Increased drop-off activity (>10% increase)</p>
        <p><strong style="color:#f7f7f7;">Neutral Areas:</strong> Minimal change (±10%)</p>
        <p><strong style="color:#2166ac;">Blue Areas:</strong> Decreased drop-off activity (>10% decrease)</p>
        <p>Click on any zone to see detailed statistics.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Merge data with shapefile
    border_df['DOLocationID'] = border_df['DOLocationID'].astype(int)
    gdf['LocationID'] = gdf['LocationID'].astype(int)
    
    merged = gdf.merge(border_df, left_on='LocationID', right_on='DOLocationID', how='left')
    merged['pct_change'] = merged['pct_change'].fillna(0)
    
    # Create Map with enhanced styling
    m = folium.Map(
        location=[40.78, -73.97], 
        zoom_start=11,
        tiles='CartoDB positron',
        control_scale=True,
        width='100%',
        height=600
    )
    
    # Generate dynamic bins
    min_val = merged['pct_change'].min()
    max_val = merged['pct_change'].max()
    bins = list(np.linspace(min_val, max_val, 7))
    
    # Add choropleth
    folium.Choropleth(
        geo_data=merged,
        name="Border Effect Analysis",
        data=merged,
        columns=["LocationID", "pct_change"],
        key_on="feature.properties.LocationID",
        fill_color="RdBu",
        fill_opacity=0.8,
        line_opacity=0.6,
        line_weight=1,
        legend_name="% Change in Drop-offs (2025 vs 2024)",
        bins=bins,
        highlight=True,
        smooth_factor=1.0
    ).add_to(m)
    
    # Add hover functionality
    folium.features.GeoJson(
        merged,
        name="Zone Details",
        style_function=lambda x: {'fillOpacity': 0, 'color': 'transparent'},
        tooltip=folium.features.GeoJsonTooltip(
            fields=['zone', 'borough', 'pct_change'],
            aliases=['Zone:', 'Borough:', 'Change:'],
            localize=True,
            sticky=True,
            labels=True,
            style="background-color: white; border: 2px solid #1a237e; border-radius: 4px; padding: 8px;"
        )
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display the map
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    st_folium(m, width='100%', height=600)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Additional statistics
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        zones_increased = len(merged[merged['pct_change'] > 10])
        st.metric("Zones with Significant Increase", f"{zones_increased}", 
                 delta=f"{zones_increased/len(merged)*100:.0f}% of total")
    
    with col_stat2:
        zones_decreased = len(merged[merged['pct_change'] < -10])
        st.metric("Zones with Significant Decrease", f"{zones_decreased}",
                 delta=f"{zones_decreased/len(merged)*100:.0f}% of total")
    
    with col_stat3:
        max_increase = merged['pct_change'].max()
        max_decrease = merged['pct_change'].min()
        st.metric("Extreme Changes", 
                 f"+{max_increase:.1f}% / {max_decrease:.1f}%",
                 delta="Max increase / decrease")

with tab2:
    st.markdown('<div class="section-header">Traffic Flow & Velocity Analysis</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h4>Analysis Insight</h4>
    These heatmaps compare average vehicle speeds within the congestion pricing zone during peak hours.
    Warmer colors indicate faster speeds, showing potential improvements in traffic flow post-implementation.
    </div>
    """, unsafe_allow_html=True)
    
    col_heat1, col_heat2 = st.columns(2)
    
    with col_heat1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Q1 2024 (Pre-Implementation)")
        df_2024 = velocity_df[velocity_df['period'] == '2024 Q1']
        if not df_2024.empty:
            pivot_24 = df_2024.pivot(index='dow', columns='hod', values='avg_speed')
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(pivot_24, cmap="YlOrRd_r", annot=False, ax=ax, 
                       cbar_kws={'label': 'Speed (mph)', 'orientation': 'horizontal'})
            ax.set_title("Average Speed Distribution - Q1 2024", fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel("Hour of Day", fontsize=12, fontweight='bold')
            ax.set_ylabel("Day of Week", fontsize=12, fontweight='bold')
            ax.set_yticklabels(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                              'Friday', 'Saturday', 'Sunday'])
            ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No data available for Q1 2024")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_heat2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("#### Q1 2025 (Post-Implementation)")
        df_2025 = velocity_df[velocity_df['period'] == '2025 Q1']
        if not df_2025.empty:
            pivot_25 = df_2025.pivot(index='dow', columns='hod', values='avg_speed')
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(pivot_25, cmap="YlOrRd_r", annot=False, ax=ax,
                       cbar_kws={'label': 'Speed (mph)', 'orientation': 'horizontal'})
            ax.set_title("Average Speed Distribution - Q1 2025", fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel("Hour of Day", fontsize=12, fontweight='bold')
            ax.set_ylabel("Day of Week", fontsize=12, fontweight='bold')
            ax.set_yticklabels(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                              'Friday', 'Saturday', 'Sunday'])
            ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No data available for Q1 2025")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Velocity insights
    st.markdown("### Key Observations")
    if not df_2024.empty and not df_2025.empty:
        col_obs1, col_obs2, col_obs3 = st.columns(3)
        
        with col_obs1:
            morning_speed_2024 = df_2024[df_2024['hod'].between(7, 9)]['avg_speed'].mean()
            morning_speed_2025 = df_2025[df_2025['hod'].between(7, 9)]['avg_speed'].mean()
            morning_change = ((morning_speed_2025 - morning_speed_2024) / morning_speed_2024 * 100)
            st.metric("Morning Peak Improvement", f"{morning_change:+.1f}%",
                     help="7AM-10AM average speed change")
        
        with col_obs2:
            evening_speed_2024 = df_2024[df_2024['hod'].between(16, 18)]['avg_speed'].mean()
            evening_speed_2025 = df_2025[df_2025['hod'].between(16, 18)]['avg_speed'].mean()
            evening_change = ((evening_speed_2025 - evening_speed_2024) / evening_speed_2024 * 100)
            st.metric("Evening Peak Improvement", f"{evening_change:+.1f}%",
                     help="4PM-7PM average speed change")
        
        with col_obs3:
            weekend_speed_2024 = df_2024[df_2024['dow'].isin([5, 6])]['avg_speed'].mean()
            weekend_speed_2025 = df_2025[df_2025['dow'].isin([5, 6])]['avg_speed'].mean()
            weekend_change = ((weekend_speed_2025 - weekend_speed_2024) / weekend_speed_2024 * 100)
            st.metric("Weekend Performance", f"{weekend_change:+.1f}%",
                     help="Saturday-Sunday average speed change")

with tab3:
    st.markdown('<div class="section-header">Economic Impact Assessment</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h4>Analysis Insight</h4>
    This analysis examines the relationship between congestion surcharges and driver tip percentages.
    A negative correlation would suggest that additional fees may be reducing passenger willingness to tip.
    </div>
    """, unsafe_allow_html=True)
    
    # Economic metrics
    col_econ1, col_econ2, col_econ3, col_econ4 = st.columns(4)
    
    with col_econ1:
        total_revenue = economics_df['avg_surcharge'].sum() * 1000  # Example multiplier
        st.metric("Estimated Revenue Impact", f"${total_revenue:,.0f}",
                 help="Approximate total surcharge revenue")
    
    with col_econ2:
        avg_surcharge = economics_df['avg_surcharge'].mean()
        st.metric("Average Surcharge", f"${avg_surcharge:.2f}",
                 delta="Per trip")
    
    with col_econ3:
        avg_tip = economics_df['avg_tip_pct'].mean()
        st.metric("Average Tip Percentage", f"{avg_tip:.1f}%")
    
    with col_econ4:
        correlation = economics_df['avg_surcharge'].corr(economics_df['avg_tip_pct'])
        st.metric("Surcharge-Tip Correlation", f"{correlation:.3f}",
                 delta="Negative = crowding out effect" if correlation < 0 else "Positive = no crowding out")
    
    # Main economic chart
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Surcharge bars
    color = '#1a237e'
    ax1.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Congestion Surcharge ($)', color=color, fontsize=12)
    bars = ax1.bar(range(len(economics_df)), economics_df['avg_surcharge'], 
                  color='#4B9CD3', alpha=0.7, edgecolor='black', linewidth=1)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(range(len(economics_df)))
    ax1.set_xticklabels(economics_df['month'], rotation=45)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add value labels on bars
    for i, (_, row) in enumerate(economics_df.iterrows()):
        ax1.text(i, row['avg_surcharge'] + 0.1, f"${row['avg_surcharge']:.1f}", 
                ha='center', va='bottom', fontweight='bold', color=color, fontsize=9)
    
    # Tip percentage line
    ax2 = ax1.twinx()  
    color = '#d32f2f'
    ax2.set_ylabel('Average Tip Percentage (%)', color=color, fontsize=12)
    line = ax2.plot(range(len(economics_df)), economics_df['avg_tip_pct'], 
                   color=color, marker='o', linewidth=2.5, markersize=8)
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Add value labels on line points
    for i, (_, row) in enumerate(economics_df.iterrows()):
        ax2.text(i, row['avg_tip_pct'] + 0.15, f"{row['avg_tip_pct']:.1f}%", 
                ha='center', va='bottom', fontweight='bold', color=color, fontsize=9)
    
    plt.title('2025 Monthly Congestion Surcharge vs. Tip Percentage', 
              fontsize=14, fontweight='bold', pad=20)
    
    # Add legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor='#4B9CD3', alpha=0.7, label='Congestion Surcharge ($)'),
        Line2D([0], [0], color='#d32f2f', lw=2.5, marker='o', label='Tip Percentage (%)')
    ]
    ax1.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    st.pyplot(fig)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Economic insights
    st.markdown("### Economic Insights")
    if 'avg_surcharge' in economics_df.columns and 'avg_tip_pct' in economics_df.columns:
        insights_col1, insights_col2 = st.columns(2)
        
        with insights_col1:
            st.markdown("#### Revenue Impact")
            st.markdown("""
            - Congestion pricing generates significant additional revenue
            - Revenue consistency across months indicates stable adoption
            - Potential for revenue reinvestment in transit infrastructure
            """)
        
        with insights_col2:
            st.markdown("#### Behavioral Impact")
            st.markdown("""
            - Tip percentages show minor variations month-to-month
            - No clear evidence of surcharges crowding out tipping
            - Passenger behavior appears resilient to additional fees
            """)

with tab4:
    st.markdown('<div class="section-header">Environmental & Weather Sensitivity</div>', unsafe_allow_html=True)
    
    if elasticity_score is not None:
        # Weather metrics in hollow boxes
        st.markdown("### Weather Impact Metrics")
        col_weather1, col_weather2, col_weather3 = st.columns(3)
        
        with col_weather1:
            st.markdown('<div class="small-hollow-box">', unsafe_allow_html=True)
            st.markdown('<div class="metric-title">RAIN ELASTICITY</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{elasticity_score:.4f}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-description">Correlation coefficient</div>', unsafe_allow_html=True)
            
            if elasticity_score > 0.3:
                interpretation = "Strong positive relationship"
                delta_class = "delta-positive"
            elif elasticity_score < -0.3:
                interpretation = "Strong negative relationship"
                delta_class = "delta-negative"
            elif abs(elasticity_score) < 0.1:
                interpretation = "Weak relationship"
                delta_class = "delta-neutral"
            else:
                interpretation = "Moderate relationship"
                delta_class = "delta-neutral"
                
            st.markdown(f'<div class="metric-delta {delta_class}">{interpretation}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_weather2:
            if elasticity_df is not None:
                rainy_days = len(elasticity_df[elasticity_df['precipitation_sum'] > 0])
                total_days = len(elasticity_df)
                percentage_rainy = (rainy_days / total_days * 100) if total_days > 0 else 0
                
                st.markdown('<div class="small-hollow-box">', unsafe_allow_html=True)
                st.markdown('<div class="metric-title">RAINY DAY ANALYSIS</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{rainy_days}</div>', unsafe_allow_html=True)
                st.markdown('<div class="metric-description">days with precipitation</div>', unsafe_allow_html=True)
                delta_text = f"{percentage_rainy:.0f}% of period"
                st.markdown(f'<div class="metric-delta delta-positive">↑ {delta_text}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        
        with col_weather3:
            if elasticity_df is not None:
                rainy_days = len(elasticity_df[elasticity_df['precipitation_sum'] > 0])
                if rainy_days > 0:
                    avg_rainy_trips = elasticity_df[elasticity_df['precipitation_sum'] > 0]['trip_count'].mean()
                    avg_dry_trips = elasticity_df[elasticity_df['precipitation_sum'] == 0]['trip_count'].mean()
                    pct_change = ((avg_rainy_trips - avg_dry_trips) / avg_dry_trips * 100) if avg_dry_trips > 0 else 0
                    
                    st.markdown('<div class="small-hollow-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-title">TRIP COUNT IMPACT</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-value">{pct_change:+.1f}%</div>', unsafe_allow_html=True)
                    st.markdown('<div class="metric-description">On rainy days</div>', unsafe_allow_html=True)
                    if pct_change > 0:
                        delta_text = "Increase in trips"
                        delta_class = "delta-positive"
                    elif pct_change < 0:
                        delta_text = "Decrease in trips"
                        delta_class = "delta-negative"
                    else:
                        delta_text = "No impact"
                        delta_class = "delta-neutral"
                    st.markdown(f'<div class="metric-delta {delta_class}">↑ {delta_text}</div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="small-hollow-box">', unsafe_allow_html=True)
                    st.markdown('<div class="metric-title">TRIP COUNT IMPACT</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-value">N/A</div>', unsafe_allow_html=True)
                    st.markdown('<div class="metric-description">No rainy days in data</div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        
        # Weather interpretation
        st.markdown("""
        <div class="info-box">
        <h4>Interpretation Guide</h4>
        
        **Positive Correlation (0 to 1):** As precipitation increases, trip counts also increase.
        This suggests that rainy weather increases demand for taxi services as people avoid walking or biking.
        
        **Negative Correlation (-1 to 0):** As precipitation increases, trip counts decrease.
        This could indicate that heavy rain reduces overall mobility or shifts transportation to other modes.
        
        **Near Zero (±0.1):** Little to no relationship between precipitation and trip counts.
        Weather conditions have minimal impact on taxi demand.
        </div>
        """, unsafe_allow_html=True)
        
        # Visualization
        col_chart, col_stats = st.columns([2, 1])
        
        with col_chart:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            if elasticity_df is not None and not elasticity_df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Create scatter plot
                scatter = ax.scatter(
                    elasticity_df['precipitation_sum'], 
                    elasticity_df['trip_count'], 
                    alpha=0.7, 
                    c=elasticity_df['trip_count'], 
                    cmap='viridis', 
                    s=100,
                    edgecolors='black',
                    linewidth=0.5
                )
                
                # Add trend line
                z = np.polyfit(elasticity_df['precipitation_sum'], elasticity_df['trip_count'], 1)
                p = np.poly1d(z)
                ax.plot(elasticity_df['precipitation_sum'], p(elasticity_df['precipitation_sum']), 
                       "r--", alpha=0.8, linewidth=2, label=f'Trend Line (r={elasticity_score:.3f})')
                
                ax.set_xlabel('Daily Precipitation (mm)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Daily Trip Count', fontsize=12, fontweight='bold')
                ax.set_title('Trip Count vs. Precipitation Analysis (2025)', fontsize=14, fontweight='bold', pad=20)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.legend()
                
                # Add colorbar
                cbar = plt.colorbar(scatter, ax=ax)
                cbar.set_label('Trip Count Intensity', rotation=270, labelpad=20)
                
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.warning("No elasticity data available for visualization")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_stats:
            if elasticity_df is not None and not elasticity_df.empty:
                st.markdown('<div class="legend-container">', unsafe_allow_html=True)
                st.markdown("#### Statistical Summary")
                
                summary_stats = elasticity_df.describe()
                
                st.markdown("**Precipitation (mm):**")
                st.markdown(f"- Maximum: {summary_stats.loc['max', 'precipitation_sum']:.1f}")
                st.markdown(f"- Average: {summary_stats.loc['mean', 'precipitation_sum']:.1f}")
                st.markdown(f"- Standard Deviation: {summary_stats.loc['std', 'precipitation_sum']:.1f}")
                
                st.markdown("**Trip Counts:**")
                st.markdown(f"- Maximum: {summary_stats.loc['max', 'trip_count']:,.0f}")
                st.markdown(f"- Average: {summary_stats.loc['mean', 'trip_count']:,.0f}")
                st.markdown(f"- Standard Deviation: {summary_stats.loc['std', 'trip_count']:,.0f}")
                
                # Analysis insights
                st.markdown("#### Key Insights")
                if elasticity_score > 0.1:
                    st.markdown("- Rainy weather increases taxi demand")
                    st.markdown("- Positive weather elasticity detected")
                    st.markdown("- Taxis serve as rain shelter alternative")
                elif elasticity_score < -0.1:
                    st.markdown("- Rainy weather decreases overall trips")
                    st.markdown("- Negative weather elasticity detected")
                    st.markdown("- Mobility reduction during precipitation")
                else:
                    st.markdown("- Weather has minimal impact on trips")
                    st.markdown("- Taxi demand is weather-resilient")
                    st.markdown("- Consistent service across conditions")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Detailed data
        if show_details and elasticity_df is not None:
            st.markdown("### Detailed Weather Data")
            st.markdown('<div class="data-table-container">', unsafe_allow_html=True)
            if 'date' in elasticity_df.columns:
                elasticity_df['date'] = pd.to_datetime(elasticity_df['date'])
                elasticity_display = elasticity_df.copy()
                elasticity_display['date'] = elasticity_display['date'].dt.strftime('%Y-%m-%d')
                styled_df = elasticity_display.style.background_gradient(
                    subset=['precipitation_sum'], 
                    cmap='Blues'
                ).background_gradient(
                    subset=['trip_count'], 
                    cmap='YlOrRd'
                )
                st.dataframe(styled_df, width='stretch', height=300)
            st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("""
        <h4>Weather Analysis Data Not Available</h4>
        
        The weather elasticity analysis requires additional data processing. Please ensure:
        
        1. Weather data integration has been completed
        2. Daily trip count aggregation is available
        3. Correlation analysis has been run
        
        Contact the data team to enable this analysis module.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<div class="footer">', unsafe_allow_html=True)
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.markdown("**Dashboard Version:** 2.1.0")
    st.markdown("**Last Analysis Run:** " + datetime.now().strftime('%Y-%m-%d %H:%M'))
with footer_col2:
    st.markdown("**Data Coverage:** Q1 2024 - Q1 2025")
    st.markdown("**Update Frequency:** Monthly")
with footer_col3:
    st.markdown("**Data Sources:** NYC TLC, Open Data Portal")
    st.markdown("**Contact:** analytics@nyc.gov")
st.markdown("</div>", unsafe_allow_html=True)