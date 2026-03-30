"""
dashboard/app.py
-----------------
ADAS Intelligent Validation — Story-driven dashboard.

Three-act narrative:
  Act 1 — Phase 1: Systematic baseline (500 scenarios, find all failures)
  Act 2 — Phase 2: Smart selection   (100 scenarios, same coverage → 5x cheaper)
  Act 3 — Phase 3: Novel discovery   (300 scenarios, finds failure modes GBT never knew)

Run: streamlit run src/dashboard/app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.database.results_db import ResultsDB

DB_PATH    = str(Path(__file__).parents[2] / "data" / "results" / "results.db")
MODELS_DIR = Path(__file__).parents[2] / "data" / "models"
RESULTS_DIR = Path(__file__).parents[2] / "data" / "results"

# ─────────────────────────────────────────────────────────────────
# SUT version metadata — shown to users for context
# ─────────────────────────────────────────────────────────────────
SUT_INFO = {
    "v1": {
        "label":   "v1 — Wet-road Bug",
        "colour":  "#E24B4A",
        "badge":   "FAIL",
        "bug":     "Wet/snow road compensation too aggressive (wet_road_factor=0.45). "
                   "AEB deceleration reduced to 45% on wet/snow → insufficient braking at ego ≥ 60 km/h.",
        "fix":     "Not fixed in this version.",
        "fails_at":"ego ≥ 60 km/h + wet or snow",
    },
    "v2": {
        "label":   "v2 — Fog-dense Regression",
        "colour":  "#E2A500",
        "badge":   "REGRESSION",
        "bug":     "Wet-road bug fixed, but lidar reflectivity patch halved sensor range in dense fog. "
                   "AEB fires at TTC = 1.0 s instead of 2.2 s → insufficient braking distance at ego ≥ 50 km/h.",
        "fix":     "Wet-road fix confirmed (v1 failures gone). New regression introduced.",
        "fails_at":"ego ≥ 50 km/h + fog_dense",
    },
    "v3": {
        "label":   "v3 — Clean Release",
        "colour":  "#1D9E75",
        "badge":   "PASS",
        "bug":     "No known defects. Both wet-road and fog_dense issues resolved.",
        "fix":     "All failures from v1 and v2 corrected.",
        "fails_at":"None",
    },
}

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ADAS Intelligent Validation",
    page_icon="🚗",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────
# Data loaders
# ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_results(sut_version: str) -> pd.DataFrame:
    return ResultsDB(DB_PATH).to_dataframe(sut_version)

@st.cache_data
def load_learning_curve() -> pd.DataFrame:
    p = RESULTS_DIR / "learning_curve.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

# ─────────────────────────────────────────────────────────────────
# Sidebar — SUT selector + version context
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Euro_NCAP_logo.svg/200px-Euro_NCAP_logo.svg.png",
             width=120)
    st.title("ADAS Validation")
    st.caption("Euro NCAP 2026 · SOTIF ISO 21448")

    st.divider()

    db_obj = ResultsDB(DB_PATH)
    available = db_obj.available_versions() or ["v1"]
    selected_version = st.selectbox("SUT Version under analysis", available, index=0)

    info = SUT_INFO.get(selected_version, {})
    badge_colour = info.get("colour", "#888")
    st.markdown(
        f"""
        <div style="background:{badge_colour}22; border-left:4px solid {badge_colour};
                    padding:10px; border-radius:4px; margin-top:8px;">
        <b style="color:{badge_colour}">{info.get('badge','')}</b>
        &nbsp;·&nbsp;<b>{info.get('label','')}</b><br><br>
        <small><b>Known defect:</b><br>{info.get('bug','—')}</small><br><br>
        <small><b>Fails at:</b> {info.get('fails_at','—')}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("**Regulations**")
    st.markdown("- Euro NCAP 2026 AEB C2C")
    st.markdown("- UNECE R157 ALKS")
    st.markdown("- ISO 21448 SOTIF")

    st.divider()
    st.markdown("**Pipeline**")
    st.markdown("Phase 1 → systematic 500 scenarios  \nPhase 2 → GBT smart 100 scenarios  \nPhase 3 → bandit novel discovery")


