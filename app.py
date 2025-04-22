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
# --- Sección 2: Pickup Intensity Map con hover interactivo ---

st.subheader("2. Pickup Heatmap (Interactive)")
st.caption("🖱️ Hover over a point to see the pickup zone and number of rides")

# Agrupar coordenadas + zona con conteo
pickup_summary = df_rides.groupby(['pickup_lat', 'pickup_lon', 'pickup_zone']) \
                         .size().reset_index(name='count')

# Crear scatter map con puntos escalados por count
fig2 = px.scatter_mapbox(
    pickup_summary,
    lat='pickup_lat',
    lon='pickup_lon',
    size='count',
    color='count',
    color_continuous_scale='Hot',  # escala de calor
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

# 7. Ride Count vs. Surge Alerts Correlation (Mejorado)
st.subheader("7. Ride Count vs. Surge Alerts Correlation")
st.caption("Este gráfico muestra la relación entre la cantidad de viajes y alertas de tráfico por zona.")

# Agrupaciones
rides_per_zone = df_rides.groupby('pickup_zone').size().reset_index(name='rides')
alerts_per_zone = df_alerts.groupby('zone').size().reset_index(name='alerts')

# Merge
merged = rides_per_zone.merge(alerts_per_zone, left_on='pickup_zone', right_on='zone')

# Gráfico mejorado
fig7 = px.scatter(
    merged,
    x='rides',
    y='alerts',
    size='rides',
    color='alerts',
    hover_name='pickup_zone',
    hover_data={'rides': True, 'alerts': True, 'pickup_zone': False},
    text='pickup_zone',
    color_continuous_scale='Blues',
    title="Relación entre Viajes y Alertas de Tráfico por Zona"
)

fig7.update_traces(marker=dict(opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
fig7.update_layout(
    xaxis_title="Cantidad de viajes",
    yaxis_title="Cantidad de alertas",
    title_x=0.3,
    height=600,
    showlegend=False
)

st.plotly_chart(fig7, use_container_width=True)


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



#o esteeee
# --- Gráfico de barras agrupadas + ratio ---
st.subheader("7.1 Comparación de Viajes y Alertas por Zona")
st.caption("Análisis conjunto del volumen de viajes y alertas, además del ratio de alertas por viaje.")

# Agrupaciones base
rides_per_zone = df_rides.groupby('pickup_zone').size().reset_index(name='Rides')
alerts_per_zone = df_alerts.groupby('zone').size().reset_index(name='Alerts')

# Merge y cálculo del ratio
merged = rides_per_zone.merge(alerts_per_zone, left_on='pickup_zone', right_on='zone')
merged['Alert_Ride_Ratio'] = merged['Alerts'] / merged['Rides']

# Formato largo
df_melted = merged.melt(
    id_vars=['pickup_zone', 'Alert_Ride_Ratio'],
    value_vars=['Rides', 'Alerts'],
    var_name='Tipo',
    value_name='Cantidad'
)

# Gráfico de barras agrupadas
fig_grouped = px.bar(
    df_melted,
    x='pickup_zone',
    y='Cantidad',
    color='Tipo',
    barmode='group',
    text='Cantidad',
    title="Viajes vs. Alertas por Zona"
)
fig_grouped.update_layout(
    xaxis_title="Zona",
    yaxis_title="Cantidad",
    xaxis_tickangle=-45,
    height=500
)
st.plotly_chart(fig_grouped, use_container_width=True)

# Mostrar zonas con ratio alto
st.markdown("#### 🔍 Zonas con mayor ratio de alertas por viaje")
top_ratios = merged.sort_values(by='Alert_Ride_Ratio', ascending=False)[['pickup_zone', 'Rides', 'Alerts', 'Alert_Ride_Ratio']]
st.dataframe(top_ratios.round(2).rename(columns={
    'pickup_zone': 'Zona',
    'Rides': 'Viajes',
    'Alerts': 'Alertas',
    'Alert_Ride_Ratio': 'Ratio Alertas/Viaje'
}))




#o finalmente este
# --- Heatmap de viajes y alertas por zona ---
st.subheader("7.2 Heatmap: Viajes y Alertas por Zona")
st.caption("Visualización intensiva por zona para detectar concentración de eventos.")

# Preparar para heatmap
heatmap_df = merged[['pickup_zone', 'Rides', 'Alerts']].set_index('pickup_zone')

# Crear heatmap con plotly
import plotly.figure_factory as ff

heatmap_data = heatmap_df.T  # Transponer para que zonas estén en columnas

fig_heat = ff.create_annotated_heatmap(
    z=heatmap_data.values,
    x=heatmap_data.columns.tolist(),
    y=heatmap_data.index.tolist(),
    colorscale='Blues',
    showscale=True,
    annotation_text=heatmap_data.values.round(0).astype(str)
)

fig_heat.update_layout(
    title="Heatmap de Rides y Alertas por Zona",
    xaxis_title="Zona",
    yaxis_title="Tipo",
    height=500
)

st.plotly_chart(fig_heat, use_container_width=True)





# 8. Hourly Ride Distribution
st.subheader("8. Hourly Ride Distribution")
df_rides['hour'] = df_rides['timestamp'].dt.hour
fig8 = px.histogram(df_rides, x='hour', nbins=24)
st.plotly_chart(fig8)
