# Project Guidelines — Energy Anomaly Detection Dashboard

---

## 1. Scope
Keep the project simple and functional. Focus on:
- Data simulation
- Anomaly detection
- Visualization

Do not add ML complexity beyond statistical methods.

---

## 2. Coding Standards
- Clear, descriptive variable names (`rolling_mean`, not `rm`)
- Modular functions — one responsibility per function
- Docstrings on all public functions
- Comments explaining anomaly logic and data generation decisions

---

## 3. Data Design
- Use realistic 24-hour patterns: morning low → midday moderate → evening peak
- Add controlled Gaussian noise to each circuit
- Each circuit has a distinct profile (Light vs Fan vs Heavy)

---

## 4. Anomaly Types
Must include all three:
1. **Spike** — sudden magnitude jump
2. **Drift** — gradual upward creep over a window
3. **Off-hours usage** — activity at unusual times (midnight–5am)

---

## 5. Visualization Rules
- Use **Plotly** (not Matplotlib — must be interactive)
- Anomalies → red circular markers on the signal line
- Label all axes properly (Time of Day, Current in Amps)
- Dark theme throughout for readability

---

## 6. Dashboard UX
- Keep sidebar uncluttered: sliders, dropdowns, one button
- Summary metrics always visible at top
- Anomaly event log always visible at bottom

---

## 7. Performance
- Keep dataset small: 5-minute intervals over 24h = 288 data points per circuit
- Use `@st.cache_data` to avoid recomputing on every widget interaction
- No heavy computation in the render loop

---

## 8. Deployment Rules
Must run with:
```
streamlit run main.py
```
Must work on Streamlit Cloud with no extra configuration (no `.env`, no secrets, no external API calls).

---

## 9. README Requirements
Must include:
- Project description + feature table
- How to run locally
- How to deploy to Streamlit Cloud
- How anomaly detection works (with pseudocode)
- How to extend to real IoT data

---

## 10. Do NOT
- Use deep learning or scikit-learn (overkill for this scope)
- Add authentication or databases
- Use external APIs
- Add unnecessary pip dependencies
- Use Matplotlib (Plotly only)
