"""Unit tests for parsers.utils.round_timestamp_to_second (half-up nearest second).

pandas ``.dt.round("s")`` is round-half-to-even, so exact .5 ties collide on
fixed-.5s-offset 1 Hz data; the helper must round ties UP instead. See
docs/decisions/2026-10-09-half-up-timestamp-rounding.md.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from parsers.utils import first_per_second, round_timestamp_to_second  # noqa: E402


def _ts(*stamps):
    return pd.Series(pd.to_datetime(list(stamps), utc=True))


def _secs(series):
    return series.dt.strftime("%S").tolist()


def test_exact_ties_round_up():
    raw = _ts(*[f"2002-07-19 00:00:0{i}.5" for i in range(6)])
    assert _secs(round_timestamp_to_second(raw)) == ["01", "02", "03", "04", "05", "06"]


def test_pandas_round_would_collide_on_ties():
    """Documents WHY the helper exists: pandas rounds ties to even."""
    raw = _ts("2002-07-19 00:00:03.5", "2002-07-19 00:00:04.5")
    assert _secs(raw.dt.round("s")) == ["04", "04"]
    assert _secs(round_timestamp_to_second(raw)) == ["04", "05"]


def test_non_ties_round_to_nearest():
    raw = _ts("2002-07-19 00:00:03.499", "2002-07-19 00:00:03.501",
              "2002-07-19 00:00:03.0", "2002-07-19 00:00:03.999")
    assert _secs(round_timestamp_to_second(raw)) == ["03", "04", "03", "04"]


def test_one_hz_half_offset_has_no_collisions():
    raw = pd.Series(pd.date_range("2002-07-19 00:00:00.5", periods=1000, freq="1s", tz="UTC"))
    out = round_timestamp_to_second(raw)
    assert out.is_unique
    assert (out.diff().dropna() == pd.Timedelta("1s")).all()


def test_carries_into_next_minute_and_day():
    raw = _ts("2002-07-19 23:59:59.5", "2002-07-19 00:00:59.7")
    out = round_timestamp_to_second(raw)
    assert out.iloc[0] == pd.Timestamp("2002-07-20 00:00:00", tz="UTC")
    assert out.iloc[1] == pd.Timestamp("2002-07-19 00:01:00", tz="UTC")


def test_utc_tz_and_nat_passthrough():
    raw = pd.Series(["2002-07-19 00:00:00.5", None, "bad"])
    out = round_timestamp_to_second(raw)
    assert str(out.dt.tz) == "UTC"
    assert out.iloc[0] == pd.Timestamp("2002-07-19 00:00:01", tz="UTC")
    assert out.iloc[1:].isna().all()


def test_first_per_second_keeps_first_sample_of_subsecond_data():
    df = pd.DataFrame({
        "Timestamp": pd.to_datetime(
            ["2002-07-19 00:00:00.9", "2002-07-19 00:00:01.1", "2002-07-19 00:00:01.4",
             "2002-07-19 00:00:02.6"], utc=True),
        "v": [1, 2, 3, 4],
    })
    out = first_per_second(df)
    # :00.9, :01.1, :01.4 all round to :01 (keep first); :02.6 -> :03
    assert out["v"].tolist() == [1, 4]
    assert _secs(out["Timestamp"]) == ["01", "03"]
