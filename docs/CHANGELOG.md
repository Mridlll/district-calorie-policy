# Changelog

## 2026-04-29 — Initial build

- Identified that legacy `Policy_Action` column in `summary_tables.xlsx`
  uses Definition A (yield-only quartile cut), not the calorie-aware
  Definition B from `NEW_AG_SCALE_UP_MAPS.ipynb`.
- Confirmed the project has district-level calorie production already
  computed in `outputs/crop_diversity_analysis/district_diversity_calorie_merged.csv`
  (also published in github.com/Mridlll/crop-diversity), built by
  `scripts/62_district_calorie_production.py` with IFCT 2017 reference and
  the coconut nut→meat correction.
- Built `01_build_district_calories.py` — produces district z-scored tags
  (Low/Medium/High) for food, food-no-coconut, total flavours.
- Built `02_apply_policy_matrix.py` — applies the Definition B yield × calorie
  matrix; preserves DefA as a side-by-side column for comparison.
- Built `03_regenerate_maps.py` — regenerates 04 and 05 maps under DefB,
  plus a transition map showing every district's DefA→DefB classification.
- Built `04_fert_overlap_DefB.py` — re-runs the FAI top-25%-by-kg/ha vs
  Scale-Up overlap. Result drops from 63/80 (DefA) to 6/80 (DefB).
- Wrote `README.md` and `docs/methodology.md` documenting both definitions,
  the data sources, and known caveats.

### Headline numbers

| Quantity | DefA (yield-only) | DefB (yield × calorie) |
|---|---:|---:|
| Scale Up | 340 | 263 |
| Pilot | 183 | 129 |
| Avoid | 172 | 239 |
| Scale Up that's also high-fert (FAI top 25%) | 63/80 | 6/80 |
| Districts unchanged across definitions | n/a | 34 (all Pilot) |

Zero districts retained the "Scale Up" label across both definitions.
