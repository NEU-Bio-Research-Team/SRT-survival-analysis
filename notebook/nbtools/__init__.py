"""Bộ công cụ dùng chung cho notebook Stage 1.

Import một dòng là đủ cho mọi cell:

    import nbtools
    from nbtools import Step, run, plan, describe

Bốn mảng việc, tách thành bốn module:
  * `config`    — đường dẫn, thiết lập chạy, kiểm tra môi trường
  * `runner`    — gọi script của pipeline, stream log, kiểm input/output
  * `artifacts` — đọc nhanh csv/parquet để kiểm chứng từng bước
  * `render`    — in markdown/bảng
"""

from . import artifacts, config, render, runner
from .artifacts import (column_groups, columns, count_rows, describe,
                        dir_summary, head, null_share, shape, unique_key,
                        value_counts)
from .config import (DATA, DOCS, FINAL, INTERIM, RAW, ROOT, SCRIPTS, SELECTION,
                     abs_path, check_layout, data_status, environment_report,
                     exists, layout_report, rel)
from .render import fail, frame, kv, md, note, ok, table, warn
from .runner import (REGISTRY, Result, Step, StepBlocked, StepFailed, plan,
                     run, run_all)

__all__ = [
    "artifacts", "config", "render", "runner",
    "Step", "run", "run_all", "plan", "REGISTRY", "Result",
    "StepFailed", "StepBlocked",
    "describe", "dir_summary", "head", "shape", "columns", "count_rows",
    "unique_key", "value_counts", "null_share", "column_groups",
    "md", "kv", "table", "note", "frame", "ok", "warn", "fail",
    "ROOT", "SCRIPTS", "SELECTION", "DATA", "RAW", "INTERIM", "FINAL", "DOCS",
    "rel", "abs_path", "exists", "environment_report", "check_environment",
    "layout_report", "check_layout", "data_status", "check_data",
]


def check_environment() -> dict:
    """In báo cáo môi trường và cảnh báo mọi thứ thiếu. Chạy cell này trước tiên."""
    r = environment_report()

    render.md("#### Folder này có đủ để chạy không")
    render.table(
        [[f"`{x['name']}`", x["ok"],
          "bắt buộc" if x["required"] else "tuỳ chọn", x["why"]]
         for x in r["layout"]],
        ["Thành phần", "Có", "", "Để làm gì"],
    )

    render.md("#### Môi trường")
    render.kv({
        "Gốc dự án": f"`{r['root']}`",
        "Python": f"{r['python']} — {r['interpreter']}",
        "Trình thông dịch": f"`{r['executable']}`",
        "Ổ đĩa còn trống": f"{r['disk_free_gb']:,.0f} GB",
    })

    render.md("#### Gói cần cho pipeline")
    render.table(
        [[name, v or "**THIẾU**", config.REQUIRED_PACKAGES[name]]
         for name, v in r["packages"].items()],
        ["Gói", "Phiên bản", "Script dùng tới"],
    )

    render.md("#### Thiết lập chạy")
    render.kv({k: str(v) for k, v in r["settings"].items()})

    if r["missing_layout"]:
        render.fail(
            "Thiếu " + ", ".join(f"`{m}`" for m in r["missing_layout"])
            + ". Không bước nào chạy được. Nếu bạn vừa giải nén bản gửi kèm, "
              "kiểm tra xem đã giải nén đủ chưa; nếu bạn copy notebook ra chỗ "
              "khác, hãy copy cả folder `notebook/` chứ không chỉ file .ipynb."
        )
    if r["missing_packages"]:
        render.fail("Thiếu gói: " + ", ".join(r["missing_packages"])
                    + " — chạy `pip install -r requirements.txt` rồi khởi động lại kernel.")
    if r["interpreter"] == "python hệ thống":
        render.warn("Notebook đang chạy bằng python hệ thống, không phải môi trường "
                    "riêng. Xem README mục 'Tạo môi trường'. Phiên bản polars lệch "
                    "thì bước 28 có thể ghi ra parquet khác.")
    if not any(x["ok"] for x in r["layout"] if not x["required"]):
        render.note("Bản này không kèm `docs/` — pipeline chạy đủ không cần nó, "
                    "nhưng các đường dẫn tới từ điển dữ liệu ở bước 29 và 32 sẽ "
                    "không mở được. Xin người gửi folder `docs/` nếu bạn cần đọc "
                    "ý nghĩa từng cột. Bước 30 vẫn tự tạo `docs/audit/` để ghi "
                    "báo cáo kiểm định.")
    if not r["missing_layout"] and not r["missing_packages"]:
        render.ok("Đủ điều kiện chạy. Cell tiếp theo sẽ nói dữ liệu đang có tới đâu.")
    return r


