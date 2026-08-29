"""Step 9: the Green Logistics Performance Index, in four published forms.

The data brief's robustness question asks whether the survival results hold with
a Green Logistics Performance Index as an extra covariate, and says to take the
construction from the published literature. There is no single construction to
take: three distinct ones exist, they disagree, and the most recent was written
specifically to replace the one before it. So all four are built here, side by
side in one file, and switching between them in a model is a change of column
name rather than a re-run of this script.

  1. glpi_pca_lpi_epi     min-max normalise the LPI headline and the EPI, then
                          weight them by the first principal component.
                          El-Nakib & Elzarka (2026), Logistics 10:56.
                          **This is the primary.** It is the most recent, and it
                          was written to fix the scale sensitivity and
                          volatility the authors attribute to the ratio form.

  2. glpi_ratio_lpi_epi   the ratio form that preceded it, in the family of
                          Starostka-Patyk, Bajdor & Bialas (2024), Ecological
                          Indicators 158:111396, who build a GLPI for the EU
                          from the LPI and the EPI. Kept as the backup the brief
                          asks for. NOTE: the exact 2024 specification has not
                          been read off the paper - it sits behind a paywall -
                          so this reproduces the *ratio family* as the 2026
                          paper characterises it, not that paper line by line.
                          Check it against the PDF before citing it as theirs.

  3. glpi_pca_components  min-max normalise the six LPI sub-indices plus two
                          environmental series, then take the first principal
                          component. This is Lau (2011), Benchmarking: An
                          International Journal 18(6):873-896 - PCA over green
                          logistics *components* - carried from his firm survey
                          onto the public country data this project has.
                          **It is the only variant whose environmental half
                          moves every year**, which matters here: see the
                          coverage note this script prints.

  4. glpi_equal_weights   the same inputs as 3, averaged. A composite index
                          whose ranking survives dropping PCA is worth more than
                          one that does not, so this exists to be compared
                          against 3 rather than used.

Inputs
  analysis/macro_panel_v2.csv   LPI headline + six sub-indices (survey waves),
                                CO2 per capita, renewable energy share (annual)
  data_raw/epi/epi2026results.xlsx   Yale EPI, one cross-section

Output: analysis/glpi.csv, keyed (iso3, year), one column per variant.
"""

import csv
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data_raw")
OUT = os.path.join(HERE, "analysis")

LPI_SUB = ["lpi_customs", "lpi_infrastructure", "lpi_intl_shipments",
           "lpi_logistics_competence", "lpi_tracking_tracing", "lpi_timeliness"]
# CO2 per capita enters negatively: more emissions is worse green performance,
# and every other input here is oriented so that higher is better.
ENV = {"co2_per_capita_t": -1, "renewable_energy_pct": +1}


def read_epi():
    """iso3 -> EPI score, from the Yale results workbook (one cross-section).

    EPI is published per release, not as an annual series, so whatever it
    contributes to a GLPI is constant over time. That is a property of the
    source, not of this code, and it is why variant 3 exists.
    """
    path = os.path.join(RAW, "epi", "epi2026results.xlsx")
    if not os.path.exists(path):
        print("  EPI workbook not on disk - variants 1 and 2 will be empty")
        return {}
    z = zipfile.ZipFile(path)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{ns}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{ns}t")))

    def cells(row):
        out = []
        for c in row.iter(f"{ns}c"):
            v = c.find(f"{ns}v")
            if v is None:
                out.append("")
            elif c.get("t") == "s":
                out.append(shared[int(v.text)])
            else:
                out.append(v.text)
        return out

    sheet = ET.fromstring(z.read("xl/worksheets/sheet2.xml"))
    rows = list(sheet.iter(f"{ns}row"))
    header = cells(rows[0])
    iso_i, epi_i = header.index("iso"), header.index("EPI.new")
    out = {}
    for row in rows[1:]:
        c = cells(row)
        if len(c) > max(iso_i, epi_i) and c[iso_i] and c[epi_i]:
            try:
                out[c[iso_i]] = float(c[epi_i])
            except ValueError:
                continue
    print(f"  EPI 2026: {len(out)} countries")
    return out


