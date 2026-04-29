"""
04_fert_overlap_DefB.py

Re-run the fertiliser-intensive vs Scale-Up overlap analysis under
Definition B (yield × calorie matrix), for both food (with coconut) and
food-no-coconut variants. Produces tables + maps.

Method
------
- "Highest fert" = top quartile of FAI 2021-22 districts by Kg/ha (N+P2O5+K2O)
- "Scale Up" comes from the new Policy_Action_DefB_food / DefB_foodnc
- Match: fuzzy on (state, district), token_sort_ratio >= 80
"""

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

FERT_SRC   = ROOT / "outputs" / "Fertiliser use_District level data.xlsx"
DEFB_SRC   = OUT / "prof_df_with_district_calories.xlsx"
SHP_PATH   = Path(r"C:\Users\Mridul\Downloads\Archives\Compressed\india_shp_2020-master\india_shp_2020-master\district\in_district.shp")

# ---------- 1. Load fertilizer ----------
print("1. Loading FAI fertiliser data...")
fert = pd.read_excel(FERT_SRC, sheet_name="Main").iloc[:, :5].copy()
fert.columns = ["Rank","District","State","Tonnes_000","KgPerHa"]
fert = fert.dropna(subset=["District","State","KgPerHa"]).reset_index(drop=True)
q75 = fert["KgPerHa"].quantile(0.75)
fert["High_Fert"] = fert["KgPerHa"] >= q75
print(f"   {len(fert)} districts in FAI, top-25% threshold {q75:.1f} kg/ha, "
      f"{fert['High_Fert'].sum()} high-fert districts")

# ---------- 2. Load DefB master ----------
print("\n2. Loading DefB Policy_Action data...")
master = pd.read_excel(DEFB_SRC)

# ---------- 3. Match fert -> DefB ----------
print("\n3. Matching fert districts to DefB master list...")
fert["state_clean"] = fert["State"].str.lower().str.strip()
fert["dist_clean"]  = fert["District"].str.lower().str.strip()
master["state_clean"] = master["State_Name"].str.lower().str.strip()
master["dist_clean"]  = master["District_Name"].str.lower().str.strip()

m_lookup = master.groupby(["state_clean","dist_clean"]).first()[
    ["State_Name","District_Name","Composite_Quartile","tag_food","tag_food_nc",
     "Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc",
     "Irrigation_Category","Gross_Irrigated_Area_Pct"]]

