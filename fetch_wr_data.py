"""
Fetches all datasets needed for NFL draft round prediction of WRs:

  1. Receiving stats  (2010-2025) — /stats/player/season?category=receiving
  2. NFL draft picks  (2010-2025) — /draft/picks
  3. Recruiting info  (2006-2025) — /recruiting/players?position=WR
       → height, weight, star rating, national rank
  4. Player usage     (2010-2025) — /player/usage?position=WR
       → overall/3rd-down/passing-down target share
  5. PPA metrics      (2010-2025) — /ppa/players/season?position=WR
       → average & total predicted points added (efficiency)

NOTE: 40-yard dash times are NFL Combine data and are not available
      through the CFBD API. A separate data source would be required.

API calls: ~84 total. All datasets cached; re-runs load from disk.
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

STATS_FILE     = Path("data/wr_receiving_stats.csv")
DRAFT_FILE     = Path("data/wr_draft_picks.csv")
RECRUITS_FILE  = Path("data/wr_recruits.csv")
USAGE_FILE     = Path("data/wr_usage.csv")
PPA_FILE       = Path("data/wr_ppa.csv")

# Recruiting classes run ~4 years before a player's final season
RECRUIT_START_YEAR = 2006

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


# ── Recruiting data (height / weight / stars / rank) ──────────────────────────

def fetch_recruiting_data() -> pd.DataFrame:
    """
    Returns one row per WR recruit with columns:
    recruit_year, athlete_id, name, committed_to, height_in, weight_lbs,
    stars, rating, national_rank, recruit_type
    """
    if RECRUITS_FILE.exists():
        print(f"Loading cached recruiting data from {RECRUITS_FILE}")
        return pd.read_csv(RECRUITS_FILE)

    Path("data").mkdir(exist_ok=True)
    years = range(RECRUIT_START_YEAR, END_YEAR + 1)
    print(f"Fetching WR recruiting data {RECRUIT_START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    all_records = []
    for year in years:
        resp = requests.get(
            f"{BASE_URL}/recruiting/players",
            headers=HEADERS,
            params={"year": year, "position": "WR"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")
            time.sleep(0.15)
            continue

        for r in resp.json():
            all_records.append({
                "recruit_year":   year,
                "recruit_id":     r.get("id"),
                "athlete_id":     r.get("athleteId"),
                "name":           r.get("name"),
                "committed_to":   r.get("committedTo"),
                "recruit_type":   r.get("recruitType"),
                "height_in":      r.get("height"),
                "weight_lbs":     r.get("weight"),
                "stars":          r.get("stars"),
                "rating":         r.get("rating"),
                "national_rank":  r.get("ranking"),
                "state":          r.get("stateProvince"),
            })

        print(f"  {year}: {len(resp.json())} WR recruits")
        time.sleep(0.15)

    df = pd.DataFrame(all_records)
    df = df.sort_values(["recruit_year", "national_rank"]).reset_index(drop=True)
    df.to_csv(RECRUITS_FILE, index=False)
    print(f"Saved {len(df)} WR recruit rows to {RECRUITS_FILE}\n")
    return df


# ── Usage metrics (target share / down-and-distance breakdown) ─────────────────

def fetch_usage_data() -> pd.DataFrame:
    """
    Returns one row per WR per season with columns:
    year, player_id, player, team, conference,
    usage_overall, usage_pass, usage_first_down, usage_second_down,
    usage_third_down, usage_standard_downs, usage_passing_downs
    """
    if USAGE_FILE.exists():
        print(f"Loading cached usage data from {USAGE_FILE}")
        return pd.read_csv(USAGE_FILE)

    Path("data").mkdir(exist_ok=True)
    years = range(START_YEAR, END_YEAR + 1)
    print(f"Fetching WR usage data {START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    all_records = []
    for year in years:
        resp = requests.get(
            f"{BASE_URL}/player/usage",
            headers=HEADERS,
            params={"year": year, "position": "WR"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")
            time.sleep(0.15)
            continue

        for p in resp.json():
            u = p.get("usage") or {}
            all_records.append({
                "year":                  year,
                "player_id":             p.get("id"),
                "player":                p.get("name"),
                "team":                  p.get("team"),
                "conference":            p.get("conference"),
                "usage_overall":         u.get("overall"),
                "usage_pass":            u.get("pass"),
                "usage_first_down":      u.get("firstDown"),
                "usage_second_down":     u.get("secondDown"),
                "usage_third_down":      u.get("thirdDown"),
                "usage_standard_downs":  u.get("standardDowns"),
                "usage_passing_downs":   u.get("passingDowns"),
            })

        print(f"  {year}: {len(resp.json())} WR usage records")
        time.sleep(0.15)

    df = pd.DataFrame(all_records)
    df = df.sort_values(["year", "usage_overall"], ascending=[True, False]).reset_index(drop=True)
    df.to_csv(USAGE_FILE, index=False)
    print(f"Saved {len(df)} WR usage rows to {USAGE_FILE}\n")
    return df


# ── PPA metrics (predicted points added — efficiency) ─────────────────────────

def fetch_ppa_data() -> pd.DataFrame:
    """
    Returns one row per WR per season with columns:
    year, player_id, player, team, conference, countable_plays,
    avg_ppa_all, avg_ppa_pass, avg_ppa_third_down, avg_ppa_passing_downs,
    total_ppa_all, total_ppa_pass
    """
    if PPA_FILE.exists():
        print(f"Loading cached PPA data from {PPA_FILE}")
        return pd.read_csv(PPA_FILE)

    Path("data").mkdir(exist_ok=True)
    years = range(START_YEAR, END_YEAR + 1)
    print(f"Fetching WR PPA data {START_YEAR}–{END_YEAR} ({len(years)} API calls)...")

    all_records = []
    for year in years:
        resp = requests.get(
            f"{BASE_URL}/ppa/players/season",
            headers=HEADERS,
            params={"year": year, "position": "WR", "threshold": 20},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Warning: {year} returned HTTP {resp.status_code}, skipping.")
            time.sleep(0.15)
            continue

        for p in resp.json():
            avg = p.get("averagePPA") or {}
            tot = p.get("totalPPA") or {}
            all_records.append({
                "year":                  p.get("season"),
                "player_id":             p.get("id"),
                "player":                p.get("name"),
                "team":                  p.get("team"),
                "conference":            p.get("conference"),
                "countable_plays":       p.get("countablePlays"),
                "avg_ppa_all":           avg.get("all"),
                "avg_ppa_pass":          avg.get("pass"),
                "avg_ppa_first_down":    avg.get("firstDown"),
                "avg_ppa_second_down":   avg.get("secondDown"),
                "avg_ppa_third_down":    avg.get("thirdDown"),
                "avg_ppa_passing_downs": avg.get("passingDowns"),
                "total_ppa_all":         tot.get("all"),
                "total_ppa_pass":        tot.get("pass"),
            })

        print(f"  {year}: {len(resp.json())} WR PPA records")
        time.sleep(0.15)

    df = pd.DataFrame(all_records)
    df = df.sort_values(["year", "total_ppa_all"], ascending=[True, False]).reset_index(drop=True)
    df.to_csv(PPA_FILE, index=False)
    print(f"Saved {len(df)} WR PPA rows to {PPA_FILE}\n")
    return df


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(stats_df, draft_df, recruits_df, usage_df, ppa_df) -> None:
    print("── Receiving Stats ─────────────────────────────────────────────────")
    print(f"  Seasons : {int(stats_df['year'].min())}–{int(stats_df['year'].max())}")
    print(f"  Rows    : {len(stats_df):,} player-seasons")
    print(f"  Teams   : {stats_df['team'].nunique()}")
    top = stats_df.nlargest(5, "yards")[["year", "player", "team", "receptions", "yards", "touchdowns"]]
    print(f"\n  Top 5 seasons by yards:\n{top.to_string(index=False)}\n")

    print("── Draft Picks ─────────────────────────────────────────────────────")
    wr = draft_df[draft_df["position"] == "Wide Receiver"]
    print(f"  Drafts  : {int(draft_df['draft_year'].min())}–{int(draft_df['draft_year'].max())}")
    print(f"  Total   : {len(draft_df):,} picks (all positions)")
    print(f"  WR picks: {len(wr):,}")
    print(f"  WR by round:\n{wr['round'].value_counts().sort_index().to_string()}\n")

    print("── Recruiting (physical attributes) ────────────────────────────────")
    hs = recruits_df[recruits_df["recruit_type"] == "HighSchool"]
    print(f"  Classes : {int(recruits_df['recruit_year'].min())}–{int(recruits_df['recruit_year'].max())}")
    print(f"  Rows    : {len(recruits_df):,} WR recruits  ({len(hs):,} HS)")
    print(f"  Avg height : {hs['height_in'].mean():.1f} in  |  Avg weight: {hs['weight_lbs'].mean():.1f} lbs")
    print(f"  Stars breakdown:\n{hs['stars'].value_counts().sort_index().to_string()}\n")

    print("── Usage Metrics ───────────────────────────────────────────────────")
    print(f"  Seasons : {int(usage_df['year'].min())}–{int(usage_df['year'].max())}")
    print(f"  Rows    : {len(usage_df):,} WR player-seasons")
    print(f"  Avg 3rd-down usage : {usage_df['usage_third_down'].mean():.3f}\n")

    print("── PPA Metrics ─────────────────────────────────────────────────────")
    print(f"  Seasons : {int(ppa_df['year'].min())}–{int(ppa_df['year'].max())}")
    print(f"  Rows    : {len(ppa_df):,} WR player-seasons")
    print(f"  Avg PPA (all) : {ppa_df['avg_ppa_all'].mean():.3f}")


if __name__ == "__main__":
    stats_df    = fetch_receiving_stats()
    draft_df    = fetch_draft_picks()
    recruits_df = fetch_recruiting_data()
    usage_df    = fetch_usage_data()
    ppa_df      = fetch_ppa_data()
    print_summary(stats_df, draft_df, recruits_df, usage_df, ppa_df)
