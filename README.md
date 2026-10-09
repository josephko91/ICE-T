# ICE-T: Integrated Ice Crystal Embeddings and Thermodynamics

Combines atmospheric aircraft campaign data from 15 field campaigns into a
single dataset for thermodynamic analysis — ice supersaturation (Si), water
vapor (qv), and temperature vs. altitude — joined exact-second to CPI
(Cloud Particle Imager) particle images for morphology/ice-habit analysis.

## Data tiers

| Tier | Definition |
|------|------------|
| L0 | Every whole second where *any* instrument in a campaign reported *anything* (union of all instrument timestamps) |
| L1 | One row per CPI particle image, joined to its exact-second L0 environmental record |
| L2 | L1 filtered to rows with every core variable present (`Tair_C, P_hPa, Si, qv, Lat, Lon, Alt_m`) |

Every cross-instrument merge is an **exact-second join** (round half-up to the
nearest second, outer merge) — never a nearest-neighbor/tolerance match. A
second with no reading from a given instrument is NaN for that instrument,
not a borrowed value from a different second.

An additional pair of tiers (`L1_cocpit`, `L2_cocpit`) left-joins particle
size, geometry, and habit-classification features from a separate COCPIT
model output onto L1/L2 by `cpi_filename`. Producing these requires access
to the external COCPIT feature database (see `scripts/join_cocpit_features.py`)
and is not part of the core pipeline run.

## Campaigns

ARM, AIRS-II, ATTREX, CRYSTAL-FACE-NASA, CRYSTAL-FACE-UND, ESCAPE, IPHEX,
ICE-L, ISDAC, MACPEX, MC3E, MIDCIX, MPACE, OLYMPEX, POSIDON

## Getting started

1. **Clone the repository:**
   ```
   git clone https://github.com/josephko91/ICE-T.git
   cd ICE-T
   ```
2. **Install dependencies** (exact versions this pipeline was validated against — see `requirements.txt`):
   ```
   pip install -r requirements.txt
   ```
3. **Provide raw campaign data.** Raw instrument files are not distributed
   in this repository (`data/` is gitignored — campaign data is
   access-restricted/large). Populate `data/raw/<CAMPAIGN>/...` per
   `config.yaml`'s per-campaign `path`/`pattern` settings before running
   the pipeline.
4. **Run the pipeline:**
   ```
   python main.py --all                    # build L0 (combined_env_data_L0.parquet)
   python scripts/build_data_tiers.py      # derive L1/L2 from L0
   python scripts/qa_checks.py             # run the 9 QC checks
   ```

## Known limitations

- **ARM qv**: 63.6% NaN — real data sparsity in the dry upper troposphere, not a parser bug.
- **CPI/env unmatched images** (6.3% of CPI images): instrument power-on
  gaps relative to the aircraft's environmental recording, not a pipeline
  bug. Concentrated in ISDAC and one ARM flight date.
- **OLYMPEX, POSIDON, ESCAPE**: L0 env data only, zero L1/L2 rows — no CPI
  imagery archived for these campaigns in this pipeline's inputs.
- **MPACE**: zero L2 rows — flew no water-vapor instrument, so Si/qv are
  NaN for every record.

Full investigation history and per-decision rationale is in
`docs/decisions/` and `docs/reports/` (see `docs/README.md`); the curated,
user-facing summary of dataset-affecting changes is
`docs/dataset-changelog.md`.

## Adding a new campaign parser

Add `parsers/<campaign>.py` implementing `load_*()` + `extract_*_standard()`
following the existing parsers, then register it in `config.yaml`.

## License

GPLv3 — see `LICENSE`.

## Contact

Questions or contributions: open an issue or pull request, or email
Joseph Ko at jk4730@columbia.edu.
