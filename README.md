# District Calorie-Aware Policy Action

Calorie-aware Scale Up / Pilot / Avoid classification for ~735 Indian districts,
combining (a) all-India yield quartiles from a 56-crop composite score with
(b) district-level food-calorie production tags (z-scored across districts using
the canonical IFCT 2017 kcal table). Replaces the legacy yield-only Policy_Action
column in `outputs/ag_scaleup_maps_v2_with_WB/summary_tables.xlsx`.

## Background — what this fixes

The legacy pipeline (`outputs/ag_scaleup_maps_v2_with_WB/build_prof_df_with_WB.py`)
defined Policy_Action purely from yield:

    Q4 -> Scale Up
    Q3 -> Scale Up
    Q2 -> Pilot
    Q1 -> Avoid

That logic ignored calorie/nutritional security entirely. A separate Colab
notebook (`NEW_AG_SCALE_UP_MAPS.ipynb`) had a calorie-aware matrix but was
never run end-to-end with district-level inputs and was never written back into
the canonical `summary_tables.xlsx`.

This project re-runs the calorie-aware logic with **real district-level
calorie tags** (built from the existing `crop_diversity_analysis` pipeline,
which uses the IFCT 2017 reference and corrects coconut units), regenerates
all downstream maps, and re-runs the fertiliser-vs-Scale-Up overlap.

## The matrix (Definition B)

| Calorie tag | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| **Low**    | Scale Up | Scale Up | Pilot    | Avoid    |
| **Medium** | Scale Up | Pilot    | Avoid    | Avoid    |
| **High**   | Pilot    | Avoid    | Avoid    | Avoid    |

- **Q1-Q4** = `Composite_Quartile` (all-India quartile of the 56-crop yield composite score)
- **Calorie tag** = z-scored district food-crop calorie production:
  - Low: z < 0
  - Medium: 0 ≤ z ≤ 1
  - High: z > 1

Two calorie variants are produced:
- `tag_food` — food-crop kcal including coconut
- `tag_food_nc` — food-crop kcal excluding coconut (sensitivity)

## Headline result

Among ~620 successfully matched districts:

|              | Definition A (yield-only) | Definition B (yield × calorie) |
|---|---:|---:|
| Scale Up     | 340 | 263 |
| Pilot        | 183 | 129 |
| Avoid        | 172 | 239 |

**Zero districts remained "Scale Up" between definitions.** Every legacy
Scale-Up district either drops to Pilot (88) or Avoid (231) under the
calorie-aware rule. Conversely, **144 legacy-Avoid districts (calorie-poor,
low-yield) become Scale Up** — exactly the demographic the policy framing
should target.

### Fertiliser overlap

Top quartile of FAI 2021-22 districts by kg/ha (N+P₂O₅+K₂O), threshold 229.9 kg/ha:

|              | High-fert districts that are Scale Up |
|---|---:|
| DefA (yield-only)        | 63 / 80  (79%) |
| DefB_food                | 6 / 80   (8%)  |
| DefB_foodnc              | 6 / 80   (8%)  |

Under DefB the six high-fert + Scale-Up districts are the genuine policy red
flags — districts where high input use is **not yet** translating to calorie
security:

- **Bihar:** Vaishali (409 kg/ha), Araria (287), Supaul (248)
- **Karnataka:** Raichur (275), Yadgir (244)
- **Uttar Pradesh:** Sonbhadra (244)

The Punjab/Haryana/Tamil-Nadu cluster that dominated the DefA overlap (Vellore
786, Yamunanagar 386, Kurukshetra 384, Ludhiana, Sangrur, Patiala…) is
correctly classified as **Avoid** under DefB — already calorie-secure and
heavily fertilised; pushing more is not a policy priority.

## Data sources

| Input | Source | Path |
|---|---|---|
| Yield composite + irrigation | Legacy `prof_df_with_WB` pipeline | `outputs/ag_scaleup_maps_v2_with_WB/prof_df_with_WB.xlsx` |
| District food-calorie production | crop_diversity_analysis pipeline (IFCT 2017, coconut nut→meat fix at 0.00015 t/nut) | `outputs/crop_diversity_analysis/district_diversity_calorie_merged.csv` |
| Fertiliser intensity | FAI 2021-22 Statbook (320 districts, 16 states only) | `outputs/Fertiliser use_District level data.xlsx` |
| Net Sown Area | irrigation_aggregates | `irrigation_aggregates.xlsx` |
| Shapefile | India Districts 2020 | `india_shp_2020-master/district/in_district.shp` |

## Pipeline

