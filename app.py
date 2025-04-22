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


#previo
# --- Sección 0: Total de Rides por Día de la Semana ---
st.subheader("0. Total de Pedidos por Día de la Semana")

df_rides['weekday'] = df_rides['day_of_week']
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
rides_by_day = df_rides['weekday'].value_counts().reindex(days_order).reset_index()
rides_by_day.columns = ['weekday', 'ride_count']

fig0 = px.bar(
    rides_by_day,
    x='ride_count',
    y='weekday',
    orientation='h',
    color='weekday',
    color_discrete_map={
        'Monday': '#1f77b4',
        'Tuesday': '#ff7f0e',
        'Wednesday': '#2ca02c',
        'Thursday': '#d62728',
        'Friday': '#9467bd',
        'Saturday': '#8c564b',
        'Sunday': '#e377c2'
    },
    title="Cantidad Total de Rides por Día de la Semana",
    labels={'ride_count': 'Cantidad de viajes', 'weekday': 'Día'}
)

fig0.update_layout(
    showlegend=False,
    yaxis=dict(categoryorder='array', categoryarray=days_order)
)

st.plotly_chart(fig0, use_container_width=True)




# 1. Active Rides Over Time

# --- Sección 1: Active Rides Over Time (una línea por selección de día) ---

df_rides['weekday'] = df_rides['day_of_week']
df_rides['timestamp_15min'] = df_rides['timestamp'].dt.floor('15T')
x_min = df_rides['timestamp_15min'].min()
x_max = df_rides['timestamp_15min'].max()

st.subheader("1. Active Rides Over Time")

col1, col2 = st.columns([1, 4], gap="large")

with col1:
    st.markdown("### Día de la semana")
    weekday_filter = st.radio(
        label="",
        options=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        index=0
    )

with col2:
    df_rides_filtered = df_rides[df_rides['weekday'] == weekday_filter]

    if df_rides_filtered.empty:
        st.warning(f"No hay datos para '{weekday_filter}'.")
    else:
        ride_counts = df_rides_filtered.groupby(
            df_rides_filtered['timestamp_15min']
        ).size().reset_index(name='ride_count')

        fig1 = px.line(
            ride_counts,
            x='timestamp_15min',
            y='ride_count',
            title=f"Active Rides Over Time - {weekday_filter}",
            labels={'timestamp_15min': 'Hora', 'ride_count': 'Cantidad de viajes'},
            line_shape='spline',
            color_discrete_sequence=['#1f77b4']  # Color fijo si quieres uno azul
        )

        fig1.update_traces(line=dict(width=2))
        fig1.update_layout(
            hovermode='x unified',
            xaxis=dict(
                tickformat='%H:%M',
                showgrid=False,
                range=[x_min, x_max]
            ),
            yaxis=dict(showgrid=True)
        )

        st.plotly_chart(fig1, use_container_width=True)
















# 2. Pickup Heatmap
# --- Sección 2: Pickup Heatmap con info interactiva al pasar el ratón ---

# --- Sección 2: Pickup Heatmap con puntos más visibles ---

st.subheader("2. Pickup Heatmap")
st.caption("🖱️ Hover over a point to see the pickup zone and ride count")

# Agrupar por coordenadas + zona
pickup_summary = df_rides.groupby(['pickup_lat', 'pickup_lon', 'pickup_zone']) \
                         .size().reset_index(name='count')

# Crear heatmap con escala más visible
fig2 = px.density_mapbox(
    pickup_summary,
    lat='pickup_lat',
    lon='pickup_lon',
    z='count',
    radius=12,  # más pequeño para definición
    center=dict(lat=40.4168, lon=-3.7038),
    zoom=11,
    mapbox_style="open-street-map",
    hover_data={
        'pickup_zone': True,
        'count': True,
        'pickup_lat': False,
        'pickup_lon': False
    },
    color_continuous_scale='Hot',  # puedes probar también 'Inferno', 'Viridis', etc.
    zmax=pickup_summary['count'].max()  # asegurar buen contraste
)

st.plotly_chart(fig2, use_container_width=True)






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
