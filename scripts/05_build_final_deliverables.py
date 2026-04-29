"""
05_build_final_deliverables.py

Build a single flat deliverables folder. Drop all DefA artifacts (error-prone),
rename DefB outputs to canonical names (no "DefB" suffix), and pull in the
non-policy maps from the legacy WB pipeline that are still valid.

Output: E:/CEEW Project/deliverables_final/
"""

import shutil
import pandas as pd
from pathlib import Path
import openpyxl

ROOT = Path(r"E:\CEEW Project")
PROJ = ROOT / "projects" / "district_calorie_policy" / "outputs"
OLD  = ROOT / "outputs" / "ag_scaleup_maps_v2_with_WB"
SHP_SRC = Path(r"C:\Users\Mridul\Downloads\Archives\Compressed\india_shp_2020-master\india_shp_2020-master\district")
DEST = ROOT / "deliverables_final"
SHP_DEST = DEST / "shapefile"

DEST.mkdir(parents=True, exist_ok=True)
SHP_DEST.mkdir(parents=True, exist_ok=True)

# ---------- 1. Maps to copy ----------
print("1. Copying maps...")
# Non-policy maps from legacy WB pipeline (still valid - irrigation, yield, binary)
legacy_maps = [
    "01_irrigation_regime.png",
    "02_yield_quartiles.png",
    "03_yield_by_irrigation_panel.png",
    "06_rainfed_irrigated_x_yield_binary.png",
    "07_rainfed_irrigated_x_yield_panel.png",
    "08a_rainfed_low_yield.png",
    "08b_rainfed_high_yield.png",
    "08c_irrigated_low_yield.png",
    "08d_irrigated_high_yield.png",
    "09a_all_irrigated.png",
    "09b_all_rainfed.png",
    "09c_all_high_yield.png",
    "09d_all_low_yield.png",
]
for fname in legacy_maps:
    shutil.copy2(OLD/fname, DEST/fname)

# New calorie-aware maps (rename to drop DefB suffix)
rename_new = [
    ("04_policy_action_DefB_food.png",            "04_policy_action.png"),
    ("04_policy_action_DefB_foodnc.png",          "04_policy_action_ex_coconut.png"),
    ("05_policy_by_irrigation_panel_DefB_food.png","05_policy_by_irrigation_panel.png"),
    ("07_fert_overlap_DefB_food.png",             "10_fert_overlap.png"),
    ("07_fert_overlap_DefB_foodnc.png",           "10_fert_overlap_ex_coconut.png"),
]
for src, dst in rename_new:
    shutil.copy2(PROJ/src, DEST/dst)
print(f"   Copied {len(legacy_maps) + len(rename_new)} maps")

# ---------- 2. district_master.xlsx (drop DefA column) ----------
print("\n2. Building district_master.xlsx (DefA dropped)...")
m = pd.read_excel(PROJ/"district_master_DefA_DefB.xlsx")
m = m.drop(columns=["Policy_Action_DefA","Transition"], errors="ignore")
m = m.rename(columns={
    "Policy_Action_DefB_food":       "Policy_Action",
    "Policy_Action_DefB_foodnc":     "Policy_Action_ex_coconut",
})
m.to_excel(DEST/"district_master.xlsx", index=False)
print(f"   Rows: {len(m)}, cols: {list(m.columns)}")

# ---------- 3. prof_df_with_district_calories.xlsx (drop DefA) ----------
print("\n3. prof_df_with_district_calories.xlsx (DefA dropped)...")
p = pd.read_excel(PROJ/"prof_df_with_district_calories.xlsx")
p = p.drop(columns=["Policy_Action_DefA"], errors="ignore")
p = p.rename(columns={
    "Policy_Action_DefB_food":       "Policy_Action",
    "Policy_Action_DefB_foodnc":     "Policy_Action_ex_coconut",
})
p.to_excel(DEST/"prof_df_with_district_calories.xlsx", index=False)
print(f"   Rows: {len(p)}")

