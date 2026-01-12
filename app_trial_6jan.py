import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components
import re
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt


# streamlit run c:/Users/meiek/Documents/RIVUS_code/GUI/app_trial.py
# Config
BASE_DIR = Path(__file__).resolve().parent.parent

# Build the two runs (fixed company + dates)
company_name =  "039. Godestadsvagen"
convential_name = "Gödestadsvägen"
folder = "2026-01-12"
# fallback: if only one folder is needed, set folder1 equal to folder0
run_id = "0_d8e6e2be-fe71-4da3-9e08-18f8eea397de"

RESULTS_PATH = BASE_DIR / "battery_optimization" / "results" / company_name / folder / run_id / "Results_All.xlsx"

# add more simulation_date_folders as needed
LOGO_PATH = BASE_DIR / "GUI" / "rivus-logo.webp"

# todo: couple with automated_reporting.py
template_key = "ownPVss"  # choose from: ownPVss, ownPV, APIPVss, APIPV          ,ss = self-sufficient 
row_selected_case_2024 = 2  # not self-sufficient, 2024 (_1)
row_selected_case_2024_ss = 0  # self-sufficient, 2024 (_2)
row_selected_case_2025 = 6  # not self-sufficient, 2025 (_3)
row_selected_case_2025_ss = 4  # self-sufficient, 2025 (_4)


def to_percent(x) -> float:
    """Convert x to a percentage in [0, 100]. Accepts 0-1 or 0-100. Handles NaN."""
    try:
        x = float(x)
    except Exception:
        return 0.0
    if math.isnan(x):
        return 0.0
    # If value looks like a fraction, convert to %
    if 0 <= x <= 1:
        return x * 100.0
    return x

def savings_pie(picked: dict):
    fcr = to_percent(picked.get("FCR% of saving", 0))
    peak = to_percent(picked.get("peak% of saving", 0))
    rest = max(0.0, 100.0 - fcr - peak)

    labels = ["Peak Shaving", "Arbitrage", "Ancillary Market Revenue"]
    values = [peak, rest, fcr]

    # Colors to match your legend (approx)
    colors = ["#76C55A", "#46B7AE", "#2E7D32"]  # light green, teal, dark green

    fig, ax = plt.subplots(figsize=(5.5, 2.4), dpi=140)
    wedges, texts, autotexts = ax.pie(
        values,
        startangle=90,
        autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
        pctdistance=0.75,
        colors=colors,
    )
    ax.axis("equal")

    ax.legend(
        wedges,
        labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
    )

    return fig

def scenario_cost_barplot(
    scenarios,
    values,
    title="Average Annual Electricity Cost per Scenario",
    ylabel="Electricity Price (EUR/kWh)",
    show_grid=True,
):
    # Clean inputs: convert to float or NaN
    clean = []
    for v in values:
        try:
            v = float(v)
        except Exception:
            v = float("nan")
        clean.append(v)

    # If everything is NaN, return an empty fig with a message
    if all(math.isnan(v) for v in clean):
        fig, ax = plt.subplots(figsize=(7.5, 3.6), dpi=140)
        ax.text(0.5, 0.5, "No cost data available", ha="center", va="center")
        ax.axis("off")
        return fig

    # Colors (match your palette)
    colors = ['#379683', '#05386B', '#2F8F5B']  # Baseline, PV only, Battery

    fig, ax = plt.subplots(figsize=(8.5, 3.6), dpi=140)

    # Bars: if a value is NaN, set bar height 0 and label as "—"
    heights = [0.0 if math.isnan(v) else v for v in clean]
    bars = ax.bar(scenarios, heights, color=colors[:len(scenarios)], edgecolor="none")

    # Title + labels (consistent font)
    ax.set_title(title, fontsize=16, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=13)
    ax.tick_params(axis='x', labelsize=12)
    ax.tick_params(axis='y', labelsize=12)


    # Make it look modern: remove spines (“black box”)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # Light grid (or none)
    if show_grid:
        ax.grid(axis="y", alpha=0.18, linewidth=1)
    else:
        ax.grid(False)

    finite_vals = [v for v in clean if not math.isnan(v)]
    vmax = max(finite_vals) if finite_vals else 0.0

    # Always start y-axis at 0
    pad = max(0.01, vmax * 0.20)
    ax.set_ylim(0.0, vmax + pad)

    # Value labels: always place above bar top, inside axes limits
    ymax = ax.get_ylim()[1]
    label_offset = 0.03 * ymax

    for bar, v in zip(bars, clean):
        x = bar.get_x() + bar.get_width() / 2
        h = bar.get_height()

        if math.isnan(v):
            ax.text(x, 0.05 * ymax, "—", ha="center", va="bottom", fontsize=12)
            continue

        y_text = h + label_offset

        # Clamp so it never leaves the plot
        y_text = min(y_text, ymax * 0.95)

        ax.text(
            x,
            y_text,
            f"€{v:.3f}",
            ha="center",
            va="bottom",
            fontsize=12,
        )

    plt.tight_layout()
    return fig



