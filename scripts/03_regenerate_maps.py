"""
03_regenerate_maps.py

Regenerate the policy-action maps (04, 05) using the calorie-aware
Policy_Action_DefB_food (and DefB_foodnc), plus a comparison map showing
DefA vs DefB at the district level.

Reuses the shapefile + state-boundary pattern from build_prof_df_with_WB.py.
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
SHP_PATH = Path(r"C:\Users\Mridul\Downloads\Archives\Compressed\india_shp_2020-master\india_shp_2020-master\district\in_district.shp")

PROF_DF_DEFB = OUT / "prof_df_with_district_calories.xlsx"
NSA_SRC = ROOT / "irrigation_aggregates.xlsx"

POLICY_COLORS = {"Scale Up":"#8cb73f","Pilot":"#029bd6","Avoid":"#CFCFCE"}
IRR_COLORS = {
    "Rainfed":              "#811C19",
    "Sparsely Irrigated":   "#F37E51",
    "Moderately Irrigated": "#86BFDE",
    "Highly Irrigated":     "#023F5C",
}
NO_DATA = "#E8E8E8"
irr_order = ["Rainfed","Sparsely Irrigated","Moderately Irrigated","Highly Irrigated"]

# ---------- 1. Load shapefile ----------
print("1. Loading shapefile...")
gdf = gpd.read_file(SHP_PATH)
gdf["stname"] = gdf["stname"].str.replace(">","A",regex=False)\
                             .str.replace("1","I",regex=False)\
                             .str.replace("|","I",regex=False)
gdf["dtname"] = gdf["dtname"].str.replace(">","A",regex=False)\
                             .str.replace("@","A",regex=False)
gdf["state_clean"] = gdf["stname"].str.lower().str.strip()
gdf["dist_clean"]  = gdf["dtname"].str.lower().str.strip()
state_gdf = gdf.dissolve(by="stname").reset_index()
print(f"   {len(gdf)} districts in shapefile")

# ---------- 2. Load prof_df with DefB ----------
print("\n2. Loading prof_df with Definition B Policy_Action...")
prof = pd.read_excel(PROF_DF_DEFB)
prof["state_clean"] = prof["State_Name"].str.lower().str.strip()
prof["dist_clean"]  = prof["District_Name"].str.lower().str.strip()
prof_cols = ["Irrigation_Category","Composite_Quartile","Composite_Score",
             "Gross_Irrigated_Area_Pct","tag_food","tag_food_nc",
             "Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc"]
prof_lookup = prof.groupby(["state_clean","dist_clean"]).first()[prof_cols]

def match_district(row):
    cand = prof_lookup.loc[prof_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return pd.Series([None]*len(prof_cols), index=prof_cols)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return pd.Series([None]*len(prof_cols), index=prof_cols)
    return cand.loc[(row["state_clean"], m[0])]

print("\n3. Fuzzy-matching prof -> shapefile...")
matched = gdf.apply(match_district, axis=1)
for c in prof_cols: gdf[c] = matched[c].values
print(f"   Matched {gdf['Policy_Action_DefB_food'].notna().sum()}/{len(gdf)} districts to DefB")

# ---------- 4. Match NSA ----------
print("\n4. Matching NSA from irrigation_aggregates...")
irr_detail = pd.read_excel(NSA_SRC, sheet_name="District_Detail")
irr_detail["NSA_ha"] = irr_detail["Net_Area_Sown_2023-24"].fillna(
    irr_detail["Net_Area_Sown_2022-23"]).fillna(
    irr_detail["Net_Area_Sown_2021-22"]).fillna(
    irr_detail["Net_Area_Sown_2020-21"])
irr_detail["irr_state_clean"] = irr_detail["State"].str.lower().str.strip()
irr_detail["irr_dist_clean"]  = irr_detail["District"].str.lower().str.strip()
irr_lookup = irr_detail.groupby(["irr_state_clean","irr_dist_clean"]).first()["NSA_ha"]

def match_nsa(row):
    cand = irr_lookup.loc[irr_lookup.index.get_level_values(0)==row["state_clean"]]
    if cand.empty: return np.nan
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None: return np.nan
    return cand.loc[(row["state_clean"], m[0])]
gdf["NSA_ha"] = gdf.apply(match_nsa, axis=1)
print(f"   NSA matched: {gdf['NSA_ha'].notna().sum()}/{len(gdf)}")

# ---------- 5. Map helper ----------
def make_policy_map(col, title, fname):
    fig, ax = plt.subplots(1,1, figsize=(14,14))
    gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    for cat, color in POLICY_COLORS.items():
        sub = gdf[gdf[col]==cat]
        if not sub.empty: sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
    ax.set_xlim(68,98); ax.set_ylim(6,38); ax.set_axis_off()
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    patches = []
    for cat, color in POLICY_COLORS.items():
        n = (gdf[col]==cat).sum()
        nsa = gdf.loc[gdf[col]==cat,"NSA_ha"].sum()
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{cat}  ({n} dist, {nsa/1e5:.0f} L ha)"))
    patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666", label="No Data"))
    ax.legend(handles=patches, loc="lower left", fontsize=10, frameon=True,
              fancybox=True, framealpha=0.92, edgecolor="#CCC")
    fig.savefig(OUT/fname, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   Saved: {fname}")

# ---------- 6. Generate maps 04 ----------
print("\n5. Generating policy-action maps...")
make_policy_map(
    "Policy_Action_DefA",
    "Policy Action — Legacy (Definition A: yield-only, Q3+Q4 -> Scale Up)",
    "04_policy_action_DefA_legacy.png")
make_policy_map(
    "Policy_Action_DefB_food",
    "Policy Action — Definition B: yield × district-calorie matrix (food crops, with coconut)",
    "04_policy_action_DefB_food.png")
make_policy_map(
    "Policy_Action_DefB_foodnc",
    "Policy Action — Definition B: yield × district-calorie matrix (food crops, ex-coconut)",
    "04_policy_action_DefB_foodnc.png")

# ---------- 7. Map 05 panel: policy by irrigation regime (DefB_food) ----------
print("\n6. Generating panel map (policy by irrigation regime, DefB_food)...")
fig, axes = plt.subplots(2,2, figsize=(22,22))
fig.suptitle("Policy Action by Irrigation Regime (Definition B: yield × calorie)",
             fontsize=18, fontweight="bold", y=0.93)
for ax, irr_cat in zip(axes.flat, irr_order):
    gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    sub = gdf[gdf["Irrigation_Category"]==irr_cat]
    for action, color in POLICY_COLORS.items():
        asub = sub[sub["Policy_Action_DefB_food"]==action]
        if not asub.empty: asub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.7)
    ax.set_xlim(68,98); ax.set_ylim(6,38); ax.set_axis_off()
    n = len(sub); n_su = (sub["Policy_Action_DefB_food"]=="Scale Up").sum()
    ax.set_title(f"{irr_cat}  ({n} districts, {n_su} Scale Up)",
                 fontsize=13, fontweight="bold", pad=10)
patches = [mpatches.Patch(facecolor=c, edgecolor="#666", label=a) for a,c in POLICY_COLORS.items()]
patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666", label="Other / No Data"))
fig.legend(handles=patches, loc="lower center", ncol=4, fontsize=11,
           frameon=True, fancybox=True, edgecolor="#CCC", bbox_to_anchor=(0.5,0.04))
fig.subplots_adjust(hspace=0.08, wspace=0.02)
fig.savefig(OUT/"05_policy_by_irrigation_panel_DefB_food.png", dpi=300,
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"   Saved: 05_policy_by_irrigation_panel_DefB_food.png")

# ---------- 8. Comparison map: DefA -> DefB transitions ----------
print("\n7. Generating DefA -> DefB transition map...")
def transition(r):
    a, b = r["Policy_Action_DefA"], r["Policy_Action_DefB_food"]
    if pd.isna(a) or pd.isna(b): return np.nan
    if a == b: return f"Unchanged ({a})"
    return f"{a} -> {b}"
gdf["Transition"] = gdf.apply(transition, axis=1)
print("   Transition counts:")
print(gdf["Transition"].value_counts(dropna=False).to_string())

TRANS_COLORS = {
    "Unchanged (Scale Up)": "#005C3A",
    "Unchanged (Pilot)":    "#86BFDE",
    "Unchanged (Avoid)":    "#A5A5A5",
    "Scale Up -> Avoid":    "#7B1A2F",   # high-yield + high-cal: deprioritised
    "Scale Up -> Pilot":    "#F37E51",
    "Pilot -> Scale Up":    "#BCD265",   # mid-yield + low-cal: now upgraded
    "Avoid -> Scale Up":    "#005C3A",   # low-yield + low-cal: now flagged
    "Avoid -> Pilot":       "#86BFDE",
    "Pilot -> Avoid":       "#811C19",
}
fig, ax = plt.subplots(1,1, figsize=(14,14))
gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
for cat, color in TRANS_COLORS.items():
    sub = gdf[gdf["Transition"]==cat]
    if not sub.empty: sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
ax.set_xlim(68,98); ax.set_ylim(6,38); ax.set_axis_off()
ax.set_title("DefA (yield-only) -> DefB (yield × calorie) — district-level transitions",
             fontsize=13, fontweight="bold", pad=12)
patches = []
for cat, color in TRANS_COLORS.items():
    n = (gdf["Transition"]==cat).sum()
    if n > 0:
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{cat} ({n})"))
patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666", label="No Data"))
ax.legend(handles=patches, loc="lower left", fontsize=9, frameon=True,
          fancybox=True, framealpha=0.92, edgecolor="#CCC")
fig.savefig(OUT/"06_DefA_to_DefB_transition_map.png", dpi=300,
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"   Saved: 06_DefA_to_DefB_transition_map.png")

# ---------- 9. Save district master with both definitions ----------
print("\n8. Saving district master with both definitions...")
master_cols = ["stname","dtname","Irrigation_Category","Composite_Quartile",
               "Composite_Score","Gross_Irrigated_Area_Pct",
               "tag_food","tag_food_nc",
               "Policy_Action_DefA","Policy_Action_DefB_food","Policy_Action_DefB_foodnc",
               "Transition","NSA_ha"]
gdf[master_cols].sort_values(["stname","dtname"]).to_excel(
    OUT/"district_master_DefA_DefB.xlsx", index=False)
print(f"   {OUT/'district_master_DefA_DefB.xlsx'}")

# ---------- 10. State rollup ----------
state_rollup = gdf.groupby("stname").agg(
    Districts=("dtname","count"),
    NSA_lakh_ha=("NSA_ha", lambda s: round(s.sum()/1e5,1)),
    DefA_ScaleUp=("Policy_Action_DefA", lambda s: (s=="Scale Up").sum()),
    DefA_Pilot=("Policy_Action_DefA", lambda s: (s=="Pilot").sum()),
    DefA_Avoid=("Policy_Action_DefA", lambda s: (s=="Avoid").sum()),
    DefB_ScaleUp=("Policy_Action_DefB_food", lambda s: (s=="Scale Up").sum()),
    DefB_Pilot=("Policy_Action_DefB_food", lambda s: (s=="Pilot").sum()),
    DefB_Avoid=("Policy_Action_DefB_food", lambda s: (s=="Avoid").sum()),
).sort_index()
state_rollup.to_csv(OUT/"state_rollup_DefA_DefB.csv")
print(f"   state_rollup_DefA_DefB.csv")

print("\nDONE.")