# ─────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────
st.markdown(
    f"## ADAS Intelligent Scenario Validation — SUT {selected_version}",
)
st.caption(
    "Three-phase AI pipeline: systematic baseline → budget-efficient regression → novel failure discovery"
)

# ─────────────────────────────────────────────────────────────────
# Load Phase 1 data (systematic scenarios only)
# ─────────────────────────────────────────────────────────────────
try:
    df_all = load_results(selected_version)
    df_p1  = df_all[~df_all["scenario_id"].str.startswith("RL_")].copy()
    has_data = len(df_p1) > 0
except Exception:
    has_data = False

if not has_data:
    st.warning(
        f"No Phase 1 results for SUT {selected_version}. "
        f"Run: `python scripts/run_phase1.py --sut_version {selected_version}`"
    )
    st.stop()


# ═════════════════════════════════════════════════════════════════
# ACT 1 — PHASE 1: SYSTEMATIC BASELINE
# ═════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Act 1 — Phase 1: Systematic Baseline")
st.caption(
    "500 scenarios run exhaustively across all parameter combinations. "
    "Establishes ground truth: *what breaks and where.*"
)

# KPI row
k1, k2, k3, k4 = st.columns(4)
total_p1       = len(df_p1)
collisions_p1  = int(df_p1["collision"].sum())
critical_p1    = int(df_p1["label_critical"].sum())
mean_ncap_p1   = df_p1["ncap_points"].mean()

k1.metric("Scenarios run",        total_p1)
k2.metric("Collisions",           collisions_p1,
          delta=f"{collisions_p1/total_p1*100:.1f}% rate", delta_color="inverse")
k3.metric("Critical (NCAP < 2)",  critical_p1,
          delta=f"{critical_p1/total_p1*100:.1f}% rate", delta_color="inverse")
k4.metric("Mean NCAP score",      f"{mean_ncap_p1:.2f} / 4.00")

col_left, col_right = st.columns(2)

# NCAP scorecard bar chart
with col_left:
    scorecard = (
        df_p1.groupby("family")
        .agg(
            scenarios=("scenario_id", "count"),
            mean_points=("ncap_points", "mean"),
            collisions=("collision", "sum"),
            critical_rate=("label_critical", "mean"),
        )
        .reset_index()
    )
    scorecard["pass"]             = scorecard["mean_points"] >= 2.0
    scorecard["Status"]           = scorecard["pass"].map({True: "PASS", False: "FAIL"})
    scorecard["mean_points"]      = scorecard["mean_points"].round(2)
    scorecard["critical_rate_pct"]= (scorecard["critical_rate"] * 100).round(1)

    fig_bar = px.bar(
        scorecard,
        x="family", y="mean_points",
        color="Status",
        color_discrete_map={"PASS": "#1D9E75", "FAIL": "#E24B4A"},
        title="Mean NCAP Points per Scenario Family",
        labels={"mean_points": "Mean NCAP Points (0–4)", "family": "Scenario Family"},
    )
    fig_bar.add_hline(y=2.0, line_dash="dash", line_color="orange",
                      annotation_text="Pass threshold (2.0)")
    fig_bar.update_layout(margin=dict(t=40, b=20), height=320)
    st.plotly_chart(fig_bar, use_container_width=True)

# Failure heatmap
with col_right:
    hm = df_p1.copy()
    hm["Speed bucket"] = pd.cut(
        hm["ego_speed_kmh"],
        bins=[0, 30, 50, 70, 90, 110],
        labels=["≤30", "31–50", "51–70", "71–90", "91–110"],
    )
    pivot = (
        hm.groupby(["Speed bucket", "weather"], observed=True)["label_critical"]
        .mean()
        .reset_index()
        .pivot(index="weather", columns="Speed bucket", values="label_critical")
    )
    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn_r",
        zmin=0, zmax=1,
        title="Failure Rate: Ego Speed vs Weather",
        labels={"color": "Failure rate", "x": "Ego speed [km/h]", "y": "Weather"},
        text_auto=".0%",
    )
    fig_heat.update_layout(margin=dict(t=40, b=20), height=320)
    st.plotly_chart(fig_heat, use_container_width=True)

# Scorecard table (collapsed)
with st.expander("NCAP scorecard table"):
    st.dataframe(
        scorecard[["family", "scenarios", "mean_points", "collisions",
                   "critical_rate_pct", "Status"]].rename(
            columns={"critical_rate_pct": "Critical %"}),
        use_container_width=True,
    )


