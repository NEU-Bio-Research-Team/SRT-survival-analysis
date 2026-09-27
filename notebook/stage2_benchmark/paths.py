"""Paths, resource limits and small shared helpers for the Stage 2 benchmark.

Import this module first in every entry point: it caps BLAS/torch threads before
numpy is imported anywhere, because this machine has 8 GB of RAM shared with an
editor session and every extra thread pool is a copy of scratch memory.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

# ---- resource limits (set before numpy/torch load their thread pools) -------
N_THREADS = int(os.environ.get("SRT_THREADS", "4"))
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, str(N_THREADS))

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.dirname(HERE)
REPO = os.path.dirname(NOTEBOOK)
if NOTEBOOK not in sys.path:
    sys.path.insert(0, NOTEBOOK)

PANEL = os.path.join(NOTEBOOK, "data", "final", "stage1_panel.parquet")
INTERIM = os.path.join(NOTEBOOK, "data", "interim")
CONFIGS = os.path.join(HERE, "configs")
ARTIFACTS = os.path.join(HERE, "artifacts")
REPORTS = os.path.join(HERE, "reports")
RUNS = os.path.join(ARTIFACTS, "runs")          # per-cell predictions, models
VIEWS = os.path.join(ARTIFACTS, "views")        # cached base tables / views
TMP = os.path.join(ARTIFACTS, "tmp")
for _d in (ARTIFACTS, REPORTS, RUNS, VIEWS, TMP):
    os.makedirs(_d, exist_ok=True)
os.environ.setdefault("SRT_BENCHMARK_TMP", TMP)


def load_yaml(name: str) -> dict:
    import yaml
    path = name if os.path.isabs(name) else os.path.join(CONFIGS, name)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def file_sha256(path: str, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


_PANEL_HASH = None


def panel_hash() -> str:
    """sha256 of the panel, cached on disk next to the views (hashing 180 MB
    every run is wasted I/O). The cache is keyed on size+mtime."""
    global _PANEL_HASH
    if _PANEL_HASH:
        return _PANEL_HASH
    st = os.stat(PANEL)
    key = f"{st.st_size}:{int(st.st_mtime)}"
    cache = os.path.join(VIEWS, "panel_hash.json")
    if os.path.exists(cache):
        with open(cache) as f:
            c = json.load(f)
        if c.get("key") == key:
            _PANEL_HASH = c["sha256"]
            return _PANEL_HASH
    _PANEL_HASH = file_sha256(PANEL)
    atomic_write_json(cache, {"key": key, "sha256": _PANEL_HASH})
    return _PANEL_HASH


def code_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"],
                                      text=True).strip()
        dirty = subprocess.call(["git", "-C", REPO, "diff", "--quiet", "--",
                                 "notebook/stage2_benchmark"]) != 0
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def stable_hash(obj) -> str:
    s = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha1(s.encode()).hexdigest()[:12]


# ---- checkpoint-safe writes ------------------------------------------------
def atomic_write_json(path: str, obj) -> None:
    """Write-then-rename, so a crash never leaves half a JSON file behind."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=_json_default)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_parquet(df, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    df.to_parquet(tmp, index=False, compression="zstd")
    os.replace(tmp, path)


def atomic_write_csv(df, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _json_default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    return str(o)


def rss_mb() -> float:
    """Resident memory of this process in MB (Linux)."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return float("nan")


def peak_rss_mb() -> float:
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return float("nan")


def mem_available_mb() -> float:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    return float("nan")
