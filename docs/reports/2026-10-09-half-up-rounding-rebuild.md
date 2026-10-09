# 2026-10-09 — Rebuild with half-up timestamp rounding (replaces floor)

Decision record: `docs/decisions/2026-10-09-half-up-timestamp-rounding.md`.
Code change: `parsers/utils.py::round_timestamp_to_second` now returns
`floor(ts + 0.5 s)` (round to nearest second, ties up) instead of
`.dt.floor("s")`. Every parser, `scripts/build_data_tiers.py` and
`scripts/diagnose_cpi_fusion.py` use that one helper, so the change applies
everywhere at once. Baseline = the 2026-09-21 build (floor); new = rebuilt
2026-10-09 from the same raw data. Same commands as always: `main.py --all`,
`build_data_tiers.py`, `qa_checks.py`, `diagnose_cpi_fusion.py`,
`diagnose_data_tiers.py`.

## 1. Why pandas' own `.round` could not be used

`Series.dt.round("s")` is round-half-to-even (NumPy / IEEE 754), not the
textbook half-up. Exact `.5` ties go to the nearest *even* second:

| raw | `.dt.round("s")` | half-up |
|---|---|---|
| `:01.5` | `:02` | `:02` |
| `:02.5` | `:02` | `:03` |
| `:03.5` | `:04` | `:04` |
| `:04.5` | `:04` | `:05` |

CRYSTAL-FACE-NASA files stamped at a fixed `.5` s offset are *all* ties, so
adjacent samples collided (4,454 duplicates in `JW20020719.WB57` alone; QC7
8,910 rows before the 2026-07-06 fix). Half-up avoids that: confirmed by this
rebuild, QC7 is unchanged at 2 exact duplicates (both MPACE, unrelated to
rounding), and CRYSTAL-FACE-NASA has 0.

## 2. Results (floor -> half-up)

| Tier | Before | After | Δ |
|---|---|---|---|
| L0 rows | 4,572,581 | 4,572,601 | +20 |
| L1 rows | 2,997,447 | 2,997,443 | −4 |
| L2 rows | 1,828,818 | 1,828,034 | −784 |

CPI/env fusion: matched 93.7% -> 93.7% (2,997,447 -> 2,997,443 of 3,200,351);
both Tair_C & Si 57.2% (1,829,607) -> 57.1% (1,828,823); all 7 core variables
57.1% (1,828,818 -> 1,828,034).

### L0 rows per campaign (only campaigns that changed)

| Campaign | Rows before | Rows after | Δ | Non-NaN Si Δ |
|---|---|---|---|---|
| ARM | 141,940 | 141,956 | +16 | +5 |
| CRYSTAL-FACE-NASA | 323,310 | 323,315 | +5 | +5 |
| POSIDON | 351,508 | 351,507 | −1 | −1 |
| ATTREX | 1,316,204 | 1,316,204 | 0 | +6 |

The other 11 campaigns have identical L0 row counts and per-variable
non-NaN counts. ARM's `n_flight_days` went 11 -> 12: one sample from the
2000-03-05 flight, just before UTC midnight, now rounds up into
`2000-03-06 00:00:00` (a one-row "flight day" with Tair/P/Alt but no Si). ARM and ATTREX are sub-second sources, so which
sample is "first in its second" shifts with the bin edges.

### L1 / L2 per campaign

| Campaign | L1 before | L1 after | L2 before | L2 after | L2 Δ |
|---|---|---|---|---|---|
| ARM | 230,029 | 230,029 | 64,706 | 64,868 | +162 |
| CRYSTAL-FACE-NASA | 78,151 | 78,151 | 20,441 | 19,982 | −459 |
| IPHEX | 38,697 | 38,697 | 28,189 | 28,171 | −18 |
| MC3E | 173,766 | 173,762 | 137,272 | 137,233 | −39 |
| MIDCIX | 90,667 | 90,667 | 18,890 | 18,460 | −430 |
| all others | unchanged | unchanged | unchanged | unchanged | 0 |

### QC (all 9 checks)

| Check | Before | After |
|---|---|---|
| QC1 range | 4 | 4 |
| QC2 consistency | 80,608 | 80,593 |
| QC3 stuck sensor | 365 | 365 |
| QC4 sentinels | 0 | 0 |
| QC5 cross-validation | 0 | 0 |
| QC6 zero-Si flight-days | 67 | 68 |
| QC7 duplicate timestamps | 2 | 2 |
| QC8 vertical profiles | 6 | 6 |
| QC9 LWC cross-check | 1,436 | 1,436 |

QC6's +1 is that same ARM `2000-03-06` one-row day (zero valid Si).

## 3. Why L2 dropped by 784 rows

CPI image timestamps are whole seconds. Sources stamped at a `.5`-second
offset used to land on `floor(t)` and now land on `floor(t) + 1`, so their
valid-data segments shift one second later relative to the CPI grid. Segment
edges are therefore re-matched: images at the old leading edge lose their
Si/Tair row, images at the new trailing edge gain one. Checked directly:

- Of the CPI images in L2 before but not after: MIDCIX 4,489, CRYSTAL-FACE-NASA
  2,136, ARM 1,694, MC3E 259, IPHEX 127. Images in L2 after but not before:
  MIDCIX 4,059, ARM 1,856, CRYSTAL-FACE-NASA 1,677, MC3E 220, IPHEX 109.
  (Counts are images, so they are larger than the net L2 change; net =
  gained − lost.)
- For the lost images' seconds in MIDCIX (204 unique seconds, all) and
  CRYSTAL-FACE-NASA (50 unique seconds, all), the new L0 has no complete
  Tair+Si row at that second but does at second+1: a one-second shift of the
  segment, not lost data.

The net loss is concentrated at segment edges and is not a data-quality
degradation. Which side is "truly" simultaneous with a CPI frame depends on
whether the instrument stamps the start, middle or end of its interval, which
is undocumented per campaign (see the decision doc's caveats).

## 4. Not rebuilt

`combined_env_data_L1_cocpit.parquet` / `_L2_cocpit.parquet` (built by
`scripts/join_cocpit_features.py` from an external, non-portable COCPIT path)
were not regenerated and are now stale relative to L1/L2. Re-run that script
when the COCPIT path is available. The earlier reports
(`2026-08-28-dataset-validation.md`, `2026-08-29-*`) describe the pre-change
(floor) numbers and are left as historical records.

## 5. Tests

`scripts/tests/test_round_timestamp.py` (new): exact ties round up, pandas
`.round` collides on `:03.5`/`:04.5` while the helper does not, non-ties round
to nearest, 1 Hz `.5`-offset series has no collisions, carries across
minute/day boundaries, UTC tz and NaT pass-through, and `first_per_second`
keeps the first sample per rounded second.
