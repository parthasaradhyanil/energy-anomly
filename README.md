# ⚡ Energy Anomaly Detection Dashboard

A Streamlit web app that simulates electrical energy usage across 3 household circuits, detects anomalies using statistical methods, and visualises everything in an interactive dark-themed dashboard.

---

## 🖥️ Features

| Feature | Detail |
|---|---|
| **3 circuit types** | Light, Fan/Motor, Heavy Load |
| **Realistic patterns** | Morning low → evening peak |
| **Two detection algorithms** | Moving Average + Z-Score |
| **Anomaly injection** | Spikes, drift, off-hours activity |
| **Interactive controls** | Sensitivity slider, circuit selector, method selector |
| **Cost estimation** | Energy (kWh) + $ cost per configurable rate |
| **Export** | Download circuit data as CSV |
| **One-click regenerate** | New random seed each press |

---

## 🚀 How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/your-username/energy-anomaly-dashboard.git
cd energy-anomaly-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run main.py
```

The app opens at `http://localhost:8501`.

---

## ☁️ Deploy to Streamlit Cloud

1. Push repo to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, branch `main`, file `main.py`.
4. Click **Deploy** — no extra config needed.

---

## 🔬 How Anomaly Detection Works

### Moving Average
```
rolling_mean  = signal.rolling(window).mean()
rolling_std   = signal.rolling(window).std()
anomaly       = |value − rolling_mean| > sensitivity × rolling_std
```
Catches local deviations — good for spikes and sudden shifts.

### Z-Score
```
z = (value − global_mean) / global_std
anomaly = |z| > sensitivity
```
Catches global outliers — good for extreme values anywhere in the day.

### Combined (default)
Union of both methods. Maximises recall at the cost of some precision.

---

## 📁 Project Structure

```
energy-anomaly-dashboard/
├── main.py          # Streamlit UI + Plotly charts
├── utils.py         # Data simulation + anomaly logic
├── requirements.txt
├── README.md
└── guidelines.md
```

---

## 🔌 Extending to Real IoT Data

Replace `simulate_circuit()` in `utils.py` with a real data source:

```python
# Example: fetch from ESP32 over HTTP
import requests

def fetch_esp32_data(ip: str) -> pd.DataFrame:
    r = requests.get(f"http://{ip}/data.json")
    return pd.DataFrame(r.json())
```

Pass the resulting DataFrame into `run_detection()` — everything else stays the same.

---

## 📜 Anomaly Types Simulated

| Type | Description |
|---|---|
| **Spike** | Sudden large current surge |
| **Drift** | Gradual upward creep over a window |
| **Off-hours** | Unusual activity between midnight–5am |

---

## ⚙️ Controls Reference

| Control | Effect |
|---|---|
| Circuit selector | Focus on one circuit or view all |
| Detection method | Algorithm used to flag anomalies |
| Sensitivity slider | 1 = very sensitive · 5 = strict |
| Cost per kWh | Adjusts cost estimation |
| Regenerate button | New random data with same settings |
