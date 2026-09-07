"""Download the EU's Combined Nomenclature regulations for 2024-2026.

TRAINS stops at 2023 - it answers 404 for every reporter in 2024 and 2025
(re-checked 29/08/2026, EU/USA/China alike), so the last two years of the
panel carry a 2023 rate forward. The rate itself is not missing from the
world, only from WITS: the EU publishes its Common Customs Tariff every
October as a Commission Implementing Regulation amending Annex I to Council
Regulation (EEC) No 2658/87, and Annex I is the full duty table, one line per
CN8 code with its conventional (MFN) rate.

  CN 2024 - Commission Implementing Regulation (EU) 2023/2364
  CN 2025 - Commission Implementing Regulation (EU) 2024/2522
  CN 2026 - Commission Implementing Regulation (EU) 2025/1926

Each is roughly 1,100 pages of PDF. No account, no key.

Usage: python3 fetch_eu_cn.py
"""

import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "raw", "eu_cn")

# year the tariff applies from -> the OJ reference of the regulation
REGS = {
    2024: "OJ:L_202302364",
    2025: "OJ:L_202402522",
    2026: "OJ:L_202501926",
}
URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri={}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def main():
    os.makedirs(OUT, exist_ok=True)
    for year, oj in REGS.items():
        dest = os.path.join(OUT, f"cn{year}.pdf")
        if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
            print(f"  cn{year}: already on disk ({os.path.getsize(dest):,} bytes)")
            continue
        req = urllib.request.Request(URL.format(oj), headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=900) as r, open(dest, "wb") as f:
                f.write(r.read())
            print(f"  cn{year}: {os.path.getsize(dest):,} bytes")
        except Exception as exc:                            # noqa: BLE001
            print(f"  cn{year}: FAILED - {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
