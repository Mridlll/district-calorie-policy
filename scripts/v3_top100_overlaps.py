"""
v3_top100_overlaps.py

Six overlap analyses, each in its own subfolder. Maps + Excel for every overlap.

Top sets (each top 100 districts):
  1. NPK Total   (TB NJ "Top 100 (N+P2O5+K2O)")
  2. N           (TB NJ "Top100_N")
  3. P2O5        (TB NJ "Top100_P")
  4. K2O         (TB NJ "Top100_K")
  5. DAP (ICAR)  (ToP_100_DAP.xlsx)

Baskets:
  - Ag Scale Up      (Scale Up + Pilot from yield x calorie z-tag matrix)
  - P2 prioritised   (P2_District_prioritisation.xlsx, 410 districts)

Six analyses:
  1-5. {top set} x Ag Scale Up   (two calorie variants: food / food_ex_coconut)
    6. DAP (ICAR) x P2 prioritised (no calorie variants)

Inputs (relative to project root):
  data/Fertiliser use_District level data.xlsx     (carried over but unused here)
  data/ToP_100_DAP.xlsx                            (DAP top 100 ICAR list)
  data/v3/TB_NJ_N-P2O5-K2O.xlsx                    (NPK + N/P/K top 100s)
  data/v3/P2_District_prioritisation.xlsx          (P2 districts)
  data/shapefile/in_district.shp                   (India 2020 districts)
  outputs/prof_df_with_district_calories.xlsx      (built by scripts 01-02)

Outputs:
  outputs/v3/{slug}/             (raw outputs)
  deliverables_v3/{slug}/        (canonical mirror)
where slug in {npk_total, n, p2o5, k2o, dap_icar, dap_icar_x_p2}.
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

PROJ = Path(__file__).resolve().parent.parent
OUT_BASE      = PROJ / "outputs" / "v3"
DEL_REPO_BASE = PROJ / "deliverables_v3"
DEL_FLAT_BASE = PROJ.parent.parent / "deliverables_final_v3"
WRITE_FLAT_MIRROR = DEL_FLAT_BASE.parent.exists()

DAP_SRC    = PROJ / "data" / "ToP_100_DAP.xlsx"
NPK_SRC    = PROJ / "data" / "v3" / "TB_NJ_N-P2O5-K2O.xlsx"
P2_SRC     = PROJ / "data" / "v3" / "P2_District_prioritisation.xlsx"
MASTER_SRC = PROJ / "outputs" / "prof_df_with_district_calories.xlsx"
SHP_PATH   = PROJ / "data" / "shapefile" / "in_district.shp"

ANALYSES = [
    # (slug, top_label, sheet_name, intensity_col, basket_kind)
    ("npk_total",     "NPK Total", "Top 100 (N+P2O5+K2O)", "Total (N+P2O5+K2O)", "ag_scale_up"),
    ("n",             "N",         "Top100_N",             "Total_N",             "ag_scale_up"),
    ("p2o5",          "P2O5",      "Top100_P",             "Total_P2O5",          "ag_scale_up"),
    ("k2o",           "K2O",       "Top100_K",             "Total_K2O",           "ag_scale_up"),
    ("dap_icar",      "DAP (ICAR)", None,                  None,                  "ag_scale_up"),
    ("dap_icar_x_p2", "DAP (ICAR)", None,                  None,                  "p2"),
]

NUTRIENT_COLOR = {
    "npk_total":     "#A23B5C",
    "n":             "#3B6FB6",
    "p2o5":          "#F37E51",
    "k2o":           "#5C9C44",
    "dap_icar":      "#6A5ACD",
    "dap_icar_x_p2": "#6A5ACD",
}
BASKET_COLOR = "#8cb73f"
OVERLAP_COLOR = "#7B1A2F"
NO_DATA = "#E8E8E8"

OUT_BASE.mkdir(parents=True, exist_ok=True)
DEL_REPO_BASE.mkdir(parents=True, exist_ok=True)
if WRITE_FLAT_MIRROR:
    DEL_FLAT_BASE.mkdir(parents=True, exist_ok=True)

# ---------- 1. Build baskets ----------
print("1. Loading master + building Ag Scale Up basket...")
master = pd.read_excel(MASTER_SRC)
master["state_clean"] = master["State_Name"].str.lower().str.strip()
master["dist_clean"]  = master["District_Name"].str.lower().str.strip()

def to_ag_scale_up(x):
    if x in ("Scale Up", "Pilot"):
        return "Ag Scale Up"
    if x == "Avoid":
        return "Avoid"
    return None

master["Ag_Scale_Up_food"]            = master["Policy_Action_DefB_food"].map(to_ag_scale_up)
master["Ag_Scale_Up_food_ex_coconut"] = master["Policy_Action_DefB_foodnc"].map(to_ag_scale_up)
n_asu  = (master["Ag_Scale_Up_food"] == "Ag Scale Up").sum()
n_asu_x = (master["Ag_Scale_Up_food_ex_coconut"] == "Ag Scale Up").sum()
print(f"   Ag Scale Up (with coconut):    {n_asu}")
print(f"   Ag Scale Up (ex-coconut):      {n_asu_x}")

# Ag Scale Up CSV bodies (mirrored into each ag_scale_up subfolder)
keep_cols = ["State_Name", "District_Name", "Composite_Quartile",
             "Composite_Score", "tag_food", "tag_food_nc",
             "Irrigation_Category", "Gross_Irrigated_Area_Pct"]
asu_csvs = {}
for col, fname in [("Ag_Scale_Up_food",            "ag_scale_up_districts.csv"),
                   ("Ag_Scale_Up_food_ex_coconut", "ag_scale_up_districts_ex_coconut.csv")]:
    asu_csvs[fname] = master[master[col] == "Ag Scale Up"][keep_cols].sort_values(
        ["State_Name", "District_Name"])

# P2 basket
print("\n2. Loading P2 prioritised districts...")
p2 = pd.read_excel(P2_SRC).iloc[:, :2].copy()
p2.columns = ["State", "District"]
p2 = p2.dropna(subset=["State", "District"]).reset_index(drop=True)
p2["state_clean"] = p2["State"].str.lower().str.strip()
p2["dist_clean"]  = p2["District"].str.lower().str.strip()
print(f"   P2 prioritised districts: {len(p2)}")

# ---------- 2. Lookup table for matching to master ----------
m_lookup = master.groupby(["state_clean", "dist_clean"]).first()[
    ["State_Name", "District_Name", "Composite_Quartile",
     "tag_food", "tag_food_nc",
     "Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut",
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
               "Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut",
               "Irrigation_Category"]

# ---------- 3. Helper: load top-100 for an analysis ----------
def load_top100(slug, sheet_name):
    if slug == "dap_icar" or slug == "dap_icar_x_p2":
        df = pd.read_excel(DAP_SRC).iloc[:, :3].copy()
        df.columns = ["Rank", "State", "District"]
    elif slug == "npk_total":
        df = pd.read_excel(NPK_SRC, sheet_name=sheet_name).copy()
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={"S.no.": "Rank", "S.No.": "Rank"})
        df = df[["Rank", "State", "District", "Total (N+P2O5+K2O)"]]
    else:
        df = pd.read_excel(NPK_SRC, sheet_name=sheet_name).copy()
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={"S.No.": "Rank", "S.no.": "Rank"})
        keep = ["Rank", "State", "District"]
        for c in df.columns:
            if c.startswith("Total_"):
                keep.append(c)
        df = df[keep]
    df = df.dropna(subset=["State", "District"]).reset_index(drop=True).head(100)
    df["state_clean"] = df["State"].str.lower().str.strip()
    df["dist_clean"]  = df["District"].str.lower().str.strip()
    return df

# ---------- 4. Shapefile ----------
print("\n3. Loading shapefile...")
gdf = gpd.read_file(SHP_PATH)
gdf["stname"] = gdf["stname"].str.replace(">", "A", regex=False) \
                             .str.replace("1", "I", regex=False) \
                             .str.replace("|", "I", regex=False)
gdf["dtname"] = gdf["dtname"].str.replace(">", "A", regex=False) \
                             .str.replace("@", "A", regex=False)
gdf["state_clean"] = gdf["stname"].str.lower().str.strip()
gdf["dist_clean"]  = gdf["dtname"].str.lower().str.strip()
state_gdf = gdf.dissolve(by="stname").reset_index()

def attach_in_set(df_top, flag_name, gdf_local):
    lookup = df_top.set_index(["state_clean", "dist_clean"]).index.unique()
    lookup_states = set(s for s, _ in lookup)
    def fn(row):
        if row["state_clean"] not in lookup_states:
            return False
        choices = [d for s, d in lookup if s == row["state_clean"]]
        m = process.extractOne(row["dist_clean"], choices,
                               scorer=fuzz.token_sort_ratio, score_cutoff=80)
        return m is not None
    gdf_local[flag_name] = gdf_local.apply(fn, axis=1)

# Attach Ag Scale Up policy onto gdf (same for all analyses)
def attach_policy(row):
    cand = m_lookup.loc[m_lookup.index.get_level_values(0) == row["state_clean"]]
    if cand.empty:
        return pd.Series([None, None],
            index=["Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut"])
    choices = cand.index.get_level_values(1).tolist()
    m = process.extractOne(row["dist_clean"], choices,
                           scorer=fuzz.token_sort_ratio, score_cutoff=80)
    if m is None:
        return pd.Series([None, None],
            index=["Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut"])
    return cand.loc[(row["state_clean"], m[0]),
                    ["Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut"]]

ap = gdf.apply(attach_policy, axis=1)
for c in ap.columns:
    gdf[c] = ap[c].values

# Attach P2 flag once
attach_in_set(p2, "In_P2", gdf)
print(f"   P2 districts in shapefile: {gdf['In_P2'].sum()}")

# ---------- 5. Map maker ----------
def make_map(gdf_local, in_set_col, basket_col, basket_value, top_label,
             basket_label, variant_label, top_color, fname):
    overlap_label    = f"Overlap (Top100 {top_label} + {basket_label})"
    set_only_label   = f"Top100 {top_label} only"
    basket_only_label = f"{basket_label} only"
    cat_colors = {
        overlap_label:     OVERLAP_COLOR,
        set_only_label:    top_color,
        basket_only_label: BASKET_COLOR,
    }

    def cat(r):
        in_top = bool(r[in_set_col])
        in_bk  = (r[basket_col] == basket_value) if basket_col else bool(r[basket_col_bool]) if False else False
        if basket_col is not None and isinstance(basket_value, str):
            in_bk = (r[basket_col] == basket_value)
        else:
            in_bk = bool(r[basket_col])
        if in_top and in_bk: return overlap_label
        if in_top:           return set_only_label
        if in_bk:            return basket_only_label
        return None
    gdf_local["Cat"] = gdf_local.apply(cat, axis=1)
    n_overlap = (gdf_local["Cat"] == overlap_label).sum()
    n_top     = (gdf_local["Cat"] == set_only_label).sum()
    n_bk      = (gdf_local["Cat"] == basket_only_label).sum()

    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    gdf_local.plot(ax=ax, color=NO_DATA, edgecolor="#D0D0D0", linewidth=0.15)
    for c, color in cat_colors.items():
        sub = gdf_local[gdf_local["Cat"] == c]
        if not sub.empty:
            sub.plot(ax=ax, color=color, edgecolor="#D0D0D0", linewidth=0.15)
    state_gdf.boundary.plot(ax=ax, edgecolor="#333333", linewidth=0.8)
    ax.set_xlim(68, 98); ax.set_ylim(6, 38); ax.set_axis_off()
    title_variant = f" [{variant_label}]" if variant_label else ""
    ax.set_title(f"Top 100 {top_label} vs {basket_label}{title_variant}\n"
                 f"Overlap: {n_overlap}  |  {basket_label} only: {n_bk}  |  "
                 f"Top100 {top_label} only: {n_top}",
                 fontsize=13, fontweight="bold", pad=14)
    patches = []
    for c, color in cat_colors.items():
        n = (gdf_local["Cat"] == c).sum()
        patches.append(mpatches.Patch(facecolor=color, edgecolor="#666",
                                      label=f"{c} ({n})"))
    patches.append(mpatches.Patch(facecolor=NO_DATA, edgecolor="#666", label="Other"))
    ax.legend(handles=patches, loc="lower left", fontsize=10, frameon=True,
              fancybox=True, framealpha=0.92, edgecolor="#CCC")
    fig.savefig(fname, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return n_overlap, n_top, n_bk

# ---------- 6. Run analyses ----------
all_results = {}
for slug, top_label, sheet_name, intensity_col, basket_kind in ANALYSES:
    print(f"\n=== {slug.upper()} : Top 100 {top_label} x {basket_kind} ===")
    out_dir      = OUT_BASE / slug
    del_repo_dir = DEL_REPO_BASE / slug
    del_flat_dir = DEL_FLAT_BASE / slug
    for d in (out_dir, del_repo_dir):
        d.mkdir(parents=True, exist_ok=True)
    if WRITE_FLAT_MIRROR:
        del_flat_dir.mkdir(parents=True, exist_ok=True)

    # Load top 100
    top_df = load_top100(slug, sheet_name)
    print(f"   Loaded top-100 ({len(top_df)} rows)")

    # Match to master
    attached = top_df.apply(
        lambda r: match_to_master(r["state_clean"], r["dist_clean"], cols_attach),
        axis=1)
    for c in cols_attach:
        top_df[c] = attached[c].values
    print(f"   Matched {top_df['Ag_Scale_Up_food'].notna().sum()}/{len(top_df)} to master")

    # Attach In_Top flag onto gdf
    flag_col = f"In_Top100_{slug}"
    attach_in_set(top_df, flag_col, gdf)

    # Build overlaps
    if basket_kind == "ag_scale_up":
        # Two calorie variants
        results = {}
        intensity_cols_for_xlsx = [c for c in top_df.columns if c.startswith("Total")]
        for col, suffix, variant_label in [
            ("Ag_Scale_Up_food",            "food",            "with coconut"),
            ("Ag_Scale_Up_food_ex_coconut", "food_ex_coconut", "ex-coconut")]:
            ov = top_df[top_df[col] == "Ag Scale Up"]
            if intensity_col and intensity_col in ov.columns:
                ov = ov.sort_values(intensity_col, ascending=False)
            else:
                ov = ov.sort_values("Rank")
            results[suffix] = ov

            # Map
            map_fname = ("top100_overlap.png" if suffix == "food"
                         else "top100_overlap_ex_coconut.png")
            n_o, n_t, n_b = make_map(gdf, flag_col, col, "Ag Scale Up",
                                     top_label, "Ag Scale Up", variant_label,
                                     NUTRIENT_COLOR[slug], out_dir / map_fname)
            print(f"   {suffix}: overlap={n_o}, basket_only={n_b}, top_only={n_t}")

        # Excel
        xlsx_path = out_dir / "top100_overlap.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            for suffix, ov in results.items():
                disp_cols = ["Rank", "District", "State"] + intensity_cols_for_xlsx \
                            + ["Composite_Quartile", "tag_food", "tag_food_nc",
                               "Irrigation_Category"]
                disp_cols = [c for c in disp_cols if c in ov.columns]
                rename = {"Rank": f"{top_label}_Rank"}
                ov[disp_cols].rename(columns=rename) \
                             .to_excel(w, sheet_name=f"Overlap_{suffix}"[:31],
                                       index=False)
            method = pd.DataFrame({
                "Field": ["Top set", "N", "Basket",
                          "Calorie variant: food",
                          "Calorie variant: food_ex_coconut",
                          "Match"],
                "Value": [f"Top 100 {top_label}", str(len(top_df)),
                          "Ag Scale Up = Scale Up + Pilot from yield x calorie z-tag matrix",
                          "Calorie z-tag built from food crops (with coconut)",
                          "Calorie z-tag built from food crops, coconut excluded",
                          "rapidfuzz token_sort_ratio >= 80 on (state, district)"]
            })
            method.to_excel(w, sheet_name="Method", index=False)
            full_cols = ["Rank", "District", "State"] + intensity_cols_for_xlsx \
                       + ["Composite_Quartile", "tag_food", "tag_food_nc",
                          "Ag_Scale_Up_food", "Ag_Scale_Up_food_ex_coconut"]
            full_cols = [c for c in full_cols if c in top_df.columns]
            top_df[full_cols].to_excel(w, sheet_name="Top100_AllVariants", index=False)
        print(f"   Wrote {xlsx_path.name}")

        # CSVs
        for fname, df in asu_csvs.items():
            df.to_csv(out_dir / fname, index=False)

        all_results[slug] = {"food": len(results["food"]),
                             "food_ex_coconut": len(results["food_ex_coconut"])}

    elif basket_kind == "p2":
        # Single overlap, no calorie variants
        # Match top_df rows to P2 list (fuzzy by state, then district)
        p2_lookup = p2.set_index(["state_clean", "dist_clean"]).index.unique()
        p2_states = set(s for s, _ in p2_lookup)
        def in_p2(row):
            if row["state_clean"] not in p2_states:
                return False
            choices = [d for s, d in p2_lookup if s == row["state_clean"]]
            m = process.extractOne(row["dist_clean"], choices,
                                   scorer=fuzz.token_sort_ratio, score_cutoff=80)
            return m is not None
        top_df["In_P2"] = top_df.apply(in_p2, axis=1)
        ov = top_df[top_df["In_P2"]].sort_values("Rank")

        n_o, n_t, n_b = make_map(gdf, flag_col, "In_P2", True,
                                 top_label, "P2 Prioritised", "",
                                 NUTRIENT_COLOR[slug],
                                 out_dir / "top100_overlap.png")
        print(f"   overlap={n_o}, P2_only={n_b}, top_only={n_t}")

        xlsx_path = out_dir / "top100_overlap.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            disp_cols = ["Rank", "District", "State", "In_P2"]
            ov[disp_cols].rename(columns={"Rank": f"{top_label}_Rank"}) \
                         .to_excel(w, sheet_name="Overlap_P2", index=False)
            method = pd.DataFrame({
                "Field": ["Top set", "N", "Basket", "Match"],
                "Value": [f"Top 100 {top_label}", str(len(top_df)),
                          f"P2 prioritised districts ({len(p2)} entries)",
                          "rapidfuzz token_sort_ratio >= 80 on (state, district)"]
            })
            method.to_excel(w, sheet_name="Method", index=False)
            top_df[["Rank", "District", "State", "In_P2"]] \
                .to_excel(w, sheet_name="Top100_AllRows", index=False)
        print(f"   Wrote {xlsx_path.name}")

        # P2 districts CSV
        p2[["State", "District"]].to_csv(out_dir / "p2_prioritised_districts.csv",
                                          index=False)
        all_results[slug] = {"overlap": len(ov)}

    # Mirror artifacts
    for f in out_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, del_repo_dir / f.name)
            if WRITE_FLAT_MIRROR:
                shutil.copy2(f, del_flat_dir / f.name)

# ---------- 7. READMEs ----------
print("\n=== Writing READMEs ===")
analysis_blurb = {
    "npk_total": "Top 100 districts by total fertiliser tonnage (N + P2O5 + K2O combined, "
                 "TB NJ master compilation, 601-row universe).",
    "n":         "Top 100 districts by total Nitrogen tonnage (TB NJ).",
    "p2o5":      "Top 100 districts by total P2O5 tonnage (TB NJ).",
    "k2o":       "Top 100 districts by total K2O tonnage (TB NJ).",
    "dap_icar":  "Top 100 DAP districts as listed by ICAR (`ToP_100_DAP.xlsx`).",
    "dap_icar_x_p2": "Top 100 DAP (ICAR) districts overlapped against the P2 prioritised "
                     f"district list ({len(p2)} entries).",
}

for slug, top_label, _, _, basket_kind in ANALYSES:
    if basket_kind == "ag_scale_up":
        r = all_results[slug]
        body = f"""# Top 100 {top_label} vs Ag Scale Up

