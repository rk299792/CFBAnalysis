"""
Analyzes whether SEC teams' win% changed in the 10 years following
their university's desegregation, compared to the 10 years prior.

NOTE: This analysis reveals correlation only. Changes in performance
may reflect coaching turnover, recruiting shifts, conference dynamics,
or many other factors coinciding with desegregation.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import mannwhitneyu
from pathlib import Path

CACHE_FILE = Path("data/sec_records.csv")
OUTPUT_FILE = Path("output/sec_deseg_impact.png")
WINDOW = 10       # years before/after to compare
MIN_SEASONS = 5   # minimum seasons required in each window to include a team

# Desegregation years (first Black students admitted to main campus)
DESEG_YEARS = {
    "Alabama":           1963,
    "Arkansas":          1948,
    "Auburn":            1964,
    "Florida":           1962,
    "Georgia":           1961,
    "Kentucky":          1949,
    "LSU":               1964,
    "Mississippi State": 1965,
    "Missouri":          1950,
    "Ole Miss":          1962,
    "South Carolina":    1963,
    "Tennessee":         1961,
    "Texas A&M":         1963,
    "Vanderbilt":        1964,
    "Texas":             1950,
    "Oklahoma":          1949,
}


def load_data() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"{CACHE_FILE} not found. Run sec_wins_heatmap.py first."
        )
    return pd.read_csv(CACHE_FILE)


def compute_before_after(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each team with a known deseg year, compute:
      - pre_avg:  mean win% in the WINDOW seasons before desegregation
      - post_avg: mean win% in the WINDOW seasons after desegregation
      - delta:    post_avg - pre_avg  (negative = got worse)
      - p_value:  Mann-Whitney U test (two-sided)
    Only includes teams with at least MIN_SEASONS in both windows while
    they were members of the SEC.
    """
    pivot = df.pivot(index="year", columns="team", values="win_pct")
    results = []

    for team, deseg_year in DESEG_YEARS.items():
        if team not in pivot.columns:
            continue

        series = pivot[team].dropna()  # only seasons team was in SEC
        pre  = series[(series.index >= deseg_year - WINDOW) & (series.index < deseg_year)]
        post = series[(series.index >= deseg_year) & (series.index < deseg_year + WINDOW)]

        if len(pre) < MIN_SEASONS or len(post) < MIN_SEASONS:
            continue

        pre_avg  = pre.mean()
        post_avg = post.mean()
        delta    = post_avg - pre_avg

        # Mann-Whitney U: tests whether post distribution differs from pre
        _, p_value = mannwhitneyu(pre.values, post.values, alternative="two-sided")

        results.append({
            "team":       team,
            "deseg_year": deseg_year,
            "pre_avg":    round(pre_avg, 4),
            "post_avg":   round(post_avg, 4),
            "delta":      round(delta, 4),
            "pre_n":      len(pre),
            "post_n":     len(post),
            "p_value":    round(p_value, 4),
        })

    return pd.DataFrame(results).sort_values("delta")


