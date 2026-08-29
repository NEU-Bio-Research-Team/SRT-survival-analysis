"""Step 8b: non-tariff measures at HS6 x date, from UNCTAD TRAINS Online.

This is the source the three public WITS files cannot replace. Those hold one
sector-level cross-section with no year dimension; this holds individual
measures, each carrying the HS6 lines it covers, the date it took effect and the
date it was repealed - which is what lets an NTM be dated in force for a product
in a year instead of averaged into a sector constant.

**No account is required.** Every earlier document in this project said one was.
That was wrong, and the reason it looked true is worth remembering: the endpoint
answers `200` with an empty array when the body is malformed, which is
indistinguishable from a permission wall. The specific requirement is that
`affectedCountries` carries the full list of country ids even when
`allAffectedCountries` is true. Send it empty and you get `[]` forever.

**The real constraint is a rate limit.** The host sits behind Cloudflare, which
returns error 1015 after a short burst - measured at roughly six requests, and
still triggered at a six-second spacing. `pageSize` is capped at 20. So this
fetcher is deliberately slow, fully resumable, and gives up rather than
hammering: every page is cached on disk, a restart skips what is already there,
and the pacing it learns is written down so the next run starts where the last
one left off rather than re-discovering the limit.

    python3 fetch_ntm_trains.py --probe        # settle the open questions cheaply
    python3 fetch_ntm_trains.py                # the pull itself, resumable
    python3 fetch_ntm_trains.py --countries IDN,THA

Output: data_raw/ntm/trainsonline/{iso3}_{page}.json.gz
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEL = os.path.join(HERE, "selection")
RAW = os.path.join(HERE, "data_raw", "ntm", "trainsonline")
API = "https://api-trains2.unctad.org"
STATE = os.path.join(RAW, "_pacing.json")

# The complete header set a real browser sends, copied from a captured request.
# None of it is a credential - there is no Authorization header and no cookie,
# which is the whole point of this file. It is reproduced in full rather than
# trimmed because the host sits behind Cloudflare: the one replay that used
# every header succeeded immediately, while the trimmed five-header version
# collected a 429 within six requests. Whether that is cause or coincidence is
# not settled, but sending the full set costs nothing.
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://trainsonline.unctad.org",
    "referer": "https://trainsonline.unctad.org/",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", '
                 '"Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
}

PAGE_SIZE = 20          # the API rejects anything larger with a 400
GAP_START = 8.0         # seconds between requests, before any 429 is seen
GAP_MAX = 90.0
BACKOFF_START = 60      # first wait after a 429
MAX_CONSECUTIVE_429 = 5 # give up and let the caller re-run later

# Every column the endpoint will return. The UI sends this block and hides most
# of it; there is no reason for a research pull to ask for less, and the two
# that matter most - the collection years and the repeal date - are exactly the
# ones the UI switches off by default.
COLUMNS = {
    "countryImposingNTMsVisible": True, "affectedCountriesNamesVisible": True,
    "ntmCodeVisible": True, "ntmDescriptionVisible": True,
    "measureDescriptionVisible": True, "productDescriptionVisible": True,
    "hsCodeVisible": True, "issuingAgencyVisible": True,
    "regulationTitleVisible": True, "regulationSymbolVisible": True,
    "implementationDateVisible": True, "regulationFileVisible": True,
    "regulationOfficialTitleOriginalVisible": False,
    "measureDescriptionOriginalVisible": False,
    "measureProductDescriptionOriginalVisible": False,
    "supportingRegulationsVisible": False,
    "measureObjectivesOriginalVisible": False,
    "yearsOfDataCollectionVisible": True, "repealDateVisible": True,
    "objectiveCodesVisible": True,
}


class RateLimited(Exception):
    """Cloudflare is refusing. Not retryable inside one call."""


class Client:
    """One conversation with the API, pacing itself and remembering the pace."""

    def __init__(self):
        self.gap = GAP_START
        self.consecutive_429 = 0
        if os.path.exists(STATE):
            try:
                with open(STATE) as f:
                    self.gap = min(GAP_MAX, float(json.load(f).get("gap", GAP_START)))
                print(f"  resuming at a learned {self.gap:.0f}s spacing")
            except (ValueError, OSError):
                pass

    def save_pacing(self):
        os.makedirs(RAW, exist_ok=True)
        with open(STATE, "w") as f:
            json.dump({"gap": self.gap}, f)

    def call(self, path, body=None, timeout=240):
        while True:
            req = urllib.request.Request(
                f"{API}/{path}",
                data=json.dumps(body).encode() if body is not None else None,
                headers=HEADERS, method="POST" if body is not None else "GET")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    payload = json.loads(r.read())
                self.consecutive_429 = 0
                time.sleep(self.gap)
                return payload
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise
                self.consecutive_429 += 1
                if self.consecutive_429 > MAX_CONSECUTIVE_429:
                    raise RateLimited(
                        f"{self.consecutive_429} consecutive 429s at a "
                        f"{self.gap:.0f}s spacing")
                # Slow down permanently, not just for this retry: a limit hit
                # once at this pace will be hit again at this pace.
                self.gap = min(GAP_MAX, self.gap * 1.5)
                self.save_pacing()
                wait = BACKOFF_START * (2 ** (self.consecutive_429 - 1))
                print(f"    rate limited - waiting {wait}s, spacing now "
                      f"{self.gap:.0f}s", flush=True)
                time.sleep(wait)
            except Exception as ex:
                print(f"    {type(ex).__name__} - retrying in 30s", flush=True)
                time.sleep(30)


def countries():
    """(iso3, trains_id) for the panel importers TRAINS actually covers."""
    path = os.path.join(SEL, "trains_countries.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} missing - run with --probe first")
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        # EUN is not a panel importer but carries every EU measure, which is how
        # the EU files them - the same consolidation the tariff pull uses.
        if r["in_panel"] == "1" or r["iso3"] == "EUN":
            out.append((r["iso3"], int(r["trains_id"])))
    return sorted(out)


def all_country_ids():
    path = os.path.join(SEL, "trains_countries.csv")
    return [int(r["trains_id"])
            for r in csv.DictReader(open(path, encoding="utf-8"))]


def query(imposing_id, page, affected):
    return {
        "imposingCountries": [imposing_id],
        "allImposingCountries": False,
        "internationalStandardsImposing": False,
        # The full list is required even with allAffectedCountries true. Sending
        # [] returns an empty array and looks exactly like a permission error.
        "affectedCountries": affected,
        "allAffectedCountries": True,
        "products": [],
        "allProducts": True,
        "NTMType": None, "ExcludeHorizontalMeasures": None,
        "FromDate": None, "ToDate": None,
        "IsImportNtm": None, "IsUnilateral": None,
        "pageNumber": page, "pageSize": PAGE_SIZE,
        "columnsVisibility": COLUMNS, "exportTo": None,
    }


def save_page(iso, page, records):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, f"{iso}_{page:05d}.json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(records, f)
    return path


def probe(client):
    """Settle the two questions that decide whether a bulk pull is feasible."""
    print("Reference: imposing countries")
    ref = client.call("imposingCountries")
    print(f"  {len(ref)} countries")

    affected = all_country_ids()
    print(f"\nDoes allProducts cover a whole country in one query? "
          f"(affectedCountries carries {len(affected)} ids)")
    got = client.call("denormalisedMeasures", query(104, 1, affected))
    print(f"  Indonesia page 1: {len(got)} records")
    if not got:
        print("  EMPTY - allProducts does not work this way; the pull would "
              "have to enumerate product ids instead")
        return
    print(f"  first record keys: {sorted(got[0])[:6]} ...")

    print("\nHow deep does pagination go? (doubling until a short page)")
    page, last_full = 1, 1
    while page <= 512:
        page *= 2
        got = client.call("denormalisedMeasures", query(104, page, affected))
        print(f"  page {page:>4}: {len(got)} records", flush=True)
        if len(got) < PAGE_SIZE:
            print(f"  -> Indonesia ends between page {last_full} and {page}; "
                  f"at most {page * PAGE_SIZE:,} measures")
            break
        last_full = page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true",
                    help="answer the feasibility questions, fetch nothing")
    ap.add_argument("--countries", default="",
                    help="comma-separated iso3 subset")
    args = ap.parse_args()

    client = Client()
    if args.probe:
        return probe(client)

    affected = all_country_ids()
    todo = countries()
    if args.countries:
        want = set(args.countries.split(","))
        todo = [(iso, cid) for iso, cid in todo if iso in want]
    print(f"{len(todo)} imposing countries to pull, {PAGE_SIZE} records a page, "
          f"{client.gap:.0f}s apart\n")

    total = 0
    try:
        for n, (iso, cid) in enumerate(todo, 1):
            page, got_country = 1, 0
            while True:
                path = os.path.join(RAW, f"{iso}_{page:05d}.json.gz")
                if os.path.exists(path):
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        records = json.load(f)
                else:
                    records = client.call("denormalisedMeasures",
                                          query(cid, page, affected))
                    save_page(iso, page, records)
                got_country += len(records)
                if len(records) < PAGE_SIZE:
                    break
                page += 1
            total += got_country
            print(f"[{n}/{len(todo)}] {iso}: {got_country:,} measures "
                  f"over {page} page(s) | running total {total:,}", flush=True)
    except RateLimited as e:
        print(f"\nStopped: {e}")
        print("Finished pages are on disk; re-run later and it resumes.")
        return 1
    print(f"\nDone. {total:,} measure records across {len(todo)} countries.")
    print("Next: scripts/build_ntm_trains.py")


if __name__ == "__main__":
    sys.exit(main())
