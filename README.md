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

Computes Spearman rank correlations of win% between every pair of SEC teams,
restricted to the **10 programs that have been continuous members since 1950**:
Alabama, Auburn, Florida, Georgia, Kentucky, LSU, Mississippi State, Ole Miss,
Tennessee, and Vanderbilt. This ensures every correlation is computed over the
full 75-year period on equal footing. Red = tend to be good/bad in the same years;
Blue = inverse relationship (one up, the other down).

#### Key Findings

**Strongest inverse correlations (one team up, other down):**

| Pair | Correlation | Interpretation |
|---|---|---|
| Alabama vs Auburn | **−0.368** | Strongest inverse — historic rivals competing for same in-state recruits |
| Alabama vs Tennessee | **−0.368** | Tied — another fierce recruiting rival; inverse trend across 75 years |
| Auburn vs Georgia | **−0.280** | Moderate inverse across shared border recruiting territory |
| LSU vs Mississippi State | **−0.232** | Mild inverse within the SEC West |
| Florida vs Ole Miss | **−0.181** | Weak inverse |

**Strongest positive correlations (rise and fall together):**

| Pair | Correlation | Interpretation |
|---|---|---|
| Alabama vs Georgia | **+0.223** | Both tend to be strong in the same eras |
| Auburn vs LSU | **+0.219** | Parallel peaks and valleys over 75 years |
| Florida vs Tennessee | **+0.160** | Moderate positive |

- **All correlations are weak to moderate** (max |r| = 0.368), suggesting no pair of
  teams is tightly locked in a zero-sum relationship over the full 75-year span.
- **The recruiting competition hypothesis finds partial support**: the two strongest
  inverse correlations (Alabama–Auburn, Alabama–Tennessee) are exactly the traditional
  rivals who most directly compete for in-state and regional recruits. However, the
  effect size is modest.
- Notably, **Alabama–LSU** shows virtually no correlation (r = −0.001), despite being
  widely considered the premier SEC rivalry of the modern era — suggesting their peaks
  and valleys are largely independent over the full historical window.

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
