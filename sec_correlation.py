import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

CACHE_FILE = Path("data/sec_records.csv")
OUTPUT_FILE = Path("output/sec_correlation_heatmap.png")

START_YEAR = 1950
END_YEAR   = 2024


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


if __name__ == "__main__":
    df = load_data()
    corr, continuous = compute_correlation(df)
    create_heatmap(corr, continuous)
