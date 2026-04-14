"""
Fetches two datasets needed for NFL draft round prediction of WRs:

  1. College receiving stats (2010-2025)  — /stats/player/season?category=receiving
  2. NFL draft picks      (2010-2025)  — /draft/picks

API calls: 1 per year × 2 endpoints × 16 years ≈ 32 calls total.
Both datasets are cached; re-runs load from disk without hitting the API.
"""

import os
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("CFBD_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"

START_YEAR = 2010
END_YEAR   = 2025

STATS_FILE = Path("data/wr_receiving_stats.csv")
DRAFT_FILE = Path("data/wr_draft_picks.csv")

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


# ── Receiving stats ────────────────────────────────────────────────────────────

def fetch_receiving_stats() -> pd.DataFrame:
    """
    Returns one row per player per season with columns:
    year, player_id, player, team, conference,
    receptions, yards, touchdowns, long, yards_per_rec
    """
    if STATS_FILE.exists():
        print(f"Loading cached receiving stats from {STATS_FILE}")
        return pd.read_csv(STATS_FILE)

    Path("data").mkdir(exist_ok=True)
    years = range(START_YEAR, END_YEAR + 1)
    print(f"Fetching receiving stats {START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    all_records = []

    for year in years:
        resp = requests.get(
            f"{BASE_URL}/stats/player/season",
            headers=HEADERS,
            params={"year": year, "category": "receiving"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")
            time.sleep(0.15)
            continue

        # API returns one record per stat type per player — pivot into one row per player
        player_map: dict = {}
        for entry in resp.json():
            key = (entry.get("playerId", entry["player"]), year)
            if key not in player_map:
                player_map[key] = {
                    "year":        year,
                    "player_id":   entry.get("playerId"),
                    "player":      entry["player"],
                    "team":        entry["team"],
                    "conference":  entry.get("conference", ""),
                }
            player_map[key][entry["statType"].upper()] = entry["stat"]

        all_records.extend(player_map.values())
        print(f"  {year}: {len(player_map)} players with receiving stats")
        time.sleep(0.15)

    df = pd.DataFrame(all_records)

    # Normalise column names
    df = df.rename(columns={
        "REC":  "receptions",
        "YDS":  "yards",
        "TD":   "touchdowns",
        "LONG": "long",
        "AVG":  "yards_per_rec",
    })

    # Cast all stat columns to numeric (API returns them as strings)
    for col in ["receptions", "yards", "touchdowns", "long", "yards_per_rec"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derive yards_per_rec if the API didn't return it directly
    if "yards_per_rec" not in df.columns:
        df["yards_per_rec"] = (
            df["yards"] / df["receptions"].replace(0, pd.NA)
        ).round(2)

    # Drop noise: players with fewer than 5 receptions in a season
    df = df[df["receptions"] >= 5]

    df = df.sort_values(["year", "yards"], ascending=[True, False]).reset_index(drop=True)
    df.to_csv(STATS_FILE, index=False)
    print(f"Saved {len(df)} player-season rows to {STATS_FILE}\n")
    return df


# ── NFL Draft picks ────────────────────────────────────────────────────────────

def fetch_draft_picks() -> pd.DataFrame:
    """
    Returns one row per draft pick (all positions) with columns:
    draft_year, round, pick, overall, nfl_team,
    player, position, college, height, weight,
    college_athlete_id
    """
    if DRAFT_FILE.exists():
        print(f"Loading cached draft picks from {DRAFT_FILE}")
        return pd.read_csv(DRAFT_FILE)

    Path("data").mkdir(exist_ok=True)
    years = range(START_YEAR, END_YEAR + 1)
    print(f"Fetching NFL draft picks {START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    all_records = []

    for year in years:
        resp = requests.get(
            f"{BASE_URL}/draft/picks",
            headers=HEADERS,
            params={"year": year},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")
            time.sleep(0.15)
            continue

        picks = resp.json()
        for p in picks:
            all_records.append({
                "draft_year":         year,
                "round":              p.get("round"),
                "pick":               p.get("pick"),
                "overall":            p.get("overall"),
                "nfl_team":           p.get("nflTeam"),
                "player":             p.get("name"),
                "position":           p.get("position"),
                "college":            p.get("collegeTeam"),
                "college_conference": p.get("collegeConference"),
                "height":             p.get("height"),
                "weight":             p.get("weight"),
                "college_athlete_id": p.get("collegeAthleteId"),
                "pre_draft_grade":    p.get("preDraftGrade"),
            })

        print(f"  {year}: {len(picks)} picks")
        time.sleep(0.15)

    df = pd.DataFrame(all_records)
    df = df.sort_values(["draft_year", "overall"]).reset_index(drop=True)
    df.to_csv(DRAFT_FILE, index=False)
    print(f"Saved {len(df)} draft pick rows to {DRAFT_FILE}\n")
    return df


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(stats_df: pd.DataFrame, draft_df: pd.DataFrame) -> None:
    print("── Receiving Stats ─────────────────────────────────────────────────")
    print(f"  Seasons : {int(stats_df['year'].min())}–{int(stats_df['year'].max())}")
    print(f"  Rows    : {len(stats_df):,}  player-seasons")
    print(f"  Teams   : {stats_df['team'].nunique()}")
    top = stats_df.nlargest(5, "yards")[["year", "player", "team", "receptions", "yards", "touchdowns"]]
    print(f"\n  Top 5 receiving seasons by yards:\n{top.to_string(index=False)}\n")

    print("── Draft Picks ─────────────────────────────────────────────────────")
    wr = draft_df[draft_df["position"] == "Wide Receiver"]
    print(f"  Drafts  : {int(draft_df['draft_year'].min())}–{int(draft_df['draft_year'].max())}")
    print(f"  Total   : {len(draft_df):,} picks across all positions")
    print(f"  WR picks: {len(wr):,}")
    if len(wr):
        print(f"\n  WR picks by round:")
        print(wr["round"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    stats_df = fetch_receiving_stats()
    draft_df = fetch_draft_picks()
    print_summary(stats_df, draft_df)
