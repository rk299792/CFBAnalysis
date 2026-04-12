import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

CACHE_FILE       = Path("data/sec_records.csv")
OUTPUT_FILE      = Path("output/sec_correlation_heatmap.png")
TIMESERIES_FILE  = Path("output/sec_rivals_timeseries.png")

# Pairs to highlight in the time series (strongest inverse correlations)
RIVAL_PAIRS = [
    ("Alabama", "Auburn"),
    ("Alabama", "Tennessee"),
]

TEAM_COLORS = {
    "Alabama":   "#9E1B32",   # crimson
    "Auburn":    "#0C2340",   # navy
    "Tennessee": "#FF8200",   # orange
}

START_YEAR = 1950
END_YEAR   = 2025


def load_data() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"{CACHE_FILE} not found. Run sec_wins_heatmap.py first to build the cache."
        )
    return pd.read_csv(CACHE_FILE)


def compute_correlation(df: pd.DataFrame):
    """
    Spearman rank correlation of win% between every pair of SEC teams,
    restricted to teams that have been continuous SEC members from
    START_YEAR through END_YEAR (no gaps, no mid-period joiners/leavers).
    """
    pivot = df.pivot(index="year", columns="team", values="win_pct")

    all_years = set(range(START_YEAR, END_YEAR + 1))
    total_seasons = len(all_years)

    # Keep only teams present in every season from START_YEAR to END_YEAR
    continuous = [
        team for team in pivot.columns
        if pivot[team].notna().sum() == total_seasons
        and pivot[team].first_valid_index() == START_YEAR
        and pivot[team].last_valid_index()  == END_YEAR
    ]
    continuous.sort()
    print(f"Continuous SEC members ({START_YEAR}–{END_YEAR}): {', '.join(continuous)}")

    pivot = pivot[continuous]

    # Spearman is more robust than Pearson for bounded, non-normal win%
    corr = pivot.corr(method="spearman")

    return corr, continuous


def create_heatmap(corr: pd.DataFrame, teams: list) -> None:
    corr = corr.loc[teams, teams]

    # Mask the upper triangle (matrix is symmetric)
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

    fig, ax = plt.subplots(figsize=(14, 12))

    sns.heatmap(
        corr,
        mask=mask,
        cmap="RdBu_r",
        vmin=-1.0,
        vmax=1.0,
        center=0,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 7.5},
        linewidths=0.4,
        linecolor="#cccccc",
        cbar_kws={"label": "Spearman Correlation", "shrink": 0.55},
        ax=ax,
    )

    ax.set_title(
        f"SEC Team Win% Correlation (Spearman rank)  |  {START_YEAR}–{END_YEAR}\n"
        "Continuous members only  |  Red = tend to rise/fall together  |  Blue = inverse",
        fontsize=12,
        pad=14,
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", rotation=0, labelsize=9)

    plt.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Correlation heatmap saved to {OUTPUT_FILE}")
    plt.show()


def create_rivals_timeseries(df: pd.DataFrame, corr: pd.DataFrame) -> None:
    """
    Two-panel time series showing win% for each rival pair side by side.
    The area between the lines is shaded to make divergence visible.
    """
    pivot = df.pivot(index="year", columns="team", values="win_pct")
    years = pivot.index.tolist()

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

    for ax, (team_a, team_b) in zip(axes, RIVAL_PAIRS):
        ca, cb = TEAM_COLORS[team_a], TEAM_COLORS[team_b]
        s_a = pivot[team_a] * 100
        s_b = pivot[team_b] * 100

        # 3-year rolling averages
        r_a = s_a.rolling(3, center=True, min_periods=2).mean()
        r_b = s_b.rolling(3, center=True, min_periods=2).mean()

        # Raw season lines (faint)
        ax.plot(years, s_a, color=ca, alpha=0.25, linewidth=0.8)
        ax.plot(years, s_b, color=cb, alpha=0.25, linewidth=0.8)

        # Rolling average lines
        ax.plot(years, r_a, color=ca, linewidth=2.2, label=f"{team_a} (3-yr avg)")
        ax.plot(years, r_b, color=cb, linewidth=2.2, label=f"{team_b} (3-yr avg)")

        # Shade between: team_a colour when a > b, team_b colour when b > a
        ax.fill_between(years, r_a, r_b,
                        where=(r_a >= r_b), interpolate=True,
                        alpha=0.15, color=ca)
        ax.fill_between(years, r_a, r_b,
                        where=(r_b > r_a), interpolate=True,
                        alpha=0.15, color=cb)

        r_val = corr.loc[team_a, team_b]
        ax.set_title(
            f"{team_a} vs {team_b}  |  Spearman r = {r_val:.3f}",
            fontsize=12, pad=8
        )
        ax.set_ylabel("Win %", fontsize=10)
        ax.set_ylim(0, 105)
        ax.legend(fontsize=9, loc="upper left")
        ax.tick_params(labelsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    axes[-1].set_xlabel("Season", fontsize=10)
    xticks = [y for y in years if y % 5 == 0]
    axes[-1].set_xticks(xticks)
    axes[-1].set_xticklabels(xticks, rotation=45, ha="right", fontsize=9)

    fig.suptitle(
        f"Alabama vs Its Strongest Inverse-Correlated Rivals ({START_YEAR}–{END_YEAR})\n"
        "Shaded area shows which team was ahead  |  Faint lines = individual seasons",
        fontsize=13, fontweight="bold", y=1.01
    )

    plt.tight_layout()
    TIMESERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(TIMESERIES_FILE, dpi=150, bbox_inches="tight")
    print(f"Rivals time series saved to {TIMESERIES_FILE}")
    plt.show()


if __name__ == "__main__":
    df = load_data()
    corr, continuous = compute_correlation(df)
    create_heatmap(corr, continuous)
    create_rivals_timeseries(df, corr)
