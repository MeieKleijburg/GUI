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
BASE_DIR = Path(__file__).resolve().parent
RESULTS_ROOT = BASE_DIR / "results"  # (basedir: C:\Users\meiek\Documents\RIVUS_code\GUI)

# Build the two runs (fixed company + dates)
company_name = "033. Stravalla"
convential_name = "Stravalla"
folder0 = "2026-01-05"
folder1 = "2026-01-06"
# add more simulation_date_folders as needed
LOGO_PATH = BASE_DIR / "rivus-logo.webp"


def list_uuids(date_dir: Path):
    return sorted([p.name for p in date_dir.iterdir() if p.is_dir()])

def read_results_excel(uuid_dir: Path) -> pd.DataFrame:
    """
    Reads the Results file from a UUID directory.
       """

    # match case-insensitively
    candidates = list(uuid_dir.glob("Results.*")) + list(uuid_dir.glob("results.*"))

    if not candidates:
        raise FileNotFoundError(f"No Results file found in {uuid_dir}")

    # Prefer Excel over CSV if both exist
    excel_files = [p for p in candidates if p.suffix.lower() in (".xlsx", ".xls")]
    csv_files = [p for p in candidates if p.suffix.lower() == ".csv"]

    if excel_files:
        f = excel_files[0]
        df = pd.read_excel(f)
    elif csv_files:
        f = csv_files[0]
        df = pd.read_csv(f)
    else:
        raise ValueError(f"Unsupported Results file type in {uuid_dir}")

    return df

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
def build_catalog(company: str, date: str) -> pd.DataFrame:
    company_dir = RESULTS_ROOT / company
    date_dir = company_dir / date

    rows = []
    for uuid in list_uuids(date_dir):
        uuid_dir = date_dir / uuid
        plots_dir = uuid_dir / "plots"
        plots_dir_exists = plots_dir.exists()


        try:
            df = read_results_excel(uuid_dir)
        except Exception as e:
            continue

        df = df.reset_index(drop=True)
        df["row_index"] = df.index
        df["company"] = company
        df["date"] = date
        df["uuid"] = uuid

        # plot file mapping (plots are OPTIONAL)
        if plots_dir_exists:
            df["plot_path"] = df["row_index"].apply(
                lambda i: str(plots_dir / f"plot{i}.html")
            )
            df["plot_exists"] = df["plot_path"].apply(lambda p: Path(p).exists())
        else:
            df["plot_path"] = None
            df["plot_exists"] = False

        rows.append(df)

    if not rows:
        return pd.DataFrame()

    catalog = pd.concat(rows, ignore_index=True)
    return catalog

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

catalog0 = build_catalog(company_name, folder0)
catalog1 = build_catalog(company_name, folder1)

catalog = pd.concat([catalog0, catalog1], ignore_index=True)


st.set_page_config(layout="wide")
st.title(f"Results Explorer {convential_name}")

# --- Sidebar filters (examples; adapt to your columns) ---
with st.sidebar:
    st.image(str(LOGO_PATH), width=200)

    st.markdown("### Filters")

    if "FCR" in catalog.columns:
        fcr_vals = sorted(catalog["FCR"].dropna().unique().tolist())
        fcr_sel = st.multiselect("Ancillary Markets", fcr_vals, default=fcr_vals)
        catalog = catalog[catalog["FCR"].isin(fcr_sel)]

    if "Self-Sufficiency" in catalog.columns:
        ss = sorted(catalog["Self-Sufficiency"].dropna().unique().tolist())
        ss_sel = st.multiselect("Self-Sufficiency", ss, default=ss)
        catalog = catalog[catalog["Self-Sufficiency"].isin(ss_sel)]

# Stop early if filters remove everything
if catalog.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# Ensure numeric types (optional but helps if strings sneak in)
for c in ["Battery Capacity", "Max Power"]:
    if c in catalog.columns:
        catalog[c] = pd.to_numeric(catalog[c], errors="coerce")

st.markdown("### Select configuration")

col1, col2 = st.columns(2)

with col1:
    if "Battery Capacity" not in catalog.columns:
        st.error("Missing column: Battery Capacity")
        st.stop()
    cap_options = sorted(catalog["Battery Capacity"].dropna().unique().tolist())
    if not cap_options:
        st.warning("No Battery Capacity values available after filters.")
        st.stop()
    cap_sel = st.selectbox("Battery Capacity", cap_options)

with col2:
    if "Max Power" not in catalog.columns:
        st.error("Missing column: Max Power")
        st.stop()
    # Max Power options depend on chosen capacity (nice UX)
    tmp = catalog[catalog["Battery Capacity"] == cap_sel]
    pmax_options = sorted(tmp["Max Power"].dropna().unique().tolist())
    if not pmax_options:
        st.warning("No Max Power values available for this Battery Capacity.")
        st.stop()
    pmax_sel = st.selectbox("Max Power", pmax_options)

remaining = catalog[
    (catalog["Battery Capacity"] == cap_sel) &
    (catalog["Max Power"] == pmax_sel)
].copy()

if remaining.empty:
    st.warning("No rows match Battery Capacity + Max Power (after left filters).")
    st.stop()

# Make display stable/predictable
sort_keys = [c for c in ["date", "uuid", "row_index"] if c in remaining.columns]
if sort_keys:
    remaining = remaining.sort_values(sort_keys, kind="mergesort")

st.caption(f"{len(remaining)} matching result(s).")

idx = st.number_input(
    "Result number",
    min_value=1,
    max_value=len(remaining),
    value=1,
    step=1,
    key="result_index_selector",
)
picked = remaining.iloc[int(idx) - 1]


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


with colB:
    st.markdown("### Row details")
    details = picked.to_dict()
    details.pop("plot_path", None)
    st.json(details)
