"""censor_block_gap must read outcomes the way the v2 panel defines a death.

Run: python -m pytest benchmark/splits/test_censor_gap.py
"""

from __future__ import annotations

import pandas as pd

from benchmark.splits.rolling_origin import censor_block, censor_block_gap


def _matrix():
    """Origins (alive years) of three spells, with the panel's target columns.

    a: alive 2012-2015, dies after 2015 (event confirmed once 2016-2017 seen).
    b: alive 2012, gap year 2013, alive 2014-2016, still alive at the end.
    c: alive 2012-2014, then the importer stops filing: censored, not dead.
    """
    rows = []
    for sid, years, last, died in (("a", range(2012, 2016), 2015, 1),
                                   ("b", [2012, 2014, 2015, 2016], 2016, 0),
                                   ("c", range(2012, 2015), 2014, 0)):
        for y in years:
            rows.append({"spell_id": sid, "year": y, "last_alive_year": last,
                         "event_u": died, "duration_u": last - y + 1})
    return pd.DataFrame(rows)


def _row(b, sid, year):
    r = b[(b.spell_id == sid) & (b.year == year)]
    return None if r.empty else (int(r.duration.iloc[0]), int(r.event.iloc[0]))


def test_death_needs_gap_plus_one_empty_years():
    df = _matrix()
    # horizon 2016: only 2016 seen empty, the death in 2015 is unconfirmed
    b = censor_block_gap(df, 2012, 2012, 2016, 1, df)
    assert _row(b, "a", 2012) == (3, 0)          # known alive through 2015
    # horizon 2017: 2016 and 2017 both empty, the death is confirmed
    b = censor_block_gap(df, 2012, 2012, 2017, 1, df)
    assert _row(b, "a", 2012) == (4, 1)
    # with no gap rule the old reading is reproduced
    assert _row(censor_block_gap(df, 2012, 2012, 2016, 0, df), "a", 2012) == (4, 1)
    assert _row(censor_block(df, 2012, 2012, 2016), "a", 2012) == (4, 1)


def test_survival_is_read_off_the_last_year_actually_alive():
    df = _matrix()
    # b is in its gap year at the horizon: alive in 2012 only -> no follow-up
    assert _row(censor_block_gap(df, 2012, 2012, 2013, 1, df), "b", 2012) is None
    # the plain rule credits a year of survival it could not have seen
    assert _row(censor_block(df, 2012, 2012, 2013), "b", 2012) == (1, 0)


def test_record_that_stops_early_is_not_followed_to_the_horizon():
    df = _matrix()
    assert _row(censor_block_gap(df, 2012, 2012, 2025, 1, df), "c", 2012) == (2, 0)
    assert _row(censor_block(df, 2012, 2012, 2025), "c", 2012) == (13, 0)
