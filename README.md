# CFB Analysis

A Python project exploring SEC college football performance trends from 1950 to 2024.
Data is sourced from the [College Football Data API](https://collegefootballdata.com).

---

## Analyses & Findings

### 1. SEC Win Percentage Heatmap (1950–2024)

**Script:** `sec_wins_heatmap.py`
**Output:** `output/sec_winpct_heatmap.png`

Visualizes every SEC team's win percentage by season across 75 years. Teams are sorted
top-to-bottom by their all-time average win percentage in the SEC. Grey cells indicate
seasons a team was not a conference member. A downward triangle (▼) marks the year each
university first admitted Black students.

#### Key Findings

- **Alabama** is the all-time leader in SEC win percentage at **73.3%**, followed by
  Georgia (66.3%), Tennessee (64.4%), Florida (64.2%), and LSU (63.6%).
- **Vanderbilt** has the lowest all-time average at **33.0%**, consistent across all eras.
- Alabama shows two clear peaks: the **Bryant era (1960s–70s)** with an average win%
  of 81.8% and 85.8% respectively, and the **Saban era (2010s–present)** at 89.0% —
  the highest single-decade average of any team in the dataset.
- **Ole Miss's 1962 season** (100% win rate) stands out as a high point immediately
  before the university's court-ordered desegregation that same year.
- Newer members Missouri (2012) and Texas A&M (2012) are visible as shorter rows on
  the right side of the chart; Texas and Oklahoma (2024) appear as single-season entries.

---

### 2. Pairwise Win% Correlation Matrix

**Script:** `sec_correlation.py`
**Output:** `output/sec_correlation_heatmap.png`

Computes Spearman rank correlations of win% between every pair of SEC teams, using
only the seasons both teams were active in the conference. Pairs with fewer than
10 shared seasons are masked. Red = tend to be good/bad in the same years;
Blue = inverse relationship (one up, the other down).

#### Key Findings

| Pair | Correlation | Interpretation |
|---|---|---|
| Tulane vs Vanderbilt | **+0.780** | Strongest positive — both historically weak; rose and fell together |
| Tennessee vs Tulane | **+0.623** | Strong positive during overlapping SEC years (1950–1965) |
| Tennessee vs Texas A&M | **−0.640** | Strongest inverse in the dataset |
| Florida vs Missouri | **−0.542** | Moderate inverse since Missouri joined in 2012 |
| Alabama vs Missouri | **−0.480** | Alabama's dominant years coincide with Missouri's weaker ones |

- **The recruiting competition hypothesis finds limited support** in the data. Most
  traditional rivals (Alabama–LSU, Alabama–Georgia, Alabama–Auburn) show weak-to-moderate
  correlations rather than the strong inverse relationship the hypothesis predicts.
- Correlations involving newer members (Missouri, Texas A&M, Texas, Oklahoma) should be
  interpreted cautiously due to limited shared seasons (1–13 years).

---

### 3. Desegregation Impact on Win Percentage

**Script:** `sec_deseg_impact.py`
**Output:** `output/sec_deseg_impact.png`

For each SEC team, compares the average win percentage in the **10 seasons before**
versus the **10 seasons after** the university's desegregation. Statistical significance
is assessed using the Mann-Whitney U test (non-parametric, two-sided).

Teams with fewer than 5 seasons of SEC data in either window were excluded
(Arkansas, Kentucky, Oklahoma, Missouri, Texas, Texas A&M, South Carolina).

#### Results by Team

| Team | Deseg. Year | Pre-Deseg Win% | Post-Deseg Win% | Change | Significant? |
|---|---|---|---|---|---|
| Ole Miss | 1962 | 81.3% | 69.0% | **−12.3 pp** | ✅ p = 0.043 |
| Mississippi State | 1965 | 43.1% | 32.0% | −11.1 pp | ✗ p = 0.185 |
| Auburn | 1964 | 75.7% | 64.6% | −11.1 pp | ✗ p = 0.209 |
| Vanderbilt | 1964 | 36.5% | 31.5% | −5.0 pp | ✗ p = 0.541 |
| Tennessee | 1961 | 63.2% | 66.4% | +3.2 pp | ✗ p = 0.646 |
| Georgia | 1961 | 49.2% | 54.6% | +5.5 pp | ✗ p = 0.423 |
| Florida | 1962 | 54.6% | 64.1% | +9.5 pp | ✗ p = 0.170 |
| LSU | 1964 | 62.4% | 72.2% | +9.8 pp | ✗ p = 0.493 |
| Alabama | 1963 | 50.4% | 78.0% | **+27.6 pp** | ✅ p = 0.044 |

#### Key Findings

- **Ole Miss** is the only team to show a **statistically significant decline** after
  desegregation (−12.3 percentage points, p = 0.043). Their win% fell from a peak
  era — including a perfect 1962 season — to a sustained period of mediocrity through
  the early 1970s.
- **Alabama** shows the largest and most statistically significant *improvement*
  (+27.6 pp, p = 0.044). This coincides almost entirely with Bear Bryant's tenure
  and his decision to integrate the program in 1971 — Alabama's win% in the 1970s
  reached 85.8%.
- **7 of 9 teams** show no statistically significant change in either direction,
  suggesting desegregation year alone does not reliably predict a shift in on-field
  performance.

#### Important Caveat

> This analysis identifies correlation, not causation. Changes in team performance
> during these windows may reflect coaching transitions, recruiting dynamics, conference
> realignment, and many other factors concurrent with desegregation. The findings
> should be interpreted as a starting point for historical inquiry, not as evidence
> of a direct causal relationship.

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API key to .env
echo 'CFBD_API_KEY=your_key_here' > .env

# Run analyses (data is cached after first run — no repeated API calls)
python sec_wins_heatmap.py
python sec_correlation.py
python sec_deseg_impact.py
```

## Data Source

All data is fetched from the [College Football Data API](https://collegefootballdata.com)
and cached locally in `data/sec_records.csv` after the first run.
