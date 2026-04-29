"""
01_build_district_calories.py

Use the project's existing district-level calorie production
(`outputs/crop_diversity_analysis/district_diversity_calorie_merged.csv`)
which was built by `scripts/62_district_calorie_production.py` with proper
coconut-nut-to-meat conversion (0.00015 t/nut) and the canonical IFCT-based
crop-kcal mapping.

Convert raw kcal → TKcal, z-score across districts, tag Low/Medium/High.

Three calorie flavours, all district-level:
  - food_TKcal   = food_crop_kcal_annual / 1e12 (cereals + millets + pulses
                   + oilseeds + sugar + vegetables + fruits + spices, includes coconut)
  - food_no_coconut_TKcal = (food_crop_kcal_annual - coconut_kcal) / 1e12
  - total_TKcal  = total_kcal_annual / 1e12 (food + arecanut + tobacco-as-zero etc.;
                    in practice this = food_TKcal because non-food crops have kcal=0)

Z-tagging matches the NEW_AG_SCALE_UP_MAPS notebook convention:
   Low: z < 0,  Medium: 0 <= z <= 1,  High: z > 1

Output:
    outputs/district_calorie_production.csv
       state, district, food_TKcal, food_no_coconut_TKcal, total_TKcal,
       z_food, z_food_nc, z_total, tag_food, tag_food_nc, tag_total
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"E:\CEEW Project")
PROJ = ROOT / "projects" / "district_calorie_policy"
OUT  = PROJ / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

CAL_SRC = ROOT / "outputs" / "crop_diversity_analysis" / "district_diversity_calorie_merged.csv"

# ---------- 1. Load existing district calorie file ----------
print("1. Loading canonical district calorie file...")
df = pd.read_csv(CAL_SRC)
print(f"   {len(df)} districts")
keep = ["state_name","district_name","total_kcal_annual","food_crop_kcal_annual",
        "coconut_kcal","coconut_kcal_share","kcal_per_hectare","food_crop_kcal_share"]
df = df[keep].copy()

# ---------- 2. Convert to TKcal ----------
print("\n2. Converting to TKcal...")
df["food_TKcal"]            = df["food_crop_kcal_annual"] / 1e12
df["food_no_coconut_TKcal"] = (df["food_crop_kcal_annual"].fillna(0)
                                - df["coconut_kcal"].fillna(0)) / 1e12
df["total_TKcal"]           = df["total_kcal_annual"] / 1e12
print(f"   food_TKcal              median {df['food_TKcal'].median():.3f}  max {df['food_TKcal'].max():.2f}")
print(f"   food_no_coconut_TKcal   median {df['food_no_coconut_TKcal'].median():.3f}  max {df['food_no_coconut_TKcal'].max():.2f}")
print(f"   total_TKcal             median {df['total_TKcal'].median():.3f}  max {df['total_TKcal'].max():.2f}")

# ---------- 3. Z-score & tag (all-India, across positive districts) ----------
print("\n3. Z-scoring and tagging (all-India)...")
def ztag(s, suffix):
    valid = (s > 0) & s.notna()
    z = pd.Series(np.nan, index=s.index)
    z.loc[valid] = (s.loc[valid] - s.loc[valid].mean()) / s.loc[valid].std(ddof=0)
    tag = pd.cut(z, bins=[-np.inf, 0, 1, np.inf], labels=["Low","Medium","High"]).astype(object)
    return z, tag

df["z_food"], df["tag_food"]       = ztag(df["food_TKcal"], "food")
df["z_food_nc"], df["tag_food_nc"] = ztag(df["food_no_coconut_TKcal"], "food_nc")
df["z_total"], df["tag_total"]     = ztag(df["total_TKcal"], "total")

print("\n   tag_food (with coconut):")
print(df["tag_food"].value_counts(dropna=False).to_string())
print("\n   tag_food_nc (excluding coconut):")
print(df["tag_food_nc"].value_counts(dropna=False).to_string())
print("\n   tag_total:")
print(df["tag_total"].value_counts(dropna=False).to_string())

# ---------- 4. Spot-check ----------
print("\n4. Spot-check top 10 districts by food_no_coconut_TKcal:")
top = df.nlargest(10, "food_no_coconut_TKcal")[
    ["state_name","district_name","food_no_coconut_TKcal","tag_food_nc","food_TKcal","tag_food"]]
print(top.to_string(index=False))

print("\n   Coconut effect: coconut_kcal_share > 50% in",
      (df["coconut_kcal_share"] > 0.5).sum(), "districts")

# ---------- 5. Save ----------
print("\n5. Saving outputs...")
out_cols = ["state_name","district_name",
            "food_TKcal","food_no_coconut_TKcal","total_TKcal",
            "coconut_kcal_share",
            "z_food","z_food_nc","z_total",
            "tag_food","tag_food_nc","tag_total",
            "kcal_per_hectare","food_crop_kcal_share"]
df[out_cols].to_csv(OUT/"district_calorie_production.csv", index=False)
print(f"   {OUT/'district_calorie_production.csv'}")
print("\nDONE.")
