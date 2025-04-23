# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import ast
from datetime import timedelta
from scipy.stats import zscore


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






# --- Section 0: Total Rides by Day of the Week ---
st.subheader("1. Total Rides by Day of the Week")

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
    title="Total Rides by Day of the Week",
    labels={'ride_count': 'Ride Count', 'weekday': 'Day'}
)

fig0.update_layout(
    showlegend=False,
    yaxis=dict(categoryorder='array', categoryarray=days_order)
)

st.plotly_chart(fig0, use_container_width=True)




# --- Section 1: Active Rides Over Time ---
df_rides['timestamp_15min'] = df_rides['timestamp'].dt.floor('15T')
x_min = df_rides['timestamp_15min'].min()
x_max = df_rides['timestamp_15min'].max()

st.subheader("1. Active Rides Over Time")

col1, col2 = st.columns([1, 4], gap="large")

with col1:
    st.markdown("### Day of the Week")
    weekday_filter = st.radio(
        label="",
        options=days_order,
        index=0
    )

with col2:
    df_rides_filtered = df_rides[df_rides['weekday'] == weekday_filter]

    if df_rides_filtered.empty:
        st.warning(f"No data available for '{weekday_filter}'.")
    else:
        ride_counts = df_rides_filtered.groupby(
            df_rides_filtered['timestamp_15min']
        ).size().reset_index(name='ride_count')

        fig1 = px.line(
            ride_counts,
            x='timestamp_15min',
            y='ride_count',
            title=f"Active Rides Over Time - {weekday_filter}",
            labels={'timestamp_15min': 'Time', 'ride_count': 'Ride Count'},
            line_shape='spline',
            color_discrete_sequence=['#1f77b4']
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






# --- Section 2: Pickup Heatmap (Interactive) ---
st.subheader("2. Pickup Heatmap (Interactive)")
st.caption("🖱️ Hover over a point to see the pickup zone and number of rides")

pickup_summary = df_rides.groupby(['pickup_lat', 'pickup_lon', 'pickup_zone']) \
                         .size().reset_index(name='count')

fig2 = px.scatter_mapbox(
    pickup_summary,
    lat='pickup_lat',
    lon='pickup_lon',
    size='count',
    color='count',
    color_continuous_scale='Hot',
    size_max=30,
    zoom=11,
    center=dict(lat=40.4168, lon=-3.7038),
    mapbox_style='open-street-map',
    hover_name='pickup_zone',
    hover_data={'count': True, 'pickup_lat': False, 'pickup_lon': False}
)

st.plotly_chart(fig2, use_container_width=True)







# 4. Ride Event Type Distribution & Incomplete Rides- RETOCAR, NO MIRAR

# --- Sección 4.1: Funnel de eventos con filtro por hora del día ---

# Diccionario de colores (si aún no lo tienes en tu script)
event_colors = {
    'Request': '#1f77b4',
    'Driver available': '#aec7e8',
    'Start car ride': '#ff4d4d',
    'Ride finished': '#ff9999'
}

# Título de sección
st.subheader("4.1 Avance de Viajes a través de Eventos (Funnel): RETOCAR, NO MIRAR")
st.caption("Este gráfico muestra cuántos viajes llegan a cada etapa del proceso de servicio")

# Filtro por hora
st.markdown("#### ⏰ Filtrar por hora del día")
hour_range = st.slider("Selecciona un rango horario", 0, 23, (0, 23))

# Asegurarse de que exista la columna 'hour'
df_rides['hour'] = df_rides['timestamp'].dt.hour

# Filtrar el DataFrame por el rango horario seleccionado
df_filtered = df_rides[(df_rides['hour'] >= hour_range[0]) & (df_rides['hour'] <= hour_range[1])]

# Definir las etapas del funnel
funnel_steps = ['Request', 'Driver available', 'Start car ride', 'Ride finished']
funnel_counts = []

# Contar rides únicos que han pasado por cada etapa en el rango de horas
for step in funnel_steps:
    count = df_filtered[df_filtered['event_type'] == step]['ride_id'].nunique()
    funnel_counts.append({'Etapa': step, 'Cantidad de viajes': count})

# Crear DataFrame para el gráfico
funnel_df = pd.DataFrame(funnel_counts)

# Crear gráfico de barras horizontales tipo funnel
fig_funnel = px.bar(
    funnel_df,
    x='Cantidad de viajes',
    y='Etapa',
    orientation='h',
    text='Cantidad de viajes',
    color='Etapa',
    color_discrete_map=event_colors
)

fig_funnel.update_traces(textposition='outside')
fig_funnel.update_layout(
    yaxis=dict(categoryorder='array', categoryarray=funnel_steps[::-1]),
    title=f"Flujo de eventos por viaje entre las {hour_range[0]}:00 y {hour_range[1]}:59",
    showlegend=False
)

# Mostrar gráfico
st.plotly_chart(fig_funnel, use_container_width=True)






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



#pruebaaaaa cual es mejor

# 7. Ride Count vs. Surge Alerts Correlation - Mejorado con barras agrupadas
st.subheader("7. Ride & Traffic Alerts per Zone")
st.caption("Comparación directa de viajes y alertas en cada zona de recogida.")

# Agrupación
rides_per_zone = df_rides.groupby('pickup_zone').size().reset_index(name='Rides')
alerts_per_zone = df_alerts.groupby('zone').size().reset_index(name='Alerts')

# Merge
merged = rides_per_zone.merge(alerts_per_zone, left_on='pickup_zone', right_on='zone')

# Formato largo para px.bar con barras agrupadas
df_melted = merged.melt(id_vars='pickup_zone', value_vars=['Rides', 'Alerts'],
                        var_name='Tipo', value_name='Cantidad')

# Plot
fig_bar = px.bar(
    df_melted,
    x='pickup_zone',
    y='Cantidad',
    color='Tipo',
    barmode='group',
    text='Cantidad',
    title="Comparación de Viajes y Alertas por Zona"
)

fig_bar.update_layout(
    xaxis_title="Zona",
    yaxis_title="Cantidad",
    title_x=0.3,
    xaxis_tickangle=-45,
    height=500
)

st.plotly_chart(fig_bar, use_container_width=True)







# --- Sección 9: Heatmap de Duración de Viajes por Día y Hora ---

# --- Sección 9: Heatmap Interactivo de Duración de Viajes ---
st.subheader("9. Heatmap Interactivo de Duración Promedio de Viajes")
st.caption("Visualiza cuánto duran los viajes promedio por día y hora.")

# Calcular duración por sesión
sessions = df_rides.pivot_table(index="ride_id", columns="event_type", values="timestamp", aggfunc="first")
sessions["session_duration"] = (sessions["Ride finished"] - sessions["Request"]).dt.total_seconds() / 60
sessions = sessions.dropna(subset=["session_duration"])
sessions["hour"] = sessions["Request"].dt.hour
sessions["day"] = sessions["Request"].dt.strftime('%Y-%m-%d')  # para eje legible

# Agrupar y pivotear
heatmap_data = sessions.groupby(["day", "hour"]).agg(avg_duration=("session_duration", "mean")).reset_index()
fig9 = px.density_heatmap(
    heatmap_data,
    x="hour",
    y="day",
    z="avg_duration",
    color_continuous_scale="YlGnBu",
    labels={"hour": "Hora del Día", "day": "Fecha", "avg_duration": "Duración Promedio (min)"},
    title="Duración Promedio de Viajes por Día y Hora"
)
fig9.update_layout(height=400)
st.plotly_chart(fig9, use_container_width=True)




# --- Sección 10: Demanda vs Oferta por Hora (Stacked Bar) ---

# --- Sección 10: Gráfico Apilado Demanda vs Oferta ---
st.subheader("10. Demanda vs Oferta por Hora")
st.caption("Compara el número de solicitudes con conductores disponibles por hora.")

df_rides["hour"] = df_rides["timestamp"].dt.floor("H")
demand_supply = df_rides[df_rides["event_type"].isin(["Request", "Driver available"])]
demand_supply_count = demand_supply.groupby(["hour", "event_type"]).size().reset_index(name="count")

fig10 = px.bar(
    demand_supply_count,
    x="hour",
    y="count",
    color="event_type",
    barmode="stack",
    labels={"hour": "Hora", "count": "Eventos", "event_type": "Tipo de Evento"},
    title="Demanda vs Oferta Horaria"
)
fig10.update_layout(xaxis_tickformat="%H:%M", height=400)
st.plotly_chart(fig10, use_container_width=True)



# --- Sección 11: Distribución de Cancelaciones ---

# --- Sección 11: Pie Interactivo de Finalización/Cancelación ---
st.subheader("11. Tasa de Cancelaciones y Finalizaciones")
st.caption("Visualiza la proporción entre viajes completados y cancelados.")

cancel_data = df_rides["event_type"].value_counts()
cancel_data = cancel_data[cancel_data.index.isin(["Request", "Cancelled", "Ride finished"])].reset_index()
cancel_data.columns = ["event_type", "count"]

fig11 = px.pie(
    cancel_data,
    values="count",
    names="event_type",
    title="Distribución de Eventos de Viaje",
    hole=0.4
)
st.plotly_chart(fig11, use_container_width=True)



# --- Sección 12: Detección de Anomalías: Z-Score en Request ---
st.subheader("12. Picos Anómalos de Solicitudes por Zona")

requests = df_rides[df_rides["event_type"] == "Request"].copy()
requests["hour"] = requests["timestamp"].dt.floor("H")
zone_hourly = requests.groupby(["start_location", "hour"]).size().reset_index(name="request_count")
zone_hourly["zscore"] = zone_hourly.groupby("start_location")["request_count"].transform(zscore)
anomalies = zone_hourly[zone_hourly["zscore"] > 3]

fig12 = px.scatter(
    anomalies, x="hour", y="request_count", color="start_location", size="zscore",
    hover_data=["zscore"],
    title="Zonas con Solicitudes Anómalas (Z-score > 3)"
)
st.plotly_chart(fig12, use_container_width=True)



# --- Sección 13: Tiempos de Espera Largos ---


# --- Section 13: Average Wait Time between Request and Driver Available ---
st.subheader("13. Average Wait Time between Request and Driver Available")

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










# --- Sección 14: Viajes Incompletos (Inicio pero sin Final) ---

# --- Sección 14: Solicitudes sin Respuesta del Conductor ---
st.subheader("14. Viajes Solicitados pero Sin Conductor Disponible")

# Filtramos ride_id según tipo de evento
requested_ids = set(df_rides[df_rides["event_type"] == "Request"]["ride_id"])
driver_available_ids = set(df_rides[df_rides["event_type"] == "Driver available"]["ride_id"])

# Ride IDs que fueron solicitados pero nunca tuvieron driver
unanswered_ids = list(requested_ids - driver_available_ids)

# Mostrar métrica principal
st.metric("Solicitudes sin respuesta de conductor", len(unanswered_ids))

# Mostrar detalles
if unanswered_ids:
    unanswered_details = df_rides[df_rides["ride_id"].isin(unanswered_ids)]
    st.dataframe(unanswered_details)





# --- Sección 15: Solicitudes Frecuentes por Mismo Ride ID ---
st.subheader("15. Solicitudes Repetidas por Ride ID en el mismo minuto")

df_rides["minute"] = df_rides["timestamp"].dt.floor("T")
frequent_requests = df_rides[df_rides["event_type"] == "Request"] \
    .groupby(["ride_id", "minute"]).size().reset_index(name="request_count")
spam_rides = frequent_requests[frequent_requests["request_count"] > 1]

fig15 = px.histogram(spam_rides, x="request_count", nbins=10,
                     title="Distribución de Solicitudes Repetidas")
st.plotly_chart(fig15, use_container_width=True)
st.dataframe(spam_rides)



# --- Sección 16: Rutas Repetidas Sospechosas ---
st.subheader("16. Rutas Sospechosas (Repetidas más de 50 veces)")

route_patterns = df_rides.groupby(["start_location", "end_location"]).size().reset_index(name="count")
templates = route_patterns[route_patterns["count"] > 50].sort_values("count", ascending=False)

fig16 = px.bar(templates, x="count", y="start_location", color="end_location",
               orientation="h", title="Rutas Repetidas Sospechosamente")
st.plotly_chart(fig16, use_container_width=True)


st.experimental_rerun()


