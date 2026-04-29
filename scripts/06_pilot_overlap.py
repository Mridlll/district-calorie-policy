"""
06_pilot_overlap.py

Mirror of 04_fert_overlap_DefB.py but for the "Pilot" basket.
Generates:
  - outputs/pilot_districts_DefB_food.csv
  - outputs/pilot_districts_DefB_foodnc.csv
  - outputs/fert_pilot_overlap_DefB.xlsx
  - outputs/08_fert_overlap_pilot_DefB_food.png
  - outputs/08_fert_overlap_pilot_DefB_foodnc.png

Then copies/renames into deliverables_final/ with the canonical scheme:
  - 11_fert_overlap_pilot.png
  - 11_fert_overlap_pilot_ex_coconut.png
  - fert_pilot_overlap.xlsx
  - pilot_districts.csv
  - pilot_districts_ex_coconut.csv
"""

import shutil
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from rapidfuzz import process, fuzz
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(r"E:\CEEW Project")
PROJ = ROOT / "projects" / "district_calorie_policy"
OUT  = PROJ / "outputs"
DEL  = ROOT / "deliverables_final"

FERT_SRC = ROOT / "outputs" / "Fertiliser use_District level data.xlsx"
DEFB_SRC = OUT / "prof_df_with_district_calories.xlsx"
SHP_PATH = Path(r"C:\Users\Mridul\Downloads\Archives\Compressed\india_shp_2020-master\india_shp_2020-master\district\in_district.shp")

TARGET = "Pilot"

# ---------- 1. Pilot district CSVs ----------
print("1. Building pilot district CSVs...")
prof = pd.read_excel(DEFB_SRC)
for col, label in [("Policy_Action_DefB_food",   "DefB_food"),
                   ("Policy_Action_DefB_foodnc", "DefB_foodnc")]:
    sub = prof[prof[col] == TARGET][
        ["State_Name", "District_Name", "Composite_Quartile",
         "Composite_Score", "tag_food", "tag_food_nc",
         "Irrigation_Category", "Gross_Irrigated_Area_Pct"]].sort_values(
        ["State_Name", "District_Name"])
    sub.to_csv(OUT / f"pilot_districts_{label}.csv", index=False)
    print(f"   pilot_districts_{label}.csv  ({len(sub)} districts)")

# ---------- 2. Load fertilizer ----------
print("\n2. Loading FAI fertiliser data...")
fert = pd.read_excel(FERT_SRC, sheet_name="Main").iloc[:, :5].copy()
fert.columns = ["Rank", "District", "State", "Tonnes_000", "KgPerHa"]
fert = fert.dropna(subset=["District", "State", "KgPerHa"]).reset_index(drop=True)
q75 = fert["KgPerHa"].quantile(0.75)
fert["High_Fert"] = fert["KgPerHa"] >= q75
print(f"   {len(fert)} FAI rows, top-25% cutoff {q75:.1f} kg/ha, "
      f"{fert['High_Fert'].sum()} high-fert districts")

# ---------- 3. Match fert -> DefB master ----------
print("\n3. Matching fert districts to DefB master...")
fert["state_clean"] = fert["State"].str.lower().str.strip()
fert["dist_clean"]  = fert["District"].str.lower().str.strip()
prof["state_clean"] = prof["State_Name"].str.lower().str.strip()
prof["dist_clean"]  = prof["District_Name"].str.lower().str.strip()

m_lookup = prof.groupby(["state_clean", "dist_clean"]).first()[
    ["State_Name", "District_Name", "Composite_Quartile", "tag_food", "tag_food_nc",
     "Policy_Action_DefA", "Policy_Action_DefB_food", "Policy_Action_DefB_foodnc",
     "Irrigation_Category", "Gross_Irrigated_Area_Pct"]]

def match_to_master(row):
    n = len(m_lookup.columns)
    cand = m_lookup.loc[m_lookup.index.get_level_values(0) == row["state_clean"]]
    if cand.empty:
        return pd.Series([None] * n, index=m_lookup.columns)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return pd.Series([None] * n, index=m_lookup.columns)
    return cand.loc[(row["state_clean"], m[0])]

attached = fert.apply(match_to_master, axis=1)
for c in attached.columns:
    fert[c] = attached[c].values
print(f"   Matched {fert['Policy_Action_DefB_food'].notna().sum()}/{len(fert)} fert rows")

# ---------- 4. Overlap tables ----------
print("\n4. Building overlap tables...")
high = fert[fert["High_Fert"]].copy()