# ═════════════════════════════════════════════════════════════════
# ACT 2 — PHASE 2: BUDGET EFFICIENCY
# ═════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Act 2 — Phase 2: Smart Test Selection (500 → 100 Scenarios)")
st.caption(
    "GBT criticality model re-orders scenarios by predicted failure probability. "
    "The 100 highest-risk scenarios catch the same defects as running all 500. "
    "*5× cost reduction.*"
)

fi_model_path = MODELS_DIR / "gbt_v1.joblib"
if fi_model_path.exists():
    try:
        from src.ml.criticality_model import CriticalityModel
        import numpy as np

        gbt_v1 = CriticalityModel.load(str(fi_model_path), sut_version="v1")
        probs   = gbt_v1.predict_proba(df_p1)
        df_p1["gbt_prob"] = probs

        df_smart  = df_p1.sort_values("gbt_prob", ascending=False).reset_index(drop=True)
        df_random = df_p1.sample(frac=1, random_state=42).reset_index(drop=True)

        # Build cumulative failure curves (no "random" — not a real industry practice)
        smart_curve         = df_smart["label_critical"].cumsum().reset_index()
        smart_curve.columns = ["scenarios_run", "failures_found"]
        smart_curve["scenarios_run"] += 1
        smart_curve["Approach"] = "GBT-smart (AI-ranked)"

        # NCAP homologation curve — fixed regulation test points:
        # CCRs/CCRm/CCRb at the standard speeds mandated by Euro NCAP 2026 (10/20/30/40/60/80 km/h ego)
        NCAP_SPEEDS   = {10, 20, 30, 40, 60, 80}
        NCAP_OVERLAPS = {50, 75, 100}
        df_ncap = df_p1[
            df_p1["ego_speed_kmh"].isin(NCAP_SPEEDS) &
            df_p1["overlap_pct"].isin(NCAP_OVERLAPS) &
            (df_p1["weather"] == "dry")
        ].copy()
        ncap_failures   = int(df_ncap["label_critical"].sum())
        ncap_scenarios  = len(df_ncap)

        total_failures_p1  = int(df_p1["label_critical"].sum())
        smart_at_100        = int(df_smart["label_critical"].iloc[:100].sum())
        smart_coverage_pct  = round(smart_at_100 / max(total_failures_p1, 1) * 100, 1)
        ncap_coverage_pct   = round(ncap_failures / max(total_failures_p1, 1) * 100, 1)

        # Load bandit curve if available for selected version
        lc_df        = load_learning_curve()
        bandit_curve = None
        if not lc_df.empty and selected_version in lc_df["sut_version"].values:
            bdf = lc_df[lc_df["sut_version"] == selected_version][
                ["episode", "cumulative_failures"]
            ].copy()
            bdf.columns     = ["scenarios_run", "failures_found"]
            bdf["Approach"] = "GBT + Bandit — novel discovery (Phase 3)"
            bandit_curve    = bdf

        curve_data = [smart_curve]
        if bandit_curve is not None:
            curve_data.append(bandit_curve)
        combined = pd.concat(curve_data, ignore_index=True)

        colour_map = {
            "GBT-smart (AI-ranked)":                    "#E24B4A",
            "GBT + Bandit — novel discovery (Phase 3)": "#1D6FE2",
        }

        bandit_total     = int(bandit_curve["failures_found"].max()) if bandit_curve is not None else 0
        bandit_scenarios = int(bandit_curve["scenarios_run"].max())  if bandit_curve is not None else 0

        fig_red = px.line(
            combined,
            x="scenarios_run", y="failures_found", color="Approach",
            title=f"SUT {selected_version} — Cumulative failures found vs scenarios executed",
            labels={
                "scenarios_run":  "Scenarios executed",
                "failures_found": "Cumulative failures found",
            },
            color_discrete_map=colour_map,
        )
        fig_red.add_vline(
            x=100, line_dash="dash", line_color="orange",
            annotation_text="100-scenario budget", annotation_position="top right",
        )
        fig_red.add_hline(
            y=total_failures_p1, line_dash="dot", line_color="#1D9E75",
            annotation_text=f"Exhaustive total ({total_failures_p1})",
            annotation_position="bottom right",
        )
        # Mark NCAP homologation fixed points as a horizontal reference
        fig_red.add_annotation(
            x=ncap_scenarios, y=ncap_failures,
            text=f"NCAP homologation pts ({ncap_scenarios} scenarios, {ncap_failures} failures)",
            showarrow=True, arrowhead=2, ax=60, ay=-30,
            font=dict(size=11, color="#888"),
        )
        fig_red.update_layout(height=420)
        st.plotly_chart(fig_red, use_container_width=True)

        # Budget efficiency KPIs — 3 meaningful industry comparisons
        b1, b2, b3 = st.columns(3)
        b1.metric(
            f"Exhaustive sweep — {total_p1} scenarios",
            f"{total_failures_p1} failures",
            "Full parametric grid · traditional approach",
        )
        b2.metric(
            "NCAP homologation fixed points",
            f"{ncap_failures} failures",
            f"{ncap_coverage_pct}% coverage · {ncap_scenarios} mandated test pts · dry only",
        )
        b3.metric(
            "GBT-smart — top 100 scenarios",
            f"{smart_at_100} failures",
            f"{smart_coverage_pct}% coverage · AI-ranked by predicted risk · {total_p1//100}x cheaper",
        )
        if bandit_curve is not None:
            st.metric(
                f"GBT + Bandit (Phase 3) — {bandit_scenarios} adaptive scenarios",
                f"{bandit_total} failures",
                f"Discovers failure regions not in training data",
            )

        st.markdown(
            f"""
            | Approach | How scenarios are chosen | Scenarios | Failures found | Industry equivalent |
            |----------|--------------------------|:---------:|:--------------:|---------------------|
            | **Exhaustive sweep** | Every speed × weather × overlap combination | {total_p1} | {total_failures_p1} | Full MIL/SIL regression suite |
            | **NCAP homologation** | Fixed speeds + overlaps mandated by Euro NCAP 2026 regulation, dry road only | {ncap_scenarios} | {ncap_failures} | Type-approval test run submitted to NCAP |
            | **GBT-smart** | AI (Gradient Boosted Trees) scores all scenarios by predicted failure probability, runs the highest-risk 100 first | 100 | {smart_at_100} | AI-augmented regression suite |
            | **GBT + Bandit** | Adaptive: tries parameter regions, learns failure patterns in real time, targets gaps the GBT model never covered | {bandit_scenarios} | {bandit_total if bandit_curve is not None else "—"} | SOTIF corner-case hunting for new SUT releases |
            """
        )

    except Exception as e:
        st.warning(f"Could not build efficiency chart: {e}")
