# Dataset Validation Report — 2026-10-09

Validation of the L0/L1/L2 (and COCPIT-joined) tiers rebuilt after the timestamp-snapping
change from floor to half-up nearest-second rounding (`parsers/utils.py::round_timestamp_to_second`,
commit `51b8bdf`; rationale in `docs/decisions/2026-10-09-half-up-timestamp-rounding.md`,
detailed before/after in `docs/reports/2026-10-09-half-up-rounding-rebuild.md`).

Unlike the 2026-08-28 validation, **this run is not a no-change reproduction**: the one
code change is the rounding rule, so some counts are expected to move. The baseline
is the 2026-09-21 build (floor, uniform Si bound), kept at hand during the rebuild.
The question this report answers: did *only* the expected things move, and by how much?

> **Addendum (later 2026-10-09):** after this validation, all Si paths were moved to one Murphy & Koop
> saturation-vapor-pressure basis, `qv_from_ppmv` was made exact, and QC5's "campaigns affected" was
> redefined (`docs/decisions/2026-10-09-si-bound-and-thermo-basis.md`,
> `docs/reports/2026-10-09-qc-and-thermo-audit.md`). Row counts, L1/L2, CPI fusion % and COCPIT matching below
> are unchanged; Si/Sw/qv values shift slightly (Si max |Δ| 0.038), QC2 is 80,662 (was 80,593), QC9 is 1,422
> (was 1,436), QC5 is 0 flags / 0 campaigns. The availability percentages below are unchanged at 0.1-point
> resolution (best-instrument Si non-NaN +3 rows overall).

## Reproduce

```bash
conda activate cpi-thermo
python main.py --all
python scripts/build_data_tiers.py
python scripts/qa_checks.py
python scripts/diagnose_cpi_fusion.py
python scripts/diagnose_data_tiers.py
python scripts/diagnose_turbulence_coverage.py
python scripts/join_cocpit_features.py          # needs the local COCPIT v1.4.0 databases
pytest scripts/tests/test_round_timestamp.py scripts/tests/test_si_bounds.py scripts/tests/test_combined_env_data.py
```

## Row/campaign counts — L0/L1/L2

| Tier | Rows | Baseline (2026-09-21) | Δ |
|---|---:|---:|---:|
| L0 | 4,572,601 | 4,572,581 | +20 |
| L1 | 2,997,443 | 2,997,447 | −4 |
| L2 | 1,828,034 | 1,828,818 | −784 |

15 campaigns at L0; 12 with CPI imagery (3,200,351 images); 10 with any L2 rows
(OLYMPEX/POSIDON/ESCAPE have no CPI imagery, MPACE has no Si/qv, as before).

L0 per-campaign: 11 of 15 campaigns have identical row counts. Changed: ARM
141,940 → 141,956 (+16), CRYSTAL-FACE-NASA 323,310 → 323,315 (+5), POSIDON
351,508 → 351,507 (−1); ATTREX is unchanged in rows (1,316,204). L2 per-campaign
changes: ARM +162, CRYSTAL-FACE-NASA −459, MIDCIX −430, MC3E −39, IPHEX −18;
all others identical. Cause: sources stamped at a `.5`-second offset move one
second later relative to the whole-second CPI timestamps, re-matching images at
the edges of valid-data segments (verified in the rebuild report §3).

## QA checks (`scripts/qa_checks.py`)

| Check | Name | Flags | Baseline | Result |
|---|---|---:|---:|---|
| QC1 | Physical range checks | 4 | 4 | match |
| QC2 | Internal consistency | 80,593 | 80,608 | −15 (expected: data shifted 1 s) |
| QC3 | Stuck-sensor / temporal continuity | 365 | 365 | match |
| QC4 | Fill/sentinel value detection | 0 | 0 | match |
| QC5 | Inter-instrument cross-validation | 0 | 0 | match |
| QC6 | Per-flight coverage audit | 68 | 67 | +1 (see below) |
| QC7 | Duplicate/out-of-order timestamps | 2 | 2 | match |
| QC8 | Vertical profile plausibility | 6 | 6 | match |
| QC9 | LWC cross-check (severe Si flags) | 1,436 | 1,436 | match |

