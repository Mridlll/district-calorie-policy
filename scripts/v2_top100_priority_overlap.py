"""
v2_top100_priority_overlap.py

V2 analysis. Two changes from v1:
  1) Scale Up + Pilot are merged into a single "Priority" basket.
  2) Use literal top 100 districts (not top-25% quantile) for both
     fertiliser and DAP.

Two SEPARATE overlaps, each in its own folder:
  - Top 100 fertiliser-intensive (by FAI 2021-22 Kg/ha)  vs  Priority
  - Top 100 DAP districts (from ToP_100_DAP.xlsx)        vs  Priority

Both run in two calorie variants: with-coconut and ex-coconut.

Output layout:
  projects/district_calorie_policy/outputs/v2/fert/
  projects/district_calorie_policy/outputs/v2/dap/

Mirrored canonical copies (no DefB labels):
  projects/district_calorie_policy/deliverables_v2/fert/
  projects/district_calorie_policy/deliverables_v2/dap/
  E:/CEEW Project/deliverables_final_v2/fert/
  E:/CEEW Project/deliverables_final_v2/dap/
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
OUT_BASE      = PROJ / "outputs" / "v2"
DEL_REPO_BASE = PROJ / "deliverables_v2"
DEL_FLAT_BASE = ROOT / "deliverables_final_v2"

FERT_SRC   = ROOT / "outputs" / "Fertiliser use_District level data.xlsx"
DAP_SRC    = ROOT / "ToP_100_DAP.xlsx"
MASTER_SRC = PROJ / "outputs" / "prof_df_with_district_calories.xlsx"
SHP_PATH   = Path(r"C:\Users\Mridul\Downloads\Archives\Compressed\india_shp_2020-master\india_shp_2020-master\district\in_district.shp")

OUT_FERT      = OUT_BASE / "fert"
OUT_DAP       = OUT_BASE / "dap"
DEL_REPO_FERT = DEL_REPO_BASE / "fert"
DEL_REPO_DAP  = DEL_REPO_BASE / "dap"
DEL_FLAT_FERT = DEL_FLAT_BASE / "fert"
DEL_FLAT_DAP  = DEL_FLAT_BASE / "dap"

for d in (OUT_FERT, OUT_DAP,
          DEL_REPO_FERT, DEL_REPO_DAP,
          DEL_FLAT_FERT, DEL_FLAT_DAP):
    d.mkdir(parents=True, exist_ok=True)

TOP_N = 100

# ---------- 1. Load master + build Priority column ----------
print("1. Loading master + building Priority basket (ScaleUp + Pilot)...")
master = pd.read_excel(MASTER_SRC)
master["state_clean"] = master["State_Name"].str.lower().str.strip()
master["dist_clean"]  = master["District_Name"].str.lower().str.strip()

def to_priority(x):
    if x in ("Scale Up", "Pilot"):
        return "Priority"
    if x == "Avoid":
        return "Avoid"
    return None

master["Policy_Action_food"]            = master["Policy_Action_DefB_food"].map(to_priority)
master["Policy_Action_food_ex_coconut"] = master["Policy_Action_DefB_foodnc"].map(to_priority)

n_pri   = (master["Policy_Action_food"] == "Priority").sum()
n_pri_x = (master["Policy_Action_food_ex_coconut"] == "Priority").sum()
print(f"   Priority (with coconut):    {n_pri}")
print(f"   Priority (ex-coconut):      {n_pri_x}")

# Priority district CSVs (built once, mirrored into both fert/ and dap/ folders)
keep_cols = ["State_Name", "District_Name", "Composite_Quartile",
             "Composite_Score", "tag_food", "tag_food_nc",
             "Irrigation_Category", "Gross_Irrigated_Area_Pct"]

priority_csvs = {}
for col, fname in [("Policy_Action_food",            "priority_districts.csv"),
                   ("Policy_Action_food_ex_coconut", "priority_districts_ex_coconut.csv")]:
    sub = master[master[col] == "Priority"][keep_cols].sort_values(
        ["State_Name", "District_Name"])
    priority_csvs[fname] = sub
    print(f"   {fname}  ({len(sub)} districts)")

# ---------- 2. Lookup table for fuzzy matching ----------
m_lookup = master.groupby(["state_clean", "dist_clean"]).first()[
    ["State_Name", "District_Name", "Composite_Quartile",
     "tag_food", "tag_food_nc",
     "Policy_Action_food", "Policy_Action_food_ex_coconut",
     "Irrigation_Category", "Gross_Irrigated_Area_Pct"]]

def match_to_master(state_clean, dist_clean, cols):
    cand = m_lookup.loc[m_lookup.index.get_level_values(0) == state_clean]
    if cand.empty:
        return pd.Series([None] * len(cols), index=cols)
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(dist_clean, choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return pd.Series([None] * len(cols), index=cols)
    return cand.loc[(state_clean, m[0]), cols]

cols_attach = ["State_Name", "District_Name", "Composite_Quartile",
               "tag_food", "tag_food_nc",
               "Policy_Action_food", "Policy_Action_food_ex_coconut",
               "Irrigation_Category"]

# ---------- 3. Fert top-100 ----------
print("\n2. Loading FAI fertiliser data + selecting top 100 by Kg/ha...")
fert = pd.read_excel(FERT_SRC, sheet_name="Main").iloc[:, :5].copy()
fert.columns = ["Rank", "District", "State", "Tonnes_000", "KgPerHa"]
fert = fert.dropna(subset=["District", "State", "KgPerHa"]).reset_index(drop=True)
fert = fert.sort_values("KgPerHa", ascending=False).reset_index(drop=True)
fert_top = fert.head(TOP_N).copy()
fert_top["state_clean"] = fert_top["State"].str.lower().str.strip()
fert_top["dist_clean"]  = fert_top["District"].str.lower().str.strip()
print(f"   {len(fert)} FAI rows; cutoff to enter top-100: {fert_top['KgPerHa'].min():.1f} kg/ha")

attached = fert_top.apply(
    lambda r: match_to_master(r["state_clean"], r["dist_clean"], cols_attach),
    axis=1)
for c in cols_attach:
    fert_top[c] = attached[c].values
print(f"   Matched {fert_top['Policy_Action_food'].notna().sum()}/{len(fert_top)} fert rows to master")

# ---------- 4. DAP top-100 ----------
print("\n3. Loading DAP top-100 list...")
dap = pd.read_excel(DAP_SRC).iloc[:, :3].copy()
dap.columns = ["Rank", "State", "District"]
dap = dap.dropna(subset=["District", "State"]).reset_index(drop=True)
dap = dap.head(TOP_N).copy()
dap["state_clean"] = dap["State"].str.lower().str.strip()
dap["dist_clean"]  = dap["District"].str.lower().str.strip()
print(f"   {len(dap)} DAP districts loaded")

attached = dap.apply(
    lambda r: match_to_master(r["state_clean"], r["dist_clean"], cols_attach),
    axis=1)
for c in cols_attach:
    dap[c] = attached[c].values
print(f"   Matched {dap['Policy_Action_food'].notna().sum()}/{len(dap)} DAP rows to master")

# ---------- 5. Overlap workbooks ----------
def write_overlap_xlsx(df_top, top_label, intensity_col, out_xlsx,
                       extra_summary_cols):
    results = {}
    for col, suffix in [("Policy_Action_food", "food"),
                        ("Policy_Action_food_ex_coconut", "food_ex_coconut")]:
        ov = df_top[df_top[col] == "Priority"]
        if intensity_col is not None and intensity_col in ov.columns:
            ov = ov.sort_values(intensity_col, ascending=False)
        else:
            ov = ov.sort_values("Rank")
        results[suffix] = ov
        pct = 100 * len(ov) / max(len(df_top), 1)
        print(f"   {top_label} x Priority ({suffix}): {len(ov)}/{len(df_top)} ({pct:.0f}%)")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        for suffix, ov in results.items():
            disp_cols = ["Rank", "District", "State"]
            if intensity_col is not None and intensity_col in ov.columns:
                disp_cols += [intensity_col]
            if "Tonnes_000" in ov.columns:
                disp_cols += ["Tonnes_000"]
            disp_cols += ["Composite_Quartile", "tag_food", "tag_food_nc",
                          "Irrigation_Category"]
            sheet_name = f"Overlap_{suffix}"
            rename = {"Rank": f"{top_label}_Rank"}
            if intensity_col == "KgPerHa":
                rename["KgPerHa"]    = "Kg_per_ha"
                rename["Tonnes_000"] = "Total_kt"
            ov[disp_cols].rename(columns=rename) \
                         .to_excel(w, sheet_name=sheet_name[:31], index=False)
        method = pd.DataFrame({
            "Field": ["Top set", "N", "Priority basket",
                      "Calorie variant: food", "Calorie variant: food_ex_coconut",
                      "Match"],
            "Value": [top_label, str(len(df_top)),
                      "Scale Up + Pilot under yield x calorie z-tag matrix",
                      "Calorie z-tag built from food crops (with coconut)",
                      "Calorie z-tag built from food crops, coconut excluded",
                      "rapidfuzz token_sort_ratio >= 80 on (state, district)"]
        })
        method.to_excel(w, sheet_name="Method", index=False)
        df_top[extra_summary_cols].to_excel(w, sheet_name="Top100_AllVariants",
                                            index=False)
    print(f"   Wrote {out_xlsx}")
    return results

# ---------- 6. Maps ----------
print("\n4. Loading shapefile + matching to top-N sets...")
gdf = gpd.read_file(SHP_PATH)
gdf["stname"] = gdf["stname"].str.replace(">", "A", regex=False) \
                             .str.replace("1", "I", regex=False) \
                             .str.replace("|", "I", regex=False)
gdf["dtname"] = gdf["dtname"].str.replace(">", "A", regex=False) \
                             .str.replace("@", "A", regex=False)
gdf["state_clean"] = gdf["stname"].str.lower().str.strip()
gdf["dist_clean"]  = gdf["dtname"].str.lower().str.strip()
state_gdf = gdf.dissolve(by="stname").reset_index()

def attach_in_set(df_top, flag_name):
    lookup = df_top.set_index(["state_clean", "dist_clean"]).index.unique()
    lookup_states = set(s for s, _ in lookup)
    def fn(row):
        if row["state_clean"] not in lookup_states:
            return False
        choices = [d for s, d in lookup if s == row["state_clean"]]
        m = process.extractOne(row["dist_clean"], choices,
                               scorer=fuzz.token_sort_ratio, score_cutoff=80)
        return m is not None
    gdf[flag_name] = gdf.apply(fn, axis=1)

attach_in_set(fert_top, "In_Top100_Fert")
attach_in_set(dap,      "In_Top100_DAP")
print(f"   Top100_Fert districts found in shapefile: {gdf['In_Top100_Fert'].sum()}")
print(f"   Top100_DAP  districts found in shapefile: {gdf['In_Top100_DAP'].sum()}")

def attach_policy(row):
    cand = m_lookup.loc[m_lookup.index.get_level_values(0) == row["state_clean"]]
    if cand.empty:
        return pd.Series([None, None],
            index=["Policy_Action_food", "Policy_Action_food_ex_coconut"])
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return pd.Series([None, None],
            index=["Policy_Action_food", "Policy_Action_food_ex_coconut"])
    return cand.loc[(row["state_clean"], m[0]),
                    ["Policy_Action_food", "Policy_Action_food_ex_coconut"]]

ap = gdf.apply(attach_policy, axis=1)
for c in ap.columns:
    gdf[c] = ap[c].values

NO_DATA = "#E8E8E8"

def make_map(in_set_col, policy_col, top_label, variant_label, out_path,
             top_color, set_color):
    overlap_label  = f"Overlap (Top100 {top_label} + Priority)"
    set_only_label = f"Top100 {top_label} only"
    pri_only_label = "Priority only"
    cat_colors = {
        overlap_label:  "#7B1A2F",
        set_only_label: top_color,
        pri_only_label: set_color,
    }
    def cat(r):
        in_top = bool(r[in_set_col])
        is_pri = (r[policy_col] == "Priority")
        if in_top and is_pri: return overlap_label
        if in_top:            return set_only_label
        if is_pri:            return pri_only_label
        return None
    gdf["Cat"] = gdf.apply(cat, axis=1)
    n_overlap = (gdf["Cat"] == overlap_label).sum()
    n_top     = (gdf["Cat"] == set_only_label).sum()
    n_pri     = (gdf["Cat"] == pri_only_label).sum()

    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    gdf.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    for c, color in cat_colors.items():
        sub = gdf[gdf["Cat"] == c]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
    ax.set_xlim(68, 98); ax.set_ylim(6, 38); ax.set_axis_off()
    ax.set_title(f"Top 100 {top_label} vs Priority [{variant_label}]\n"
                 f"Overlap: {n_overlap}  |  Priority only: {n_pri}  |  Top100 {top_label} only: {n_top}",
                 fontsize=13, fontweight="bold", pad=14)
    patches = []
    for c, color in cat_colors.items():
        n = (gdf["Cat"] == c).sum()
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{c} ({n})"))
    patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666",
                                  label="Other"))
    ax.legend(handles=patches, loc="lower left", fontsize=10, frameon=True,
              fancybox=True, framealpha=0.92, edgecolor="#CCC")
    fig.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   Saved {out_path.name}")

# ---------- 7. Run for fert and dap ----------
fert_summary_cols = ["Rank", "District", "State", "KgPerHa", "Tonnes_000",
                     "Composite_Quartile", "tag_food", "tag_food_nc",
                     "Policy_Action_food", "Policy_Action_food_ex_coconut"]
dap_summary_cols  = ["Rank", "District", "State",
                     "Composite_Quartile", "tag_food", "tag_food_nc",
                     "Policy_Action_food", "Policy_Action_food_ex_coconut"]

print("\n5. Fert outputs (outputs/v2/fert/)...")
fert_results = write_overlap_xlsx(
    fert_top, "Top100_Fert", "KgPerHa",
    OUT_FERT / "top100_fert_overlap.xlsx", fert_summary_cols)
make_map("In_Top100_Fert", "Policy_Action_food",            "Fert", "with coconut",
         OUT_FERT / "top100_fert_overlap.png",            "#F37E51", "#8cb73f")
make_map("In_Top100_Fert", "Policy_Action_food_ex_coconut", "Fert", "ex-coconut",
         OUT_FERT / "top100_fert_overlap_ex_coconut.png", "#F37E51", "#8cb73f")
for fname, df in priority_csvs.items():
    df.to_csv(OUT_FERT / fname, index=False)

print("\n6. DAP outputs (outputs/v2/dap/)...")
dap_results = write_overlap_xlsx(
    dap, "Top100_DAP", None,
    OUT_DAP / "top100_dap_overlap.xlsx", dap_summary_cols)
make_map("In_Top100_DAP", "Policy_Action_food",            "DAP", "with coconut",
         OUT_DAP / "top100_dap_overlap.png",            "#6A5ACD", "#8cb73f")
make_map("In_Top100_DAP", "Policy_Action_food_ex_coconut", "DAP", "ex-coconut",
         OUT_DAP / "top100_dap_overlap_ex_coconut.png", "#6A5ACD", "#8cb73f")
for fname, df in priority_csvs.items():
    df.to_csv(OUT_DAP / fname, index=False)

# ---------- 8. Mirror canonical artifacts ----------
print("\n7. Mirroring canonical artifacts to deliverables_v2/ folders...")
fert_artifacts = ["top100_fert_overlap.png",
                  "top100_fert_overlap_ex_coconut.png",
                  "top100_fert_overlap.xlsx",
                  "priority_districts.csv",
                  "priority_districts_ex_coconut.csv"]
dap_artifacts  = ["top100_dap_overlap.png",
                  "top100_dap_overlap_ex_coconut.png",
                  "top100_dap_overlap.xlsx",
                  "priority_districts.csv",
                  "priority_districts_ex_coconut.csv"]
for f in fert_artifacts:
    shutil.copy2(OUT_FERT / f, DEL_REPO_FERT / f)
    shutil.copy2(OUT_FERT / f, DEL_FLAT_FERT / f)
for f in dap_artifacts:
    shutil.copy2(OUT_DAP / f, DEL_REPO_DAP / f)
    shutil.copy2(OUT_DAP / f, DEL_FLAT_DAP / f)
print(f"   Fert: copied {len(fert_artifacts)} files into both deliverables folders")
print(f"   DAP : copied {len(dap_artifacts)} files into both deliverables folders")

# ---------- 9. READMEs ----------
def write_readme(path, kind, n_overlap_food, n_overlap_xc):
    if kind == "fert":
        title = "Top 100 Fertiliser-Intensive vs Priority"
        method = ("Top 100 districts by Kg/ha total fertiliser (FAI 2021-22, "
                  "320-row universe; N+P2O5+K2O).")
        files = """
