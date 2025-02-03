import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ----------------------
# Load and Process GPS Data
# ----------------------
@st.cache_data  # This decorator ensures the data is cached and not reloaded on every interaction
def load_gps_data():
    """
    Loads GPS data from the CSV file and adds vendor information
    for demonstration purposes.
    """
    df = pd.read_csv("gps_data_cleaned.csv")
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Add vendor information based on trailer_id patterns
    # In a real scenario, this would come from the data source
    vendor_mapping = {
        'Trailer_1': 'VendorA',
        'Trailer_2': 'VendorA',
        'Trailer_3': 'VendorB',
        'Trailer_4': 'VendorC',
    }
    df['vendor'] = df['trailer_id'].map(vendor_mapping).fillna('Unknown Vendor')  # Replace NaN with 'Unknown Vendor'
    
    return df

# ----------------------
# Streamlit App Layout
# ----------------------
def main():
    st.title("Multi-Vendor GPS Visualization")
    st.markdown(
        """
        This application visualizes GPS data from multiple vendors tracking different trailers.
        The data is loaded from historical records and includes information about trailer locations,
        timestamps, and the corresponding vendors.
        """
    )
    
    # Load GPS data
    df_gps = load_gps_data()
    
    # Add vendor filter
    vendors = sorted(df_gps['vendor'].unique().tolist())
    selected_vendors = st.multiselect(
        "Select Vendors:",
        options=vendors,
        default=vendors
    )
    
    # Add trailer filter
    trailers = sorted(df_gps[df_gps['vendor'].isin(selected_vendors)]['trailer_id'].unique().tolist())
    selected_trailers = st.multiselect(
        "Select Trailers:",
        options=trailers,
        default=trailers
    )
    
    # Filter data based on selections
    filtered_df = df_gps[
        (df_gps['vendor'].isin(selected_vendors)) &
        (df_gps['trailer_id'].isin(selected_trailers))
    ]

    # Date range filter
    min_date = df_gps['timestamp'].min().date()
    max_date = df_gps['timestamp'].max().date()
    date_range = st.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['timestamp'].dt.date >= start_date) &
            (filtered_df['timestamp'].dt.date <= end_date)
        ]

    # Show data summary
    st.subheader("Data Summary")
    st.write(f"Showing {len(filtered_df)} GPS records from {len(filtered_df['vendor'].unique())} vendors")
    
    # Display latest position for each trailer
    st.subheader("Latest Positions")
    latest_positions = filtered_df.sort_values('timestamp').groupby('trailer_id').last()
    st.dataframe(latest_positions[['vendor', 'latitude', 'longitude', 'timestamp']])
    
    # Plotly map visualization
    if not filtered_df.empty:
        st.subheader("Map View")
        fig = px.scatter_mapbox(
            filtered_df,
            lat="latitude",
            lon="longitude",
            color="vendor",
            hover_data=["trailer_id", "timestamp"],
            zoom=4,
            height=600,
            animation_frame=filtered_df['timestamp'].dt.strftime('%Y-%m-%d'),
            title="GPS Positions Over Time"
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":30,"l":0,"b":0}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No GPS records match the current filters.")

if __name__ == "__main__":
    main()
