"""Đọc nhanh các artifact của pipeline (csv / csv.gz / parquet) để kiểm chứng.

Nguyên tắc: không bao giờ nạp cả file vào RAM. panel_final.csv nặng ~900 MB và
máy tham chiếu chỉ có 8 GB, nên đếm dòng thì đếm byte, còn parquet thì đọc
metadata. Mọi hàm ở đây đều rẻ.
"""

from __future__ import annotations

import csv as _csv
import gzip
import io
from pathlib import Path

import polars as pl

from . import config, render


def _p(path) -> Path:
    return config.abs_path(path)


def _is_parquet(path: Path) -> bool:
    return path.suffix == ".parquet"


def count_rows(path) -> int:
    """Số dòng dữ liệu (không tính header). Parquet đọc metadata, CSV đếm byte."""
    p = _p(path)
    if _is_parquet(p):
        return pl.scan_parquet(p).select(pl.len()).collect().item()
    opener = gzip.open if p.suffix == ".gz" else open
    n = 0
    with opener(p, "rb") as f:  # type: ignore[operator]
        while chunk := f.read(8 << 20):
            n += chunk.count(b"\n")
    return max(n - 1, 0)


def columns(path) -> list[str]:
    """Danh sách cột, không nạp dữ liệu."""
    p = _p(path)
    if _is_parquet(p):
        return pl.scan_parquet(p).collect_schema().names()
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8", newline="") as f:  # type: ignore[operator]
        return next(_csv.reader(f))


def head(path, n: int = 5) -> pl.DataFrame:
    """n dòng đầu. CSV đọc dạng chuỗi hết để không vấp kiểu dữ liệu lẫn lộn."""
    p = _p(path)
    if _is_parquet(p):
        return pl.scan_parquet(p).head(n).collect()
    return pl.read_csv(p, n_rows=n, infer_schema_length=0, truncate_ragged_lines=True)


def shape(path) -> tuple[int, int]:
    return count_rows(path), len(columns(path))


def describe(path, n: int = 5, show_columns: int = 0) -> None:
    """In kích thước, số dòng × cột và mấy dòng đầu của một artifact."""
    p = _p(path)
    if not p.exists():
        render.fail(f"Chưa có `{config.rel(p)}` — bước dựng ra nó chưa chạy.")
        return
    rows, cols = shape(p)
    render.kv({
        "File": f"`{config.rel(p)}`",
        "Dung lượng": render.human_bytes(p.stat().st_size),
        "Số dòng": f"{rows:,}",
        "Số cột": f"{cols:,}",
    })
    if show_columns:
        names = columns(p)
        render.md("**Cột:** " + ", ".join(f"`{c}`" for c in names[:show_columns])
                  + (f" … (+{len(names) - show_columns} cột nữa)"
                     if len(names) > show_columns else ""))
    if n:
        render.frame(head(p, n))


def dir_summary(path, pattern: str = "*") -> None:
    """Thư mục raw: bao nhiêu file, nặng bao nhiêu, file đầu và cuối."""
    p = _p(path)
    if not p.exists():
        render.fail(f"Chưa có thư mục `{config.rel(p)}`.")
        return
    files = sorted(f for f in p.rglob(pattern) if f.is_file())
    total = sum(f.stat().st_size for f in files)
    render.kv({
        "Thư mục": f"`{config.rel(p)}`",
        "Số file": f"{len(files):,}",
        "Tổng dung lượng": render.human_bytes(total),
        "File đầu": f"`{files[0].name}`" if files else "—",
        "File cuối": f"`{files[-1].name}`" if files else "—",
    })


def unique_key(path, keys: list[str]) -> None:
    """Kiểm tra bộ khoá có duy nhất không — grain của bảng."""
    p = _p(path)
    lf = pl.scan_parquet(p) if _is_parquet(p) else pl.scan_csv(p, infer_schema_length=10_000)
    n, d = (lf.select(pl.len()).collect().item(),
            lf.select(keys).unique().select(pl.len()).collect().item())
    if n == d:
        render.ok(f"`{' × '.join(keys)}` là khoá duy nhất — {n:,} dòng, {d:,} tổ hợp.")
    else:
        render.fail(f"`{' × '.join(keys)}` KHÔNG duy nhất — {n:,} dòng nhưng chỉ "
                    f"{d:,} tổ hợp ({n - d:,} dòng trùng).")


def value_counts(path, col: str, top: int = 10) -> pl.DataFrame:
    """Phân bố một cột — dùng để đọc censor_reason, start_reason, staging_cat..."""
    p = _p(path)
    lf = pl.scan_parquet(p) if _is_parquet(p) else pl.scan_csv(
        p, infer_schema_length=0, truncate_ragged_lines=True)
    out = (lf.select(col).group_by(col).len()
           .sort("len", descending=True).head(top).collect())
    total = out["len"].sum()
    return out.with_columns((pl.col("len") / total * 100).round(1).alias("pct_of_top"))


def null_share(path, cols: list[str] | None = None, limit: int = 25) -> pl.DataFrame:
    """Tỷ lệ null từng cột — cách nhanh nhất để thấy module nào phủ tới đâu."""
    p = _p(path)
    lf = pl.scan_parquet(p) if _is_parquet(p) else pl.scan_csv(
        p, infer_schema_length=10_000)
    schema = lf.collect_schema().names()
    names = [c for c in (cols or schema[:limit]) if c in schema]
    absent = [c for c in (cols or []) if c not in schema]
    if absent:
        render.warn("Không có cột: " + ", ".join(f"`{c}`" for c in absent))
    if not names:
        return pl.DataFrame({"column": [], "nulls": [], "null_pct": []})
    counts = lf.select([pl.col(c).null_count().alias(c) for c in names]).collect()
    n = lf.select(pl.len()).collect().item()
    return (counts.transpose(include_header=True,
                             header_name="column", column_names=["nulls"])
            .with_columns((pl.col("nulls") / n * 100).round(1).alias("null_pct"))
            .sort("null_pct", descending=True))


def column_groups(path, prefixes: dict[str, tuple[str, ...]]) -> None:
    """Đếm cột theo nhóm chủ đề — cách đọc 209 cột mà không cần liệt kê hết."""
    names = columns(path)
    rows, claimed = [], set()
    for label, pats in prefixes.items():
        hit = [c for c in names if any(pat in c for pat in pats)]
        claimed.update(hit)
        rows.append([label, len(hit), ", ".join(f"`{c}`" for c in hit[:4])
                     + (" …" if len(hit) > 4 else "")])
    rows.append(["còn lại", len(names) - len(claimed), ""])
    render.table(rows, ["Nhóm", "Số cột", "Ví dụ"])