@st.cache_data(show_spinner=False)
def build_catalog(results_path: Path = None, company: str = None, date: str = None, uuid: str = None) -> pd.DataFrame:
    """
    Load Results Excel file and add metadata columns.
    If results_path is provided, use it; otherwise use RESULTS_PATH global.
    """
    if results_path is None:
        results_path = RESULTS_PATH
    if company is None:
        company = company_name
    if date is None:
        date = folder
    if uuid is None:
        uuid = run_id
    
    # Read the Excel file
    df = pd.read_excel(results_path)
    df = df.reset_index(drop=True)
    
    # Add metadata columns
    df["row_index"] = df.index
    df["company"] = company
    df["date"] = date
    df["uuid"] = uuid
    
    # Check for plots directory (optional)
    plots_dir = results_path.parent / "plots"
    plots_dir_exists = plots_dir.exists()
    
    if plots_dir_exists:
        df["plot_path"] = df["row_index"].apply(
            lambda i: str(plots_dir / f"plot{i}.html")
        )
        df["plot_exists"] = df["plot_path"].apply(lambda p: Path(p).exists())
    else:
        df["plot_path"] = None
        df["plot_exists"] = False
    
    return df

def html_plot(path: str | None, height=700):
    if not path:
        st.info("No plot available for this configuration.")
        return
    p = Path(path)
    if not p.exists():
        st.info("Plot file not found.")
        return
    html = p.read_text(encoding="utf-8", errors="ignore")
    components.html(html, height=height, scrolling=True)



# --- Streamlit App ---

df_results = build_catalog()

print("Catalog (df_results):")
print(df_results)

ss_mode = st.selectbox(
    "Self-Sufficiency",
    ["Auto", "On", "Off"],
    index=0,
    help="Auto infers On/Off from import/export. On/Off forces the value."
)

def _find_col(df, keywords):
    for col in df.columns:
        lname = col.lower()
        if any(k in lname for k in keywords):
            return col
    return None

def infer_self_sufficiency(df_results: pd.DataFrame) -> pd.DataFrame:
    df = df_results.copy()
    ss_col = None

    if "Self-Sufficiency" in df.columns:
        pattern = re.compile(r"import\s*([0-9.+\-eE]+).*export\s*([0-9.+\-eE]+)", re.IGNORECASE)

        def parse_ss(val):
            if not isinstance(val, str):
                return None
            m = pattern.search(val)
            if not m:
                return None
            try:
                imp = float(m.group(1))
                exp = float(m.group(2))
                return "Off" if (abs(imp) < 1e-9 and abs(exp) < 1e-9) else "On"
            except Exception:
                return None

        parsed = df["Self-Sufficiency"].apply(parse_ss)
        if parsed.notna().any():
            df["Self-Sufficiency"] = parsed.fillna(df["Self-Sufficiency"].astype(str))
            ss_col = "Self-Sufficiency"

    if ss_col is None:
        imp_col = _find_col(df, ["import"])
        exp_col = _find_col(df, ["export"])
        if imp_col and exp_col:
            df[imp_col] = pd.to_numeric(df[imp_col], errors="coerce").fillna(0.0)
            df[exp_col] = pd.to_numeric(df[exp_col], errors="coerce").fillna(0.0)

            def ss_from_cols(row):
                imp = float(row[imp_col]) if pd.notna(row[imp_col]) else 0.0
                exp = float(row[exp_col]) if pd.notna(row[exp_col]) else 0.0
                return "Off" if (abs(imp) < 1e-9 and abs(exp) < 1e-9) else "On"

            df["Self-Sufficiency"] = df.apply(ss_from_cols, axis=1)
        else:
            if "Self-Sufficiency" not in df.columns:
                df["Self-Sufficiency"] = "On"

    return df

