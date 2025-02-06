import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_folium import folium_static
from folium import plugins
import json
from datetime import datetime
from keboola_streamlit import KeboolaStreamlit
import os 

URL = st.secrets["kbc_url"]
TOKEN = st.secrets["kbc_token"]
TABLE_ID = st.secrets["table_id"]
keboola = KeboolaStreamlit(root_url=URL, token=TOKEN)
# Set page config
st.set_page_config(
    page_title="Route Visualization",
    page_icon="🚚",
    layout="wide"
)

# Add custom CSS for better tab styling
st.markdown("""
    <style>

    /* Add Premier Trailer branding colors */
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 4px;
        padding: 1rem;
    }
    .stMetric:hover {
        background-color: #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

# Add logo
st.markdown(
f'''
    <div style="text-align: right;">
        <img src="https://assets-global.website-files.com/5e21dc6f4c5acf29c35bb32c/5e21e66410e34945f7f25add_Keboola_logo.svg" alt="Logo" width="200">
    </div>
''',
unsafe_allow_html=True
)
st.title("Premier Trailer Dashboard")

# Create tabs
tab1, tab2, tab3 = st.tabs([
    "_Live_ Status Dashboard", 
    "Route Details",
    "Data Quality Check", 
    
])

# Add near the top of the file, after imports
if 'route_progress' not in st.session_state:
    # Initialize default progress
    st.session_state.route_progress = {
        'ROUTE_1': 0.27,  # 33% complete
        'ROUTE_2': 0.43,  # 40% complete
        'ROUTE_3': 0.52,  # 50% complete
        'ROUTE_4': 0.22,  # 25% complete
        'ROUTE_5': 0.34   # 33% complete
    }
with tab1:
    @st.cache_data
    def load_data():
        # Read routes data
        # Define paths for data files
        data_dir = os.path.dirname(__file__)
        routes_path = os.path.join(data_dir, '1routes_vehicles_status.csv')
        routes_df = pd.read_csv(routes_path)
        
        # Convert distance from km to miles
        routes_df['distance'] = routes_df['distance'] * 0.621371
        
        # Load GeoJSON data for each route
        geojson_files = {
            'ROUTE_1': 'ors__v2_directions_{profile}_get_1738763340945.geojson',
            'ROUTE_2': 'ors__v2_directions_{profile}_get_1738763410958.geojson', 
            'ROUTE_3': 'ors__v2_directions_{profile}_get_1738763387823.geojson',
            'ROUTE_4': 'ors__v2_directions_{profile}_get_1738798617562.geojson',
            'ROUTE_5': 'ors__v2_directions_{profile}_get_1738798896409.geojson'
        }
        
        geojson_data = {}
        for route_id, filename in geojson_files.items():
            geojson_path = os.path.join(data_dir, filename)
            with open(geojson_path, 'r') as f:
                geojson_data[route_id] = json.load(f)
                
        return routes_df, geojson_data

    def split_route(locations, progress):
        split_index = int(len(locations) * progress)
        return locations[:split_index], locations[split_index:]

    @st.fragment
    def create_route_map(selected_routes, routes_df, geojson_data):
        # Create a base map centered on central US with closer zoom
        m = folium.Map(
            location=[37.0902, -90.7129],  # Moved 5 degrees east from -95.7129
            zoom_start=4.5,
            tiles='cartodbpositron'
        )

        # Define some colors for different routes
        colors = ['darkred', 'darkblue', 'darkgreen', 'purple', 'orange']

        # Process each selected route
        for idx, route_id in enumerate(selected_routes):
            # Get route info
            route_info = routes_df[routes_df['route_id'] == route_id].iloc[0]
            
            # Get coordinates from GeoJSON
            coordinates = geojson_data[route_id]['features'][0]['geometry']['coordinates']
            locations = [[coord[1], coord[0]] for coord in coordinates]
            
            color = colors[idx % len(colors)]
            
            # Use progress from session state
            progress = st.session_state.route_progress[route_id]
            
            # Split route into completed and remaining portions
            completed_route, remaining_route = split_route(locations, progress)
            
            # Draw completed portion of route (darker)
            folium.PolyLine(
                locations=completed_route,
                weight=4,
                color=color,
                opacity=0.9
            ).add_to(m)
            
            # Draw remaining portion of route (lighter) only if there are remaining points
            if remaining_route:
                plugins.AntPath(
                    locations=remaining_route,
                    weight=3,
                    color=color,
                    opacity=0.6,
                    popup=f"Route: {route_id} ({route_info['route_description']})",
                    delay=1000,
                    dash_array=[10, 20],
                    pulse_color='#FFF'
                ).add_to(m)
            
            # Add vehicle marker at current position (use the last point of the route if 100% complete)
            vehicle_position = completed_route[-1] if completed_route else locations[0]
            
            # Calculate remaining distance and time (ensure they don't go below 0)
            remaining_distance = max(route_info['distance'] * (1 - progress), 0)
            remaining_time = max(route_info['duration'] * (1 - progress), 0)
            
            # Calculate average speed in mph
            avg_speed = (route_info['distance']/1609.34) / (route_info['duration']/3600)
            
            vehicle_icon = folium.DivIcon(
                html=f'''
                    <div style="font-family: FontAwesome; color: {color}; background-color: {color}; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 16px;">🚛</span>
                    </div>
                ''',
                icon_size=(25, 25)
            )
            
            folium.Marker(
                vehicle_position,
                icon=vehicle_icon,
                tooltip=f"""
                <b>{route_id}</b><br>
                Vehicle: {route_info['vehicle_make']} {route_info['vehicle_model']}<br>
                Completed: {progress*100:.0f}%<br>
                Remaining Distance: {remaining_distance/1609.34:.1f} miles<br>
                Remaining Time: {remaining_time/3600:.1f} hours<br>
                Average Speed: {avg_speed:.1f} mph
                """
            ).add_to(m)
            # Add markers for start and end points
            folium.Marker(
                locations[0],
                tooltip=f"Start: {route_info['start']}",
                icon=folium.DivIcon(
                    html=f'''
                        <div style="background-color: #2ecc71; width: 18px; height: 18px; 
                             border-radius: 50%; border: 2px solid white;">
                        </div>
                    ''',
                    icon_size=(18, 18),
                )
            ).add_to(m)
            
            folium.Marker(
                locations[-1],
                tooltip=f"End: {route_info['end']}",
                icon=folium.DivIcon(
                    html=f'''
                        <div style="background-color: #e74c3c; width: 18px; height: 18px; 
                             border-radius: 50%; border: 2px solid white;">
                        </div>
                    ''',
                    icon_size=(18, 18),
                )
            ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Display the map in Streamlit
        st_folium(m, width=1400, height=600)

        # Display route information
        if selected_routes:
            #st.subheader("Route Details")
            for route_id in selected_routes:
                route_info = routes_df[routes_df['route_id'] == route_id].iloc[0]
                # Get the correct progress for this specific route
                route_progress = st.session_state.route_progress[route_id]
                # Calculate remaining distance and time using the correct progress
                remaining_distance = route_info['distance'] * (1 - route_progress)
                remaining_time = route_info['duration'] * (1 - route_progress)
                
                with st.expander(f"📍 {route_id} - {route_info['route_description']}"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "Total Distance (miles)", 
                            f"{route_info['distance']/1000:.1f}",
                        )
                    with col2:
                        st.metric(
                            "Total Duration (hours)", 
                            f"{route_info['duration']/3600:.1f}",
                        )
                    with col3:
                        st.metric("Status", route_info['route_status'])
                    with col4:
                        st.metric("Completed", f"{route_progress*100:.0f}%")
                    
                    st.write("Vehicle Information:")
                    st.markdown(f"""
                        - Vehicle ID: {route_info['vehicle_id']}
                        - Make: {route_info['vehicle_make']}
                        - Model: {route_info['vehicle_model']}
                        - Year: {route_info['vehicle_year']}
                        - Fuel Type: {route_info['vehicle_fuelTypePrimary']}
                        - Additional Info: {route_info['vehicle_additionalInfo']}
                    """)
    routes_df, geojson_data = load_data()
    # Create a route selector

    route_ids = list(geojson_data.keys())
    selected_routes = st.pills(
        "Select from Active Vehicles",
        options=route_ids,
        default=route_ids,
        selection_mode="multi",
        format_func=lambda x: f"{x} ({routes_df[routes_df['route_id'] == x].iloc[0]['route_description']})"
    )
    col1, col2= st.columns([4,1], gap="medium")
    with col1:
        create_route_map(selected_routes, routes_df, geojson_data)
    with col2:        
        current_time = datetime.now().strftime("%H:%M:%S")
        st.metric("Last Updated", current_time)
        def update_progress():
            # Increment progress for each route by a small amount
            for route_id in st.session_state.route_progress:
                current_progress = st.session_state.route_progress[route_id]
                # Add 5% progress, but don't exceed 100%
                st.session_state.route_progress[route_id] = min(current_progress + 0.01, 1.0)

        st.button("🔄 Update Data", use_container_width=True, on_click=update_progress, type="tertiary")




def create_geojson_route_map(route_df):
    """Create a map with the CSV route data colored by road types"""
    # Use the pre-loaded data

    # Define colors for different road types
    road_type_colors = {
        'tertiary': '#FFA500',    # Orange
        'secondary': '#4169E1',    # Royal Blue
        'primary': '#FF0000',      # Red
        'residential': '#32CD32',  # Lime Green
        'motorway': '#800080',     # Purple
        'trunk': '#8B4513',        # Saddle Brown
        'unclassified': '#808080', # Gray
        'footway': '#FFD700',      # Gold
        'service': '#20B2AA',      # Light Sea Green
        'path': '#DDA0DD',         # Plum
        'cycleway': '#00CED1',     # Dark Turquoise
        'pedestrian': '#F08080',   # Light Coral
        'living_street': '#98FB98', # Pale Green
        'track': '#DEB887'         # Burlywood
    }

    # Calculate the center point of the route
    center_lat = route_df['LAT'].mean()
    center_lon = route_df['LONG'].mean()

    # Create a map centered on the route
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)

    # Group the dataframe by road type to draw segments
    current_road_type = None
    current_coordinates = []
    current_segment_info = {}

    for idx, row in route_df.iterrows():
        if current_road_type != row['road_type']:
            # Draw the previous segment if it exists
            if current_coordinates and len(current_segment_info) > 0:
                color = road_type_colors.get(current_road_type, '#808080')
                # Create detailed tooltip HTML
                tooltip_html = f"""
                <div style='font-family: Arial; font-size: 12px; min-width: 200px; white-space: nowrap;'>
                    <div style='font-weight: bold; color: {color}; margin-bottom: 4px;'>
                        {current_segment_info.get('name', 'Unnamed Road')}
                    </div>
                    <b>Type:</b> {current_road_type.title()}<br>
                    <b>Speed Limit:</b> {current_segment_info.get('speed_limit', 'Unknown')}<br>
                    <b>Lanes:</b> {current_segment_info.get('lanes_total', 'Unknown')}<br>
                    <b>Surface:</b> {current_segment_info.get('surface', 'Unknown')}
                </div>
                """
                
                folium.PolyLine(
                    current_coordinates,
                    weight=4,
                    color=color,
                    opacity=0.8,
                    tooltip=folium.Tooltip(tooltip_html)
                ).add_to(m)

            # Start new segment
            current_road_type = row['road_type']
            current_coordinates = []
            current_segment_info = row.to_dict()

        current_coordinates.append([row['LAT'], row['LONG']])

    # Draw the last segment
    if current_coordinates and len(current_segment_info) > 0:
        color = road_type_colors.get(current_road_type, '#808080')
        tooltip_html = f"""
        <div style='font-family: Arial; font-size: 12px; min-width: 200px; white-space: nowrap;'>
            <div style='font-weight: bold; color: {color}; margin-bottom: 4px;'>
                {current_segment_info.get('name', 'Unnamed Road')}
            </div>
            <b>Type:</b> {current_road_type.title()}<br>
            <b>Speed Limit:</b> {current_segment_info.get('speed_limit', 'Unknown')}<br>
            <b>Lanes:</b> {current_segment_info.get('lanes_total', 'Unknown')}<br>
            <b>Surface:</b> {current_segment_info.get('surface', 'Unknown')}
        </div>
        """
        
        folium.PolyLine(
            current_coordinates,
            weight=4,
            color=color,
            opacity=0.8,
            tooltip=folium.Tooltip(tooltip_html)
        ).add_to(m)

    # Add markers for start and end points
    folium.Marker(
        [route_df.iloc[0]['LAT'], route_df.iloc[0]['LONG']],
        popup='Start',
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)

    folium.Marker(
        [route_df.iloc[-1]['LAT'], route_df.iloc[-1]['LONG']],
        popup='End',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

    return m

with tab2:
    path = os.path.join(os.path.dirname(__file__), '823_road_type.csv')
    road_type_df = pd.read_csv(path)
    
    # Add play/pause controls
    col1, col2 = st.columns([4,1], gap="medium")
    with col1:
        # First create the slider
        step = st.slider(
            "Timeline",
            0,
            len(road_type_df) - 1,
            round(len(road_type_df) / 2),
            label_visibility="collapsed",
            format=""  # This hides the numbers
        )
        
        # Then calculate progress
        progress = step / (len(road_type_df) - 1)
        
        # Add custom labels above the slider
        left_label = "Houston, TX"
        right_label = "New Orleans, LA"
        
        cols = st.columns([1, 4, 1])
        with cols[0]:
            st.markdown(f"<div style='text-align: left; color: #666;'>{left_label}</div>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<div style='text-align: right; color: #666;'>{right_label}</div>", unsafe_allow_html=True)
        # Get the current step data
        current_step = road_type_df.iloc[step]
        st.markdown("<br>", unsafe_allow_html=True)
        # Create the base map showing the complete route
        m = create_geojson_route_map(road_type_df)
        
        # Add a marker for the current vehicle position with custom icon
        vehicle_icon = folium.DivIcon(
            html=f'''
                <div style="font-family: FontAwesome; color: white; background-color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 16px;">🚛</span>
                </div>
            ''',
            icon_size=(25, 25)
        )
        
        current_location = [current_step['LAT'], current_step['LONG']]
        folium.Marker(
            current_location,
            icon=vehicle_icon,
            tooltip=f"""
            <div style='font-family: Arial; font-size: 12px;'>
                <b>Current Location Details:</b><br>
                Road Type: {current_step['road_type']}<br>
                Speed Limit: {current_step['speed_limit']}<br>
                Surface: {current_step['surface']}<br>
                Name: {current_step['name']}
            </div>
            """
        ).add_to(m)
        
        # Display the map
        folium_static(m, width=1000, height=500)
    with col2:
        # Display current road information in a more organized way
        # Add road type color legen        
        st.metric("Road Type", current_step['road_type'].title())
        st.metric("Speed Limit", f"{current_step['speed_limit']}")
        st.metric("Surface", current_step['surface'].title())
        st.metric("Lanes", current_step['lanes_total'])
        
        st.markdown("#### Route Types")
        # Get unique road types and their percentages
        road_type_counts = road_type_df['road_type'].value_counts()
        total_segments = len(road_type_df)
                # Define colors for different road types (same as in create_geojson_route_map)
        road_type_colors = {
            'tertiary': '#FFA500',    # Orange
            'secondary': '#4169E1',    # Royal Blue
            'primary': '#FF0000',      # Red
            'residential': '#32CD32',  # Lime Green
            'motorway': '#800080',     # Purple
            'trunk': '#8B4513',        # Saddle Brown
            'unclassified': '#808080', # Gray
            'footway': '#FFD700',      # Gold
            'service': '#20B2AA',      # Light Sea Green
            'path': '#DDA0DD',         # Plum
            'cycleway': '#00CED1',     # Dark Turquoise
            'pedestrian': '#F08080',   # Light Coral
            'living_street': '#98FB98', # Pale Green
            'track': '#DEB887'         # Burlywood
        }
        # Create legend with colored boxes and percentages
        for road_type in road_type_counts.index:
            percentage = (road_type_counts[road_type] / total_segments) * 100
            color = road_type_colors.get(road_type, '#808080')
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; margin: 2px 0; font-size: 0.9em;">
                    <div style="width: 12px; height: 12px; background-color: {color}; 
                              margin-right: 6px; border-radius: 2px;"></div>
                    <div style="flex-grow: 1;">{road_type.title()}</div>
                    <div style="color: #666;">{percentage:.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )

with tab3:
    # Load the driver data
    if 'driver_data' not in st.session_state:
        st.session_state.driver_data = keboola.read_table(TABLE_ID)
        # Convert timestamp column to string to make it editable
        st.session_state.driver_data['timestamp'] = st.session_state.driver_data['timestamp'].astype(str)
    
    # Function to check if timestamp matches the correct format
    def is_valid_timestamp(ts):
        try:
            datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False
    
    # Add a column for format validation
    st.session_state.driver_data['is_valid_format'] = st.session_state.driver_data['timestamp'].apply(is_valid_timestamp)
    
    # Get only invalid timestamps
    incorrect_timestamps = st.session_state.driver_data[~st.session_state.driver_data['is_valid_format']]
    
    if len(incorrect_timestamps) > 0:
        st.warning(f"Found {len(incorrect_timestamps)} rows with incorrect timestamp format.")
        st.markdown("""
        The timestamps should be in the following format: `YYYY-MM-DD HH:MM:SS`
        """)
    
    # Create column configuration for the editor
    column_config = {
        "timestamp": st.column_config.TextColumn(
            "timestamp",
            help="Format: YYYY-MM-DD HH:MM:SS",
            width="medium",
        )
    }
    
    # Display only rows with invalid timestamps
    edited_df = st.data_editor(
        incorrect_timestamps,
        key='timestamp_editor',
        disabled=[col for col in incorrect_timestamps.columns if col != 'timestamp'],
        column_config=column_config,
        use_container_width=True,
        height=500,
        hide_index=True
    )
    # Add save button
    col1, col2, col3, col4, col5 = st.columns(5)
    if col1.button("Save to Keboola", type="primary"):
        try:
            # Update the validation column
            edited_df['is_valid_format'] = edited_df['timestamp'].apply(is_valid_timestamp)
            # Check if there are still invalid timestamps
            edited_df = edited_df[edited_df['is_valid_format']]
            valid_rows = edited_df.drop('is_valid_format', axis=1)
            with st.spinner(f"Saving corrected data to Keboola..."):
                keboola.write_table(TABLE_ID, valid_rows, is_incremental=True)
            st.success("Data successfully saved!")
    
        except Exception as e:
            st.error(f"An error occurred while saving: {str(e)}")

    if col5.button("Reload Data", type="tertiary", use_container_width=True):
        # Remove from session state and reload
        if 'driver_data' in st.session_state:
            del st.session_state.driver_data
        with st.spinner("Reloading data..."):
            st.session_state.driver_data = keboola.read_table(TABLE_ID)
            # Convert timestamp column to string to make it editable
            st.session_state.driver_data['timestamp'] = st.session_state.driver_data['timestamp'].astype(str)
        st.rerun()
if __name__ == "__main__":
    pass  # Main execution is now handled by the tabs