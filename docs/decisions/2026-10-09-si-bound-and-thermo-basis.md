# 2026-10-09 — Thermodynamic units, one saturation-vapor-pressure basis, and the Si [-1, 2] bound

## Question

A review of the paper text asked (a) whether the equations handle units
explicitly (Murphy & Koop e_s is in Pa, `P_hPa` is in hPa) and (b) what
justifies masking `Si` outside [-1, 2], given that very high `Si` is physically
documented near the homogeneous-freezing threshold.

## 1. Units (convention, now pinned in code and tests)

| Quantity | Unit | Where |
|---|---|---|
| Temperature at the API | degC (`*_C`) or K (`*_K`) | argument names |
| Murphy & Koop (2005) e_s (ice, liquid) | evaluated with T in K; **returns Pa** | `parsers/utils.py::es_ice` (Pa), `es_liq_hPa` (converts) |
| e_s, e, P everywhere else | **hPa**; Pa -> hPa is `/ 100` (`_PA_PER_HPA`) | `es_ice_hPa`, `es_liq_hPa`, `P_hPa` |
| Vapor pressure from a volume mixing ratio | `e [hPa] = ppmv * 1e-6 * P [hPa]` (x is a mole fraction, dimensionless) | `si_from_ppmv` |
| Si | `e / e_s,ice(T) - 1`, e and e_s in the **same** unit; dimensionless | all paths |
| q_v | `1000 * eps * e / (P - e)` g/kg of dry air; e, P in the same unit; eps = 18.015/28.964 | `qv_from_e_P` |

Findings that led to code changes (all verified numerically):

- `es_ice`'s docstring said "hPa" but the expression returns Pa (611.207 at 0 degC;
  Murphy & Koop's anchor is 611.657 Pa at 273.16 K). The *behavior* was right —
  `es_ice_hPa`/`es_liq_hPa` divide by 100 and `si_from_frost_point` uses only the
  unit-free ratio of two `es_ice` values — so no data was affected by the
  docstring. Docstring fixed; the magic `100` is now `_PA_PER_HPA`.
- **One saturation-vapor-pressure basis.** The paper says Si/qv use "a single common
  thermodynamic basis" (Murphy & Koop 2005). That was not true of the code:
  `si_from_ppmv` (ATTREX, MACPEX, CRYSTAL-FACE-NASA HW/ALIAS, ICE-L MRTDL), POSIDON
  (`posidon.py`) and IPHEX (`iphex.py`, both the frost-point chilled-mirror Si and the
  Ophir Si) used a Magnus/Tetens fit `6.112*exp(22.46*Tc/(Tc+272.6))`. IPHEX was
  internally inconsistent (Si via Tetens, qv via Murphy & Koop). Tetens/Magnus differs
  from Murphy & Koop in e_s by 0.05% at -50 degC, 0.5% at -70 degC, 1.3% at -85 degC.
  All paths now call `es_ice_hPa`. `scripts/tests/test_thermo_units.py` asserts the
  ppmv and frost-point paths give identical Si for matching inputs.
- **Exact q_v for ppmv paths.** `qv_from_ppmv` was `eps * ppmv * 1e-3`, i.e.
  `eps * e / P`, omitting the `(P - e)` of the paper's equation (~2% high at
  20,000 ppmv, <0.1% in the upper troposphere). It is now `1000*eps*x/(1-x)`, identical
  to `qv_from_e_P(x*P, P)`.
- `scripts/qa_checks.py` used a literal `0.622`; it now imports `EPSILON` (0.62197).
- Measured data effect: see `docs/reports/2026-10-09-qc-and-thermo-audit.md`.

## 2. Why Si is masked outside [-1, 2]

