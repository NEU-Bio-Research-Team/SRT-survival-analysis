"""Trình bày kết quả trong notebook: markdown, bảng, cảnh báo.

Tách riêng khỏi phần chạy pipeline để cell nào cũng in ra cùng một kiểu, và để
các module khác không phải biết gì về IPython.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

try:  # notebook
    from IPython.display import Markdown, display

    _HAS_IPYTHON = True
except Exception:  # chạy bằng python thường
    _HAS_IPYTHON = False


def md(text: str) -> None:
    """In markdown. Ngoài notebook thì in text thô."""
    if _HAS_IPYTHON:
        display(Markdown(text))
    else:
        print(text)


def human_bytes(n: float | None) -> str:
    if n is None:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024
    return f"{n} B"


def human_time(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f} giây"
    if seconds < 3600:
        return f"{seconds / 60:.1f} phút"
    return f"{seconds / 3600:.2f} giờ"


def _cell(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "✅" if v else "❌"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v).replace("|", "\\|")


def table(rows: Iterable[Sequence], headers: Sequence[str]) -> None:
    """Bảng markdown từ list of rows."""
    rows = list(rows)
    out = ["| " + " | ".join(str(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(c) for c in r) + " |")
    md("\n".join(out))


def kv(mapping: Mapping, headers: Sequence[str] = ("Mục", "Giá trị")) -> None:
    table(list(mapping.items()), headers)


def note(text: str) -> None:
    md(f"> {text}")


def ok(text: str) -> None:
    md(f"**✅ {text}**")


def warn(text: str) -> None:
    md(f"**⚠️ {text}**")


def fail(text: str) -> None:
    md(f"**❌ {text}**")


def heading(text: str, level: int = 4) -> None:
    md("#" * level + " " + text)


def frame(df, n: int | None = None) -> None:
    """Hiển thị DataFrame polars (hoặc bất cứ thứ gì có repr đẹp)."""
    obj = df.head(n) if n is not None and hasattr(df, "head") else df
    if _HAS_IPYTHON:
        display(obj)
    else:
        print(obj)