def check_data() -> dict:
    """Bảng dữ liệu sẵn có, và kết luận: chạy notebook này mất bao lâu."""
    rows = data_status()
    full = {r["label"]: not r["missing"] for r in rows}

    render.md("#### Dữ liệu sẵn có")
    render.table(
        [[r["label"], f"{r['n'] - len(r['missing'])}/{r['n']}",
          render.human_bytes(r["bytes"]) if r["bytes"] else "—",
          ", ".join(f"`{m}`" for m in r["missing"][:3])
          + (" …" if len(r["missing"]) > 3 else "")]
         for r in rows],
        ["Mốc dữ liệu", "Có", "Dung lượng", "Thiếu"],
    )

    has_final = full["final · panel Stage 1 (bước 28)"]
    has_merged = full["interim · data tổng (bước 24)"]
    has_interim = all(v for k, v in full.items() if k.startswith("interim"))
    has_raw = all(v for k, v in full.items() if k.startswith("raw"))
    nothing = not any(r["bytes"] for r in rows)

    if has_final and has_interim and has_raw:
        verdict, wait = ("Đủ toàn bộ. Mọi bước dựng sẽ được bỏ qua; notebook chạy "
                         "như một bản hướng dẫn đọc, mọi số liệu lấy từ file thật."), \
                        "vài phút"
    elif has_final and has_interim:
        verdict, wait = ("Đủ để chạy hết notebook. Thiếu `raw/` nên không dựng lại "
                         "được từ đầu, nhưng mọi cell kiểm chứng đều chạy."), "vài phút"
    elif has_final:
        verdict, wait = ("Đọc được Phần 4–5 và toàn bộ phần chữ. Các cell kiểm chứng "
                         "ở Phần 2–3 sẽ báo thiếu file — xin thêm `interim/`."), "vài phút"
    elif has_merged:
        verdict, wait = "Có data tổng. Chạy được từ bước 27 để dựng panel cuối.", "20 phút"
    elif has_raw:
        verdict, wait = ("Có đủ `raw/`. Đặt `nbtools.config.OFFLINE = True` rồi Run All: "
                         "Phần 1 được bỏ qua sạch, notebook dựng lại từ bước 12 "
                         "— không cần mạng, không cần API key."), "16 phút"
    elif nothing:
        verdict, wait = ("Chưa có dữ liệu. Notebook sẽ chạy thật từ đầu, kể cả tải API. "
                         "Cần `.env` có COMTRADE_PRIMARY_KEY."), \
                        "nhiều ngày (quota Comtrade)"
    else:
        verdict, wait = ("Dữ liệu có một phần. Bước nào thiếu output sẽ tự chạy, "
                         "bước nào đủ thì bỏ qua."), "tuỳ phần còn thiếu"

    render.md(f"**Kết luận:** {verdict}")
    render.md(f"**Thời gian dự kiến để chạy hết notebook: ~{wait}.**")

    if has_raw and not has_interim and not config.OFFLINE:
        render.note("Gợi ý: có đủ `raw/` mà `OFFLINE` vẫn là `False`. Bật lên ở cell "
                    "thiết lập ngay dưới đây để chắc chắn không bước nào lén gọi API.")
    return {"rows": rows, "verdict": verdict, "wait": wait,
            "has_raw": has_raw, "has_interim": has_interim, "has_final": has_final}
