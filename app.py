# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# Set layout
st.set_page_config(page_title="Uber Real-Time Dashboard", layout="wide")
st.title("🚕 Uber Real-Time Analytics Dashboard")

# Load data (you can change these paths as needed)
ride_path = "ride_events.json"
traffic_path = "traffic_surge_alerts.json"

# Load JSON data
df_rides = pd.read_json(ride_path)
df_alerts = pd.read_json(traffic_path)

# Convert timestamp columns to datetime
df_rides['timestamp'] = pd.to_datetime(df_rides['timestamp'])
df_rides['pickup_time'] = pd.to_datetime(df_rides['pickup_time'])
df_rides['dropoff_time'] = pd.to_datetime(df_rides['dropoff_time'])

# 1. Active Rides Over Time
st.subheader("1. Active Rides Over Time")
ride_counts = df_rides.groupby(df_rides['timestamp'].dt.floor('min')).size().reset_index(name='ride_count')
fig1 = px.line(ride_counts, x='timestamp', y='ride_count')
st.plotly_chart(fig1)

# 2. Pickup Heatmap
st.subheader("2. Pickup Heatmap")
fig2 = px.density_mapbox(df_rides, lat='pickup_lat', lon='pickup_lon', radius=10,
                         center=dict(lat=40.7, lon=-73.9), zoom=10,
                         mapbox_style="open-street-map")
st.plotly_chart(fig2)

# 3. Top 10 Pickup Zones
st.subheader("3. Top 10 Pickup Zones")
top_zones = df_rides['pickup_zone'].value_counts().nlargest(10).reset_index()
top_zones.columns = ['zone', 'count']
fig3 = px.bar(top_zones, x='zone', y='count')
st.plotly_chart(fig3)

# 4. Ride Status Distribution
st.subheader("4. Ride Status Distribution")
fig4 = px.pie(df_rides, names='status')
st.plotly_chart(fig4)

# 5. Average Ride Duration per Zone
st.subheader("5. Average Ride Duration per Zone")
df_rides['duration_min'] = (df_rides['dropoff_time'] - df_rides['pickup_time']).dt.total_seconds() / 60
avg_duration = df_rides.groupby('pickup_zone')['duration_min'].mean().nlargest(10).reset_index()
fig5 = px.bar(avg_duration, x='pickup_zone', y='duration_min')
st.plotly_chart(fig5)

# 6. Live Traffic Surge Alerts by Zone
st.subheader("6. Live Traffic Surge Alerts by Zone")
surge_by_zone = df_alerts['zone'].value_counts().reset_index()
surge_by_zone.columns = ['zone', 'alerts']
fig6 = px.bar(surge_by_zone, x='zone', y='alerts')
st.plotly_chart(fig6)

# 7. Rides vs. Surge Alerts Correlation
st.subheader("7. Rides vs. Surge Alerts Correlation")
merged = df_rides.groupby('pickup_zone').size().reset_index(name='rides')     .merge(df_alerts.groupby('zone').size().reset_index(name='alerts'),
           left_on='pickup_zone', right_on='zone')
fig7 = px.scatter(merged, x='rides', y='alerts', text='pickup_zone')
st.plotly_chart(fig7)

# 8. Hourly Ride Distribution
st.subheader("8. Hourly Ride Distribution")
df_rides['hour'] = df_rides['timestamp'].dt.hour
fig8 = px.histogram(df_rides, x='hour', nbins=24)
st.plotly_chart(fig8)
