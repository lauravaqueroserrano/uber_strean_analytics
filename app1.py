# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import ast
from datetime import timedelta
from scipy.stats import zscore
from azure.storage.blob import BlobServiceClient
from io import BytesIO

# Set layout
st.set_page_config(page_title="Uber Real-Time Dashboard", layout="wide")
st.title("Uber Real-Time Analytics Dashboard")

# Azure connection
conn_str = "DefaultEndpointsProtocol=https;AccountName=iesstsabbadbab;AccountKey=/Z4VcADF8fi/0zqf5v4aJk47k5MAUZFTVx7bkbdId3N0zG+UQv7bmA9Qr6ygGEGMEYwikrOBfRjk+AStl5SehA==;EndpointSuffix=core.windows.net"
container_name = "group4"

blob_service_client = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_service_client.get_container_client(container_name)

def read_json_from_blob(blob_name):
    blob_client = container_client.get_blob_client(blob_name)
    stream = BytesIO()
    blob_client.download_blob().readinto(stream)
    stream.seek(0)
    return pd.read_json(stream)

def load_alerts_from_blob(blob_name):
    blob_client = container_client.get_blob_client(blob_name)
    raw_json = blob_client.download_blob().readall()
    raw_alerts = json.loads(raw_json)
    flat_alerts = []
    for zone, alerts in raw_alerts.items():
        for alert in alerts:
            alert["zone"] = zone
            flat_alerts.append(alert)
    return pd.DataFrame(flat_alerts)

def read_jsons_from_prefix(prefix):
    dataframes = []
    for blob in container_client.list_blobs(name_starts_with=prefix):
        if blob.name.endswith(".json"):
            blob_client = container_client.get_blob_client(blob)
            content = blob_client.download_blob().readall()
            try:
                df = pd.read_json(BytesIO(content))
                dataframes.append(df)
            except ValueError as e:
                st.warning(f"❌ Error leyendo {blob.name}: {e}")
    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        st.error(f"No JSON files found under prefix: {prefix}")
        st.stop()


# Read data from blob
df_rides = read_jsons_from_prefix("ride_stream/")
df_alerts = read_jsons_from_prefix("traffic_stream/")




# Transform ride data
if 'timestamp_event' in df_rides.columns:
    df_rides['timestamp'] = pd.to_datetime(df_rides['timestamp_event'])
    df_rides['pickup_time'] = df_rides['timestamp']
    df_rides['dropoff_time'] = df_rides['pickup_time'] + timedelta(minutes=5)

    df_rides['start_coordinates'] = df_rides['start_coordinates'].apply(ast.literal_eval)
    df_rides = df_rides[df_rides['start_coordinates'].apply(lambda x: isinstance(x, list) and len(x) == 2)]

    df_rides[['pickup_lat', 'pickup_lon']] = pd.DataFrame(df_rides['start_coordinates'].tolist(), index=df_rides.index)
    df_rides['pickup_zone'] = df_rides['start_location']
    df_rides['status'] = df_rides['event_type']
else:
    st.error("Missing expected columns in ride events file.")
    st.stop()

# Load and flatten traffic alerts
def load_alerts(path):
    with open(path, 'r') as f:
        raw_alerts = json.load(f)
    flat_alerts = []
    for zone, alerts in raw_alerts.items():
        for alert in alerts:
            alert["zone"] = zone
            flat_alerts.append(alert)
    return pd.DataFrame(flat_alerts)

df_alerts = load_alerts(traffic_path)
df_alerts['timestamp'] = pd.to_datetime(df_alerts['timestamp'])

# Section 0: Total Rides by Day of the Week
import plotly.express as px
import streamlit as st

st.header("Basic Analytics")
st.subheader("1. Tumbling Technique: Total Rides by Day of the Week")

# Prepare data
df_rides['weekday'] = df_rides['day_of_week']
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
rides_by_day = df_rides['weekday'].value_counts().reindex(days_order).reset_index()
rides_by_day.columns = ['weekday', 'ride_count']

# Refined green-only gradient
custom_greens = [
    [0.0, '#d0f0c0'],  # light mint green
    [0.25, '#a8ddb5'],
    [0.5, '#7bcb96'],
    [0.75, '#4daf4a'],
    [1.0, '#006400']   # forest green
]

# Build the bar chart
fig0 = px.bar(
    rides_by_day,
    x='ride_count',
    y='weekday',
    orientation='h',
    color='ride_count',
    color_continuous_scale=custom_greens,
    title="Total Rides by Day of the Week",
    labels={'ride_count': 'Ride Count', 'weekday': 'Day'}
)

