"""Step 5b: the 2025 US reciprocal tariff schedule, straight from the source.

The data brief makes the 2025 US action the central covariate of the whole
design - "46% -> 10% -> 20%/40%" - and nothing in TRAINS carries it: WITS
answers 404 for every 2024 and 2025 tariff year, and the schedules it does hold
stop at 2023. The measure lives instead in **chapter 99 of the US Harmonized
Tariff Schedule**, which is where the United States parks temporary,
proclamation-driven duties, and both places that publish it are open:

  USITC HTS REST      hts.usitc.gov/reststop - subchapter III (9903.01) carries
                      the April action, subchapter IV (9903.02) the August one.
                      Each heading names its country, its rate, its effective
                      date and, when superseded, the Federal Register citation
                      that ended it.
  Federal Register    federalregister.gov/api/v1 - the executive orders and
                      annexes themselves, for the dates and the legal trail.

Neither needs an account, which is why this runs today rather than waiting on
USITC DataWeb (registration) or the WTO-IMF tariff tracker (subscription key).

What this does *not* settle is product scope. The exempt subheadings sit in
"U.S. note 2(v)(iii)(a)", a note the REST endpoint does not return, so the
exemption headings (9903.01.32, 9903.01.33) are recorded as flags without their
enumerated product lists. Treat the rate as country-level until that list is
added by hand from the HTS notes.

Output: data/raw/us_tariffs_2025/
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "raw", "us_tariffs_2025")
UA = "Mozilla/5.0 (compatible; trade-survival-research/1.0)"

# Subchapter III opens at 9903.01 (IEEPA actions: Canada, Mexico, China, then
# the April reciprocal rates); subchapter IV at 9903.02 (the August rates and
# the transshipment penalty). One request covers both.
HTS = ("https://hts.usitc.gov/reststop/exportList"
       "?from=9903.01.00&to=9903.02.99&format=JSON&styles=false")

# Every 2025 Federal Register document whose text turns on the reciprocal
# tariffs. `term` searches full text, so amendments and annexes come along with
# the original order.
FR = ("https://www.federalregister.gov/api/v1/documents.json"
      "?per_page=100&order=oldest"
      "&conditions%5Bterm%5D=reciprocal%20tariff"
      "&conditions%5Bpublication_date%5D%5Bgte%5D=2025-01-01"
      "&fields%5B%5D=document_number&fields%5B%5D=title"
      "&fields%5B%5D=publication_date&fields%5B%5D=type"
      "&fields%5B%5D=executive_order_number&fields%5B%5D=html_url"
      "&fields%5B%5D=citation")

# The chapter's legal notes, which the REST endpoint does not return. U.S. note
# 2(v)(iii)(a) is where the exempt subheadings are enumerated - pharmaceuticals,
# semiconductors, critical minerals, energy - and that list is the difference
# between "Viet Nam faces 20%" and "Viet Nam faces 20% on the products actually
# covered". Kept as the source of record; extracting the list from it is a
# separate job and has not been done.
NOTES = ("https://hts.usitc.gov/reststop/file"
         "?release=currentRelease&filename=Chapter%2099")

FILES = [("hts_9903.json", HTS, "USITC HTS chapter 99, subchapters III and IV"),
         ("federal_register.json", FR, "Federal Register, 2025 reciprocal "
                                       "tariff documents"),
         ("hts_chapter99_notes.pdf", NOTES, "USITC HTS chapter 99 legal notes "
                                            "(PDF, exemption lists)")]


def fetch(url, timeout=300, retries=4):
    ctx = ssl.create_default_context()
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, b""
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, b""
        except Exception:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return 0, b""
    return 0, b""


def main():
    os.makedirs(RAW, exist_ok=True)
    for name, url, label in FILES:
        path = os.path.join(RAW, name)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            print(f"  {label}: already on disk "
                  f"({os.path.getsize(path):,} bytes)")
            continue
        print(f"  {label}: downloading ...", flush=True)
        status, body = fetch(url)
        if status != 200 or len(body) < 1024:
            print(f"    FAILED (http {status}, {len(body)} bytes)")
            continue
        if name.endswith(".json"):
            try:
                payload = json.loads(body)
            except ValueError:
                print("    FAILED: response was not JSON")
                continue
            n = len(payload) if isinstance(payload, list) else \
                payload.get("count", len(payload))
            note = f", {n} records"
        elif not body.startswith(b"%PDF"):
            print("    FAILED: response was not a PDF")
            continue
        else:
            note = ""
        with open(path, "wb") as f:
            f.write(body)
        print(f"    {len(body):,} bytes{note} -> {name}")
    print("\nDone. Next: scripts/build_covariates.py (step 6)")


if __name__ == "__main__":
    sys.exit(main())
