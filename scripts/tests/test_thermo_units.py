"""Unit/consistency tests for the thermodynamic helpers in parsers/utils.py.

Pins the unit convention (Murphy & Koop e_s in Pa from es_ice(); hPa everywhere
else) and that every Si/qv path shares one Murphy & Koop basis.
See docs/decisions/2026-10-09-si-bound-and-thermo-basis.md.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from parsers.utils import (  # noqa: E402
    EPSILON, es_ice, es_ice_hPa, es_liq_hPa, qv_from_e_P, qv_from_ppmv,
    si_from_frost_point, si_from_ppmv,
)


def test_es_ice_is_pa_and_matches_triple_point():
    # Water triple point: 273.16 K, 611.657 Pa (Murphy & Koop 2005 anchor value).
    assert es_ice(273.16 - 273.15) == pytest.approx(611.657, abs=0.15)


def test_hpa_wrappers_divide_by_100():
    for t in (-85.0, -50.0, -10.0, 0.0):
        assert es_ice_hPa(t) == pytest.approx(es_ice(t) / 100.0)
    # liquid and ice agree at 0 degC to <0.1% (both ~6.11 hPa)
    assert es_liq_hPa(0.0) == pytest.approx(es_ice_hPa(0.0), rel=1e-3)


def test_liquid_to_ice_ratio_is_si_at_water_saturation():
    # Si at water saturation: ~1.45 (-38 degC), ~1.99 (-85 degC)
    assert es_liq_hPa(-38.0) / es_ice_hPa(-38.0) == pytest.approx(1.446, abs=0.005)
    assert es_liq_hPa(-85.0) / es_ice_hPa(-85.0) == pytest.approx(1.986, abs=0.01)


def test_qv_from_e_P_known_value():
    assert qv_from_e_P(1.0, 500.0) == pytest.approx(1000 * EPSILON * 1.0 / 499.0)


@pytest.mark.parametrize("P", [50.0, 250.0, 500.0, 1000.0])
@pytest.mark.parametrize("ppmv", [5.0, 500.0, 20000.0])
def test_qv_from_ppmv_equals_qv_from_e_P(ppmv, P):
    e_hPa = ppmv * 1e-6 * P
    assert qv_from_ppmv(ppmv) == pytest.approx(qv_from_e_P(e_hPa, P), rel=1e-12)


def test_ppmv_and_frost_point_paths_share_one_basis():
    # Build the ppmv that corresponds to frost point Tf at (T, P): both Si paths must agree.
    for t_c, tf_c, p in [(-60.0, -62.0, 250.0), (-30.0, -31.0, 500.0), (-80.0, -78.0, 120.0)]:
        ppmv = es_ice_hPa(tf_c) / p * 1e6
        si_p = si_from_ppmv(ppmv, t_c + 273.15, p)
        si_f = si_from_frost_point(tf_c, t_c)
        assert float(si_p) == pytest.approx(float(si_f), abs=1e-10)


def test_si_from_ppmv_invalid_inputs_are_nan():
    assert np.isnan(si_from_ppmv(-5.0, 220.0, 250.0))
    assert np.isnan(si_from_ppmv(100.0, 220.0, -1.0))
