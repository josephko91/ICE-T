# 2026-10-09 — QC-table audit and thermodynamic units/basis fix

Triggered by a review of the paper's QC table and equations. Decision record with the
unit convention, the Si [-1, 2] justification and references:
`docs/decisions/2026-10-09-si-bound-and-thermo-basis.md`. Baseline = the half-up-rounding
build earlier the same day (`docs/reports/2026-10-09-dataset-validation.md`); new = rebuilt
after the code changes below. Row keys and columns are identical (4,572,601 L0 rows).

## 1. QC table audit

| Issue found | Verdict | Fix |
|---|---|---|
| QC5 "0 flags / 5 campaigns affected" | Real mismatch: code counted campaigns *compared* (5), flags are pairs with \|r\|<0.5 (0) | `qa_checks.py` now counts campaigns with ≥1 flagged pair (0); notes record "15 instrument pairs compared across 5 campaigns" |
| "% of dataset" for QC3/5/6/8 | Not meaningful: flags there are stuck runs / instrument pairs / flight-days / pressure bins, not rows | pct is now NaN ("n/a") for those; new `flag_unit` column in `00_qaqc_summary.csv`; flag totals are not additive across checks |
| Caption: flags "retained in the dataset and marked" | False as built: L0/L1/L2 contain no flag columns (checked); flags exist only in `logs/qaqc/<ts>/*.csv` | wording fix in the paper (flag lists are QC output files); no pipeline change |
| OLYMPEX in the known limitation but no CPI imagery | Correct observation: the 1,436 QC9 rows are 1,391 IPHEX + 45 OLYMPEX at **L0 only**; **0 appear in L1 or L2** (exact-second join) | paper now says L0-only |
| "Ambiguity" framing | Partly overstated: 143 of the QC9 rows are IPHEX at -30…-20 °C with Si up to 1.68, 110 of them above water saturation (1.23-1.33 there); homogeneous freezing of solution droplets does not apply at those T | paper/decision doc call those more consistent with an instrument artifact; the 1,279 rows at T ≤ -38 °C (Si ≤ 1.53, all below water saturation) remain plausible |
| Pasted table values | Older than the repo (QC1 6→4, QC2 80,648→80,608 on 2026-09-21; QC2 80,593 / QC6 68 after half-up rounding) | regenerated from the final build (below) |

## 2. Units and equations

`es_ice` is **Pa** (docstring said hPa; behavior was correct); all other e_s/e/P are hPa;
`q_v` and `Si` formulas unchanged in form. Full unit table in the decision doc. Real
inconsistencies fixed:

1. **One Murphy & Koop basis.** `si_from_ppmv` (ATTREX, MACPEX, CRYSTAL-FACE-NASA HW/ALIAS,
   ICE-L MRTDL), POSIDON and IPHEX (frost-point and Ophir) used a Tetens/Magnus e_s
   (0.05% / 0.5% / 1.3% different at -50 / -70 / -85 °C). Now all use `es_ice_hPa`.
2. **Exact q_v for ppmv sources:** `1000·ε·x/(1−x)` (was `ε·x`).
3. `qa_checks.py` uses `EPSILON` (0.62197) instead of 0.622.
4. New `scripts/tests/test_thermo_units.py` (known M&K value, Pa→hPa, q_v paths agree,
   ppmv-Si == frost-point-Si).

## 3. Effect of the rebuild (L0, same 4,572,601 rows)

| Column | Non-NaN before → after | Values changed | Median \|Δ\| | Max \|Δ\| |
|---|---|---:|---:|---:|
| Si (best) | 2,698,734 → 2,698,737 | 1,084,118 | 0 | 0.038 |
| Sw | 2,697,835 → 2,697,838 | 1,084,117 | 0 | 0.019 |
| qv (best) | 3,408,336 → 3,408,338 | 1,604,038 | 0 | 0.72 g/kg |

Si changed in six campaigns (median \|ΔSi\| where affected: ATTREX 0.005, POSIDON 0.006,
MACPEX 0.0004, IPHEX 6e-5; max 0.038 ATTREX). Campaign mean Si: ATTREX −0.2841 → −0.2906,
POSIDON −0.1765 → −0.1832, MACPEX −0.4848 → −0.4854 (others ≤ 0.0002). Largest qv shifts are
POSIDON/ATTREX/MACPEX high-ppmv points (up to 0.72 g/kg, the `1/(1−x)` term). Three Si
values (and 8 `Si_ALIAS`) that were just above 2 are now just below it and are kept; none lost.

L1/L2 and the COCPIT join are **unchanged**: L1 2,997,443, L2 1,828,034, CPI match 93.7%,
57.1% with Tair_C and Si, COCPIT-matched 914,528 (L1) / 530,599 (L2). Row-level QC:

| Check | Before | After | Note |
|---|---:|---:|---|
| QC1 | 4 | 4 | |
| QC2 | 80,593 | 80,662 | +69: IPHEX +24 and POSIDON +21 from the changed qv/Si; AIRS-II/MC3E/ICE-L/CFN +25 from `0.622 → 0.62197` (qv_sat 0.005% lower); no new failure mode |
| QC3 | 365 | 365 | |
| QC4 | 0 | 0 | |
| QC5 | 0 flags / **5** campaigns | 0 flags / **0** campaigns | definition fix |
| QC6 | 68 | 68 | |
| QC7 | 2 | 2 | |
| QC8 | 6 | 6 | |
| QC9 | 1,436 | 1,422 (IPHEX 1,377, OLYMPEX 45) | IPHEX Si shifted across the 1.05 trigger; 0 rows in L1/L2 |

## 4. Si bound — numbers on the rebuilt L0

350 values > 1.5 and 41 > 1.9 are kept; **586 L0 rows have Si above water saturation** at their
own temperature (ESCAPE 347, IPHEX 115, MACPEX 63, CRYSTAL-FACE-NASA 55, ICE-L 5, AIRS-II 1).
Si = 2 ≈ es_liq/es_ice at -85 °C (1.986). A temperature-dependent cap is a possible follow-up,
not applied (uniform-bound decision of 2026-09-21).
