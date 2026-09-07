"""Download EVFTA Annex 2-A and its five appendices.

Annex 2-A is the tariff-elimination annex of the EU-Viet Nam FTA. Appendix
2-A-1 is the *Union's* schedule - the duty a Vietnamese exporter actually
faces - and is the one the identification strategy needs; the others are kept
so the parse can be checked against the legal text it came from.

Source: Centre for WTO and Integration (VCCI), which mirrors the signed text.
The EU publishes the same annex in OJ L 186, 12.6.2020, but only inside the
full Official Journal, which is an order of magnitude larger to fetch.

No account, no key. Usage: python3 fetch_evfta_annex.py
"""

import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "raw", "evfta")

BASE = "https://wtocenter.vn/download"
FILES = {
    "annex-2a": 17733,        # Sections A-C: the staging-category definitions
    "appendix-2a1": 17734,    # Tariff Schedule of the Union      <- the one we parse
    "appendix-2a2": 17735,    # Tariff Schedule of Viet Nam
    "appendix-2a3": 17736,    # Tariff-rate quotas
    "appendix-2a4": 17737,
    "appendix-2a5": 17738,
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def fetch(name, doc_id):
    dest = os.path.join(OUT, name + ".pdf")
    if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
        print(f"  {name}: already on disk ({os.path.getsize(dest):,} bytes)")
        return
    url = f"{BASE}/{doc_id}/{name}.pdf"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=900) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  {name}: {os.path.getsize(dest):,} bytes")


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"EVFTA Annex 2-A -> {OUT}")
    for name, doc_id in FILES.items():
        try:
            fetch(name, doc_id)
        except Exception as exc:                       # noqa: BLE001
            print(f"  {name}: FAILED - {exc}", file=sys.stderr)
    print("done")


if __name__ == "__main__":
    main()
