"""
generate_figures.py

Generates 5 consolidated, presentation-ready figures from the NHS Cost
Intelligence processed dataset, replacing the previous set of 10.

Design principles (per project guardrails):
- Median and activity-weighted median/mean are used as the primary summary
  statistics, NOT the simple mean, because Activity, Unit_Cost, Actual_Cost,
  Expected_Cost and NCCI are strongly right-skewed with extreme outliers.
- Every figure is captioned as descriptive evidence, not an efficiency or
  performance judgement.
- Figures are designed to be readable by both technical and non-technical
  audiences: clear titles, plain-language subtitles, minimal jargon.

Run from the repository root:
    python generate_figures.py

Outputs to: Figures/
    fig1_cost_distribution_skew.png
    fig2_top_services_median_cost.png
    fig3_provider_variation_by_activity.png
    fig4_ncci_overview.png
    fig5_mapping_pot_comparison.png

Update CSV_PATH below to your actual processed CSV filename.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "nhs_ncc_clean.csv"
FIGURES_DIR = PROJECT_ROOT / "Figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
})


def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Processed CSV not found at {CSV_PATH}. "
            "Update CSV_PATH in generate_figures.py."
        )
    df = pd.read_csv(CSV_PATH)
    valid = df[
        (df["Activity"] > 0)
        & df["Unit_Cost"].notna()
        & df["Service"].notna()
        & (df["Service"] != "999 - Unknown")
    ].copy()
    return df, valid


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cum_weights = np.cumsum(weights)
    cutoff = cum_weights[-1] / 2.0
    return values[np.searchsorted(cum_weights, cutoff)]


# ---------------------------------------------------------------------------
# Figure 1: Why median, not mean -- distribution skew
# ---------------------------------------------------------------------------
def fig1_distribution_skew(valid: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5))

    costs = valid["Unit_Cost"].clip(upper=valid["Unit_Cost"].quantile(0.99))
    ax.hist(costs, bins=60, color="#4C72B0", alpha=0.85)

    median_val = valid["Unit_Cost"].median()
    mean_val = valid["Unit_Cost"].mean()

    ax.axvline(median_val, color="#2E7D32", linewidth=2.5, label=f"Median: £{median_val:,.0f}")
    ax.axvline(mean_val, color="#C62828", linewidth=2.5, linestyle="--", label=f"Mean: £{mean_val:,.0f}")

    ax.set_title(
        "Reported unit costs are heavily skewed by a small number of very\n"
        "expensive services -- the mean is misleading here",
        fontsize=13, fontweight="bold", loc="left"
    )
    ax.set_xlabel("Reported unit cost (£, top 1% clipped for display)")
    ax.set_ylabel("Number of records")
    ax.legend(frameon=False, fontsize=10)
    fig.text(
        0.01, -0.02,
        "Plain-language takeaway: most services cost far less than the average suggests. "
        "A handful of very high-cost specialist services pull the mean upward. The median "
        "better represents a 'typical' record.",
        fontsize=9, color="#555555", wrap=True
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(FIGURES_DIR / "fig1_cost_distribution_skew.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2: Top services by activity-weighted median unit cost
# ---------------------------------------------------------------------------
def fig2_top_services(valid: pd.DataFrame, min_activity: int = 50, min_providers: int = 3) -> None:
    grouped = valid.groupby("Service").apply(
        lambda g: pd.Series({
            "total_activity": g["Activity"].sum(),
            "provider_count": g["Provider"].nunique(),
            "median_unit_cost": g["Unit_Cost"].median(),
            "weighted_median_unit_cost": weighted_median(
                g["Unit_Cost"].to_numpy(), g["Activity"].to_numpy()
            ),
        })
    ).reset_index()

    eligible = grouped[
        (grouped["total_activity"] >= min_activity)
        & (grouped["provider_count"] >= min_providers)
    ].sort_values("weighted_median_unit_cost", ascending=False).head(10)

    fig, ax = plt.subplots(figsize=(9, 6))
    eligible_sorted = eligible.sort_values("weighted_median_unit_cost")
    ax.barh(
        eligible_sorted["Service"].str.slice(0, 40),
        eligible_sorted["weighted_median_unit_cost"],
        color="#4C72B0",
    )
    ax.set_title(
        "The most expensive services, using a robust cost measure\n"
        "(activity-weighted median, not a simple average)",
        fontsize=13, fontweight="bold", loc="left"
    )
    ax.set_xlabel("Activity-weighted median unit cost (£)")
    fig.text(
        0.01, -0.05,
        "Plain-language takeaway: this is a descriptive cost benchmark, not an efficiency "
        "ranking. High-cost services are often specialist or complex care and this alone "
        "does not indicate waste or poor performance.",
        fontsize=9, color="#555555", wrap=True
    )
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(FIGURES_DIR / "fig2_top_services_median_cost.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: Provider-level cost variation vs activity volume
# ---------------------------------------------------------------------------
def fig3_provider_variation(valid: pd.DataFrame) -> None:
    provider_activity = valid.groupby("Provider")["Activity"].sum()
    provider_cost_median = valid.groupby("Provider")["Unit_Cost"].median()

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(
        provider_activity, provider_cost_median,
        alpha=0.5, s=28, color="#4C72B0", edgecolors="none"
    )
    ax.set_xscale("log")
    ax.set_title(
        "Providers with lower total activity report more variable costs",
        fontsize=13, fontweight="bold", loc="left"
    )
    ax.set_xlabel("Total provider activity (log scale)")
    ax.set_ylabel("Median reported unit cost (£)")
    fig.text(
        0.01, -0.02,
        "Plain-language takeaway: low-volume providers show more scattered costs. "
        "This is expected statistically (small samples are noisier) and is a pattern "
        "for further investigation, not evidence of poor performance.",
        fontsize=9, color="#555555", wrap=True
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(FIGURES_DIR / "fig3_provider_variation_by_activity.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4: NCCI overview (median-centred, trimmed for readability)
# ---------------------------------------------------------------------------
def fig4_ncci_overview(valid: pd.DataFrame) -> None:
    ncci = valid["NCCI"].dropna()
    trimmed = ncci[(ncci >= ncci.quantile(0.01)) & (ncci <= ncci.quantile(0.99))]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(trimmed, bins=60, color="#4C72B0", alpha=0.85)
    median_ncci = ncci.median()
    ax.axvline(median_ncci, color="#2E7D32", linewidth=2.5, label=f"Median NCCI: {median_ncci:.0f}")
    ax.legend(frameon=False, fontsize=10)
    ax.set_title(
        "NCCI (cost index) is centred near 100 but has a long tail\n"
        "of much higher values",
        fontsize=13, fontweight="bold", loc="left"
    )
    ax.set_xlabel("NCCI (1st-99th percentile shown)")
    ax.set_ylabel("Number of records")
    fig.text(
        0.01, -0.02,
        "Plain-language takeaway: NCCI is an index, not a validated efficiency score. "
        "Its formula and scale need confirmation before drawing performance conclusions "
        "from it.",
        fontsize=9, color="#555555", wrap=True
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(FIGURES_DIR / "fig4_ncci_overview.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5: Mapping_Pot group comparison (median cost + total activity)
# ---------------------------------------------------------------------------
def fig5_mapping_pot(valid: pd.DataFrame) -> None:
    grouped = valid.groupby("Mapping_Pot").agg(
        median_unit_cost=("Unit_Cost", "median"),
        total_activity=("Activity", "sum"),
    ).reset_index().sort_values("median_unit_cost", ascending=False).head(12)

    fig, ax1 = plt.subplots(figsize=(9.5, 6))
    x = np.arange(len(grouped))
    ax1.bar(x, grouped["median_unit_cost"], color="#4C72B0", alpha=0.85, label="Median unit cost (£)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(grouped["Mapping_Pot"].str.slice(0, 18), rotation=45, ha="right")
    ax1.set_ylabel("Median unit cost (£)")

    ax2 = ax1.twinx()
    ax2.plot(x, grouped["total_activity"], color="#C62828", marker="o", linewidth=2, label="Total activity")
    ax2.set_ylabel("Total activity")

    ax1.set_title(
        "Mapping_Pot groups differ in typical cost and total activity\n"
        "(descriptive comparison only)",
        fontsize=13, fontweight="bold", loc="left"
    )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, fontsize=9, loc="upper right")

    fig.text(
        0.01, -0.08,
        "Plain-language takeaway: these groups are descriptive categories, not causal "
        "cost drivers. Differences may reflect case mix, service type or reporting "
        "practices.",
        fontsize=9, color="#555555", wrap=True
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(FIGURES_DIR / "fig5_mapping_pot_comparison.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    _, valid = load_data()
    fig1_distribution_skew(valid)
    fig2_top_services(valid)
    fig3_provider_variation(valid)
    fig4_ncci_overview(valid)
    fig5_mapping_pot(valid)
    print(f"5 figures written to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()