{analysis_blurb[slug]}

## Files
| File | Contents |
|---|---|
| top100_overlap.png            | Top 100 {top_label} vs Ag Scale Up, food calorie tag (with coconut) |
| top100_overlap_ex_coconut.png | Same, calorie tag excluding coconut |
| top100_overlap.xlsx           | Overlap tables (both calorie variants) + method + full top-100 |
| ag_scale_up_districts.csv     | Ag Scale Up basket, food calorie tag (with coconut) - {n_asu} districts |
| ag_scale_up_districts_ex_coconut.csv | Ag Scale Up basket, ex-coconut - {n_asu_x} districts |

## Headline
- Overlap, food (with coconut):    **{r['food']}/100**
- Overlap, food (ex-coconut):      **{r['food_ex_coconut']}/100**

## Ag Scale Up basket
`Ag Scale Up` = `Scale Up` + `Pilot` from the yield x district-calorie z-tag
matrix (Low-Medium calorie + yield headroom). 392 districts.
"""
    else:
        r = all_results[slug]
        body = f"""# Top 100 {top_label} vs P2 Prioritised

{analysis_blurb[slug]}

## Files
| File | Contents |
|---|---|
| top100_overlap.png  | Top 100 {top_label} vs P2 prioritised districts |
| top100_overlap.xlsx | Overlap table + method + full top-100 |
| p2_prioritised_districts.csv | P2 prioritised districts ({len(p2)}) |

