
# 🚕 Uber Real-Time Analytics Dashboard

This project provides a real-time analytics dashboard for ride-sharing and traffic surge data in Madrid. It simulates Uber-style data pipelines using Streamlit for visualization and Apache Spark for ingestion from Azure Event Hub. Data is stored in JSON/Avro formats and transformed for real-time and historical analysis.


## 📁 Repository Structure

```
.
├── app.py
├── azure_connection.py
├── milestone_1.ipynb
├── milestone_2.1.ipynb
├── ride_events.json
├── traffic_surge_alerts.json
├── ride_events.avro
├── traffic_surge_alerts.avro
├── requirements.txt
└── README.md
```

---

## 🗂️ File Descriptions

- **`app.py`**: Main Streamlit app containing all dashboard visualizations (ride volumes, heatmaps, demand/supply, anomalies, etc.).
- **`azure_connection.py`**: Defines Spark session and streaming pipeline from Azure Event Hub, using Avro data format.
- **`milestone_1.ipynb`**: Initial data exploration and cleaning for ride events and traffic alerts.
- **`milestone_2.1.ipynb`**: Streaming design with windowing (tumbling, hopping, session-based) using Spark.
- **`ride_events.json`**: Cleaned and flattened ride event data used in the dashboard.
- **`traffic_surge_alerts.json`**: Flattened traffic alert data including surge multipliers by zone.
- **`ride_events.avro`**: Simulated raw ride data in Avro format from Event Hub.
- **`traffic_surge_alerts.avro`**: Simulated raw traffic alert data in Avro format.
- **`requirements.txt`**: List of required Python libraries (Streamlit, Pandas, Plotly, etc.).

---

## 🚀 How to Run the Dashboard

### 1. Clone the repository
```bash
git clone https://github.com/your-username/uber-analytics-dashboard.git
cd uber-analytics-dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Streamlit app
```bash
streamlit run app.py
```

> Ensure `ride_events.json` and `traffic_surge_alerts.json` are in the root folder before running.

---

