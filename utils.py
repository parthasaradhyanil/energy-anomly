"""
utils.py — Data simulation and anomaly detection logic
Energy Anomaly Detection Dashboard
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ─────────────────────────────────────────────────────────────
# DATA SIMULATION
# ─────────────────────────────────────────────────────────────

def generate_time_index(hours: int = 24, freq_minutes: int = 5) -> pd.DatetimeIndex:
    """Generate a time index for one day at given frequency."""
    start = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    periods = int((hours * 60) / freq_minutes)
    return pd.date_range(start=start, periods=periods, freq=f"{freq_minutes}min")


def base_load_pattern(time_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Create a realistic 24-hour load pattern.
    - Low usage: midnight → early morning
    - Rising: 6am → 9am
    - Moderate: 9am → 5pm
    - Peak: 5pm → 10pm
    - Falling: 10pm → midnight
    """
    hours = time_index.hour + time_index.minute / 60.0
    pattern = (
        0.3                                          # base load
        + 0.4 * np.exp(-((hours - 7.5) ** 2) / 4)  # morning ramp
        + 0.6 * np.exp(-((hours - 19.0) ** 2) / 6) # evening peak
        + 0.2 * np.exp(-((hours - 12.5) ** 2) / 3) # midday bump
    )
    return pattern


def simulate_circuit(
    name: str,
    time_index: pd.DatetimeIndex,
    seed: int = 42,
    anomaly_rate: float = 0.03
) -> pd.DataFrame:
    """
    Simulate current (Amps) for a named circuit type.

    Circuit profiles:
    - Light:      low, stable (0.5–2 A)
    - Fan/Motor:  moderate with oscillations (2–6 A)
    - Heavy Load: irregular, high spikes (5–15 A)
    """
    rng = np.random.default_rng(seed)
    n = len(time_index)
    base = base_load_pattern(time_index)

    if name == "Light":
        scale, offset, noise_std = 1.5, 0.5, 0.15
        osc = 0.0
    elif name == "Fan/Motor":
        scale, offset, noise_std = 3.5, 2.0, 0.4
        # Simulate motor oscillation (cycling on/off)
        osc = 0.8 * np.sin(2 * np.pi * np.arange(n) / 12)
    else:  # Heavy Load
        scale, offset, noise_std = 8.0, 4.5, 0.8
        osc = 0.0

    signal = offset + scale * base + osc
    noise = rng.normal(0, noise_std, n)
    current = np.clip(signal + noise, 0, None)

    # ── Inject synthetic anomalies ──────────────────────────
    current, anomaly_labels = inject_anomalies(
        current, time_index, rng, anomaly_rate, name
    )

    df = pd.DataFrame({
        "timestamp": time_index,
        "current_A": current,
        "anomaly": anomaly_labels,
        "circuit": name,
    })
    return df