```
01_build_district_calories.py
   reads:  crop_diversity_analysis/district_diversity_calorie_merged.csv
   writes: outputs/district_calorie_production.csv
           (state, district, food_TKcal, food_no_coconut_TKcal, total_TKcal,
            z_*, tag_food, tag_food_nc, tag_total)

02_apply_policy_matrix.py
   reads:  prof_df_with_WB.xlsx + district_calorie_production.csv
   writes: outputs/prof_df_with_district_calories.xlsx (adds DefA + DefB columns)
           outputs/scaleup_districts_DefA.csv
           outputs/scaleup_districts_DefB_food.csv
           outputs/scaleup_districts_DefB_foodnc.csv

03_regenerate_maps.py
   reads:  prof_df_with_district_calories.xlsx + shapefile
   writes: outputs/04_policy_action_DefA_legacy.png
           outputs/04_policy_action_DefB_food.png
           outputs/04_policy_action_DefB_foodnc.png
           outputs/05_policy_by_irrigation_panel_DefB_food.png
           outputs/06_DefA_to_DefB_transition_map.png
           outputs/district_master_DefA_DefB.xlsx
           outputs/state_rollup_DefA_DefB.csv

04_fert_overlap_DefB.py
   reads:  Fertiliser use_District level data.xlsx + prof_df_with_district_calories.xlsx
   writes: outputs/fert_scaleup_overlap_DefB.xlsx
           outputs/07_fert_overlap_DefA.png
           outputs/07_fert_overlap_DefB_food.png
           outputs/07_fert_overlap_DefB_foodnc.png
```

Run order is sequential (01 → 04). Each script is idempotent and self-contained.

## Reproduction

```bash
cd "E:/CEEW Project"
python projects/district_calorie_policy/scripts/01_build_district_calories.py
python projects/district_calorie_policy/scripts/02_apply_policy_matrix.py
python projects/district_calorie_policy/scripts/03_regenerate_maps.py
python projects/district_calorie_policy/scripts/04_fert_overlap_DefB.py
```

Dependencies: pandas, numpy, geopandas, matplotlib, rapidfuzz, openpyxl.

## Caveats

1. **Crop scope.** District calories use the 54 crops in `all_crops_apy`
   (cereals, millets, pulses, oilseeds, sugar, vegetables/tubers, fruits,
   nuts, spices). It does **not** include animal-source foods (milk, eggs,
   meat, fish) which are state-only in the underlying agri stats. State-level
   nutritional-security calculations include those; district calorie tags
   here capture **production-side cropping output only**.

2. **Coconut.** India Data Portal records coconut as number of nuts but
   labels the column "tonnes". The canonical pipeline applies the
   0.00015 t/nut correction (~150 g edible meat per nut). 9 districts have
   coconut > 50% of food-crop kcal; the `*_foodnc` variant strips it as
   sensitivity.

3. **FAI fertiliser data covers only 16 states** (320 districts) — the NE,
   J&K, Kerala, HP, Jharkhand, Assam and others are not in the FAI Statbook.
   Districts in unfiled states show as "Other / Not in FAI data" in the
   overlap maps.

4. **Calorie z-tagging is across all districts (all-India).** Districts with
   zero/missing crop production are tagged as null, not Low.

5. **Composite_Score / Composite_Quartile is unchanged from the legacy
   pipeline.** It's still the all-India yield quartile of a 56-crop composite;
   if you want yield quartiles within irrigation regime or within calorie
   tag, that's a separate analysis (not in this project).

## Files

```
projects/district_calorie_policy/
├── README.md                              # this file
├── docs/
│   └── methodology.md                     # detailed method, matrix derivation, comparison
├── data/
│   └── crop_calorie_reference.csv         # crop -> kcal mapping (reference, not used directly;
│                                          #  canonical pipeline already applies IFCT 2017)
├── scripts/
│   ├── 01_build_district_calories.py
│   ├── 02_apply_policy_matrix.py
│   ├── 03_regenerate_maps.py
│   └── 04_fert_overlap_DefB.py
└── outputs/
    ├── district_calorie_production.csv
    ├── prof_df_with_district_calories.xlsx
    ├── district_master_DefA_DefB.xlsx
    ├── state_rollup_DefA_DefB.csv
    ├── scaleup_districts_DefA.csv
    ├── scaleup_districts_DefB_food.csv
    ├── scaleup_districts_DefB_foodnc.csv
    ├── fert_scaleup_overlap_DefB.xlsx
    ├── 04_policy_action_DefA_legacy.png
    ├── 04_policy_action_DefB_food.png
    ├── 04_policy_action_DefB_foodnc.png
    ├── 05_policy_by_irrigation_panel_DefB_food.png
    ├── 06_DefA_to_DefB_transition_map.png
    ├── 07_fert_overlap_DefA.png
    ├── 07_fert_overlap_DefB_food.png
    └── 07_fert_overlap_DefB_foodnc.png
```

## Status

- [x] District-level calorie tags built from canonical pipeline
- [x] Definition B matrix applied (food + food-no-coconut variants)
- [x] Policy_Action maps regenerated (DefA legacy, DefB_food, DefB_foodnc, transition map)
- [x] Fertiliser overlap re-run under DefB
- [ ] State-level calorie-aware version (using `State_Total_Calorie_Level` from prof_df) — defer
- [ ] Push to GitHub as a sister repo to `crop-diversity`
