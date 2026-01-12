import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components
import pandas as pd
import math
import matplotlib.pyplot as plt


# ----------------------------
# Config
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

company_name = "039. Godestadsvagen"
convential_name = "Gödestadsvägen"
folder = "2026-01-12"
run_id = "5_7f53f1fe-d366-47eb-882a-fbd0c66c0296"

RESULTS_PATH = (
    BASE_DIR / "results" / company_name / folder / run_id / "Results_All.xlsx"
)
LOGO_PATH = BASE_DIR / "GUI" / "rivus-logo.webp"
API_PV = False # whether the API PV scenarios were run

# Canonical row_index values from the Excel (6 scenarios total)
# 2024: baseline (no battery), battery, battery + self-sufficiency focus
ROW_2024_BASE = 0
ROW_2024_BAT  = 1
ROW_2024_SS   = 5

# 2025: baseline (no battery), battery, battery + self-sufficiency focus
# UPDATE these three to match your Excel row_index values:
ROW_2025_BASE = 8
ROW_2025_BAT  = 9
ROW_2025_SS   = 13

ROW_MAP = {
    # 2024
    ("2024", "No battery", "Off"): ROW_2024_BASE,
    ("2024", "Battery",  "Off"): ROW_2024_BAT,
    ("2024", "Battery",  "On"):  ROW_2024_SS,

    # 2025
    ("2025", "No battery", "Off"): ROW_2025_BASE,
    ("2025", "Battery",  "Off"): ROW_2025_BAT,
    ("2025", "Battery",  "On"):  ROW_2025_SS,
}

# Header / Subheader templates (battery details are filled from the selected row)
HEADER_MAP = {
    ("2024", "No battery", "Off"): ("Baseline 2024", "PV installed"),
    ("2024", "Battery", "Off"): (
        "Battery I ({bat_desc})",
        "Peak Shaving, Arbitrage, Ancillary Market revenues",
    ),
    ("2024", "Battery", "On"): (
        "Battery II ({bat_desc})",
        "Self-sufficiency objective and Peak Shaving, Arbitrage, Ancillary Market revenues",
    ),

    ("2025", "No battery", "Off"): ("Baseline 2025", "PV installed"),
    ("2025", "Battery", "Off"): (
        "Battery I ({bat_desc})",
        "Peak Shaving, Arbitrage, Ancillary Market revenues",
    ),
    ("2025", "Battery", "On"): (
        "Battery II ({bat_desc})",
        "Self-sufficiency objective and Peak Shaving, Arbitrage,Ancillary Market revenues",
    ),
}

