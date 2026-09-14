import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from typing import Optional


import pandas as pd
import plotly.express as px
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
FIGURES_DIR = REPO_ROOT / "Figures"
DB_PATH = REPO_ROOT / "data" / "processed" / "nhs_costs.duckdb"



def ensure_database_built() -> None:
    """
    Builds the DuckDB database on first run if it does not already exist.

    This makes the app self-building from the committed source CSV, so it
    works both locally and on a fresh deployment (e.g. Streamlit Cloud)
    where only the repository files -- not previously-built local
    artefacts -- are available.
    """
    if DB_PATH.exists():
        return

    with st.spinner("First run: building the NHS costs database from source data..."):
        from src.load_database import build_database

        try:
            build_database()
        except FileNotFoundError as exc:
            st.error(
                "Could not build the database because the source CSV was not found. "
                "Make sure the processed CSV is committed to the repository and that "
                "CSV_PATH in src/load_database.py points to it."
            )
            st.exception(exc)
            st.stop()
        except ValueError as exc:
            st.error(
                "The source CSV is missing required columns. Check that it is the "
                "row-level processed dataset, not an aggregated chart-output CSV."
            )
            st.exception(exc)
            st.stop()



ensure_database_built()


from dashboard.queries import get_filter_options, get_service_benchmarks