def inject_anomalies(
    current: np.ndarray,
    time_index: pd.DatetimeIndex,
    rng: np.random.Generator,
    rate: float,
    circuit_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Inject three types of anomalies into the signal:
    1. Spike  — sudden large jump in current
    2. Drift  — gradual upward creep over a window
    3. Off-hours usage — activity during typically idle times
    """
    n = len(current)
    labels = np.zeros(n, dtype=int)  # 0 = normal, 1 = anomaly
    current = current.copy()

    n_anomalies = max(1, int(n * rate))

    # 1. Spikes
    spike_idx = rng.choice(n, size=max(1, n_anomalies // 2), replace=False)
    for idx in spike_idx:
        magnitude = rng.uniform(3, 8) * current[idx]
        current[idx] = min(current[idx] + magnitude, 50)
        labels[idx] = 1

    # 2. Drift — pick a random window and ramp up
    drift_start = rng.integers(n // 4, 3 * n // 4)
    drift_len = rng.integers(5, 15)
    drift_end = min(drift_start + drift_len, n)
    drift = np.linspace(0, rng.uniform(2, 5), drift_end - drift_start)
    current[drift_start:drift_end] += drift
    labels[drift_start:drift_end] = 1

    # 3. Off-hours usage (midnight–5am unusual activity)
    hours = time_index.hour
    off_hours_mask = hours < 5
    off_hours_idx = np.where(off_hours_mask)[0]
    if len(off_hours_idx) > 2:
        selected = rng.choice(off_hours_idx, size=min(3, len(off_hours_idx)), replace=False)
        for idx in selected:
            current[idx] += rng.uniform(2, 5)
            labels[idx] = 1

    return current, labels


# ─────────────────────────────────────────────────────────────
# ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────

def detect_moving_average(
    series: pd.Series,
    window: int = 12,
    threshold_multiplier: float = 2.5
) -> pd.Series:
    """
    Moving average anomaly detection.
    An anomaly is flagged when |value − rolling_mean| > threshold_multiplier × rolling_std.

    Args:
        series: time-series of current values
        window: rolling window size (number of data points)
        threshold_multiplier: sensitivity — lower = more sensitive

    Returns:
        Boolean Series, True where anomaly detected
    """
    rolling_mean = series.rolling(window=window, center=True, min_periods=1).mean()
    rolling_std  = series.rolling(window=window, center=True, min_periods=1).std().fillna(1)
    deviation    = (series - rolling_mean).abs()
    threshold    = threshold_multiplier * rolling_std
    return deviation > threshold


def detect_zscore(
    series: pd.Series,
    threshold: float = 3.0
) -> pd.Series:
    """
    Z-score anomaly detection.
    An anomaly is flagged when |z-score| > threshold.

    Z-score = (value − mean) / std_dev

    Args:
        series: time-series of current values
        threshold: standard deviations above mean to flag

    Returns:
        Boolean Series, True where anomaly detected
    """
    mean = series.mean()
    std  = series.std()
    if std == 0:
        return pd.Series(False, index=series.index)
    z_scores = (series - mean).abs() / std
    return z_scores > threshold


def run_detection(
    df: pd.DataFrame,
    sensitivity: float = 2.5,
    method: str = "Combined"
) -> pd.DataFrame:
    """
    Apply anomaly detection to a circuit DataFrame.

    Args:
        df: DataFrame with 'current_A' column
        sensitivity: threshold multiplier (lower = more detections)
        method: 'Moving Average', 'Z-Score', or 'Combined'

    Returns:
        DataFrame with added 'detected' boolean column
    """
    series = df["current_A"]

    ma_flags    = detect_moving_average(series, threshold_multiplier=sensitivity)
    zscore_flag = detect_zscore(series, threshold=sensitivity)

    if method == "Moving Average":
        df = df.copy()
        df["detected"] = ma_flags
    elif method == "Z-Score":
        df = df.copy()
        df["detected"] = zscore_flag
    else:  # Combined — union of both methods
        df = df.copy()
        df["detected"] = ma_flags | zscore_flag

    return df


# ─────────────────────────────────────────────────────────────
# SUMMARY STATISTICS
# ─────────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame, cost_per_kwh: float = 0.12) -> dict:
    """
    Compute summary statistics for a circuit.

    Energy (kWh) estimated assuming 230V mains:
        Power (W) = Current (A) × Voltage (V)
        Energy (kWh) = Power (W) × Hours / 1000
    """
    total_anomalies  = int(df["detected"].sum())
    peak_current     = round(float(df["current_A"].max()), 2)
    avg_current      = round(float(df["current_A"].mean()), 2)

    # Estimate energy: assume 230 V, 5-minute intervals
    hours_per_sample = 5 / 60
    power_w          = df["current_A"] * 230
    energy_kwh       = (power_w * hours_per_sample / 1000).sum()
    estimated_cost   = round(energy_kwh * cost_per_kwh, 4)

    return {
        "total_anomalies": total_anomalies,
        "peak_current_A":  peak_current,
        "avg_current_A":   avg_current,
        "energy_kwh":      round(energy_kwh, 3),
        "estimated_cost":  estimated_cost,
    }