# MUST be the first Streamlit call
st.set_page_config(layout="wide")
# --- Simple Rivus-green styling ---
st.markdown(
    """
    <style>
      :root {
        --rivus-green: #2E7D32;
        --rivus-green-soft: rgba(46,125,50,0.10);
      }

      /* Sidebar headers */
      section[data-testid="stSidebar"] h1, 
      section[data-testid="stSidebar"] h2, 
      section[data-testid="stSidebar"] h3 {
        color: var(--rivus-green);
      }

      /* Main headers */
      h1, h2, h3 {
        color: var(--rivus-green);
      }

      /* Metric label + value */
      div[data-testid="stMetricLabel"] p {
        color: #2b2b2b;
      }
      div[data-testid="stMetricValue"] {
        border-left: 4px solid var(--rivus-green);
        padding-left: 12px;
      }

      /* Info boxes slightly green */
      div[data-testid="stAlert"] {
        border-left: 4px solid var(--rivus-green);
        background: var(--rivus-green-soft);
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers
# ----------------------------
def to_percent(x) -> float:
    """Convert x to percentage in [0,100]. Accepts 0-1 or 0-100. Handles NaN."""
    try:
        x = float(x)
    except Exception:
        return 0.0
    if math.isnan(x):
        return 0.0
    if 0 <= x <= 1:
        return x * 100.0
    return x


def savings_pie(picked: dict):
    fcr = to_percent(picked.get("FCR% of saving", 0))
    peak = to_percent(picked.get("peak% of saving", 0))
    rest = max(0.0, 100.0 - fcr - peak)

    labels = ["Peak Shaving", "Arbitrage", "Ancillary Market Revenue"]
    values = [peak, rest, fcr]

    # Keep your palette
    colors = ["#2E7D32", "#66BB6A", "#A5D6A7"]

    fig, ax = plt.subplots(figsize=(2.4, 4.5), dpi=140)
    wedges, _, _ = ax.pie(
        values,
        startangle=90,
        autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
        pctdistance=0.75,
        colors=colors,
    )
    ax.axis("equal")
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    return fig


def scenario_cost_barplot(
    scenarios,
    values,
    title="Average Annual Electricity Cost per Scenario",
    ylabel="Electricity Price (EUR/kWh)",
    show_grid=True,
    show_deltas=True,
):
    clean = []
    for v in values:
        try:
            clean.append(float(v))
        except Exception:
            clean.append(float("nan"))

    if all(math.isnan(v) for v in clean):
        fig, ax = plt.subplots(figsize=(7.5, 3.6), dpi=140)
        ax.text(0.5, 0.5, "No cost data available", ha="center", va="center")
        ax.axis("off")
        return fig

    # Greener, consistent palette (baseline slightly muted)
    colors = ["#A5D6A7", "#66BB6A", "#2E7D32"]

    fig, ax = plt.subplots(figsize=(8.5, 3.6), dpi=140)
    heights = [0.0 if math.isnan(v) else v for v in clean]
    bars = ax.bar(scenarios, heights, color=colors[: len(scenarios)], edgecolor="none")

    ax.set_ylabel(ylabel, fontsize=13)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=12)

    for spine in ["top", "right", "left", "bottom"]:
        ax.spines[spine].set_visible(False)

    ax.grid(axis="y", alpha=0.18, linewidth=1) if show_grid else ax.grid(False)

    finite_vals = [v for v in clean if not math.isnan(v)]
    vmax = max(finite_vals) if finite_vals else 0.0
    pad = max(0.01, vmax * 0.25)
    ax.set_ylim(0.0, vmax + pad)

    ymax = ax.get_ylim()[1]
    label_offset = 0.03 * ymax

    # Baseline for deltas (first bar)
    base = clean[0] if len(clean) > 0 else float("nan")
    base_ok = (base is not None) and (not math.isnan(base))

    for i, (bar, v) in enumerate(zip(bars, clean)):
        x = bar.get_x() + bar.get_width() / 2
        h = bar.get_height()

        if math.isnan(v):
            ax.text(x, 0.05 * ymax, "—", ha="center", va="bottom", fontsize=12)
            continue

        # Main label (absolute)
        y_text = min(h + label_offset, ymax * 0.95)
        ax.text(x, y_text, f"€{v:.3f}", ha="center", va="bottom", fontsize=12)

        # Delta label vs baseline (for non-baseline bars)
        if show_deltas and i > 0 and base_ok:
            delta = v - base
            pct = (delta / base * 100.0) if base != 0 else float("nan")

            # Example: "−€0.012 (−18%)" or "+€0.005 (+7%)"
            sign = "+" if delta > 0 else "−"
            d_abs = abs(delta)
            pct_txt = "" if math.isnan(pct) else f" ({sign}{abs(pct):.0f}%)"

            delta_txt = f"{sign}€{d_abs:.3f}{pct_txt}"

            # place inside bar area a bit lower for readability
            y_delta = max(0.02 * ymax, h - 0.12 * ymax)
            ax.text(
                x,
                y_delta,
                delta_txt,
                ha="center",
                va="bottom",
                fontsize=11,
                color="#1b5e20",
            )
    fig.tight_layout()
    return fig

def plot_folder_from_config_id(config_id: str) -> str:
    # year
    year = "y1" if "yo1" in config_id else "y0"

    # import cap
    if "ic5000" in config_id:
        imp = "imp5000.0"
    else:
        imp = "imp0.0"

    # export cap (currently always 0.0)
    exp = "exp0.0"

    # all / ea flag
    all_flag = "alltrue" if config_id.endswith("eaTrue") else "allfalse"

    return f"{year}_{imp}_{exp}_{all_flag}"

@st.cache_data(show_spinner=False)
def load_results(results_path: Path) -> pd.DataFrame:
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found:\n{results_path}")

    df = pd.read_excel(results_path).reset_index(drop=True)
    df["row_index"] = df.index

    plots_root = results_path.parent / "plots"

    def resolve_plot_path(row) -> str | None:
        config_id = row.get("config_id")
        if not isinstance(config_id, str) or not config_id:
            return None

        folder = plot_folder_from_config_id(config_id)
        folder_path = plots_root / folder
        if not folder_path.exists():
            return None

        # robust cast
        try:
            cap = float(row.get("Battery Capacity", 0) or 0)
        except Exception:
            cap = 0.0

        # Your convention: plot0 for cap==0, plot1 for cap>0
        if cap == 0:
            candidate = folder_path / "plot0.html"
            return str(candidate) if candidate.exists() else None

        candidate = folder_path / "plot1.html"
        if candidate.exists():
            return str(candidate)

        # fallback: if plot1 isn't there, return any plot*.html
        plot_files = sorted(folder_path.glob("plot*.html"))
        return str(plot_files[0]) if plot_files else None

    df["plot_path"] = df.apply(resolve_plot_path, axis=1)

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


def _num(picked: dict, key: str):
    v = picked.get(key, None)
    try:
        v = float(v)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None


def battery_desc_from_row(picked: dict) -> str:
    """
    Returns something like: '150 kWh, 25 kW'
    Adjust column names here if your Excel uses different ones.
    """
    cap = _num(picked, "Battery Capacity")
    pwr = _num(picked, "Max Power")

    parts = []
    if cap is not None:
        parts.append(f"{cap:.0f} kWh")
    if pwr is not None:
        parts.append(f"{pwr:.0f} kW")

    return ", ".join(parts) if parts else "size, capacity and power"


def render_header(year: str, battery: str, ss_focus: str, picked: dict):
    header_tpl, subheader = HEADER_MAP[(year, battery, ss_focus)]
    bat_desc = battery_desc_from_row(picked)
    header = header_tpl.format(bat_desc=bat_desc)

    st.title(f"{convential_name}")
    st.header(header)
    st.subheader(subheader)

# ----------------------------
# App
# ----------------------------
# Sidebar controls (customer-facing)
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=200)

    st.markdown("### Controls")

    year = st.selectbox("Year", ["2024", "2025"], index=0)

    battery = st.radio(
        "Battery",
        ["No battery", "Battery"],
        index=0,
    )

    self_sufficiency_focus = st.radio(
        "Self-sufficiency focus",
        ["Off", "On"],
        index=0,
        help="Prioritise self-sufficiency instead of minimum cost (requires a battery).",
    )

# Enforce valid combinations (no battery + SS focus doesn't exist in your 6 scenarios)
if battery == "No battery" and self_sufficiency_focus == "On":
    st.info("Self-sufficiency focus requires a battery. Switched to Off.")
    self_sufficiency_focus = "Off"

# Load data
try:
    df_results = load_results(RESULTS_PATH)
except Exception as e:
    st.error(str(e))
    st.stop()

# Pick selected row_index (stable) 
selected_row_index = ROW_MAP[(year, battery, self_sufficiency_focus)]
picked_df = df_results[df_results["row_index"] == selected_row_index]

if picked_df.empty:
    st.error(
        f"Selected configuration (row_index={selected_row_index}) not found in the Results file.\n"
        f"Check your ROW_2024_* / ROW_2025_* constants."
    )
    st.stop()

picked = picked_df.iloc[0].to_dict()

# Header + Subheader based on selection
render_header(year, battery, self_sufficiency_focus, picked)

# Main layout

if battery == "Battery":
        st.markdown("### Key metrics")
        payback_bat = picked.get("Payback Time battery", None)
        if payback_bat is None or (isinstance(payback_bat, float) and math.isnan(payback_bat)):
            st.metric("Payback time (battery)", "—")
        else:
            st.metric("Payback time (battery)", f"{float(payback_bat):.1f} years")

        c1, c2 = st.columns([3, 2], vertical_alignment="top")

        with c1:
            if API_PV:
                scenarios = ["Baseline", "PV only", "Battery"]
                values = [
                    picked.get("Electricity cost/kWh base case"),
                    picked.get("Electricity cost/kWh with PV"),
                    picked.get("Electricity cost/kWh with PV and battery"),
                ]
            else:
                scenarios = ["Baseline", "Battery"]
                values = [
                    picked.get("Electricity cost/kWh with PV"),
                    picked.get("Electricity cost/kWh with PV and battery"),
                ]

            st.markdown('<div class="chart-title">Average Annual Electricity Cost per Scenario</div>', unsafe_allow_html=True)
            fig = scenario_cost_barplot(scenarios, values, title=" ")
            st.pyplot(fig, clear_figure=True)
            _ = plt.close(fig)

        with c2:
            st.markdown('<div class="chart-title">Savings breakdown</div>',
            unsafe_allow_html=True)
            st.pyplot(savings_pie(picked), clear_figure=True)


if battery == "Battery":
    st.markdown("### Optimization Plots")
else:
    st.markdown("### Demand and Solar Plots")

html_plot(picked.get("plot_path", None), height=720)

# Details
details = dict(picked)
details.pop("plot_path", None)

with st.expander("Details", expanded=False):
    st.json(details)