- **QC7 is the key check for this change** and is unchanged at 2 exact duplicates
  (both MPACE, unrelated to rounding): CRYSTAL-FACE-NASA, whose `.5`-offset 1 Hz
  files collided under pandas' round-half-to-even, has 0 duplicates under half-up.
- **QC6 +1**: a single ARM sample from the 2000-03-05 flight, just before UTC
  midnight, now rounds up into `2000-03-06 00:00:00` and creates a one-row
  "flight day" (Tair/P/Alt present, no Si). ARM `n_flight_days` 11 → 12.
- QC2 −15 is the net effect of a handful of rows moving by one second; no new
  failure mode.

## CPI/env timestamp fusion

| Metric | Count | % | Baseline |
|---|---:|---:|---|
| Matched env timestamp | 2,997,443 / 3,200,351 | 93.7% | 2,997,447 (93.7%) |
| Both `Tair_C` and `Si` present | 1,828,823 / 3,200,351 | 57.1% | 1,829,607 (57.2%) |
| All 7 core variables | 1,828,034 / 3,200,351 | 57.1% | 1,828,818 (57.1%) |

Headline percentages are unchanged at one decimal except "both Tair_C and Si"
(57.2% → 57.1%, −784 images, the same segment-edge shift as L2).

## COCPIT-joined tiers (`scripts/join_cocpit_features.py`, COCPIT v1.4.0)

| Tier | Matched to a COCPIT feature row | % | Baseline |
|---|---:|---:|---|
| L1 | 914,528 / 2,997,443 | 30.51% | 914,527 / 2,997,447 (30.51%) |
| L2 | 530,599 / 1,828,034 | 29.03% | 531,346 / 1,828,818 (29.05%) |

`combined_env_data_L1_cocpit.parquet` and `_L2_cocpit.parquet` were regenerated;
all five parquets in `data/out/` (L0, L1, L2, L1_cocpit, L2_cocpit) are consistent
with the half-up build. The matching is by `cpi_filename`, which the rounding
change does not touch, so the match rate is essentially unchanged.

## Turbulence coverage (`scripts/diagnose_turbulence_coverage.py`)

Wind_U/V/W and `EDR_m23s1` coverage per campaign is **identical at 0.1-percentage-point
resolution** to the pre-change build (checked column by column against the baseline
L0). Absolute non-NaN counts moved only for ARM (+16 Wind_W / EDR, the 16 extra
rows) — no other campaign's turbulence columns changed. Current values:
AIRS-II 96.9%, ARM 0%/100%/100%, ATTREX 43.9%/43.6%, CRYSTAL-FACE-NASA 81.5%
(confirmed again; see the 2026-08-28 validation for the history of that
figure), CRYSTAL-FACE-UND 77.7%/93.1%, ESCAPE 0%/100%, ICE-L ~100%, IPHEX
88.4–88.5%/99.3%, ISDAC 90.7–98.6%, MACPEX 83.1–83.3%, MC3E 77.7%/93.6%,
MIDCIX 0%, MPACE 47.5%/51.2%, OLYMPEX 99.1%/100%, POSIDON 96.4–96.6%/96.1%.

## L0 data availability by campaign (% non-null)