else:
    st.info(
        "Run Phase 2 to train the GBT model: "
        "`python scripts/run_phase2.py --sut_version v1 --budget 100`"
    )

# SHAP feature importance
fi_csv = MODELS_DIR / f"shap_importance_{selected_version}.csv"
if not fi_csv.exists():
    fi_csv = MODELS_DIR / "shap_importance_v1.csv"   # fallback to v1 model
if fi_csv.exists():
    with st.expander("What drives failures? — SHAP feature importance"):
        fi_df = pd.read_csv(fi_csv)
        fig_shap = px.bar(
            fi_df.head(8),
            x="mean_abs_shap", y="feature",
            orientation="h",
            title="Top scenario parameters driving critical outcomes (SHAP)",
            labels={"mean_abs_shap": "Mean |SHAP value|", "feature": "Scenario parameter"},
            color="mean_abs_shap",
            color_continuous_scale="Blues",
        )
        fig_shap.update_layout(yaxis={"categoryorder": "total ascending"}, height=300)
        st.plotly_chart(fig_shap, use_container_width=True)


# ═════════════════════════════════════════════════════════════════
# ACT 3 — PHASE 3: NOVEL FAILURE DISCOVERY (BANDIT)
# ═════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Act 3 — Phase 3: Novel Failure Discovery (UCB Bandit)")
st.caption(
    "When a new SUT version ships, the bandit agent probes regions the GBT never trained on. "
    "It finds *unknown unknowns* — failure modes systematic testing would miss entirely. "
    "This addresses ISO 21448 SOTIF: *known-unknowns vs unknown-unknowns*."
)