st.set_page_config(
    page_title="What Can NHS Cost Data Tell Us?",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Consolidated 5-figure set (fig1-fig5), replacing the original 10 static
# figures. Filenames match generate_figures.py output.
# ---------------------------------------------------------------------------
FIGURES = {
    "Cost distribution and skew": {
        "file": "fig1_cost_distribution_skew.png",
        "description": (
            "Reported unit costs are heavily skewed by a small number of very "
            "expensive services, so the mean is misleading here. The median "
            "(£405) better represents a typical record than the mean (£1,874)."
        ),
    },
    "Top services by weighted median cost": {
        "file": "fig2_top_services_median_cost.png",
        "description": (
            "The most expensive services using a robust cost measure "
            "(activity-weighted median, not a simple average). This is a "
            "descriptive cost benchmark, not an efficiency ranking -- high-cost "
            "services are often specialist or complex care."
        ),
    },
    "Provider variation by activity": {
        "file": "fig3_provider_variation_by_activity.png",
        "description": (
            "Providers with lower total activity report more variable costs. "
            "This is expected statistically (small samples are noisier) and is "
            "a pattern for further investigation, not evidence of poor performance."
        ),
    },
    "NCCI overview": {
        "file": "fig4_ncci_overview.png",
        "description": (
            "NCCI is centred near 100 (median 96) but has a long tail of much "
            "higher values. NCCI is an index, not a validated efficiency score -- "
            "its formula and scale need confirmation before drawing performance "
            "conclusions from it."
        ),
    },
    "Mapping_Pot comparison": {
        "file": "fig5_mapping_pot_comparison.png",
        "description": (
            "Mapping_Pot groups differ in typical cost and total activity. This "
            "is a descriptive comparison only -- differences may reflect case "
            "mix, service type or reporting practices, not a causal MFF effect."
        ),
    },
}



@st.cache_data
def figure_path(filename: str) -> Path:
    return FIGURES_DIR / filename



def render_figure(name: str) -> None:
    figure = FIGURES[name]
    path = figure_path(figure["file"])

    if path.exists():
        st.image(str(path), width=800)
        st.caption(figure["description"])
    else:
        st.error(f"Figure not found: {path}")
        st.code(f"Place the image at Figures/{figure['file']}")



def render_disclaimer() -> None:
    st.warning(
        "This dashboard presents descriptive evidence. It does not establish "
        "provider efficiency, causality or poor performance. High cost and high "
        "variation should be treated as signals for further investigation."
    )



# ---------------------------------------------------------------------------
# Interactive, SQL-backed service-cost page (DuckDB via dashboard/queries.py)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cached_filter_options() -> dict:
    return get_filter_options()



@st.cache_data(show_spinner=False)
def cached_service_benchmarks(
    min_activity: int,
    min_provider_count: int,
    department: Optional[str],
    mapping_pot: Optional[str],
    limit: int,
) -> pd.DataFrame:
    return get_service_benchmarks(
        min_activity=min_activity,
        min_provider_count=min_provider_count,
        department=department,
        mapping_pot=mapping_pot,
        limit=limit,
    )



def render_interactive_service_costs() -> None:
    st.subheader("Interactive activity-weighted benchmark")
    st.caption(
        "Set your own activity and provider-count thresholds to explore the "
        "SQL-backed benchmark directly. This is a **descriptive benchmark**, "
        "not an efficiency ranking. Differences may reflect case mix, complexity, "
        "provider structure, reporting or service-delivery differences."
    )

    options = cached_filter_options()

    col1, col2 = st.columns(2)
    with col1:
        min_activity = st.slider(
            "Minimum service activity", min_value=0, max_value=5000, value=50, step=10
        )
        department = st.selectbox(
            "Department (optional)", options=["All"] + options["departments"]
        )
    with col2:
        min_provider_count = st.slider(
            "Minimum provider count", min_value=1, max_value=50, value=3, step=1
        )
        mapping_pot = st.selectbox(
            "Mapping_Pot (optional)", options=["All"] + options["mapping_pots"]
        )

    department_filter = None if department == "All" else department
    mapping_pot_filter = None if mapping_pot == "All" else mapping_pot

    df = cached_service_benchmarks(
        min_activity=min_activity,
        min_provider_count=min_provider_count,
        department=department_filter,
        mapping_pot=mapping_pot_filter,
        limit=15,
    )

    if df.empty:
        st.warning(
            "No services meet the selected thresholds. Try lowering the "
            "minimum activity or minimum provider count."
        )
        return

    fig = px.bar(
        df.sort_values("activity_weighted_unit_cost"),
        x="activity_weighted_unit_cost",
        y="service",
        orientation="h",
        hover_data={
            "total_activity": True,
            "provider_count": True,
            "median_unit_cost": ":.2f",
            "simple_mean_unit_cost": ":.2f",
            "actual_cost_per_activity": ":.2f",
            "activity_weighted_unit_cost": ":.2f",
        },
        labels={
            "activity_weighted_unit_cost": "Activity-weighted unit cost (£)",
            "service": "Service",
        },
        title="Top eligible services by activity-weighted unit cost",
    )
    fig.update_layout(height=550, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Filtered results**")
    st.dataframe(
        df.style.format(
            {
                "activity_weighted_unit_cost": "£{:.2f}",
                "median_unit_cost": "£{:.2f}",
                "simple_mean_unit_cost": "£{:.2f}",
                "actual_cost_per_activity": "£{:.2f}",
                "total_activity": "{:,.0f}",
            }
        ),
        use_container_width=True,
    )

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered results as CSV",
        data=csv_bytes,
        file_name="service_cost_benchmark.csv",
        mime="text/csv",
    )

    st.info(
        "Note: this ranking reflects reported activity-weighted unit cost only. "
        "It is not an efficiency ranking and should not be used to label any "
        "provider or service as inefficient without further investigation."
    )



st.title("What Can NHS Cost Data Tell Us About Variation in Service Costs?")
st.markdown(
    "**NHS National Cost Collection 2024/25**  \n"
    "An exploratory analysis of activity-weighted benchmarks, provider variation, "
    "cost metrics and NCCI distributions."
)


with st.sidebar:
    st.header("Dashboard navigation")
    page = st.radio(
        "Go to",
        [
            "Overview",
            "Service costs",
            "Provider variation",
            "NCCI and variance",
            "Mapping_Pot groups",
        ],
    )

    st.divider()
    st.caption("Data scope")
    st.write("Cleaned NCC 2024/25 data")
    st.write("MFF-unadjusted")
    st.write("Approximately 38,562 numeric records")


if page == "Overview":
    st.header("Overview")
    st.write(
        "This dashboard investigates how reported NHS service costs vary across "
        "services, providers and descriptive grouping variables. It focuses on "
        "robust summaries rather than relying on simple means alone."
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Numeric records", "~38,562")
    metric_2.metric("Median NCCI", "96")
    metric_3.metric("NCCI p99", "~419")
    metric_4.metric("Median variance", "−£3,295")

    st.subheader("Questions explored")
    questions = [
        "Which services have the highest activity-weighted reported unit costs?",
        "Does reported provider cost stability relate to activity volume?",
        "How do Mapping_Pot groups differ descriptively in cost and activity?",
    ]
    for question in questions:
        st.markdown(f"- {question}")

    st.subheader("Main descriptive findings")
    findings = [
        "Reported unit cost is strongly right-skewed: median £405 vs mean £1,874 -- the mean is misleading here.",
        "Low-activity providers show more variable reported unit costs; this is statistically expected, not evidence of poor performance.",
        "Specialist services (e.g. paediatric cardiac surgery, intermediate care, critical care transport) dominate the activity-weighted cost benchmark.",
        "NCCI is centred near 96 but has a long right tail (p99 ≈ 419) and needs formula validation before any efficiency use.",
        "Mapping_Pot groups differ descriptively in typical cost and total activity; this does not establish a causal MFF effect.",
    ]
    for finding in findings:
        st.markdown(f"- {finding}")

    render_disclaimer()


elif page == "Service costs":
    st.header("Service cost benchmarks")
    st.write(
        "These figures compare reported service costs using activity-weighted "
        "benchmarks and show why robust measures are preferred over simple means."
    )

    tabs = st.tabs(["Interactive benchmark", "Top services (weighted median)", "Distribution and skew"])
    with tabs[0]:
        render_interactive_service_costs()
    with tabs[1]:
        render_figure("Top services by weighted median cost")
    with tabs[2]:
        render_figure("Cost distribution and skew")

    st.subheader("Interpretation")
    st.write(
        "Activity-weighted median cost is the preferred high-level benchmark because it "
        "reflects both typical cost and the contribution of activity volume, without being "
        "dominated by extreme values the way a simple mean is. The distribution figure shows "
        "why: a handful of very high-cost specialist services pull the mean (£1,874) well "
        "above the median (£405)."
    )
    render_disclaimer()


elif page == "Provider variation":
    st.header("Provider activity and cost variation")
    st.write(
        "This figure examines whether reported unit costs become more dispersed "
        "when providers have low total activity."
    )

    render_figure("Provider variation by activity")

    st.subheader("Interpretation")
    st.write(
        "Providers with lower total activity show more scattered median unit costs. "
        "This is consistent with a small-sample/denominator effect, where a limited "
        "number of cases can substantially move a reported unit cost. It is a pattern "
        "requiring further investigation, not evidence that any provider performs poorly."
    )
    render_disclaimer()


elif page == "NCCI and variance":
    st.header("NCCI overview")
    st.write(
        "This section treats NCCI as a diagnostic variable rather than a "
        "direct efficiency score."
    )

    render_figure("NCCI overview")

    st.subheader("Interpretation")
    st.write(
        "NCCI is centred near a median of 96, with a long positive tail extending to "
        "roughly 419 at the 99th percentile. The shape suggests a typical central range "
        "with a meaningful minority of much higher values that warrant individual review."
    )

    st.subheader("Validation checks required")
    checks = [
        "Confirm the exact NCCI formula, denominator and scale.",
        "Count missing, zero and negative NCCI values.",
        "Review the highest NCCI records individually.",
        "Assess sensitivity to small expected costs (potential denominator effect).",
        "Reconcile Actual_Cost, Expected_Cost and Variance definitions.",
    ]
    for check in checks:
        st.markdown(f"- {check}")
    render_disclaimer()


elif page == "Mapping_Pot groups":
    st.header("Descriptive Mapping_Pot comparison")
    st.write(
        "This figure compares median unit cost and total activity across "
        "Mapping_Pot groups. Differences should be interpreted descriptively only."
    )

    render_figure("Mapping_Pot comparison")

    st.subheader("What may explain group differences?")
    explanations = [
        "Different service mixes.",
        "Different provider mixes.",
        "Differences in patient complexity.",
        "Regional or organisational variation.",
        "Different activity distributions.",
        "Cost allocation and reporting differences.",
    ]
    for explanation in explanations:
        st.markdown(f"- {explanation}")

    st.info(
        "Mapping_Pot is used here as a descriptive grouping variable. The figure "
        "does not establish that an MFF-related factor causes the observed cost differences."
    )


st.divider()
st.caption(
    "Exploratory analysis only | NHS NCC 2024/25 | Validate data definitions and account for case mix before making stronger claims"
)
st.caption("Data source: NHS National Cost Collection 2024/25. This dashboard is exploratory and should not be used as a standalone performance assessment.")