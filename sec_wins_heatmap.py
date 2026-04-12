import os
import time
from pathlib import Path

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CFBD_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"
CACHE_FILE = Path("data/sec_records.csv")
OUTPUT_FILE = Path("output/sec_wins_heatmap.png")

START_YEAR = 1950
END_YEAR = 2024


def fetch_sec_records() -> pd.DataFrame:
    """
    Fetch SEC team win records for every season from START_YEAR to END_YEAR.
    Results are cached to CACHE_FILE so the API is only called once.
    """
    if CACHE_FILE.exists():
        print(f"Loading cached data from {CACHE_FILE}")
        return pd.read_csv(CACHE_FILE)

    if not API_KEY or API_KEY == "your_api_key_here":
        raise ValueError("CFBD_API_KEY is not set in your .env file.")

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    records = []
    years = range(START_YEAR, END_YEAR + 1)

    print(f"Fetching SEC records {START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    for year in years:
        resp = requests.get(
            f"{BASE_URL}/records",
            headers=headers,
            params={"year": year, "conference": "SEC"},
            timeout=10,
        )

        if resp.status_code == 200:
            for entry in resp.json():
                records.append(
                    {
                        "year": year,
                        "team": entry["team"],
                        "wins": entry["total"]["wins"],
                    }
                )
        else:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")

        time.sleep(0.15)  # stay well within rate limits

    df = pd.DataFrame(records)
    df.to_csv(CACHE_FILE, index=False)
    print(f"Data saved to {CACHE_FILE}  ({len(df)} rows)")
    return df


def create_heatmap(df: pd.DataFrame) -> None:
    # Pivot: rows = teams, columns = years, values = wins
    pivot = df.pivot(index="team", columns="year", values="wins")

    # Sort teams by total wins descending so the strongest programs are at top
    pivot = pivot.loc[pivot.sum(axis=1, skipna=True).sort_values(ascending=False).index]

    # Mask cells where the team was not in the SEC that season
    mask = pivot.isna()

    fig, ax = plt.subplots(figsize=(28, 9))

    sns.heatmap(
        pivot,
        mask=mask,
        cmap="YlOrRd",
        vmin=0,
        vmax=13,
        linewidths=0.2,
        linecolor="#cccccc",
        annot=False,
        cbar_kws={"label": "Regular Season + Bowl Wins", "shrink": 0.6},
        ax=ax,
    )

    # Grey out seasons where a team was not in the SEC
    ax.set_facecolor("#d0d0d0")

    # Thin out x-axis labels — show every 5 years
    all_years = pivot.columns.tolist()
    ax.set_xticks(
        [i + 0.5 for i, y in enumerate(all_years) if y % 5 == 0]
    )
    ax.set_xticklabels(
        [y for y in all_years if y % 5 == 0],
        rotation=45,
        ha="right",
        fontsize=9,
    )

    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    ax.set_title(
        f"SEC Team Wins by Season ({START_YEAR}–{END_YEAR})\n"
        "Sorted by all-time SEC wins  |  Grey = not in SEC that season",
        fontsize=14,
        pad=14,
    )
    ax.set_xlabel("Season", fontsize=11, labelpad=8)
    ax.set_ylabel("", fontsize=11)

    plt.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Heatmap saved to {OUTPUT_FILE}")
    plt.show()


if __name__ == "__main__":
    df = fetch_sec_records()
    create_heatmap(df)