# Style the layout
fig0.update_layout(
    showlegend=False,
    yaxis=dict(categoryorder='array', categoryarray=days_order),
    title_font_size=22,
    xaxis_title_font=dict(size=16),
    yaxis_title_font=dict(size=16),
    xaxis_tickfont=dict(size=14),
    yaxis_tickfont=dict(size=14),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=80, r=40, t=60, b=40),
    coloraxis_showscale=False
)

# Add values as text
fig0.update_traces(
    text=rides_by_day['ride_count'],
    textposition='outside',
    marker_line_color='white',
    marker_line_width=1.2
)

st.plotly_chart(fig0, use_container_width=True)





# Section 1: Active Rides Over Time
st.subheader("2. Hopping Technique: Active Rides Over Time")
df_rides['timestamp_15min'] = df_rides['timestamp'].dt.floor('15T')
x_min = df_rides['timestamp_15min'].min()
x_max = df_rides['timestamp_15min'].max()

col1, col2 = st.columns([1, 4], gap="large")

with col1:
    st.markdown("### Select Day of the Week")
    weekday_filter = st.radio(label="", options=days_order, index=0)

with col2:
    df_rides_filtered = df_rides[df_rides['weekday'] == weekday_filter]

    if df_rides_filtered.empty:
        st.warning(f"No data available for '{weekday_filter}'.")
    else:
        ride_counts = df_rides_filtered.groupby(df_rides_filtered['timestamp_15min']).size().reset_index(name='ride_count')

        fig1 = px.line(
            ride_counts,
            x='timestamp_15min',
            y='ride_count',
            title=f"Active Rides Over Time - {weekday_filter}",
            labels={'timestamp_15min': 'Time', 'ride_count': 'Ride Count'},
            line_shape='spline',
            color_discrete_sequence=['#2ca02c']  # green line
        )

        fig1.update_traces(line=dict(width=2))
        fig1.update_layout(
            hovermode='x unified',
            xaxis=dict(tickformat='%H:%M', showgrid=False, range=[x_min, x_max]),
            yaxis=dict(showgrid=True),
            title_font_size=20,
            xaxis_title_font=dict(size=14),
            yaxis_title_font=dict(size=14),
            margin=dict(l=50, r=40, t=50, b=40)
        )

        st.plotly_chart(fig1, use_container_width=True)






# --- Section X: Distribution of Ride Requests by Uber Type (Pie Chart) ---
st.subheader("3. Distribution of Ride Requests by Uber Type")
st.caption("Proportion of 'Request' events by 'uber_share' or 'regular_uber' type")

# Filter only 'Request' events
requests = df_rides[df_rides["event_type"] == "Request"]

# Count by Uber type
request_counts = requests["uber_type"].value_counts().reset_index()
request_counts.columns = ["Uber Type", "Count"]

# Pie chart
fig_pie = px.pie(
    request_counts,
    names="Uber Type",
    values="Count",
    title="Proportion of Ride Requests by Uber Type",
    color="Uber Type",
    color_discrete_map={
        "uber_share": "#1f77b4",       # blue
        "regular_uber": "#2ca02c"      # green
    },
    hole=0.3  # makes it a donut chart if preferred
)

st.plotly_chart(fig_pie, use_container_width=True)

# Total
st.metric("Total Ride Requests", len(requests))


st.subheader("4. Comparison of Ubers vs. Users in Ubers")
st.caption("Counts rides that started in the last 15 minutes. Assumes 100 Ubers available at the start.")

# Ensure timestamp is in datetime format
df_rides["timestamp"] = pd.to_datetime(df_rides["timestamp"])

# Create 15-minute intervals
df_rides["interval_15min"] = df_rides["timestamp"].dt.floor("15min")

# Define time range to analyze
all_intervals = pd.date_range(df_rides["timestamp"].min(), df_rides["timestamp"].max(), freq="15min")

# For each interval, count rides that started in the last 15 minutes
active_summary = []
for current_time in all_intervals:
    start_time = current_time - pd.Timedelta(minutes=15)

    mask = (
        (df_rides["event_type"] == "Start car ride") &
        (df_rides["timestamp"] > start_time) &
        (df_rides["timestamp"] <= current_time)
    )

    users = df_rides.loc[mask, "ride_id"].nunique()
    ubers = 100 - users

    active_summary.append({
        "interval_15min": current_time,
        "users_in_uber": users,
        "available_ubers": max(0, ubers)
    })

# Create results dataframe
df_result = pd.DataFrame(active_summary)

# Display in Streamlit
st.dataframe(df_result, use_container_width=True)



# --- Section 13: Long Wait Times ---

