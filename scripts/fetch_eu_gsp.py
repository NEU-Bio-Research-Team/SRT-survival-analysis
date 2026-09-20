"""Pull the EU's GSP schedules from TRAINS, as group codes.

Before EVFTA, Vietnamese goods did not enter the EU at the MFN rate: Viet Nam
was a beneficiary of the EU's standard GSP arrangement. TRAINS files that
schedule, but under a *group* partner code rather than under Viet Nam's own
704, which is why `fetch_tariffs.py` - which asks only for partner 704 - never
saw it, and why every pre-2020 EU episode in the panel carries an MFN rate
that overstates what was actually charged.

The group codes the EU's own availability record lists, checked 29/08/2026:

  G26  GSP Beneficiaries: EU 2000        2000-2003
  G27  GSP Beneficiaries: EU 2004        2004-2013 (not 2010)
  P24  GSP Beneficiaries: EU 2010        2010
  A34  GSP Beneficiaries: EU 2014        2014
  L20  GSP for LDC Beneficiaries: EU     2015 - LDC only, Viet Nam is not one,
                                         pulled purely as a contrast

From 2015 to 2019 the EU files no GSP group at all, so those five years cannot
be recovered from TRAINS; from August 2020 EVFTA supersedes GSP anyway and the
rate comes from the staging schedule instead.

Caveat to carry into the writing: a group schedule is the arrangement, not
Viet Nam's entitlement under it. Product graduation can remove individual
sections for individual beneficiaries, and TRAINS does not publish who was
graduated when.

Usage: python3 fetch_eu_gsp.py
"""

import csv
import gzip
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_tariffs as ft                                   # noqa: E402

EUN = "918"
TARGETS = ([("G26", y) for y in range(2000, 2004)]
           + [("G27", y) for y in range(2004, 2014) if y != 2010]
           + [("P24", 2010), ("A34", 2014), ("L20", 2015)])

OUT = os.path.join(ft.RAW, "pref")


def main():
    os.makedirs(OUT, exist_ok=True)
    done = skipped = failed = 0
    for group, year in TARGETS:
        path = os.path.join(OUT, f"EUN_{year}_{group}.csv.gz")
        if os.path.exists(path):
            skipped += 1
            continue
        status, payload = ft.fetch(
            f"{ft.WITS}/SDMX/V21/datasource/TRN/reporter/{EUN}"
            f"/partner/{group}/product/ALL/year/{year}/datatype/reported")
        if status == 200 and payload:
            rows = ft.parse_tariff(payload)
            ft.save(path, rows)
            done += 1
            print(f"  EUN {year} <- {group}: {len(rows):,} lines", flush=True)
        else:
            failed += 1
            print(f"  EUN {year} <- {group}: HTTP {status}", flush=True)
        time.sleep(ft.SLEEP)
    print(f"\nGSP pass: {done} downloaded, {skipped} already on disk, "
          f"{failed} without data")


if __name__ == "__main__":
    main()