results = {}
for col, label in [("Policy_Action_DefB_food",   "DefB_food"),
                   ("Policy_Action_DefB_foodnc", "DefB_foodnc")]:
    overlap = high[high[col] == TARGET].sort_values("KgPerHa", ascending=False)
    results[label] = overlap
    pct = 100 * len(overlap) / max(len(high), 1)
    print(f"   {label}: {len(overlap)} of {len(high)} high-fert districts are Pilot ({pct:.0f}%)")

xlsx_path = OUT / "fert_pilot_overlap_DefB.xlsx"
with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
    for label, df in results.items():
        out_df = df[["Rank", "District", "State", "KgPerHa", "Tonnes_000",
                     "Composite_Quartile", "tag_food", "tag_food_nc",
                     "Irrigation_Category"]].rename(columns={
            "Rank": "FAI_Rank_Tonnes",
            "KgPerHa": "Kg_per_ha",
            "Tonnes_000": "Total_kt"})
        out_df.to_excel(w, sheet_name=f"Overlap_{label}", index=False)
    note = pd.DataFrame({
        "Field": ["High_Fert definition", "Top-quartile cutoff",
                  "Target basket", "DefB_food", "DefB_foodnc",
                  "Match method", "FAI states covered"],
        "Value": [f"Top 25% of FAI 2021-22 districts by Kg/ha",
                  f"{q75:.1f} kg/ha",
                  "Pilot (yield-quartile x calorie-tag matrix middle band)",
                  "Yield x calorie matrix (food crops, with coconut), district-level z-tag",
                  "Yield x calorie matrix (food crops, ex-coconut), district-level z-tag",
                  "rapidfuzz token_sort_ratio >= 80 on (state, district)",
                  ", ".join(sorted(fert["State"].unique()))]
    })
    note.to_excel(w, sheet_name="Method", index=False)
    high[["District", "State", "KgPerHa",
          "Policy_Action_DefA", "Policy_Action_DefB_food",
          "Policy_Action_DefB_foodnc", "tag_food", "Composite_Quartile"]] \
        .sort_values("KgPerHa", ascending=False) \
        .to_excel(w, sheet_name="HighFert_AllDefs", index=False)
print(f"   Wrote {xlsx_path}")

for label, df in results.items():
    print(f"\n   --- {label} pilot overlap top 15 ---")
    if len(df) == 0:
        print("    (none)")
        continue
    print(df[["District", "State", "KgPerHa", "Composite_Quartile", "tag_food"]]
          .head(15).to_string(index=False))

# ---------- 5. Maps ----------
print("\n5. Building maps...")
gdf = gpd.read_file(SHP_PATH)
gdf["stname"] = gdf["stname"].str.replace(">", "A", regex=False) \
                             .str.replace("1", "I", regex=False) \
                             .str.replace("|", "I", regex=False)
gdf["dtname"] = gdf["dtname"].str.replace(">", "A", regex=False) \
                             .str.replace("@", "A", regex=False)
gdf["state_clean"] = gdf["stname"].str.lower().str.strip()
gdf["dist_clean"]  = gdf["dtname"].str.lower().str.strip()
state_gdf = gdf.dissolve(by="stname").reset_index()

fert_lookup = fert.set_index(["state_clean", "dist_clean"])[["KgPerHa", "High_Fert"]]
def attach_fert(row):
    cand = fert_lookup.loc[fert_lookup.index.get_level_values(0) == row["state_clean"]]
    if cand.empty:
        return (np.nan, False)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return (np.nan, False)
    rec = cand.loc[(row["state_clean"], m[0])]
    return (rec["KgPerHa"], bool(rec["High_Fert"]))

attached = gdf.apply(lambda r: pd.Series(attach_fert(r),
                    index=["KgPerHa", "High_Fert"]), axis=1)
gdf["KgPerHa"] = attached["KgPerHa"]
gdf["High_Fert"] = attached["High_Fert"].astype(bool)

def attach_policy(row):
    cand = m_lookup.loc[m_lookup.index.get_level_values(0) == row["state_clean"]]
    if cand.empty:
        return pd.Series([None, None],
            index=["Policy_Action_DefB_food", "Policy_Action_DefB_foodnc"])
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return pd.Series([None, None],
            index=["Policy_Action_DefB_food", "Policy_Action_DefB_foodnc"])
    return cand.loc[(row["state_clean"], m[0]),
                    ["Policy_Action_DefB_food", "Policy_Action_DefB_foodnc"]]