# --- Section 13: Average Wait Time between Request and Driver Available ---
st.subheader("5. Average Wait Time between Request and Driver Available")

# Filter only relevant events
filtered = df_rides[df_rides["event_type"].isin(["Request", "Driver available"])]

# Sort by ride_id and timestamp
filtered = filtered.sort_values(["ride_id", "timestamp"])

# Get the first timestamp of each event per ride
first_events = filtered.groupby(["ride_id", "event_type"])["timestamp"].first().unstack()

# Drop rides without both events
first_events = first_events.dropna(subset=["Request", "Driver available"])

if first_events.empty:
    st.warning("No rides found with both events: 'Request' and 'Driver available'")
else:
    # Calculate wait time in seconds
    first_events["wait_to_driver_sec"] = (first_events["Driver available"] - first_events["Request"]).dt.total_seconds()

    # Compute and display the average wait time in seconds
    avg_wait_seconds = first_events["wait_to_driver_sec"].mean()
    st.metric(label="Average Wait Time (seconds)", value=f"{avg_wait_seconds:.2f}")





# --- Section +1: Top 10 Longest Unique Durations ---
st.subheader("6. Top 10 Longest Unique Durations (Start → Finish)")
st.caption("Shows the longest durations without repeated times")

# Filter relevant events
ride_events = df_rides[df_rides["event_type"].isin(["Start car ride", "Ride finished"])]
ride_events = ride_events.sort_values(["ride_id", "timestamp"])

# Group and get timestamps
start_finish = ride_events.groupby(["ride_id", "event_type"])["timestamp"].first().unstack()
start_finish = start_finish.dropna(subset=["Start car ride", "Ride finished"])

# Calculate duration
start_finish["ride_duration_min"] = (start_finish["Ride finished"] - start_finish["Start car ride"]).dt.total_seconds() / 60

# Remove duplicate durations
unique_durations = start_finish.drop_duplicates(subset="ride_duration_min")

# Top 10 longest
top_unique = unique_durations.sort_values("ride_duration_min", ascending=False).head(10).reset_index()

# Plot
fig_top_unique = px.bar(
    top_unique,
    x="ride_duration_min",
    y="ride_id",
    orientation="h",
    color="ride_duration_min",
    color_continuous_scale="Greens",
    labels={"ride_duration_min": "Duration (min)", "ride_id": "Ride ID"},
    title="Top 10 Rides with Longest Unique Durations"
)

fig_top_unique.update_layout(yaxis=dict(autorange="reversed"))
fig_top_unique.update_traces(text=top_unique["ride_duration_min"].round(1), textposition="outside")

st.plotly_chart(fig_top_unique, use_container_width=True)





# --- Section 14: Incomplete Rides ---

st.subheader("7. Number of Cancelled Ubers")

ride_id_counts = df_rides['ride_id'].value_counts()
single_rides = ride_id_counts[ride_id_counts == 1].index

# Display metric only
st.metric("Cancelled Ubers", len(single_rides))



st.header("Intermediate Analytics")



# --- Section 9: Trip Duration Heatmap by Day and Hour ---
# --- Section 9 (Revised): Interactive Heatmap of Active Ubers by Day and Minute ---
st.subheader("1. Active Ubers by Day and Minute")
st.caption("Visualize how many Ubers are active per minute on each day")

# Create exact minute column (rounded to the minute)
df_rides['minute'] = df_rides['timestamp'].dt.floor("T")  # floor to exact minute

# Create readable date column
df_rides['day'] = df_rides['minute'].dt.strftime("%Y-%m-%d")

# Create readable hour:minute string for X-axis
df_rides['minute_str'] = df_rides['minute'].dt.strftime("%H:%M")

# Group by day and minute, counting active Ubers
active_by_minute = df_rides.groupby(["day", "minute_str"]).size().reset_index(name="active_ubers")

# Create heatmap
fig9 = px.density_heatmap(
    active_by_minute,
    x="minute_str",
    y="day",
    z="active_ubers",
    color_continuous_scale="Greens",
    title="Active Ubers by Day and Minute",
    labels={"minute_str": "Time (HH:MM)", "day": "Date", "active_ubers": "Active Ubers"}
)

# Better visuals
fig9.update_layout(
    height=500,
    xaxis_nticks=24,  # adjust based on how many minutes you want to show per hour
)

st.plotly_chart(fig9, use_container_width=True)


st.header("Advanced Analytics")


import pandas as pd
import numpy as np
from scipy.stats import zscore

st.subheader("1. Anomalous Request Peaks by Zone (Every 15 Minutes)")

# Filter requests
requests = df_rides[df_rides["event_type"] == "Request"].copy()