# ---------- 4. fert_scaleup_overlap.xlsx (drop DefA sheet, rename DefB) ----------
print("\n4. fert_scaleup_overlap.xlsx (DefA stripped)...")
src = PROJ/"fert_scaleup_overlap_DefB.xlsx"
xl = pd.ExcelFile(src)
with pd.ExcelWriter(DEST/"fert_scaleup_overlap.xlsx", engine="openpyxl") as w:
    for sheet in xl.sheet_names:
        if "DefA" in sheet:
            continue
        df = pd.read_excel(xl, sheet_name=sheet)
        # Drop any DefA column from HighFert_AllDefs
        df = df.drop(columns=[c for c in df.columns if "DefA" in str(c)], errors="ignore")
        # Rename columns to drop DefB suffix
        df = df.rename(columns={
            "Policy_Action_DefB_food":       "Policy_Action",
            "Policy_Action_DefB_foodnc":     "Policy_Action_ex_coconut",
        })
        out_sheet = sheet.replace("_DefB_food","").replace("_DefB_foodnc","_ex_coconut").replace("_DefB","")
        if out_sheet == "Overlap": out_sheet = "Overlap_HighFert_ScaleUp"
        df.to_excel(w, sheet_name=out_sheet[:31], index=False)
print(f"   Sheets: {xl.sheet_names} -> filtered")

# ---------- 5. district_calorie_production.csv (as-is) ----------
print("\n5. Copying district_calorie_production.csv...")
shutil.copy2(PROJ/"district_calorie_production.csv", DEST/"district_calorie_production.csv")

# ---------- 6. scaleup_districts.csv (DefB_food only, renamed) ----------
print("\n6. scaleup_districts.csv (rename from DefB_food)...")
shutil.copy2(PROJ/"scaleup_districts_DefB_food.csv",   DEST/"scaleup_districts.csv")
shutil.copy2(PROJ/"scaleup_districts_DefB_foodnc.csv", DEST/"scaleup_districts_ex_coconut.csv")

# ---------- 7. state_rollup.csv (drop DefA cols) ----------
print("\n7. state_rollup.csv (DefA cols dropped)...")
sr = pd.read_csv(PROJ/"state_rollup_DefA_DefB.csv")
sr = sr.drop(columns=[c for c in sr.columns if "DefA" in c], errors="ignore")
sr = sr.rename(columns={
    "DefB_ScaleUp":"ScaleUp",
    "DefB_Pilot":  "Pilot",
    "DefB_Avoid":  "Avoid",
})
sr.to_csv(DEST/"state_rollup.csv", index=False)
print(f"   Cols: {list(sr.columns)}")

# ---------- 8. binary_summary.xlsx (no policy - keep as-is) ----------
print("\n8. binary_summary.xlsx (irrigation x yield - no DefA dependency)...")
shutil.copy2(OLD/"binary_summary.xlsx", DEST/"binary_summary.xlsx")

# ---------- 9. district_classification_detail.xlsx (no policy column - keep) ----------
print("\n9. district_classification_detail.xlsx (kept)...")
shutil.copy2(OLD/"district_classification_detail.xlsx", DEST/"district_classification_detail.xlsx")

# ---------- 10. Shapefile ----------
print("\n10. Shapefile...")
for ext in ["shp","shx","dbf","prj"]:
    shutil.copy2(SHP_SRC/f"in_district.{ext}", SHP_DEST/f"in_district.{ext}")
print(f"   {len(list(SHP_DEST.iterdir()))} files in shapefile/")

# ---------- 11. README ----------
print("\n11. Writing README...")
(DEST/"README.md").write_text("""# Final Deliverables — District Calorie-Aware Policy Action

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
""", encoding="utf-8")
print(f"   {DEST/'README.md'}")

# ---------- 12. List final folder ----------
print("\n12. Final folder contents:")
for f in sorted(DEST.rglob("*")):
    if f.is_file():
        size_kb = f.stat().st_size / 1024
        rel = f.relative_to(DEST)
        print(f"   {rel}  ({size_kb:,.0f} KB)")

print("\nDONE.")