lc_df = load_learning_curve()

if lc_df.empty:
    st.info(
        "No Phase 3 data yet. Run: "
        "`python scripts/run_phase3.py --sut_version v2 --episodes 300 --ucb_c 2.0`"
    )
else:
    # Show all available SUT versions from bandit runs
    bandit_versions = sorted(lc_df["sut_version"].unique().tolist())

    left, right = st.columns([2, 1])

    with left:
        fig_lc = px.line(
            lc_df,
            x="episode", y="cumulative_failures",
            color="sut_version",
            markers=False,
            title="Bandit learning curve — failures discovered over scenarios",
            labels={
                "episode":              "Scenarios executed (bandit)",
                "cumulative_failures":  "Cumulative failures found",
                "sut_version":          "SUT version probed",
            },
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_lc.update_layout(height=360)
        st.plotly_chart(fig_lc, use_container_width=True)

    with right:
        st.markdown("#### SOTIF interpretation")
        for ver in bandit_versions:
            ver_lc        = lc_df[lc_df["sut_version"] == ver]
            total_bandit  = int(ver_lc["cumulative_failures"].max()) if len(ver_lc) > 0 else 0
            total_scenarios = int(ver_lc["episode"].max()) if len(ver_lc) > 0 else 0
            info_v        = SUT_INFO.get(ver, {})
            st.markdown(
                f"""
                <div style="border-left:4px solid {info_v.get('colour','#888')};
                            padding:8px 12px; margin-bottom:10px; border-radius:3px;
                            background:{info_v.get('colour','#888')}11;">
                <b>SUT {ver}</b> — {info_v.get('badge','')}<br>
                <small>{total_bandit} failures in {total_scenarios} scenarios</small><br>
                <small style="color:#666">{info_v.get('fails_at','—')}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Known-unknown vs unknown-unknown explanation
    st.markdown("#### Why does this matter?")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            """
            **Known-unknowns** (Phase 2 GBT catches these)
            - Wet-road failures at ego ≥ 60 km/h — seen in v1 training data
            - GBT assigns high failure probability → smart selector prioritises them
            - Phase 2 finds 90%+ of these in 100 scenarios instead of 500
            """
        )
    with col_b:
        st.markdown(
            """
            **Unknown-unknowns** (Phase 3 bandit discovers these)
            - Fog-dense regression in v2 — *never appeared in v1 training data*
            - GBT assigns ~0% failure probability → smart selector ignores them
            - Bandit discovers them because UCB forces exploration of low-confidence arms
            - Directly addresses **ISO 21448 SOTIF** corner-case coverage
            """
        )

    # SUT comparison summary
    st.markdown("#### SUT version comparison")
    rows = []
    for ver in ["v1", "v2", "v3"]:
        try:
            df_ver = load_results(ver)
            df_ver_p1 = df_ver[~df_ver["scenario_id"].str.startswith("RL_")]
            rows.append({
                "SUT": ver,
                "Description": SUT_INFO[ver]["label"],
                "Phase 1 scenarios": len(df_ver_p1),
                "Failures (NCAP<2)": int(df_ver_p1["label_critical"].sum()),
                "Failure rate": f"{df_ver_p1['label_critical'].mean()*100:.1f}%",
                "Status": SUT_INFO[ver]["badge"],
                "Fails at": SUT_INFO[ver]["fails_at"],
            })
        except Exception:
            rows.append({
                "SUT": ver,
                "Description": SUT_INFO[ver]["label"],
                "Phase 1 scenarios": "—",
                "Failures (NCAP<2)": "—",
                "Failure rate": "—",
                "Status": SUT_INFO[ver]["badge"],
                "Fails at": SUT_INFO[ver]["fails_at"],
            })

    sut_table = pd.DataFrame(rows)
    st.dataframe(sut_table, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════
# Raw data (always collapsed)
# ═════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("Raw scenario results — Phase 1 systematic"):
    display_cols = [
        "scenario_id", "family", "ego_speed_kmh", "target_speed_kmh",
        "weather", "time_of_day", "overlap_pct",
        "ncap_points", "collision", "label_critical",
    ]
    st.dataframe(df_p1[display_cols], use_container_width=True)