# Group by zone and 15-minute intervals
requests["interval_15min"] = requests["timestamp"].dt.floor("15min")
zone_15min = requests.groupby(["start_location", "interval_15min"]).size().reset_index(name="request_count")

# Z-score by zone
zone_15min["zscore"] = zone_15min.groupby("start_location")["request_count"].transform(
    lambda x: zscore(x, ddof=0) if len(x) > 1 else 0
)

# Filter moderate anomalies (currently zscore > 1 to get data)
anomalies = zone_15min[zone_15min["zscore"] > 1]

# CONDITIONAL FORMATTING FUNCTION FOR ENTIRE ROW
def highlight_row(row):
    if row["request_count"] in [4]:
        return ['background-color: #ffe6e6'] * len(row)
    return [''] * len(row)

# Apply row-wise styling
styled_df = anomalies.style.apply(highlight_row, axis=1).format({"zscore": "{:.4f}"})

# Display styled table
st.dataframe(styled_df, use_container_width=True)









# --- Section 16: Suspicious Repeated Routes ---

st.subheader("2. Suspicious Routes (Repeated more than 50 times)")

route_patterns = df_rides.groupby(["start_location", "end_location"]).size().reset_index(name="count")
templates = route_patterns[route_patterns["count"] > 10].sort_values("count", ascending=False)

# Custom darker green gradient
darker_greens = [
    "#74c476",  # medium green
    "#31a354",  # darker
    "#006d2c"   # forest green
]

fig16 = px.bar(
    templates,
    x="count",
    y="start_location",
    color="count",
    orientation="h",
    color_continuous_scale=darker_greens,
    title="Suspiciously Repeated Routes"
)

fig16.update_layout(
    xaxis_title="Number of Repeats",
    yaxis_title="Start Location",
    title_font_size=20,
    height=500,
    coloraxis_showscale=False,
    margin=dict(l=80, r=40, t=60, b=40),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)'
)

st.plotly_chart(fig16, use_container_width=True)





# --- Section 2: Pickup Heatmap (Interactive) ---

st.subheader("3. Pickup Heatmap")
st.caption("3. Hover over a point to see the pickup zone and number of rides")

pickup_summary = df_rides.groupby(['pickup_lat', 'pickup_lon', 'pickup_zone']) \
                         .size().reset_index(name='count')

fig2 = px.scatter_mapbox(
    pickup_summary,
    lat='pickup_lat',
    lon='pickup_lon',
    size='count',
    color='count',
    color_continuous_scale='Greens',  # changed from 'Hot' to 'Greens'
    size_max=30,
    zoom=11,
    center=dict(lat=40.4168, lon=-3.7038),
    mapbox_style='open-street-map',
    hover_name='pickup_zone',
    hover_data={'count': True, 'pickup_lat': False, 'pickup_lon': False},
    title="Pickup Density by Location"
)

fig2.update_layout(
    margin=dict(l=10, r=10, t=40, b=10),
    height=500,
    coloraxis_showscale=True
)

st.plotly_chart(fig2, use_container_width=True)






import plotly.express as px
import streamlit as st
import pandas as pd


# -------------------------
# 4. Ride Event Volume Over a Time Range (Streamlit + Plotly)
# -------------------------

import streamlit as st
import pandas as pd
import plotly.express as px

# Título de la sección
st.subheader("4. Ride Event Volume Over a Time Range")
st.caption("Este gráfico muestra cuántos eventos ocurrieron por tipo durante el rango de tiempo seleccionado.")

# Asegurarse de que el timestamp esté redondeado a minuto
df_rides["timestamp_min"] = df_rides["timestamp"].dt.floor("min")

# Obtener los límites del tiempo
min_time = df_rides["timestamp_min"].min().to_pydatetime()
max_time = df_rides["timestamp_min"].max().to_pydatetime()

# Selector de rango de tiempo
time_range = st.slider(
    "Selecciona un rango de tiempo (resolución por minuto):",
    min_value=min_time,
    max_value=max_time,
    value=(min_time, max_time),
    format="HH:mm"
)

# Filtrar eventos que ocurrieron dentro del rango exacto (NO acumulado)
df_events_in_range = df_rides[
    (df_rides["timestamp_min"] >= time_range[0]) &
    (df_rides["timestamp_min"] <= time_range[1])
]

# Paso 1: Contar eventos por tipo
event_counts_dict = df_events_in_range['event_type'].value_counts().to_dict()

# Paso 2: Calcular Driver available como 100 - Requests
total_requests = event_counts_dict.get("Request", 0)
driver_available = max(100 - total_requests, 0)  # aseguramos que no sea negativo