## Headline
- Overlap: **{r['overlap']}/100**
"""
    (DEL_REPO_BASE / slug / "README.md").write_text(body, encoding="utf-8")
    if WRITE_FLAT_MIRROR:
        (DEL_FLAT_BASE / slug / "README.md").write_text(body, encoding="utf-8")

# Top-level README
top_readme = ["# Final Deliverables v3 - Top 100 Overlaps\n",
              "Six overlap analyses, each in its own subfolder. Maps + Excel for each.\n\n",
              "## Subfolders\n",
              "| Folder | Top set | Basket |\n",
              "|---|---|---|\n"]
for slug, top_label, _, _, basket_kind in ANALYSES:
    bk = "Ag Scale Up" if basket_kind == "ag_scale_up" else "P2 Prioritised"
    top_readme.append(f"| {slug}/ | Top 100 {top_label} | {bk} |\n")
top_readme.append("\n## Headline overlaps\n\n| Analysis | Overlap |\n|---|---|\n")
for slug, top_label, _, _, basket_kind in ANALYSES:
    r = all_results[slug]
    if basket_kind == "ag_scale_up":
        top_readme.append(f"| Top 100 {top_label} x Ag Scale Up (food)            | "
                          f"{r['food']}/100 |\n")
        top_readme.append(f"| Top 100 {top_label} x Ag Scale Up (food_ex_coconut) | "
                          f"{r['food_ex_coconut']}/100 |\n")
    else:
        top_readme.append(f"| Top 100 {top_label} x P2 Prioritised | {r['overlap']}/100 |\n")

(DEL_REPO_BASE / "README.md").write_text("".join(top_readme), encoding="utf-8")
if WRITE_FLAT_MIRROR:
    (DEL_FLAT_BASE / "README.md").write_text("".join(top_readme), encoding="utf-8")

# ---------- 8. Headline ----------
print("\n=== HEADLINE ===")
print(f"Ag Scale Up basket:  food = {n_asu} | ex-coconut = {n_asu_x}")
print(f"P2 Prioritised basket: {len(p2)} districts")
for slug, top_label, _, _, basket_kind in ANALYSES:
    r = all_results[slug]
    if basket_kind == "ag_scale_up":
        print(f"  Top 100 {top_label:11s} x Ag Scale Up (food):            {r['food']}/100")
        print(f"  Top 100 {top_label:11s} x Ag Scale Up (food_ex_coconut): {r['food_ex_coconut']}/100")
    else:
        print(f"  Top 100 {top_label:11s} x P2 Prioritised:                {r['overlap']}/100")

print("\nDONE.")
