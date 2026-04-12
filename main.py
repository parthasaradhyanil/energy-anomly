"""
main.py — Energy Anomaly Detection Dashboard
Run with: streamlit run main.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import (
    generate_time_index,
    simulate_circuit,
    run_detection,
    compute_summary,
)

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Energy Anomaly Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS — dark industrial theme
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0d1117; color: #e6edf3; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.75rem; }
    [data-testid="stMetricValue"] { color: #58a6ff; font-weight: 700; }
    [data-testid="stMetricDelta"]  { color: #3fb950; }

    /* Anomaly metric delta override */
    .anomaly-metric [data-testid="stMetricValue"] { color: #f85149; }

    /* Section headings */
    h1 { color: #58a6ff !important; letter-spacing: -0.5px; }
    h2, h3 { color: #e6edf3 !important; }

    /* Divider */
    hr { border-color: #30363d; }

    /* Buttons */
    .stButton > button {
        background: #238636;
        color: #fff;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        transition: background 0.2s;
    }
    .stButton > button:hover { background: #2ea043; }

    /* Slider label */
    .stSlider label { color: #8b949e; }

    /* Select box */
    .stSelectbox label { color: #8b949e; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SESSION STATE — preserve random seed across reruns
# ─────────────────────────────────────────────────────────────
if "seed" not in st.session_state:
    st.session_state.seed = 42


# ─────────────────────────────────────────────────────────────
# SIDEBAR — controls
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ Controls")
    st.markdown("---")

    circuit_choice = st.selectbox(
        "Circuit",
        ["All Circuits", "Light", "Fan/Motor", "Heavy Load"],
        help="Select which circuit to inspect in detail."
    )

    detection_method = st.selectbox(
        "Detection Method",
        ["Combined", "Moving Average", "Z-Score"],
        help="Algorithm used to flag anomalies."
    )

    sensitivity = st.slider(
        "Anomaly Sensitivity",
        min_value=1.0, max_value=5.0, value=2.5, step=0.1,
        help="Lower = more sensitive (more anomalies flagged)."
    )

    cost_per_kwh = st.slider(
        "Cost per kWh (USD)",
        min_value=0.05, max_value=0.50, value=0.12, step=0.01,
        help="Local electricity rate for cost estimation."
    )

    st.markdown("---")

    if st.button("🔄 Regenerate Data", use_container_width=True):
        st.session_state.seed = st.session_state.seed + 1

    st.markdown("---")
    st.markdown("""
    **Anomaly Types Detected:**
    - 🔴 **Spike** — sudden current surge
    - 🟠 **Drift** — gradual creep upward
    - 🟡 **Off-hours** — usage at unusual times
    """)

    st.markdown("---")
    st.caption("Detection Methods:")
    st.caption("**Moving Average** — flags deviations from rolling mean")
    st.caption("**Z-Score** — flags values beyond N standard deviations")
    st.caption("**Combined** — union of both methods")


# ─────────────────────────────────────────────────────────────
# DATA GENERATION
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data(seed: int, sensitivity: float, method: str, cost: float):
    """Generate and cache all circuit data."""
    time_index = generate_time_index(hours=24, freq_minutes=5)
    circuits = ["Light", "Fan/Motor", "Heavy Load"]
    all_data = {}

    for i, name in enumerate(circuits):
        df = simulate_circuit(name, time_index, seed=seed + i)
        df = run_detection(df, sensitivity=sensitivity, method=method)
        all_data[name] = df

    return all_data


with st.spinner("Generating circuit data..."):
    data = load_data(
        st.session_state.seed,
        sensitivity,
        detection_method,
        cost_per_kwh
    )


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("# ⚡ Energy Anomaly Detection Dashboard")
st.markdown("Real-time simulation of household electrical circuits with statistical anomaly detection.")
st.markdown("---")


# ─────────────────────────────────────────────────────────────
# HELPER: build a Plotly time-series figure for one circuit
# ─────────────────────────────────────────────────────────────
CIRCUIT_COLORS = {
    "Light":      "#58a6ff",   # blue
    "Fan/Motor":  "#3fb950",   # green
    "Heavy Load": "#e3b341",   # amber
}


def build_circuit_figure(df: pd.DataFrame, circuit_name: str) -> go.Figure:
    """Return a Plotly figure for a single circuit with anomalies highlighted."""
    color = CIRCUIT_COLORS.get(circuit_name, "#58a6ff")
    normal    = df[~df["detected"]]
    anomalies = df[df["detected"]]

    fig = go.Figure()

    # Normal signal line
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["current_A"],
        mode="lines",
        name="Current (A)",
        line=dict(color=color, width=1.5),
        hovertemplate="%{x|%H:%M} — %{y:.2f} A<extra></extra>",
    ))

    # Anomaly markers
    if len(anomalies) > 0:
        fig.add_trace(go.Scatter(
            x=anomalies["timestamp"],
            y=anomalies["current_A"],
            mode="markers",
            name="Anomaly",
            marker=dict(color="#f85149", size=8, symbol="circle",
                        line=dict(color="#ff7b72", width=1.5)),
            hovertemplate="⚠️ %{x|%H:%M} — %{y:.2f} A<extra>ANOMALY</extra>",
        ))

    fig.update_layout(
        title=dict(text=f"<b>{circuit_name}</b>", font=dict(color=color, size=15)),
        paper_bgcolor="#161b22",
        plot_bgcolor="#0d1117",
        font=dict(color="#8b949e", size=11),
        xaxis=dict(
            showgrid=True, gridcolor="#21262d", gridwidth=1,
            title="Time of Day", titlefont=dict(color="#8b949e"),
            tickformat="%H:%M",
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#21262d", gridwidth=1,
            title="Current (A)", titlefont=dict(color="#8b949e"),
        ),
        legend=dict(
            bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
            font=dict(color="#e6edf3"),
        ),
        margin=dict(t=45, b=30, l=50, r=20),
        height=280,
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────────────────────
# SUMMARY METRICS — aggregate across all circuits
# ─────────────────────────────────────────────────────────────
summaries = {
    name: compute_summary(df, cost_per_kwh=cost_per_kwh)
    for name, df in data.items()
}

total_anomalies = sum(s["total_anomalies"] for s in summaries.values())
peak_overall    = max(s["peak_current_A"]  for s in summaries.values())
avg_overall     = round(
    sum(s["avg_current_A"] for s in summaries.values()) / len(summaries), 2
)
total_cost      = round(sum(s["estimated_cost"]  for s in summaries.values()), 3)
total_energy    = round(sum(s["energy_kwh"]      for s in summaries.values()), 2)

st.markdown("### 📊 System Overview")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("⚠️ Total Anomalies", total_anomalies)
with col2:
    st.metric("🔺 Peak Current", f"{peak_overall} A")
with col3:
    st.metric("〰️ Average Current", f"{avg_overall} A")
with col4:
    st.metric("⚡ Energy Used", f"{total_energy} kWh")
with col5:
    st.metric("💰 Est. Cost", f"${total_cost}")

st.markdown("---")


# ─────────────────────────────────────────────────────────────
# CIRCUIT PLOTS
# ─────────────────────────────────────────────────────────────
circuits_to_show = (
    ["Light", "Fan/Motor", "Heavy Load"]
    if circuit_choice == "All Circuits"
    else [circuit_choice]
)

if circuit_choice == "All Circuits":
    st.markdown("### 📈 All Circuits — Time Series")
    for name in circuits_to_show:
        st.plotly_chart(
            build_circuit_figure(data[name], name),
            use_container_width=True,
            config={"displayModeBar": False},
        )

else:
    # ── Detail view for a single circuit ─────────────────────
    df_sel = data[circuit_choice]
    st.markdown(f"### 📈 {circuit_choice} Circuit — Detail View")

    # Per-circuit metrics
    s = summaries[circuit_choice]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Anomalies",    s["total_anomalies"])
    m2.metric("Peak",         f"{s['peak_current_A']} A")
    m3.metric("Average",      f"{s['avg_current_A']} A")
    m4.metric("Est. Cost",    f"${s['estimated_cost']}")

    # Main chart — taller for detail view
    fig = build_circuit_figure(df_sel, circuit_choice)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Anomaly distribution by hour
    st.markdown("#### 🕐 Anomalies by Hour of Day")
    anomaly_by_hour = (
        df_sel[df_sel["detected"]]
        .assign(hour=df_sel["timestamp"].dt.hour)
        .groupby("hour")
        .size()
        .reindex(range(24), fill_value=0)
        .reset_index()
    )
    anomaly_by_hour.columns = ["hour", "count"]

    bar_fig = go.Figure(go.Bar(
        x=anomaly_by_hour["hour"],
        y=anomaly_by_hour["count"],
        marker_color="#f85149",
        hovertemplate="Hour %{x}:00 — %{y} anomalies<extra></extra>",
    ))
    bar_fig.update_layout(
        paper_bgcolor="#161b22", plot_bgcolor="#0d1117",
        font=dict(color="#8b949e"),
        xaxis=dict(title="Hour of Day", showgrid=False,
                   tickmode="linear", dtick=2),
        yaxis=dict(title="Anomaly Count", showgrid=True, gridcolor="#21262d"),
        margin=dict(t=10, b=30, l=50, r=20),
        height=220,
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    # Raw data table
    with st.expander("🗂️ View Raw Data"):
        display_df = df_sel[["timestamp", "current_A", "detected"]].copy()
        display_df.columns = ["Timestamp", "Current (A)", "Anomaly Detected"]
        display_df["Current (A)"] = display_df["Current (A)"].round(3)
        st.dataframe(display_df, use_container_width=True, height=300)

        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"{circuit_choice.lower().replace('/', '_')}_data.csv",
            mime="text/csv",
        )


# ─────────────────────────────────────────────────────────────
# COMBINED ANOMALY OVERVIEW (always shown at bottom)
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔴 Anomaly Event Log")

all_anomalies = pd.concat([
    df[df["detected"]][["timestamp", "current_A", "circuit"]]
    for df in data.values()
]).sort_values("timestamp").reset_index(drop=True)

if len(all_anomalies) == 0:
    st.info("No anomalies detected. Try lowering the sensitivity slider.")
else:
    all_anomalies.columns = ["Timestamp", "Current (A)", "Circuit"]
    all_anomalies["Current (A)"] = all_anomalies["Current (A)"].round(3)
    all_anomalies["Time"] = all_anomalies["Timestamp"].dt.strftime("%H:%M")
    all_anomalies = all_anomalies[["Time", "Circuit", "Current (A)"]]

    st.dataframe(
        all_anomalies,
        use_container_width=True,
        height=250,
    )

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "⚡ Energy Anomaly Detection Dashboard · "
    "Simulated data · Detection: Moving Average + Z-Score · "
    "Built with Streamlit + Plotly"
)