| Campaign | n_rows | Tair_C | P_hPa | Si | qv | Sw | Lat | Lon | Alt_m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AIRS-II | 312,792 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| ARM | 141,956 | 99.0 | 100.0 | 36.4 | 36.4 | 36.4 | 91.7 | 91.7 | 100.0 |
| ATTREX | 1,316,204 | 44.0 | 44.0 | 37.6 | 91.4 | 37.6 | 43.9 | 43.9 | 43.9 |
| CRYSTAL-FACE-NASA | 323,315 | 50.3 | 100.0 | 50.3 | 50.3 | 50.3 | 99.9 | 99.9 | 99.9 |
| CRYSTAL-FACE-UND | 200,864 | 98.3 | 99.5 | 66.2 | 65.9 | 65.9 | 99.9 | 99.9 | 100.0 |
| ESCAPE | 67,380 | 86.9 | 98.4 | 86.5 | 86.3 | 86.5 | 100.0 | 100.0 | 98.4 |
| ICE-L | 210,561 | 100.0 | 100.0 | 99.7 | 99.8 | 99.7 | 100.0 | 100.0 | 99.7 |
| IPHEX | 287,600 | 99.6 | 100.0 | 68.4 | 68.8 | 68.4 | 99.4 | 99.4 | 99.4 |
| ISDAC | 357,071 | 99.9 | 99.4 | 100.0 | 99.3 | 99.9 | 100.0 | 97.5 | 100.0 |
| MACPEX | 307,780 | 90.7 | 90.7 | 63.4 | 63.4 | 63.4 | 90.7 | 90.7 | 90.7 |
| MC3E | 165,431 | 98.6 | 100.0 | 88.2 | 88.2 | 88.2 | 90.7 | 90.7 | 100.0 |
| MIDCIX | 181,459 | 41.8 | 41.8 | 41.8 | 41.8 | 41.8 | 100.0 | 100.0 | 98.2 |
| MPACE | 139,360 | 58.9 | 100.0 | 0.0 | 0.0 | 0.0 | 89.4 | 89.4 | 89.4 |
| OLYMPEX | 209,321 | 100.0 | 100.0 | 58.4 | 58.4 | 58.4 | 100.0 | 100.0 | 100.0 |
| POSIDON | 351,507 | 97.2 | 98.2 | 52.0 | 53.1 | 52.0 | 76.6 | 76.6 | 76.6 |

Compared column by column with the pre-change L0, every availability percentage
is identical at 0.1-point resolution; only absolute non-NaN counts moved (ARM
Tair +15 / P +16 / Si +5 / Lat,Lon +10 / Alt +16; ATTREX Si/qv/Sw +6;
CRYSTAL-FACE-NASA Tair/P/Si/qv/Sw +5; POSIDON Si/Sw −1). The ESCAPE `qv`
figure (86.3) differs from the 2026-08-28 table (86.4) because of the 2026-09-21
uniform-Si-bound rebuild, not this change. MPACE Si/qv/Sw = 0% by design (no
water-vapor instrument flown).

## Tests

`pytest scripts/tests/test_round_timestamp.py scripts/tests/test_si_bounds.py
scripts/tests/test_combined_env_data.py` — 31 passed (7 new rounding tests: exact
ties round up, pandas `.round` collides on `:03.5`/`:04.5` while the helper does
not, non-ties round to nearest, 1 Hz `.5`-offset series has no collisions,
minute/day carry, UTC/NaT pass-through, `first_per_second` keeps the first
sample per rounded second). The built-parquet Si-bound invariants hold on the
rebuilt tiers.

## Known issues / open caveats

Unchanged by this rebuild — see CLAUDE.md's "Known issues / active
investigations". New caveat from this change: alignment of `.5`-offset sources
against whole-second CPI timestamps now follows nearest-second rather than
start-of-second, and whether each instrument's stamp marks the start, middle or
end of its averaging interval is undocumented per campaign (decision doc,
"Caveats").

## Conclusion

Switching timestamp snapping from floor to half-up nearest-second rounding moved
the dataset only where expected: L0 +20 rows (ARM, CRYSTAL-FACE-NASA, POSIDON),
L1 −4, L2 −784 (segment-edge re-matching against whole-second CPI timestamps),
with QC7 unchanged at 2 (no timestamp collisions), QC1/3/4/5/8/9 unchanged, QC2
−15 and QC6 +1 (a single ARM sample crossing UTC midnight), CPI match rate
unchanged at 93.7%, and per-campaign availability and turbulence coverage
unchanged at 0.1-point resolution. All five `data/out/` parquets are
regenerated and mutually consistent.
