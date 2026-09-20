"""Product families: the one definition of the product key, for every source.

A family is the panel's product unit: an HS1992 (H0) code, or a small set of
them, together with every code of a later revision that belongs to it. Every
script that turns an HS code into a family - trade, world trade, TRAINS tariffs,
NTMs, EVFTA/CN, CBAM, the US exemption list - goes through this module, so
the numerator, the denominator and every covariate describe the same goods.

**Step 1: the WITS conversion tables.** `H1_to_H0` ... `H6_to_H0` point every
code of a later revision at exactly one H0 code (many-to-one, measured: no
code points at two). Each (revision, code) is unioned with its H0 target.

**Step 2: orphans are merged into the family that absorbed them.** When a
revision merges several H0 codes into one new code, the WITS table keeps one
target and every other H0 code loses its last successor. A relationship in such
a code then vanishes the year its importer adopts the revision and the panel
reads a death, while the goods keep moving under the sibling family: 1,982 of
1,983 exposed episode-years "died" that way in v1. For each orphan `h` of
revision `r`, the UNSD correlation sheet lists the `r`-codes that took over its
content; each of those has a WITS target `d`, and `h` is unioned with `d`.

The merge is **restricted to the same HS4**. Unrestricted, the orphan links
chain into one family of 228 H0 codes across chapters 24-28 (and pure
connected components over the n:n sheet into one of 1,368), which would no
longer be a product. Within HS4 the largest family has 10 codes and 70% of the
exposed episode-years are resolved. The orphans left over keep their own
family; build_spells.py censors their spells at the revision switch instead of
reading a death, and `receivers` records which families absorbed their goods so
a spell born there at the switch is marked left-truncated.

The family id is the smallest H0 code in the family (`H0_620213` for the
women's-coats merge), so ids are deterministic and, because merges never
leave an HS4, the first four digits of an id are still the family's HS4.

Outputs (write_family_map): data/interim/family_map.csv (revision, hs6,
family) and data/interim/family_members.csv (family, n_h0, h0_codes, merged).
"""

import csv
import glob
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONC = os.path.join(HERE, "data", "raw", "concordance")
UNSD = os.path.join(CONC, "unsd")
OUT = os.path.join(HERE, "data", "interim")
REVS = ("H1", "H2", "H3", "H4", "H5", "H6")


class Union:
    """Union-find whose roots are H0 nodes where possible, the smallest H0
    code winning, so a family's id does not depend on the order of unions."""

    def __init__(self):
        self.parent = {}
        self.receivers = defaultdict(set)   # revision -> absorbing H0 families
        self.merges = []                    # (revision, orphan h0, receiver h0)
        self.unmerged = []                  # (revision, orphan h0)

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if ra[0] == "H0" and rb[0] == "H0":
            root, child = (ra, rb) if ra[1] < rb[1] else (rb, ra)
        elif rb[0] == "H0":
            root, child = rb, ra
        else:
            root, child = ra, rb
        self.parent[child] = root


def wits_tables():
    """revision -> {code: H0 code}, from the WITS conversion exports."""
    out = {}
    for rev in REVS:
        files = glob.glob(os.path.join(CONC, f"{rev}_to_H0", "*.CSV")) + \
            glob.glob(os.path.join(CONC, f"{rev}_to_H0", "*.csv"))
        if not files:
            raise SystemExit(f"no WITS concordance for {rev} in {CONC}")
        tab = {}
        # The WITS exports are not all UTF-8 (H4_to_H0 carries Latin-1).
        with open(files[0], encoding="utf-8-sig", errors="replace") as f:
            for row in csv.reader(f):
                if len(row) < 3:
                    continue
                src, dst = row[0].strip(), row[2].strip()
                if len(src) == 6 and len(dst) == 6 and src.isdigit() and dst.isdigit():
                    tab[src] = dst
        out[rev] = tab
    return out


def _code(v):
    if isinstance(v, float) and v == int(v):
        v = str(int(v)).zfill(6)
    v = str(v).strip().replace(".", "")
    return v if re.fullmatch(r"\d{6}", v) else None


def unsd_correlations():
    """revision -> [(code of that revision, H0 code)], every n:n link."""
    import openpyxl
    import xlrd
    out = {}
    for rev in REVS:
        paths = glob.glob(os.path.join(UNSD, f"{rev}_to_H0_unsd.*"))
        if not paths:
            raise SystemExit(f"{UNSD} has no table for {rev} - run "
                             f"scripts/fetch_concordance_unsd.py")
        path, links = paths[0], []
        if path.endswith(".xlsx"):
            wb = openpyxl.load_workbook(path, read_only=True)
            sheets = [ws for ws in wb.worksheets if "correl" in ws.title.lower()]
            rows = (r for ws in sheets for r in ws.iter_rows(values_only=True))
        else:
            wb = xlrd.open_workbook(path)
            sheets = [s for s in wb.sheets() if "correl" in s.name.lower()]
            rows = (s.row_values(i) for s in sheets for i in range(s.nrows))
        for r in rows:
            codes = [c for c in (_code(x) for x in list(r)[:4] if x is not None) if c]
            if len(codes) >= 2:
                links.append((codes[0], codes[1]))
        out[rev] = links
    return out


