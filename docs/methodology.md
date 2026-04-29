# Methodology

## The two definitions of "Scale Up" in this project

**Definition A — yield-only (legacy).** Was used in:
- `outputs/ag_scaleup_maps_v2_with_WB/build_prof_df_with_WB.py`
- `notebooks/ag_scaleup_maps.ipynb`
- All downstream `summary_tables.xlsx`, `District_Master`, policy maps 04/05

```python
policy_map = {"Q4":"Scale Up", "Q3":"Scale Up", "Q2":"Pilot", "Q1":"Avoid"}
prof["Policy_Action"] = prof["Composite_Quartile"].map(policy_map)
```

The Composite_Score is a yield index across 56 crops. Composite_Quartile cuts
that score into all-India quartiles. Definition A says: top half by yield → Scale Up,
bottom quarter → Avoid. **No calorie / nutrition input.**

**Definition B — yield × calorie matrix.** Was defined in
`NEW_AG_SCALE_UP_MAPS.ipynb` but never run end-to-end with district-level
calorie data, never written to the canonical master sheet.

```python
def get_policy_action(row):
    q = row["composite_quartile"]
    c = row["calorie_tag"]
    return {
        "Low":    {"Q1":"Scale Up", "Q2":"Scale Up", "Q3":"Pilot", "Q4":"Avoid"},
        "Medium": {"Q1":"Scale Up", "Q2":"Pilot",    "Q3":"Avoid", "Q4":"Avoid"},
        "High":   {"Q1":"Pilot",    "Q2":"Avoid",    "Q3":"Avoid", "Q4":"Avoid"},
    }[c][q]
```

The intuition: Scale Up should target **calorie-deficit districts that have
yield headroom remaining**. High-yield + already-calorie-rich districts get
Avoid because there's nothing meaningful to push.

## What the notebook left unspecified

The notebook computes `calorie_tag` like this:

```python
district_calories["z_total_calories"] = zscore(district_calories["Total_Calories"])
district_calories["calorie_tag"] = pd.cut(
    district_calories["z_total_calories"],
    bins=[-np.inf, 0, 1, np.inf],
    labels=["Low", "Medium", "High"]
)
```

But the input `Total_Calories` column was uploaded interactively in Colab
and never saved into the project. The `prof_df` only carries STATE-LEVEL
calorie attributes (`State_ZScore_Total_TKcal`, `State_Total_Calorie_Level`)
broadcast onto each district. Running the notebook against state-broadcast
data would just give every district within a state the same tag — not what
the matrix is designed for.

## How this project produces real district-level tags

The crop-diversity project (`scripts/62_district_calorie_production.py`,
mirrored at github.com/Mridlll/crop-diversity) already has district-level
calorie production at `outputs/crop_diversity_analysis/district_diversity_calorie_merged.csv`.
It's built by:

1. Loading the 1997-2021 APY data (`all_crops_apy_1997_2021_india_data_portal.csv`)
2. Mapping each crop to a kcal/100g value from IFCT 2017
3. Special-casing coconut (production data is in number-of-nuts, mislabelled
   "tonnes"; convert at 0.00015 t edible meat per nut)
4. Filtering implausible yields (>200 t/ha for non-coconut)
5. Computing per-district `total_kcal_annual`, `food_crop_kcal_annual`,
   `coconut_kcal`, kcal shares per food group, etc.

This project's `01_build_district_calories.py` then:
- Converts kcal → TKcal (÷ 1e12)
- Computes z-scores across the 725 districts (production-positive)
- Tags Low / Medium / High using the same bins as the notebook

Three flavours produced (only `food_TKcal` and `food_no_coconut_TKcal` are
used downstream because non-food crops contribute 0):

| Flavour | What it is |
|---|---|
| `food_TKcal` | Food-crop calories: cereals + millets + pulses + oilseeds + sugar + vegetables + fruits + spices, **including coconut** |
| `food_no_coconut_TKcal` | Same but coconut subtracted |
| `total_TKcal` | All crops including non-food (=`food_TKcal` since non-food kcal=0) |

## Tagging distribution

Across 725 production-positive districts:

| Tag | n |
|---|---:|
| Low (z < 0) | 467 |
| Medium (0 ≤ z ≤ 1) | 205 |
| High (z > 1) | 53 |