| top100_fert_overlap.png | Top 100 fert vs Priority, food calorie tag (with coconut) |
| top100_fert_overlap_ex_coconut.png | Same, calorie tag excluding coconut |
| top100_fert_overlap.xlsx | Overlap tables (both calorie variants) + method + full top-100 |
"""
    else:
        title = "Top 100 DAP vs Priority"
        method = ("Top 100 DAP districts as listed in `ToP_100_DAP.xlsx`.")
        files = """
| top100_dap_overlap.png | Top 100 DAP vs Priority, food calorie tag (with coconut) |
| top100_dap_overlap_ex_coconut.png | Same, calorie tag excluding coconut |
| top100_dap_overlap.xlsx | Overlap tables (both calorie variants) + method + full top-100 |
"""
    text = f"""# {title} (v2)

**V2 changes vs v1:** Scale Up and Pilot are merged into a single `Priority`
basket; we use the literal top 100 (not a top-25% quantile) to define the
intensive set.

## Top set definition

{method}

## Files

| File | Contents |
|---|---|{files}| priority_districts.csv | Priority basket, food calorie tag (with coconut) - {n_pri} districts |
| priority_districts_ex_coconut.csv | Priority basket, food calorie tag ex-coconut - {n_pri_x} districts |

## Headline

- Overlap, food (with coconut):    {n_overlap_food} of 100
- Overlap, food (ex-coconut):      {n_overlap_xc} of 100

