# Top 100 Fertiliser-Intensive vs Priority (v2)

**V2 changes vs v1:** Scale Up and Pilot are merged into a single `Priority`
basket; we use the literal top 100 (not a top-25% quantile) to define the
intensive set.

## Top set definition

Top 100 districts by Kg/ha total fertiliser (FAI 2021-22, 320-row universe; N+P2O5+K2O).

## Files

| File | Contents |
|---|---|
| top100_fert_overlap.png | Top 100 fert vs Priority, food calorie tag (with coconut) |
| top100_fert_overlap_ex_coconut.png | Same, calorie tag excluding coconut |
| top100_fert_overlap.xlsx | Overlap tables (both calorie variants) + method + full top-100 |
| priority_districts.csv | Priority basket, food calorie tag (with coconut) - 392 districts |
| priority_districts_ex_coconut.csv | Priority basket, food calorie tag ex-coconut - 392 districts |

## Headline

- Overlap, food (with coconut):    20 of 100
- Overlap, food (ex-coconut):      20 of 100

## The Priority basket

`Priority` = `Scale Up` + `Pilot` from the yield x district-calorie z-tag
matrix - districts in the bottom two calorie bands (Low / Medium) AND in
yield quartiles Q1-Q3 of the all-India 56-crop composite. Districts in the
upper-right of the matrix (saturated calorie + top-yield) remain `Avoid`
and are excluded from Priority.