The distribution is heavily right-skewed: a small number of mega-producing
districts (large WB rice districts, AP/TN coastal, Punjab) dominate national
production, so most districts are below the mean.

## Joining to the master prof_df

`02_apply_policy_matrix.py` fuzzy-matches each prof_df row (764 rows from
the legacy WB-patched master) to the calorie file (725 rows) using
rapidfuzz `token_sort_ratio ≥ 80` on (state, district), state-restricted.

Result: 650 of 764 prof rows matched. The 114 unmatched rows are mostly:
- Districts in prof_df not in the APY 1997-2021 dataset (newly-formed districts,
  some Telangana/Sikkim/NE)
- Spelling variants below the 80 threshold

Unmatched rows get NaN for the calorie tag and therefore NaN Policy_Action_DefB.

## Composite_Quartile-vs-tag crosstab

```
                         Q1   Q2   Q3   Q4
tag=Low                  ...  ...  ...  ...    -> Scale Up / Scale Up / Pilot / Avoid
tag=Medium               ...  ...  ...  ...    -> Scale Up / Pilot    / Avoid / Avoid
tag=High                 ...  ...  ...  ...    -> Pilot    / Avoid    / Avoid / Avoid
```

A naive expectation: tag and quartile correlate strongly (high producers tend
to be high yielders). They do — but not perfectly. The matrix's interesting
cells are:

- **Low + Q1 → Scale Up** (low yield, low calorie production: classic intervention target)
- **Low + Q2 → Scale Up** (sub-mean calorie, mid-low yield: still room to grow)
- **High + Q4 → Avoid** (Punjab/Haryana/coastal AP type: already maxed out)
- **Medium + Q4 → Avoid** (mid-calorie state, top yield: enough)

## Why Definition A and B disagree so much

Composite_Quartile and calorie tag are correlated but **far from identical**.
A district can be Q4 yield (top-of-class composite over 56 crops) while
producing relatively little total calorific output, because:
- The composite weights each crop's yield equally in z-score terms, regardless
  of total tonnage or calorie content
- A district producing modest amounts of high-yielding crops (e.g. a
  small horticulture-heavy district) can score Q4 on yield-rank but Low on
  total kcal output
- Conversely, a Bihar district can be middling on Composite_Score (Q2-Q3)
  but produce a lot of rice/wheat → Medium calorie tag

When the matrix forces both to align (Q3+Q4 must also be calorie-rich to be
Avoid; Q1+Q2 must also be calorie-poor to be Scale Up), the resulting
Policy_Action diverges sharply from the yield-only label. In our data:

- 231 DefA Scale-Up districts → DefB Avoid (mostly Q4-yield + Medium/High calorie)
- 144 DefA Avoid districts → DefB Scale Up (Q1-yield + Low calorie)
- Zero districts stayed "Scale Up" across both definitions

## What the legacy `summary_tables.xlsx` Policy_Action column means now

It is **yield-only**. If anyone has been treating that column as a
calorie-aware recommendation, they have been reading more into it than the
code does. This project's `district_master_DefA_DefB.xlsx` carries both
labels side-by-side so that downstream consumers can choose which to use.

## What's NOT done here (and why)

- **Within-state quartiles.** All quartiles are all-India. A within-state cut
  ("scale up the top half of *each* state regardless of national rank") would
  give a different answer; that's a separate analysis.
- **Within-irrigation quartiles.** Same.
- **Animal-source calories at district level.** Milk/eggs/meat/fish are
  state-level only in this project's underlying data; including them at
  district level would require a different data source.
- **Population-normalised tags** (per-capita kcal). Currently raw production
  z-scored. A per-capita version would change the tag for high-population
  districts (UP, Bihar) — likely shifting more of them into Low.
- **Time series.** Calorie production is 5-year average (2015-2019 in the
  underlying merged file). Yield composite is also a single-year snapshot.
  No trend / change-over-time policy view.

## Sensitivity to coconut

Coconut dominates production calories in 9 Kerala/coastal districts
(coconut_kcal_share > 50%). The `_foodnc` variant strips coconut and
re-z-scores. In our data the tag distribution is essentially identical
because z-scoring is robust to the heavy tail (coconut shifts a few districts
out of "High" but the bin counts are similar). For policy framing, both
variants give the same 263 Scale-Up districts.

If you want a stricter coconut sensitivity (re-rank composite score
ex-coconut as well), that's a deeper rebuild — not in scope here.