- **Lower bound, -1:** exact. `Si = e/e_s - 1` and `e >= 0`.
- **Upper bound, 2:** an *engineering plausibility cut*, not a physical law; no
  publication prescribes 2.0. It is chosen because it sits at the upper edge of what
  is documented for real atmospheric/laboratory conditions:
  - Homogeneous freezing of aqueous solution droplets is governed by water activity
    (Koop et al. 2000), giving an onset ice saturation ratio that rises as T falls.
    Laboratory onsets at cirrus temperatures reach about 1.6-1.7 (WAC) and 1.7-2.0
    (AIDA) between 185 and 205 K (Schneider et al. 2021); Baumgartner et al. (2022) report
    thresholds at low T possibly higher than the Koop line.
  - In situ, Kraemer et al. (2009) found no supersaturation above water saturation in
    clear air in their quality-checked flights, and frequent in-cloud
    super/subsaturation below 205 K.
  - Computed from Murphy & Koop (this repo, `es_liq_hPa/es_ice_hPa`), the ice
    saturation ratio at *water* saturation is 1.45 (-38 degC), 1.72 (-60 degC),
    1.83 (-70 degC), **1.99 (-85 degC)**. Si = 2 is therefore approximately water
    saturation at the coldest temperatures sampled (ATTREX reaches -87 degC): a
    uniform cap that does not reject documented cold-cirrus values.
- The pipeline **masks** (sets NaN), it never clips to the bound; "clip" in prose
  should read "set to missing".

### Honest limitations of this bound

- It is uniform, so at warm temperatures it admits values above water saturation
  (water saturation is only 1.2-1.4 between -20 and -30 degC). Counted on the
  rebuilt L0: **586 rows have Si above water saturation at their own
  temperature** (ESCAPE 347, IPHEX 115, MACPEX 63, CRYSTAL-FACE-NASA 55, ICE-L 5,
  AIRS-II 1). A temperature-dependent cap `Si <= es_liq/es_ice` would be physically
  tighter but contradicts the 2026-09-21 decision for one dataset-wide bound, so it is
  recorded here as a possible follow-up and **not applied**.
- Effect of the bound (2026-08-28 construction report): 1,560 best-instrument values
  (0.058% of valid Si) are removed (CRYSTAL-FACE-NASA 1,286, ESCAPE 272, MACPEX 2);
  350 L0 Si values >1.5 and 41 >1.9 are retained (rebuilt L0).

## 3. QC9 and the "known limitation"

QC9's 1,422 rows (1,436 before the Murphy & Koop basis switch moved some IPHEX Si
across the 1.05 trigger) are 1,377 IPHEX + 45 OLYMPEX **at L0 only**; exact-second
matching shows **none** of them in L1 or L2, and OLYMPEX has no CPI imagery. Of the
1,422, 1,279 are at T <= -38 degC (Si <= 1.53, all below water saturation: plausible cirrus),
but 143 IPHEX rows are at -30...-20 degC with Si up to 1.68, **110 of them above water
saturation** (1.23-1.33 there). Homogeneous freezing of solution droplets does not
apply at those temperatures, so those rows are more consistent with an instrument
artifact than with "approaching the homogeneous-freezing threshold".

## References (DOIs verified via Crossref / publisher pages, 2026-10-09)

- Koop, T., Luo, B., Tsias, A., Peter, T.: Water activity as the determinant for
  homogeneous ice nucleation in aqueous solutions, *Nature*, 406, 611-614,
  doi:10.1038/35020537, 2000.
- Murphy, D. M., Koop, T.: Review of the vapour pressures of ice and supercooled water
  for atmospheric applications, *Q. J. R. Meteorol. Soc.*, 131(608), 1539-1565,
  doi:10.1256/qj.04.94, 2005.
- Kraemer (Krämer), M., et al.: Ice supersaturations and cirrus cloud crystal numbers,
  *Atmos. Chem. Phys.*, 9, 3505-3522, doi:10.5194/acp-9-3505-2009, 2009. (Abstract
  statements used: no supersaturation above water saturation in clear air; frequent
  in-cloud super/subsaturation below 205 K.)
- Schneider, J., et al.: High homogeneous freezing onsets of sulfuric acid aerosol at
  cirrus temperatures, *Atmos. Chem. Phys.*, 21, 14403-14425,
  doi:10.5194/acp-21-14403-2021, 2021.
- Baumgartner, M., et al.: New investigations on homogeneous ice nucleation: the effects
  of water activity and water saturation formulations, *Atmos. Chem. Phys.*, 22, 65-91,
  doi:10.5194/acp-22-65-2022, 2022.
