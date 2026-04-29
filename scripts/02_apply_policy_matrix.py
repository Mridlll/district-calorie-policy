"""
02_apply_policy_matrix.py

Merge district-level calorie tags into prof_df_with_WB and apply the
Definition B policy matrix to derive a calorie-aware Policy_Action.

Matrix (from NEW_AG_SCALE_UP_MAPS.ipynb):
    Calorie tag    Q1         Q2         Q3        Q4
    Low            Scale Up   Scale Up   Pilot     Avoid
    Medium         Scale Up   Pilot      Avoid     Avoid
    High           Pilot      Avoid      Avoid     Avoid

Q1-Q4 = Composite_Quartile (yield-based, all-India quartile of Composite_Score).

Outputs three Policy_Action variants:
    Policy_Action_DefA       = legacy yield-only (Q3+Q4 -> Scale Up)
    Policy_Action_DefB_food  = matrix using tag_food (incl coconut)
    Policy_Action_DefB_foodnc= matrix using tag_food_nc (excl coconut)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from rapidfuzz import process, fuzz
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(r"E:\CEEW Project")
PROJ = ROOT / "projects" / "district_calorie_policy"
OUT  = PROJ / "outputs"

PROF_SRC = ROOT / "outputs" / "ag_scaleup_maps_v2_with_WB" / "prof_df_with_WB.xlsx"
CAL_SRC  = OUT / "district_calorie_production.csv"

POLICY_MATRIX = {
    ("Low",    "Q1"): "Scale Up",
    ("Low",    "Q2"): "Scale Up",
    ("Low",    "Q3"): "Pilot",
    ("Low",    "Q4"): "Avoid",
    ("Medium", "Q1"): "Scale Up",
    ("Medium", "Q2"): "Pilot",
    ("Medium", "Q3"): "Avoid",
    ("Medium", "Q4"): "Avoid",
    ("High",   "Q1"): "Pilot",
    ("High",   "Q2"): "Avoid",
    ("High",   "Q3"): "Avoid",
    ("High",   "Q4"): "Avoid",
}

# ---------- 1. Load ----------
print("1. Loading prof_df and district calorie tags...")
prof = pd.read_excel(PROF_SRC)
cal = pd.read_csv(CAL_SRC)
print(f"   prof_df: {len(prof)} rows, calorie file: {len(cal)} districts")

# Legacy Definition A
prof["Policy_Action_DefA"] = prof["Composite_Quartile"].map(
    {"Q4":"Scale Up","Q3":"Scale Up","Q2":"Pilot","Q1":"Avoid"})

# ---------- 2. Fuzzy-match prof -> calorie file ----------
print("\n2. Fuzzy-matching prof_df districts to calorie file...")
prof["state_clean"] = prof["State_Name"].str.lower().str.strip()
prof["dist_clean"]  = prof["District_Name"].str.lower().str.strip()
cal["state_clean"]  = cal["state_name"].str.lower().str.strip()
cal["dist_clean"]   = cal["district_name"].str.lower().str.strip()

cal_lookup = cal.set_index(["state_clean","dist_clean"])[
    ["food_TKcal","food_no_coconut_TKcal","total_TKcal",
     "tag_food","tag_food_nc","tag_total","coconut_kcal_share"]]

def match_calorie(row):
    cand = cal_lookup.loc[cal_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return pd.Series([np.nan]*7,
        index=["food_TKcal","food_no_coconut_TKcal","total_TKcal",
               "tag_food","tag_food_nc","tag_total","coconut_kcal_share"])
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return pd.Series([np.nan]*7,
        index=["food_TKcal","food_no_coconut_TKcal","total_TKcal",
               "tag_food","tag_food_nc","tag_total","coconut_kcal_share"])
    return cand.loc[(row["state_clean"], m[0])]

matched = prof.apply(match_calorie, axis=1)
for c in matched.columns:
    prof[c] = matched[c].values
print(f"   Matched {prof['tag_food'].notna().sum()}/{len(prof)} prof rows")

# ---------- 3. Apply matrix ----------
print("\n3. Applying Definition B matrix...")
def apply_matrix(row, tag_col):
    q = row.get("Composite_Quartile")
    t = row.get(tag_col)
    if pd.isna(q) or pd.isna(t): return np.nan
    return POLICY_MATRIX.get((str(t), str(q)), np.nan)

prof["Policy_Action_DefB_food"]   = prof.apply(lambda r: apply_matrix(r, "tag_food"), axis=1)
prof["Policy_Action_DefB_foodnc"] = prof.apply(lambda r: apply_matrix(r, "tag_food_nc"), axis=1)

print("\n   Policy_Action_DefA (legacy yield-only):")
print(prof["Policy_Action_DefA"].value_counts(dropna=False).to_string())
print("\n   Policy_Action_DefB_food (yield x calorie, with coconut):")
print(prof["Policy_Action_DefB_food"].value_counts(dropna=False).to_string())
print("\n   Policy_Action_DefB_foodnc (yield x calorie, ex-coconut):")
print(prof["Policy_Action_DefB_foodnc"].value_counts(dropna=False).to_string())

# ---------- 4. Comparison: how many districts changed status? ----------
print("\n4. DefA -> DefB_food crosstab:")
print(pd.crosstab(prof["Policy_Action_DefA"], prof["Policy_Action_DefB_food"],
                  margins=True, dropna=False).to_string())

# ---------- 5. Save ----------
print("\n5. Saving merged prof_df...")
out_path = OUT / "prof_df_with_district_calories.xlsx"
prof.drop(columns=["state_clean","dist_clean"]).to_excel(out_path, index=False)
print(f"   {out_path}")

# Also save key Scale-Up lists
for col, label in [("Policy_Action_DefB_food", "DefB_food"),
                   ("Policy_Action_DefB_foodnc","DefB_foodnc"),
                   ("Policy_Action_DefA",       "DefA")]:
    su = prof[prof[col]=="Scale Up"][
        ["State_Name","District_Name","Composite_Quartile",
         "Composite_Score","tag_food","tag_food_nc",
         "Irrigation_Category","Gross_Irrigated_Area_Pct"]].sort_values(
        ["State_Name","District_Name"])
    su.to_csv(OUT / f"scaleup_districts_{label}.csv", index=False)
    print(f"   scaleup_districts_{label}.csv  ({len(su)} districts)")

print("\nDONE.")