def read_macro():
    path = os.path.join(OUT, "macro_panel_v2.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    print(f"  macro_panel_v2.csv: {len(rows):,} country-years")
    return rows


def minmax(col):
    """Scale to [0,1] over the non-missing values, ignoring blanks."""
    vals = [v for v in col if v is not None]
    if not vals:
        return [None] * len(col)
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [0.5 if v is not None else None for v in col]
    return [None if v is None else (v - lo) / (hi - lo) for v in col]


def first_pc(matrix):
    """Scores on the first principal component of the correlation matrix.

    Standardise, take the leading eigenvector, and orient it so that higher is
    better - the sign of an eigenvector is arbitrary, and an index that comes
    out upside down between runs is worse than no index at all. The convention
    used: the loading on the first input must be positive.
    """
    x = np.asarray(matrix, dtype=float)
    mu, sd = x.mean(axis=0), x.std(axis=0, ddof=0)
    sd[sd == 0] = 1.0
    z = (x - mu) / sd
    vals, vecs = np.linalg.eigh(np.cov(z, rowvar=False, ddof=0))
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    w = vecs[:, 0]
    if w[0] < 0:
        w = -w
    share = vals[0] / vals.sum() if vals.sum() else float("nan")
    return z @ w, w, share


def main():
    print("Reading inputs")
    epi = read_epi()
    macro = read_macro()

    def num(row, key):
        v = row.get(key, "")
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    keys = [(r["iso3"], int(r["year"])) for r in macro]
    lpi_overall = [num(r, "lpi_overall") for r in macro]
    subs = {c: [num(r, c) for r in macro] for c in LPI_SUB}
    env = {c: [num(r, c) for r in macro] for c in ENV}
    epi_col = [epi.get(iso) for iso, _ in keys]

    out = [{"iso3": iso, "year": y} for iso, y in keys]

    # ---- variants 1 and 2: LPI headline against EPI
    n_lpi_epi = sum(1 for a, b in zip(lpi_overall, epi_col)
                    if a is not None and b is not None)
    print(f"\nVariants 1-2 (LPI x EPI): {n_lpi_epi:,} country-years usable")
    if n_lpi_epi:
        l_s, e_s = minmax(lpi_overall), minmax(epi_col)
        rows = [i for i in range(len(keys))
                if l_s[i] is not None and e_s[i] is not None]
        scores, w, share = first_pc([[l_s[i], e_s[i]] for i in rows])
        print(f"  PCA weights  LPI {w[0]:+.3f}  EPI {w[1]:+.3f}  "
              f"(first PC explains {100*share:.1f}%)")
        for k, i in enumerate(rows):
            out[i]["glpi_pca_lpi_epi"] = round(float(scores[k]), 6)
        for i in rows:
            # the ratio form: logistics performance per unit of environmental
            # performance, both on their native scales
            if e_s[i] and epi_col[i]:
                out[i]["glpi_ratio_lpi_epi"] = round(
                    lpi_overall[i] / epi_col[i] * 100, 6)

    # ---- variants 3 and 4: the six sub-indices plus the environment
    cols3 = LPI_SUB + list(ENV)
    scaled = {}
    for c in LPI_SUB:
        scaled[c] = minmax(subs[c])
    for c, sign in ENV.items():
        s = minmax(env[c])
        scaled[c] = [None if v is None else (v if sign > 0 else 1 - v)
                     for v in s]
    rows = [i for i in range(len(keys))
            if all(scaled[c][i] is not None for c in cols3)]
    print(f"\nVariants 3-4 (six LPI sub-indices + environment): "
          f"{len(rows):,} country-years usable")
    if rows:
        m = [[scaled[c][i] for c in cols3] for i in rows]
        scores, w, share = first_pc(m)
        print(f"  first PC explains {100*share:.1f}%")
        for c, wi in zip(cols3, w):
            print(f"    {c:<28} {wi:+.3f}")
        for k, i in enumerate(rows):
            out[i]["glpi_pca_components"] = round(float(scores[k]), 6)
            out[i]["glpi_equal_weights"] = round(
                float(np.mean(m[k])), 6)

    cols = ["iso3", "year", "glpi_pca_lpi_epi", "glpi_ratio_lpi_epi",
            "glpi_pca_components", "glpi_equal_weights"]
    path = os.path.join(OUT, "glpi.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"\n  wrote {path} ({len(out):,} rows)")
    for c in cols[2:]:
        n = sum(1 for r in out if r.get(c) not in (None, ""))
        print(f"    {c:<24} {n:>6,} filled ({100*n/len(out):5.1f}%)")

    # Correlations between the variants say how much the choice matters. If they
    # rank countries the same way, the robustness check is insensitive to it and
    # that is worth knowing before anyone argues about which paper to follow.
    print("\n  Spearman rank correlation between variants "
          "(on country-years where both exist):")
    names = cols[2:]
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            pairs = [(r[names[a]], r[names[b]]) for r in out
                     if r.get(names[a]) not in (None, "")
                     and r.get(names[b]) not in (None, "")]
            if len(pairs) < 3:
                continue
            x = np.argsort(np.argsort([p[0] for p in pairs]))
            y = np.argsort(np.argsort([p[1] for p in pairs]))
            rho = np.corrcoef(x, y)[0, 1]
            print(f"    {names[a]:<22} vs {names[b]:<22} "
                  f"rho={rho:+.3f}  (n={len(pairs):,})")


if __name__ == "__main__":
    sys.exit(main())