## The Priority basket

`Priority` = `Scale Up` + `Pilot` from the yield x district-calorie z-tag
matrix - districts in the bottom two calorie bands (Low / Medium) AND in
yield quartiles Q1-Q3 of the all-India 56-crop composite. Districts in the
upper-right of the matrix (saturated calorie + top-yield) remain `Avoid`
and are excluded from Priority.
"""
    path.write_text(text, encoding="utf-8")

n_fert_food = len(fert_results["food"])
n_fert_xc   = len(fert_results["food_ex_coconut"])
n_dap_food  = len(dap_results["food"])
n_dap_xc    = len(dap_results["food_ex_coconut"])

write_readme(DEL_REPO_FERT / "README.md", "fert", n_fert_food, n_fert_xc)
write_readme(DEL_FLAT_FERT / "README.md", "fert", n_fert_food, n_fert_xc)
write_readme(DEL_REPO_DAP  / "README.md", "dap",  n_dap_food,  n_dap_xc)
write_readme(DEL_FLAT_DAP  / "README.md", "dap",  n_dap_food,  n_dap_xc)
print("   Wrote 4 READMEs")

# ---------- 10. Headline summary ----------
print("\n=== HEADLINE ===")
print(f"Priority basket:  food = {n_pri} | ex-coconut = {n_pri_x}")
print(f"Top100 Fert x Priority [food]:           {n_fert_food}/100")
print(f"Top100 Fert x Priority [food ex-coconut]: {n_fert_xc}/100")
print(f"Top100 DAP  x Priority [food]:           {n_dap_food}/100")
print(f"Top100 DAP  x Priority [food ex-coconut]: {n_dap_xc}/100")

print("\nDONE.")
