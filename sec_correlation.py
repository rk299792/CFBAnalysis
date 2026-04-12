import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

CACHE_FILE = Path("data/sec_records.csv")
OUTPUT_FILE = Path("output/sec_correlation_heatmap.png")

# Pairs with fewer shared SEC seasons than this are shown as NaN
MIN_OVERLAP_YEARS = 10


def load_data() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"{CACHE_FILE} not found. Run sec_wins_heatmap.py first to build the cache."
        )
    return pd.read_csv(CACHE_FILE)


def compute_correlation(df: pd.DataFrame):
    """
    Spearman rank correlation of win% between every pair of SEC teams,
    computed only over the seasons both teams were in the SEC.
    Pairs with fewer than MIN_OVERLAP_YEARS shared seasons are masked.
    """
    # Pivot so rows = seasons, columns = teams
    pivot = df.pivot(index="year", columns="team", values="win_pct")

    # Spearman is more robust than Pearson for bounded, non-normal win%
    corr = pivot.corr(method="spearman", min_periods=MIN_OVERLAP_YEARS)

    # Count shared seasons for each pair (for the subtitle annotation)
    overlap = pivot.notna().T.dot(pivot.notna()).astype(int)

    return corr, overlap


def create_heatmap(corr: pd.DataFrame, overlap: pd.DataFrame) -> None:
    teams = sorted(corr.columns)
    corr = corr.loc[teams, teams]
    overlap = overlap.loc[teams, teams]

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
        "SEC Team Win% Correlation (Spearman rank)\n"
        f"Red = tend to be good/bad together  |  Blue = inverse (one up, other down)"
        f"  |  Min. {MIN_OVERLAP_YEARS} shared SEC seasons required",
        fontsize=12,
        pad=14,
    )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.tick_params(axis="y", rotation=0, labelsize=9)

    # Footnote listing teams with limited overlap
    limited = [
        f"{t} ({int(overlap.loc[t].drop(t).min())} yrs min)"
        for t in teams
        if overlap.loc[t].drop(t).min() < 30
    ]
    if limited:
        fig.text(
            0.01, 0.01,
            "Limited overlap (<30 shared seasons): " + ", ".join(limited),
            fontsize=7, color="#555555",
        )

    plt.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Correlation heatmap saved to {OUTPUT_FILE}")
    plt.show()


if __name__ == "__main__":
    df = load_data()
    corr, overlap = compute_correlation(df)
    create_heatmap(corr, overlap)