ap = gdf.apply(attach_policy, axis=1)
for c in ap.columns:
    gdf[c] = ap[c].values

NO_DATA = "#E8E8E8"
CAT_COLORS = {
    "Overlap (HighFert + Pilot)": "#4B2E83",
    "High Fert only":             "#F37E51",
    "Pilot only":                 "#E2A93B",
}

def make_overlap_map(policy_col, label, fname):
    def cat(r):
        if r["High_Fert"] and r[policy_col] == TARGET:
            return "Overlap (HighFert + Pilot)"
        if r["High_Fert"]:
            return "High Fert only"
        if r[policy_col] == TARGET:
            return "Pilot only"
        return None
    gdf["Cat"] = gdf.apply(cat, axis=1)
    n_overlap = (gdf["Cat"] == "Overlap (HighFert + Pilot)").sum()
    n_hf      = (gdf["Cat"] == "High Fert only").sum()
    n_pi      = (gdf["Cat"] == "Pilot only").sum()
    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    for c, color in CAT_COLORS.items():
        sub = gdf[gdf["Cat"] == c]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
    ax.set_xlim(68, 98); ax.set_ylim(6, 38); ax.set_axis_off()
    ax.set_title(f"High-Fert (Top 25% kg/ha, FAI 2021-22) vs Pilot [{label}]\n"
                 f"Overlap: {n_overlap}  |  Pilot only: {n_pi}  |  High Fert only: {n_hf}",
                 fontsize=13, fontweight="bold", pad=14)
    patches = []
    for c, color in CAT_COLORS.items():
        n = (gdf["Cat"] == c).sum()
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{c} ({n})"))
    patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666",
                                  label="Other / Not in FAI data"))
    ax.legend(handles=patches, loc="lower left", fontsize=10, frameon=True,
              fancybox=True, framealpha=0.92, edgecolor="#CCC")
    fig.savefig(OUT / fname, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   Saved {fname}")

make_overlap_map("Policy_Action_DefB_food",   "DefB food",    "08_fert_overlap_pilot_DefB_food.png")
make_overlap_map("Policy_Action_DefB_foodnc", "DefB food-nc", "08_fert_overlap_pilot_DefB_foodnc.png")

# ---------- 6. Mirror into deliverables_final/ ----------
print("\n6. Copying canonical artifacts into deliverables_final/...")
DEL.mkdir(parents=True, exist_ok=True)

# Maps -> 11_*
shutil.copy2(OUT / "08_fert_overlap_pilot_DefB_food.png",
             DEL / "11_fert_overlap_pilot.png")
shutil.copy2(OUT / "08_fert_overlap_pilot_DefB_foodnc.png",
             DEL / "11_fert_overlap_pilot_ex_coconut.png")

# Pilot district CSVs (rename: drop DefB suffix; foodnc -> _ex_coconut)
shutil.copy2(OUT / "pilot_districts_DefB_food.csv",
             DEL / "pilot_districts.csv")
shutil.copy2(OUT / "pilot_districts_DefB_foodnc.csv",
             DEL / "pilot_districts_ex_coconut.csv")

# Excel: strip DefB suffixes from sheet names + columns to match scaleup deliverable
xl = pd.ExcelFile(xlsx_path)
with pd.ExcelWriter(DEL / "fert_pilot_overlap.xlsx", engine="openpyxl") as w:
    for sheet in xl.sheet_names:
        if "DefA" in sheet:
            continue
        df = pd.read_excel(xl, sheet_name=sheet)
        df = df.drop(columns=[c for c in df.columns if "DefA" in str(c)],
                     errors="ignore")
        df = df.rename(columns={
            "Policy_Action_DefB_food":   "Policy_Action",
            "Policy_Action_DefB_foodnc": "Policy_Action_ex_coconut",
        })
        out_sheet = (sheet
                     .replace("_DefB_food", "")
                     .replace("_DefB_foodnc", "_ex_coconut")
                     .replace("_DefB", ""))
        if out_sheet == "Overlap":
            out_sheet = "Overlap_HighFert_Pilot"
        df.to_excel(w, sheet_name=out_sheet[:31], index=False)

print(f"   Copied: 11_fert_overlap_pilot.png, 11_fert_overlap_pilot_ex_coconut.png")
print(f"           fert_pilot_overlap.xlsx, pilot_districts.csv, pilot_districts_ex_coconut.csv")

print("\nDONE.")
