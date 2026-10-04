# data/out

Pipeline outputs. Parquet files are gitignored (rebuild with the commands below); only this README is tracked.

| File | Contents | Built by |
|------|----------|----------|
| `combined_env_data_L0.parquet` | **L0.** Every whole second where any instrument in a campaign reported anything (union of all instrument timestamps). 15 campaigns, standard env schema (`Tair_C, P_hPa, Si, qv, Lat, Lon, Alt_m`, per-instrument columns, wind/EDR). | `python main.py --all` |
| `combined_env_data_L1.parquet` | **L1.** One row per CPI particle image, joined to its exact-second L0 record. `cpi_filename` identifies the image; images sharing a second duplicate that second's env data. Contains no OLYMPEX/POSIDON/ESCAPE rows (no CPI imagery). | `python scripts/build_data_tiers.py` |
| `combined_env_data_L2.parquet` | **L2.** L1 filtered to rows with all core variables present (`Tair_C, P_hPa, Si, qv, Lat, Lon, Alt_m`). | `python scripts/build_data_tiers.py` |
| `combined_env_data_L1_cocpit.parquet` | L1 plus COCPIT v1.4.0 particle size/geometric/habit features, joined on `cpi_filename`. About 30% of rows have a matched feature row. | `python scripts/join_cocpit_features.py` |
| `combined_env_data_L2_cocpit.parquet` | L2 plus the same COCPIT features. | `python scripts/join_cocpit_features.py` |

The `_cocpit` files depend on an external COCPIT path and are not part of `main.py`'s pipeline.
See `CLAUDE.md` ("Data tiers") for details.
