# 2026-10-09 — Timestamp snapping: half-up nearest-second rounding (supersedes floor)

## Question

Every parser snaps each instrument's timestamp to a whole second
(`parsers/utils.py::round_timestamp_to_second`) before the exact-second
merge. Since 2026-07-06 that helper *floored*. The docs described this as
"floored to the nearest second", which is not a coherent description, and
the intent was nearest-second rounding. Which rule should the pipeline use?

## Why not pandas `.dt.round("s")`

**pandas does not implement textbook round-half-up.** `Series.dt.round`
follows NumPy / IEEE 754 *round half to even* ("banker's rounding"): a value
strictly above or below .5 rounds normally, but an **exact .5 tie goes to the
nearest even second**, not up. Python's built-in `round(2.5) == 2` behaves the
same way. Verified with pandas 3.0.2:

| raw     | `.dt.round("s")` | `.dt.floor("s")` | half-up (adopted) |
|---------|------------------|------------------|-------------------|
| `:00.5` | `:00`            | `:00`            | `:01`             |
| `:01.5` | `:02`            | `:01`            | `:02`             |
| `:02.5` | `:02`            | `:02`            | `:03`             |
| `:03.5` | `:04`            | `:03`            | `:04`             |
| `:04.5` | `:04`            | `:04`            | `:05`             |
| `:05.5` | `:06`            | `:05`            | `:06`             |

Some raw sources (CRYSTAL-FACE-NASA, e.g. `JW20020719.WB57`) sample at 1 Hz
with every timestamp at a fixed `.5` s offset, so *every* sample is a tie.
Under `.dt.round` adjacent samples pair up (`:01.5` and `:02.5` both become
`:02`): about half the file turned into duplicate-timestamp rows (4,454 in
that one file; QC7 flagged 8,910 rows pipeline-wide) and the odd seconds were
left empty. That was the bug fixed on 2026-07-06 (commit `ee1a933`).

## Decision

Round **half-up**: `floor(ts + 0.5 s)`. Ties go up; anything else goes to the
nearest second. The `floor` is just the truncation step that completes the
offset-then-truncate idiom; the result is ordinary nearest-second rounding.
1 Hz data at any fixed sub-second offset maps one-to-one onto distinct
seconds, so the collision bug cannot recur.

Why this supersedes the 2026-07-06 / 2026-07-07 floor choice: those documents
compared floor only against banker's rounding and never against half-up. The
collision problem is a property of the tie-break rule, not of rounding, so it
is not a reason to prefer floor. The function name (`round_timestamp_to_second`)
was already accurate for half-up and is unchanged.

## What changes in the data

Integer-second sources are unaffected (no ties, no fractional part). Sources
with a fractional-second stamp now land on `round(t)` instead of `floor(t)`,
i.e. up to 1 s later. Measured effect of the full rebuild is in
`docs/reports/2026-10-09-half-up-rounding-rebuild.md`: L0 +20 rows, L1 −4,
L2 −784, QC7 unchanged.

## Caveats

- Neither rule is inherently "more correct" for cross-instrument alignment;
  it depends on whether each instrument stamps the start, middle or end of
  its averaging interval, which is not documented per campaign. Half-up
  matches the nearest whole-second grid point; floor assumed start-of-interval.
  CPI image timestamps are whole seconds, so sources with a `.5` offset are
  now matched to the CPI second *after* the one they matched before (see the
  report's L2 analysis).
- Sub-second sources (ARM 4 Hz, ATTREX UCATS ~1.5 s) still put several raw
  samples in one second under any rounding rule; these are handled by the
  keep-first dedupe (`first_per_second`, ATTREX parser), not by rounding.
- `scripts/tests/test_round_timestamp.py` pins the tie behaviour and the
  no-collision property.
