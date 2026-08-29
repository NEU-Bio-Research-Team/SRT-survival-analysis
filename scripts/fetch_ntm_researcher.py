"""Step 8c: the UNCTAD TRAINS NTM researcher file, streamed and filtered.

This replaces the page-by-page pull in `fetch_ntm_trains.py`, which could not
finish: the `POST /denormalisedMeasures` route caps `pageSize` at 20 and sits
behind a Cloudflare rule that answered 429 six times across 31 minutes of
backoff. The researcher file is the same database published as one blob, over a
plain GET that is not rate-limited at all - one request instead of thousands.

    https://api-trains2.unctad.org/get-researcher-file/2   -> NTMs_HS2012ver_Researcher.csv
    https://api-trains2.unctad.org/get-researcher-file/3   -> MetadataForTheResearcherFile2023.pdf

**The file is 10,548,645,866 bytes and the host offers no gzip and honours no
Range header** - a partial request is answered `200` with the whole blob. So
there is no resuming a broken transfer; the only sane shape is to filter while
it streams and never hold the whole thing. Measured throughput ~3 MB/s, so one
pass is about an hour.

What is kept, and why:

- `Partner in {WLD, VNM, ...competitors}`. Most measures are erga omnes and
  appear as `WLD`, not as a row naming Viet Nam - filtering on `VNM` alone drops
  ~99% of what applies to Viet Nam. The competitor codes are kept because the
  brief asks for a trade-diversion control, and they cost ~2% of the bytes.
- Every NTM chapter for `Reporter == VNM` (its own export measures, chapter P),
  but chapters A-O only for everyone else: chapter P from an importing country
  governs *its* exports, not what Vietnamese goods meet on arrival.

Columns are documented in the metadata PDF except `MinStartYear`/`MaxEndYear`,
which the 2023 edition predates. Checked against 5.41m rows of the file itself:
`MinStartYear <= Year <= MaxEndYear` holds in 100.0% of rows, and 87.9% of rows
have `ntm_all == 1`, so for most cells the pair is one measure's own in-force
window rather than an envelope over several.

Output: data_raw/ntm/researcher/ntm_researcher_filtered.csv.gz
"""

import gzip
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data_raw", "ntm", "researcher")
URL = "https://api-trains2.unctad.org/get-researcher-file/2"
DOC = "https://api-trains2.unctad.org/get-researcher-file/3"

# The full header set a browser sends. Cloudflare fronts this host; the trimmed
# version of these headers is what earned 429s on the POST route, so the GET is
# given the same treatment even though it has never been refused.
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://trainsonline.unctad.org",
    "referer": "https://trainsonline.unctad.org/",
    "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
}

# Viet Nam, plus the world code that carries most measures, plus the competitor
# set the brief names for the trade-diversion control.
KEEP_PARTNERS = {
    "WLD", "VNM",
    "CHN", "IND", "IDN", "THA", "MYS", "PHL", "KHM", "BGD",
    "PAK", "LKA", "MMR", "MEX", "TUR",
}

FIELDS = 21
I_REPORTER, I_PARTNER, I_NTMCODE = 2, 4, 18


def fetch(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest)


def main():
    os.makedirs(OUT, exist_ok=True)
    final = os.path.join(OUT, "ntm_researcher_filtered.csv.gz")
    tmp = final + ".part"

    doc = os.path.join(OUT, "MetadataForTheResearcherFile2023.pdf")
    if not os.path.exists(doc):
        print(f"metadata pdf -> {fetch(DOC, doc):,} bytes", flush=True)

    req = urllib.request.Request(URL, headers=HEADERS)
    t0 = time.time()
    total = kept = seen = 0
    tail = b""
    header_written = False

    with urllib.request.urlopen(req, timeout=300) as r:
        declared = int(r.headers.get("content-length", 0))
        print(f"streaming {declared:,} bytes from {URL}", flush=True)
        with gzip.open(tmp, "wt", newline="", compresslevel=6) as out:
            while True:
                chunk = r.read(1 << 22)
                if not chunk:
                    break
                total += len(chunk)
                buf = tail + chunk
                lines = buf.split(b"\n")
                tail = lines.pop()
                for raw in lines:
                    if not raw:
                        continue
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                    if not header_written:
                        out.write(line + "\n")
                        header_written = True
                        continue
                    seen += 1
                    f = line.split(",")
                    if len(f) != FIELDS:
                        continue
                    if f[I_PARTNER] not in KEEP_PARTNERS:
                        continue
                    if f[I_NTMCODE][:1] == "P" and f[I_REPORTER] != "VNM":
                        continue
                    out.write(line + "\n")
                    kept += 1
                if total % (1 << 30) < (1 << 22):
                    el = time.time() - t0
                    pct = 100.0 * total / declared if declared else 0
                    rate = total / el / 1e6 if el else 0
                    eta = (declared - total) / (total / el) / 60 if total else 0
                    print(
                        f"  {total/1e9:5.2f} GB ({pct:4.1f}%)  {seen:,} rows read, "
                        f"{kept:,} kept  {rate:.1f} MB/s  eta {eta:.0f} min",
                        flush=True,
                    )

    if tail.strip():
        line = tail.decode("utf-8", "replace").rstrip("\r")
        f = line.split(",")
        if len(f) == FIELDS and f[I_PARTNER] in KEEP_PARTNERS:
            with gzip.open(tmp, "at", newline="") as out:
                out.write(line + "\n")
            kept += 1
            seen += 1

    os.replace(tmp, final)
    el = time.time() - t0
    print(
        f"done in {el/60:.1f} min: read {total:,} bytes / {seen:,} rows, "
        f"kept {kept:,} ({100.0*kept/max(seen,1):.1f}%) -> "
        f"{os.path.getsize(final):,} bytes gzipped",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())
