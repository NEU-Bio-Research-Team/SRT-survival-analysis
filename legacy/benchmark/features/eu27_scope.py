"""Year-varying EU-27 membership, shared by build_matrix.py (--eu27-only) and any
ad-hoc diagnostic that needs the same VN x EU27 restriction.

selection/eu_tariff_mapping.csv encodes membership of the EU *customs regime*
per (iso3, year) via `tariff_reporter == "EUN"`. That is the right flag for
tariffs, but it is not the B0 sample on its own: GBR is "EUN" through 2020
(Brexit transition period) and HRV only from 2013 (accession). B0 in
Stage1_Research_Framework.md fixes the main sample as EU-27 and says
"UK tách riêng (Brexit) ... Không gộp vào mẫu chính".

So the main sample is the intersection of two conditions:
  1. iso3 is one of the 27 post-Brexit members (the "EUN" set in the mapping's
     last year), which removes GBR in every year; and
  2. iso3 is "EUN" in that origin year, which keeps HRV out before accession.

The mapping stops at 2023 - there is no EU accession or exit after that, so
later years carry 2023's membership forward.
"""

from __future__ import annotations

import pandas as pd

N_MEMBERS = 27


def eu27_membership(mapping_path: str, through_year: int) -> pd.DataFrame:
    """(importer, year) pairs in the B0 main sample, extended to `through_year`."""
    eu = pd.read_csv(mapping_path)
    eu = eu[eu["tariff_reporter"] == "EUN"][["iso3", "year"]].rename(
        columns={"iso3": "importer"})
    max_year = int(eu["year"].max())
    members = set(eu.loc[eu["year"] == max_year, "importer"])
    if len(members) != N_MEMBERS or "GBR" in members:
        raise ValueError(f"expected the {N_MEMBERS} post-Brexit members in "
                         f"{max_year}, got {len(members)}: {sorted(members)}")
    eu = eu[eu["importer"].isin(members)]
    if through_year > max_year:
        carried = eu[eu["year"] == max_year]
        extra = pd.concat(
            [carried.assign(year=y) for y in range(max_year + 1, through_year + 1)],
            ignore_index=True)
        eu = pd.concat([eu, extra], ignore_index=True)
    return eu


def filter_eu27(df: pd.DataFrame, mapping_path: str,
                importer_col: str = "importer",
                year_col: str = "year") -> pd.DataFrame:
    """Keep only rows whose (importer, year) is in the B0 EU-27 main sample."""
    through_year = int(df[year_col].max())
    eu = eu27_membership(mapping_path, through_year)
    eu = eu.rename(columns={"importer": importer_col, "year": year_col})
    merged = df.merge(eu.assign(_eu27=True), on=[importer_col, year_col],
                      how="left")
    is_eu27 = merged["_eu27"].astype("boolean").fillna(False)
    kept = merged[is_eu27].drop(columns=["_eu27"])
    return kept.reset_index(drop=True)