def sig_label(p: float) -> str:
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def create_figure(results: pd.DataFrame, df: pd.DataFrame) -> None:
    fig, (ax_bar, ax_ts) = plt.subplots(
        1, 2, figsize=(18, 8),
        gridspec_kw={"width_ratios": [2, 1.4]}
    )

    # ── Panel 1: bar chart of delta for all teams ──────────────────────────
    colors = ["#c0392b" if d < 0 else "#27ae60" for d in results["delta"]]
    ole_miss_color = "#8e44ad"  # highlight Ole Miss in purple
    colors = [
        ole_miss_color if t == "Ole Miss" else c
        for t, c in zip(results["team"], colors)
    ]

    bars = ax_bar.barh(results["team"], results["delta"] * 100, color=colors, edgecolor="white")

    # Annotate bars with delta value and significance
    for bar, (_, row) in zip(bars, results.iterrows()):
        sig = sig_label(row["p_value"])
        label = f"{row['delta']*100:+.1f}%{sig}"
        x_pos = bar.get_width() + (0.3 if bar.get_width() >= 0 else -0.3)
        ha = "left" if bar.get_width() >= 0 else "right"
        ax_bar.text(x_pos, bar.get_y() + bar.get_height() / 2,
                    label, va="center", ha=ha, fontsize=8.5)

    ax_bar.axvline(0, color="black", linewidth=0.8)
    ax_bar.set_xlabel("Change in Win% (percentage points)", fontsize=10)
    ax_bar.set_title(
        f"Change in Win% in the {WINDOW} Years After Desegregation\n"
        "vs. the 10 Years Prior  |  * p<0.05  ** p<0.01 (Mann-Whitney)",
        fontsize=11, pad=10
    )
    ax_bar.tick_params(axis="y", labelsize=9)

    # Legend
    worse_patch  = mpatches.Patch(color="#c0392b",  label="Got worse")
    better_patch = mpatches.Patch(color="#27ae60",  label="Got better")
    om_patch     = mpatches.Patch(color=ole_miss_color, label="Ole Miss")
    ax_bar.legend(handles=[worse_patch, better_patch, om_patch],
                  fontsize=8, loc="lower right")

    # ── Panel 2: Ole Miss win% time series ────────────────────────────────
    pivot = df.pivot(index="year", columns="team", values="win_pct")
    om_deseg  = DESEG_YEARS["Ole Miss"]   # 1962

    # Restrict to exactly the 10-year windows used in the analysis
    om_series = pivot["Ole Miss"].dropna()
    om_series = om_series[
        (om_series.index >= om_deseg - WINDOW) &
        (om_series.index <  om_deseg + WINDOW)
    ]

    # Rolling 3-year average to smooth noise
    om_roll = om_series.rolling(3, center=True, min_periods=2).mean()

    ax_ts.plot(om_series.index, om_series.values * 100,
               color="#cccccc", linewidth=1, zorder=1, label="Season win%")
    ax_ts.plot(om_roll.index, om_roll.values * 100,
               color=ole_miss_color, linewidth=2.2, zorder=2, label="3-yr rolling avg")
    ax_ts.axvline(om_deseg, color="black", linewidth=1.5, linestyle="--", zorder=3)
    ax_ts.axvspan(om_deseg, om_deseg + WINDOW, alpha=0.08, color="#c0392b",
                  label=f"10 yrs post-deseg")
    ax_ts.axvspan(om_deseg - WINDOW, om_deseg, alpha=0.08, color="#27ae60",
                  label=f"10 yrs pre-deseg")

    # Annotate before/after averages
    om_row = results[results["team"] == "Ole Miss"].iloc[0]
    ax_ts.axhline(om_row["pre_avg"] * 100, color="#27ae60",
                  linewidth=1, linestyle=":", alpha=0.8)
    ax_ts.axhline(om_row["post_avg"] * 100, color="#c0392b",
                  linewidth=1, linestyle=":", alpha=0.8)
    ax_ts.text(om_deseg - WINDOW + 0.3, om_row["pre_avg"] * 100 + 1.5,
               f"Pre avg: {om_row['pre_avg']*100:.1f}%", fontsize=8, color="#27ae60")
    ax_ts.text(om_deseg + 0.3, om_row["post_avg"] * 100 + 1.5,
               f"Post avg: {om_row['post_avg']*100:.1f}%", fontsize=8, color="#c0392b")

    ax_ts.set_xlim(om_deseg - WINDOW - 0.5, om_deseg + WINDOW - 0.5)
    ax_ts.set_ylim(0, 105)
    ax_ts.set_xlabel("Season", fontsize=10)
    ax_ts.set_ylabel("Win %", fontsize=10)
    ax_ts.set_title(
        f"Ole Miss Win% Around Desegregation ({om_deseg})\n"
        f"Δ = {om_row['delta']*100:+.1f} pp  |  p = {om_row['p_value']:.3f}",
        fontsize=11, pad=10
    )
    ax_ts.legend(fontsize=8, loc="upper right")
    ax_ts.tick_params(labelsize=9)

    fig.suptitle(
        "Did SEC Teams Get Worse After University Desegregation?",
        fontsize=14, fontweight="bold", y=1.01
    )

    fig.text(
        0.5, -0.02,
        "Note: Correlation only — changes may reflect coaching turnover, "
        "recruiting shifts, conference dynamics, or other concurrent factors.",
        ha="center", fontsize=8, color="#555555"
    )

    plt.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Figure saved to {OUTPUT_FILE}")
    plt.show()


if __name__ == "__main__":
    df = load_data()
    results = compute_before_after(df)

    print("\n── Before/After Desegregation (win%) ──────────────────────────────")
    print(results.to_string(index=False))

    create_figure(results, df)