def build_families(merge_orphans=None, verbose=True):
    """The union-find over (revision, code) nodes; see the module docstring.

    FAMILIES_WITS_ONLY=1 in the environment skips step 2 and reproduces the v1
    key exactly - a verification switch for refactors, not a modelling option."""
    if merge_orphans is None:
        merge_orphans = os.environ.get("FAMILIES_WITS_ONLY") != "1"
    u = Union()
    tables = wits_tables()
    pairs = 0
    for rev in REVS:
        for src, dst in tables[rev].items():
            u.union(("H0", dst), (rev, src))
            pairs += 1
    if verbose:
        print(f"  concordance links: {pairs:,}")
    if not merge_orphans:
        return u

    corr = unsd_correlations()
    all_h0 = {d for tab in tables.values() for d in tab.values()}
    for rev in REVS:
        tab = tables[rev]
        # Column-order guard: the UNSD sheet must agree with WITS on most links,
        # otherwise the two columns were read the wrong way round.
        linkset = set(corr[rev])
        agree = sum(1 for s, d in tab.items() if (s, d) in linkset) / len(tab)
        if agree < 0.9:
            raise SystemExit(f"UNSD {rev} agrees with WITS on only {agree:.0%} "
                             f"of links - check the column order")
        successors = set(tab.values())
        by_h0 = defaultdict(set)
        for new, old in corr[rev]:
            by_h0[old].add(new)
        for h in sorted(all_h0 - successors):
            targets = {tab[c] for c in by_h0.get(h, ()) if c in tab}
            same = sorted(d for d in targets if d[:4] == h[:4])
            for d in same:
                u.union(("H0", h), ("H0", d))
                u.merges.append((rev, h, d))
            if not same:
                u.unmerged.append((rev, h))
                u.receivers[rev] |= {f"H0_{d}" for d in targets}
    # receivers are named by the H0 code; resolve to final family ids
    for rev in list(u.receivers):
        u.receivers[rev] = {family_of(u, "H0", f[3:]) for f in u.receivers[rev]}
    if verbose:
        fams = defaultdict(set)
        for node in list(u.parent):
            if node[0] == "H0":
                fams[u.find(node)].add(node[1])
        print(f"  orphan merges within HS4: {len(u.merges):,} links; "
              f"{len(u.unmerged):,} orphan-revision pairs left unmerged; "
              f"{len(fams):,} families, largest {max(len(v) for v in fams.values())} H0 codes")
    return u


def family_of(u, rev, code):
    """Family key for a reported code; unmapped codes stand alone."""
    root = u.find((rev, code)) if (rev, code) in u.parent else None
    if root is None:
        # code absent from the concordance (new line, or already H0)
        root = u.find(("H0", code)) if ("H0", code) in u.parent else (rev, code)
    return f"{root[0]}_{root[1]}"


def table_map(u, rev, tables=None):
    """{code: family} for the codes the WITS table of `rev` lists - for readers
    that must ignore codes outside the table, as the NTM and CBAM ones do."""
    tables = tables or wits_tables()
    return {src: family_of(u, rev, src) for src in tables[rev]}


def families_in_revision(u, tables=None):
    """revision -> the families at least one code of that revision maps to.
    A family missing from a revision cannot be reported in it at all."""
    tables = tables or wits_tables()
    out = {rev: {family_of(u, rev, s) for s in tables[rev]} for rev in REVS}
    out["H0"] = {family_of(u, "H0", n[1]) for n in list(u.parent) if n[0] == "H0"}
    return out


def write_family_map(u, out_dir=OUT):
    os.makedirs(out_dir, exist_ok=True)
    nodes = sorted(u.parent)
    members = defaultdict(set)
    with open(os.path.join(out_dir, "family_map.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["revision", "hs6", "family"])
        for rev, code in nodes:
            fam = family_of(u, rev, code)
            w.writerow([rev, code, fam])
            if rev == "H0":
                members[fam].add(code)
    with open(os.path.join(out_dir, "family_members.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["family", "n_h0", "h0_codes", "merged"])
        for fam in sorted(members):
            codes = sorted(members[fam])
            w.writerow([fam, len(codes), ";".join(codes), int(len(codes) > 1)])
    with open(os.path.join(out_dir, "family_merges.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["revision", "orphan_h0", "receiver_h0", "action"])
        for rev, h, d in u.merges:
            w.writerow([rev, h, d, "merged_same_hs4"])
        for rev, h in u.unmerged:
            w.writerow([rev, h, "", "censor_at_switch"])
    return len(members)


if __name__ == "__main__":
    fam = build_families()
    n = write_family_map(fam)
    print(f"  wrote family_map.csv / family_members.csv / family_merges.csv "
          f"({n:,} families)")
