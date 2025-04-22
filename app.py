# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import ast
from datetime import timedelta

# Set layout
st.set_page_config(page_title="Uber Real-Time Dashboard", layout="wide")
st.title("🚕 Uber Real-Time Analytics Dashboard")

# Load data
ride_path = "ride_events.json"
traffic_path = "traffic_surge_alerts.json"

# Check if files exist
if not os.path.exists(ride_path):
    st.error(f"Ride events file not found: {ride_path}")
    st.stop()
if not os.path.exists(traffic_path):
    st.error(f"Traffic alerts file not found: {traffic_path}")
    st.stop()

# Load JSON data
df_rides = pd.read_json(ride_path)

# Transform ride data
if 'timestamp_event' in df_rides.columns:
    df_rides['timestamp'] = pd.to_datetime(df_rides['timestamp_event'])
    df_rides['pickup_time'] = df_rides['timestamp']
    df_rides['dropoff_time'] = df_rides['pickup_time'] + timedelta(minutes=5)
    
    # Fix start_coordinates from string to list
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

# 1. Active Rides Over Time

# --- Sección: 1. Active Rides Over Time (con filtro por día y scatterplot) ---

# Asegurar que la columna 'weekday' venga del JSON directamente
df_rides['weekday'] = df_rides['day_of_week']

# Filtro lateral SOLO para este gráfico
weekday_filter = st.sidebar.selectbox(
    "Filtrar por día de la semana (solo afecta al gráfico 1)",
    options=['Todos', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
)

# Copia filtrada del dataset
df_rides_filtered = df_rides.copy()
if weekday_filter != 'Todos':
    df_rides_filtered = df_rides[df_rides['weekday'] == weekday_filter]

# Título de sección
st.subheader("1. Active Rides Over Time (Scatter View)")

# Mostrar gráfico o aviso si no hay datos
if df_rides_filtered.empty:
    st.warning(f"No hay datos disponibles para '{weekday_filter}'.")
else:
    # Agrupar por intervalos de 15 minutos
    ride_counts = df_rides_filtered.groupby(df_rides_filtered['timestamp'].dt.floor('15T')) \
                                   .size().reset_index(name='ride_count')

    # Crear scatterplot
    fig1 = px.scatter(
        ride_counts,
        x='timestamp',
        y='ride_count',
        title="Active Rides Over Time",
        labels={'timestamp': 'Hora', 'ride_count': 'Cantidad de viajes'}
    )

    # Mostrar el gráfico
    st.plotly_chart(fig1)









# 2. Pickup Heatmap
st.subheader("2. Pickup Heatmap")
fig2 = px.density_mapbox(df_rides, lat='pickup_lat', lon='pickup_lon', radius=10,
                         center=dict(lat=40.4168, lon=-3.7038), zoom=11,
                         mapbox_style="open-street-map")
st.plotly_chart(fig2)

# 3. Top 10 Pickup Zones
st.subheader("3. Top 10 Pickup Zones")
top_zones = df_rides['pickup_zone'].value_counts().nlargest(10).reset_index()
top_zones.columns = ['zone', 'count']
fig3 = px.bar(top_zones, x='zone', y='count')
st.plotly_chart(fig3)

# 4. Ride Event Type Distribution & Incomplete Rides
st.subheader("4. Distribución de Tipos de Evento y Viajes Incompletos")

# Pie chart de tipos de eventos
fig4 = px.pie(df_rides, names='status', title="Distribución de Tipos de Evento")
st.plotly_chart(fig4)

# Viajes incompletos (que no tienen 'Start car ride' ni 'Ride finished')
incomplete_rides = df_rides.groupby('ride_id')['event_type'].apply(set)
incomplete = incomplete_rides[incomplete_rides.apply(lambda x: 'Start car ride' not in x and 'Ride finished' not in x)]
st.markdown(f"**Viajes solicitados pero nunca iniciados:** {len(incomplete)}")

# 5. Simulated Ride Duration by Zone
st.subheader("5. Simulated Ride Duration per Zone")
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

# 6.1 Promedio de Surge Multiplier por Zona
st.subheader("6.1 Promedio de Surge Multiplier por Zona")
avg_surge = df_alerts.groupby('zone')['surge_multiplier'].mean().reset_index()
fig_surge = px.bar(avg_surge, x='zone', y='surge_multiplier')
st.plotly_chart(fig_surge)

# 7. Ride Count vs. Surge Alerts Correlation
st.subheader("7. Ride Count vs. Surge Alerts Correlation")
merged = df_rides.groupby('pickup_zone').size().reset_index(name='rides') \
    .merge(df_alerts.groupby('zone').size().reset_index(name='alerts'),
           left_on='pickup_zone', right_on='zone')
fig7 = px.scatter(merged, x='rides', y='alerts', text='pickup_zone')
st.plotly_chart(fig7)

# 8. Hourly Ride Distribution
st.subheader("8. Hourly Ride Distribution")
df_rides['hour'] = df_rides['timestamp'].dt.hour
fig8 = px.histogram(df_rides, x='hour', nbins=24)
st.plotly_chart(fig8)