def match_to_master(row):
    n = len(m_lookup.columns)
    cand = m_lookup.loc[m_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return pd.Series([None]*n, index=m_lookup.columns)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return pd.Series([None]*n, index=m_lookup.columns)
    return cand.loc[(row["state_clean"], m[0])]

attached = fert.apply(match_to_master, axis=1)
for c in attached.columns: fert[c] = attached[c].values
print(f"   Matched {fert['Policy_Action_DefB_food'].notna().sum()}/{len(fert)} fert rows")

# ---------- 4. Build overlap tables for each definition ----------
print("\n4. Building overlap tables...")
high = fert[fert["High_Fert"]].copy()

results = {}
for col, label in [("Policy_Action_DefA","DefA"),
                   ("Policy_Action_DefB_food","DefB_food"),
                   ("Policy_Action_DefB_foodnc","DefB_foodnc")]:
    overlap = high[high[col]=="Scale Up"].sort_values("KgPerHa", ascending=False)
    results[label] = overlap
    print(f"   {label}: {len(overlap)} of {len(high)} high-fert districts are Scale Up "
          f"({100*len(overlap)/len(high):.0f}%)")

# Save xlsx
with pd.ExcelWriter(OUT/"fert_scaleup_overlap_DefB.xlsx", engine="openpyxl") as w:
    for label, df in results.items():
        out_df = df[["Rank","District","State","KgPerHa","Tonnes_000",
                     "Composite_Quartile","tag_food","tag_food_nc",
                     "Irrigation_Category"]].rename(columns={
            "Rank":"FAI_Rank_Tonnes","KgPerHa":"Kg_per_ha","Tonnes_000":"Total_kt"})
        out_df.to_excel(w, sheet_name=f"Overlap_{label}", index=False)
    # Method note
    note = pd.DataFrame({
        "Field":["High_Fert definition","Top-quartile cutoff","DefA",
                 "DefB_food","DefB_foodnc","Match method","FAI states covered"],
        "Value":[f"Top 25% of FAI 2021-22 districts by Kg/ha",
                 f"{q75:.1f} kg/ha",
                 "Yield-only legacy: Composite_Quartile in {Q3,Q4} -> Scale Up",
                 "Yield × calorie matrix (food crops, with coconut), district-level z-tag",
                 "Yield × calorie matrix (food crops, ex-coconut), district-level z-tag",
                 "rapidfuzz token_sort_ratio >= 80 on (state, district)",
                 ", ".join(sorted(fert["State"].unique()))]
    })
    note.to_excel(w, sheet_name="Method", index=False)

    # Comparison
    fert_summary = high[["District","State","KgPerHa",
                          "Policy_Action_DefA","Policy_Action_DefB_food",
                          "Policy_Action_DefB_foodnc","tag_food","Composite_Quartile"]]
    fert_summary.sort_values("KgPerHa", ascending=False).to_excel(
        w, sheet_name="HighFert_AllDefs", index=False)
print(f"   Wrote {OUT/'fert_scaleup_overlap_DefB.xlsx'}")

# ---------- 5. Print top of each ----------
for label, df in results.items():
    print(f"\n   --- {label} overlap top 15 ---")
    if len(df) == 0:
        print("    (none)")
        continue
    print(df[["District","State","KgPerHa","Composite_Quartile","tag_food"]].head(15).to_string(index=False))

# ---------- 6. Map: 4-way categorical for each DefB variant ----------
print("\n5. Building maps...")
gdf = gpd.read_file(SHP_PATH)
gdf["stname"] = gdf["stname"].str.replace(">","A",regex=False)\
                             .str.replace("1","I",regex=False)\
                             .str.replace("|","I",regex=False)
gdf["dtname"] = gdf["dtname"].str.replace(">","A",regex=False)\
                             .str.replace("@","A",regex=False)
gdf["state_clean"] = gdf["stname"].str.lower().str.strip()
gdf["dist_clean"]  = gdf["dtname"].str.lower().str.strip()
state_gdf = gdf.dissolve(by="stname").reset_index()

# fert lookup
fert_lookup = fert.set_index(["state_clean","dist_clean"])[["KgPerHa","High_Fert"]]
def attach_fert(row):
    cand = fert_lookup.loc[fert_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return (np.nan, False)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return (np.nan, False)
    rec = cand.loc[(row["state_clean"], m[0])]
    return (rec["KgPerHa"], bool(rec["High_Fert"]))

attached = gdf.apply(lambda r: pd.Series(attach_fert(r),
                    index=["KgPerHa","High_Fert"]), axis=1)
gdf["KgPerHa"] = attached["KgPerHa"]
gdf["High_Fert"] = attached["High_Fert"].astype(bool)
print(f"   gdf with fert: {gdf['KgPerHa'].notna().sum()}")

# attach DefB Policy
def attach_policy(row):
    cand = m_lookup.loc[m_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return pd.Series([None,None,None],
        index=["Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc"])
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return pd.Series([None,None,None],
        index=["Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc"])
    return cand.loc[(row["state_clean"], m[0]),
                    ["Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc"]]

ap = gdf.apply(attach_policy, axis=1)
for c in ap.columns: gdf[c] = ap[c].values

NO_DATA = "#E8E8E8"
CAT_COLORS = {
    "Overlap (HighFert + ScaleUp)": "#7B1A2F",
    "High Fert only":               "#F37E51",
    "Scale Up only":                "#8cb73f",
}

def make_overlap_map(policy_col, label, fname):
    def cat(r):
        if r["High_Fert"] and r[policy_col]=="Scale Up": return "Overlap (HighFert + ScaleUp)"
        if r["High_Fert"]:                               return "High Fert only"
        if r[policy_col]=="Scale Up":                    return "Scale Up only"
        return None
    gdf["Cat"] = gdf.apply(cat, axis=1)
    n_overlap = (gdf["Cat"]=="Overlap (HighFert + ScaleUp)").sum()
    n_hf = (gdf["Cat"]=="High Fert only").sum()
    n_su = (gdf["Cat"]=="Scale Up only").sum()
    fig, ax = plt.subplots(1,1, figsize=(14,14))
    gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    for c, color in CAT_COLORS.items():
        sub = gdf[gdf["Cat"]==c]
        if not sub.empty: sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
    ax.set_xlim(68,98); ax.set_ylim(6,38); ax.set_axis_off()
    ax.set_title(f"High-Fert (Top 25% kg/ha, FAI 2021-22) vs Scale-Up [{label}]\n"
                 f"Overlap: {n_overlap}  |  Scale Up only: {n_su}  |  High Fert only: {n_hf}",
                 fontsize=13, fontweight="bold", pad=14)
    patches = []
    for c, color in CAT_COLORS.items():
        n = (gdf["Cat"]==c).sum()
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{c} ({n})"))
    patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666",
                                  label="Other / Not in FAI data"))
    ax.legend(handles=patches, loc="lower left", fontsize=10, frameon=True,
              fancybox=True, framealpha=0.92, edgecolor="#CCC")
    fig.savefig(OUT/fname, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   Saved {fname}")

make_overlap_map("Policy_Action_DefA",        "DefA legacy",   "07_fert_overlap_DefA.png")
make_overlap_map("Policy_Action_DefB_food",   "DefB food",     "07_fert_overlap_DefB_food.png")
make_overlap_map("Policy_Action_DefB_foodnc", "DefB food-nc",  "07_fert_overlap_DefB_foodnc.png")

print("\nDONE.")