# Paso 3: Reconstruir las etapas del funnel
funnel_data = {
    "Stage": ["Request", "Driver available", "Start car ride", "Ride finished"],
    "Number of events": [
        total_requests,
        driver_available,
        event_counts_dict.get("Start car ride", 0),
        event_counts_dict.get("Ride finished", 0)
    ]
}

event_counts = pd.DataFrame(funnel_data)

# Colores verde oscuro bonitos
custom_greens = ["#a1d99b", "#74c476", "#31a354", "#006d2c"]
max_val = event_counts["Number of events"].max()

event_counts["color"] = event_counts["Number of events"].apply(
    lambda x: custom_greens[int((x / max_val) * (len(custom_greens) - 1))] if max_val > 0 else custom_greens[0]
)

# Título dinámico
title_text = f"Event Counts Occurring During {time_range[0].strftime('%H:%M')} – {time_range[1].strftime('%H:%M')}"

# Gráfico de barras horizontal
fig_event_volume = px.bar(
    event_counts,
    x="Number of events",
    y="Stage",
    orientation="h",
    text="Number of events",
    color="color",
    color_discrete_map={c: c for c in event_counts["color"]},
    title=title_text
)

fig_event_volume.update_traces(
    textposition="outside",
    marker_line_color='white',
    marker_line_width=1.3
)

fig_event_volume.update_layout(
    yaxis=dict(categoryorder="array", categoryarray=["Ride finished", "Start car ride", "Driver available", "Request"]),
    showlegend=False,
    xaxis_title="Número de Eventos",
    yaxis_title="Tipo de Evento",
    margin=dict(l=80, r=40, t=60, b=40),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)'
)

# Mostrar gráfico
st.plotly_chart(fig_event_volume, use_container_width=True)





# 4. Live Traffic Surge Alerts by Zone
st.subheader("5. Live Traffic Surge Alerts by Zone")
surge_by_zone = df_alerts['zone'].value_counts().reset_index()
surge_by_zone.columns = ['zone', 'alerts']
fig6 = px.bar(
    surge_by_zone,
    x='zone',
    y='alerts',
    color='alerts',
    color_continuous_scale='Greens',
    title="Number of Traffic Surge Alerts per Zone",
    labels={'alerts': 'Alert Count', 'zone': 'Zone'}
)
fig6.update_layout(
    xaxis_tickangle=-45,
    height=400,
    coloraxis_showscale=False
)
st.plotly_chart(fig6, use_container_width=True)


# 5. Average Surge Multiplier by Zone
st.subheader("6. Average Surge Multiplier by Zone")
avg_surge = df_alerts.groupby('zone')['surge_multiplier'].mean().reset_index()
fig_surge = px.bar(
    avg_surge,
    x='zone',
    y='surge_multiplier',
    color='surge_multiplier',
    color_continuous_scale='Greens',
    title="Average Surge Multiplier per Zone",
    labels={'surge_multiplier': 'Avg Surge Multiplier', 'zone': 'Zone'}
)
fig_surge.update_layout(
    xaxis_tickangle=-45,
    height=400,
    coloraxis_showscale=False
)
st.plotly_chart(fig_surge, use_container_width=True)


# 6. Ride & Traffic Alerts per Zone - Grouped Bar Chart
st.subheader("7. Ride & Traffic Alerts per Zone")
st.caption("Direct comparison of rides and alerts in each pickup zone.")

# Grouping
rides_per_zone = df_rides.groupby('pickup_zone').size().reset_index(name='Rides')
alerts_per_zone = df_alerts.groupby('zone').size().reset_index(name='Alerts')

# Merge dataframes
merged = rides_per_zone.merge(alerts_per_zone, left_on='pickup_zone', right_on='zone')

# Melt to long format for grouped bars
df_melted = merged.melt(
    id_vars='pickup_zone',
    value_vars=['Rides', 'Alerts'],
    var_name='Type',
    value_name='Count'
)

# Custom green tones for categories
green_palette = {
    'Rides': '#31a354',    # vivid green
    'Alerts': '#a1d99b'    # light leafy green
}

fig_bar = px.bar(
    df_melted,
    x='pickup_zone',
    y='Count',
    color='Type',
    barmode='group',
    text='Count',
    color_discrete_map=green_palette,
    title="Comparison of Rides and Alerts by Zone"
)

fig_bar.update_layout(
    xaxis_title="Zone",
    yaxis_title="Count",
    title_x=0.3,
    xaxis_tickangle=-45,
    height=500,
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)'
)

st.plotly_chart(fig_bar, use_container_width=True)