# --- apply user's choice ---
if ss_mode == "Auto":
    df_results = infer_self_sufficiency(df_results)
else:
    # Force a constant value for all rows
    df_results = df_results.copy()
    df_results["Self-Sufficiency"] = ss_mode

st.set_page_config(layout="wide")
st.title(f"Results Explorer {convential_name}")

# --- Sidebar filters (examples; adapt to your columns) ---
with st.sidebar:
    st.image(str(LOGO_PATH), width=200)

    st.markdown("### Filters")

    ### ADD non fcr cases if NEEDED (sometimes not presented to customers)
    # if "FCR" in df_results.columns:
    #     fcr_vals = sorted(df_results["FCR"].dropna().unique().tolist())
    #     fcr_sel = st.multiselect("Ancillary Markets", fcr_vals, default=fcr_vals)
    #     df_results = df_results[df_results["FCR"].isin(fcr_sel)]

    if "Self-Sufficiency" in df_results.columns:
        ss = sorted(df_results["Self-Sufficiency"].dropna().unique().tolist())
        ss_sel = st.multiselect("Self-Sufficiency", ss, default=ss)
        df_results = df_results[df_results["Self-Sufficiency"].isin(ss_sel)]

# Stop early if filters remove everything
if df_results.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# Ensure numeric types (optional but helps if strings sneak in)
for c in ["Battery Capacity", "Max Power"]:
    if c in df_results.columns:
        df_results[c] = pd.to_numeric(df_results[c], errors="coerce")

st.markdown("### Select configuration")

# Manual row selection (default): Year + Battery option map to pre-set row indices
year = st.sidebar.selectbox("Year", ["2024", "2025"], index=0)
battery_option = st.sidebar.radio("Battery option", ["Baseline", "Battery"], index=0)

# Map to pre-set row indices
if year == "2024":
    selected_row = row_selected_case_2024 if battery_option == "Baseline" else row_selected_case_2024_ss
else:
    selected_row = row_selected_case_2025 if battery_option == "Baseline" else row_selected_case_2025_ss

if selected_row < 0 or selected_row >= len(df_results):
    st.error(f"Selected row {selected_row} out of range (0..{len(df_results)-1}).")
    st.stop()

picked = df_results.iloc[selected_row]


colA, colB = st.columns([2, 1])

with colA:
    # --- Above-plot KPIs + pie chart ---
    payback_bat = picked.get("Payback Time battery", None)

    st.markdown("### Key metrics")
    if payback_bat is None or (isinstance(payback_bat, float) and math.isnan(payback_bat)):
        st.metric("Payback time (battery)", "—")
    else:
        st.metric("Payback time (battery)", f"{float(payback_bat):.1f} years")

    # ===== Scenario cost bar chart =====
    scenarios = ['Baseline', 'PV only', 'Battery']

    values = [
        picked.get("Electricity cost/kWh base case"),
        picked.get("Electricity cost/kWh with PV"),
        picked.get("Electricity cost/kWh with PV and battery"),
    ]

    if all(v is not None and not (isinstance(v, float) and math.isnan(v)) for v in values):
        fig_bar = scenario_cost_barplot(
            scenarios,
            values,
            title="Average Annual Electricity Cost per Scenario",
        )
        st.pyplot(fig_bar, clear_figure=True)
    else:
        st.info("Electricity cost data not available for this configuration.")

    # ===== Savings breakdown pie chart =====
    fig_pie = savings_pie(picked)
    st.pyplot(fig_pie, clear_figure=True)

    # ===== Main optimization plot =====
    st.markdown("### Optimization plot")
    html_plot(picked.get("plot_path", None), height=720)


# Details moved into a collapsed expander further down (closed by default)
details = picked.to_dict()
details.pop("plot_path", None)

with st.expander("Details", expanded=False):
    st.json(details)
