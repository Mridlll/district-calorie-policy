# Final Deliverables — District Calorie-Aware Policy Action

All files in this folder use the calorie-aware Policy_Action (yield-quartile ×
district-level food-calorie tag matrix). The legacy yield-only Policy_Action is
NOT included here — it was error-prone and conflated yield-tier with policy
recommendation.

## Maps

| File | What it is |
|---|---|
| 01_irrigation_regime.png | Four-tier irrigation regime |
| 02_yield_quartiles.png | All-India composite yield quartiles (56 crops) |
| 03_yield_by_irrigation_panel.png | Yield quartiles within each irrigation regime |
| **04_policy_action.png** | **Policy_Action: yield × district calorie matrix (food crops, with coconut)** |
| **04_policy_action_ex_coconut.png** | Same, coconut excluded (sensitivity) |
| **05_policy_by_irrigation_panel.png** | Policy_Action panelled by irrigation regime |
| 06_rainfed_irrigated_x_yield_binary.png | Binary 2×2: rainfed/irrigated × high/low yield |
| 07_rainfed_irrigated_x_yield_panel.png | Same as 06, panelled |
| 08a-d | Each binary quadrant individually highlighted |
| 09a-d | All-irrigated / all-rainfed / all-high-yield / all-low-yield |
| **10_fert_overlap.png** | **Fertiliser top-25%-by-kg/ha vs Scale-Up overlap** |
| **10_fert_overlap_ex_coconut.png** | Same, calorie tag excluding coconut |

## Tables

| File | Contents |
|---|---|
| **district_master.xlsx** | 735-row district master: irrigation, yield quartile, calorie tag, **Policy_Action** (with and without coconut), NSA |
| **prof_df_with_district_calories.xlsx** | Full prof_df enriched with district-level food/no-coconut/total TKcal and z-tags |
| **fert_scaleup_overlap.xlsx** | Fertiliser top-25% × Scale-Up overlap tables (both calorie variants) + method note |
| district_classification_detail.xlsx | Rainfed/irrigated × high/low yield 2×2 classification per district |
| binary_summary.xlsx | Crosstabs behind the binary classification |
| district_calorie_production.csv | 725 districts × food/no-coconut/total TKcal, z-scores, Low/Medium/High tags |
| scaleup_districts.csv | The Scale-Up basket (food crops with coconut) — 263 districts |
| scaleup_districts_ex_coconut.csv | Scale-Up basket with calorie tag excluding coconut |
| state_rollup.csv | State-level counts of Scale-Up / Pilot / Avoid |

## Shapefile

`shapefile/in_district.{shp,shx,dbf,prj}` — India districts 2020 (735 districts,
WGS84 lat/lon). Self-contained; usable directly with geopandas.

## The Policy_Action matrix

Definition: yield × district-level food-calorie z-tag.

| Calorie tag | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| **Low**    (z<0)   | Scale Up | Scale Up | Pilot    | Avoid    |
| **Medium** (0≤z≤1) | Scale Up | Pilot    | Avoid    | Avoid    |
| **High**   (z>1)   | Pilot    | Avoid    | Avoid    | Avoid    |

- Q1-Q4 = all-India quartile of the 56-crop Composite_Score (yield).
- Calorie tag = z-score of district food-crop calorie production (TKcal),
  computed across the 725 production-positive districts. Built via the IFCT
  2017 reference table from `outputs/crop_diversity_analysis/district_diversity_calorie_merged.csv`
  (with the coconut nut→meat correction at 0.00015 t/nut).

## Headline numbers

- 263 Scale-Up districts (calorie-deficit + yield headroom)
- 129 Pilot
- 239 Avoid (mostly already-saturated calorie-rich districts)
- ~104 unmatched (small/new districts not in the calorie file)

Of FAI's top-25%-by-kg/ha fertiliser-intensive districts (80 total, 16 states):
**6 are Scale Up** — Vaishali, Araria, Supaul (Bihar); Raichur, Yadgir
(Karnataka); Sonbhadra (UP). These are the genuine policy red flags: heavy
fertiliser use that isn't translating into calorie security.

## Reproducibility

The full pipeline lives at `projects/district_calorie_policy/` and is
mirrored at https://github.com/Mridlll/district-calorie-policy.
