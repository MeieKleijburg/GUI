import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components
import re
import pandas as pd


#   streamlit run c:/Users/meiek/Documents/RIVUS_code/GUI/app.py
# Whats left:
# [] pdf maker
# [] depic the year its run better; FCR on or off better; self sufficiency

BASE = Path(r"C:\Users\meiek\Documents\RIVUS_code\battery_optimization\results")
company = "036. Herrestad4"
SCENARIO_ROOT = BASE/ company
results_path = SCENARIO_ROOT / "Results_t.xlsx"
LOGO_PATH = r"C:\Users\meiek\Documents\RIVUS_code\GUI\rivus-logo.webp"
# Header
st.set_page_config(page_title="Scenario GUI", layout="wide")

st.image(LOGO_PATH, width=200)

st.title("Scenario Explorer")
st.caption("PV • Battery • Flexibility analysis")

st.write("Hello! This is a simple GUI to explore different scenarios. You are watching currently for company " + company)


folders = sorted([p.name for p in SCENARIO_ROOT.iterdir() if p.is_dir()])
scenario = st.selectbox("Pick scenario", folders)

scenario_path = SCENARIO_ROOT / scenario
candidates = list(scenario_path.rglob("Plot.html")) + list(scenario_path.rglob("plot.html"))

st.write("Selected:", scenario)

st.subheader("Interactive plot")
if not candidates:
    st.warning("No Plot.html found under this scenario folder.")
else:
    plot_html = candidates[0]  # if multiple, you can add another selectbox
    st.caption(f"Showing: {plot_html.relative_to(SCENARIO_ROOT)}")

    html = plot_html.read_text(encoding="utf-8", errors="ignore")
    components.html(html, height=700, scrolling=True)

# helpers to match excel with scenario  
def parse_scenario_name(name: str) -> dict:
    """
    Extracts values from folder name like:
    '1kW PV 150kWh Battery 25kW MaxPower 400 EUR\\kWh 0 EUR\\kW'
    """
    def grab(pattern, cast=float):
        m = re.search(pattern, name, flags=re.IGNORECASE)
        return cast(m.group(1)) if m else None

    pv_kw      = grab(r"(\d+(?:\.\d+)?)\s*kW\s*PV", float)
    bat_kwh    = grab(r"(\d+(?:\.\d+)?)\s*kWh\s*Battery", float)
    pmax_kw    = grab(r"(\d+(?:\.\d+)?)\s*kW\s*MaxPower", float)
    cap_price  = grab(r"(\d+(?:\.\d+)?)\s*EUR\\kWh", float)   # note: folder uses backslash
    pow_price  = grab(r"(\d+(?:\.\d+)?)\s*EUR\\kW", float)

    return {
        "PV Size": pv_kw,
        "Battery Capacity": bat_kwh,
        "Max Power": pmax_kw,
        "Battery Capacity Price (EUR/kWh)": cap_price,
        "Battery Power Price (EUR/kWh)": pow_price,
    }

def find_results_row(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    hits = df.copy()
    for col, val in params.items():
        if val is None or col not in hits.columns:
            continue
        # robust numeric matching (Excel can load ints/floats)
        hits = hits[pd.to_numeric(hits[col], errors="coerce") == float(val)]
    return hits


df = pd.read_excel(results_path)
def arrow_safe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Convert any datetime64 columns to datetime (fine)
    # Then force all object columns to string (this avoids mixed object issues)
    obj_cols = out.select_dtypes(include=["object"]).columns
    if len(obj_cols) > 0:
        out[obj_cols] = out[obj_cols].astype(str)

    return out

# scenario is the selected folder name from selectbox
params = parse_scenario_name(scenario)
matches = find_results_row(df, params)

st.subheader("Results")

if matches.empty:
    st.warning("No matching row found in results.xlsx for this scenario.")
    st.write("Parsed params:", params)  # helpful debug
else:
    if len(matches) > 1:
        st.info(f"Found {len(matches)} matching rows; showing the first.")
    row = matches.iloc[0]

    # Show key metrics (pick your favorites)
    st.metric("Payback Time (PV and) battery", row.get("Payback Time (PV and) battery", "—"))
    st.metric("Self-sufficiency (SSR %)", row.get("Self-sufficiency (SSR %)", "—"))
    st.metric("Electricity cost/kWh with PV and battery", row.get("Electricity cost/kWh with PV and battery", "—"))

    # Show full row
    row_df = row.to_frame(name="value").reset_index()
    row_df.columns = ["metric", "value"]
    row_df["value"] = row_df["value"].astype(str)  # safest for single-row display
    st.dataframe(row_df)
