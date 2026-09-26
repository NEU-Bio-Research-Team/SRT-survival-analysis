"""Chạy một bước của pipeline như tiến trình con và stream log vào notebook.

Mỗi bước được mô tả bằng một `Step`: lệnh chạy, file nó **cần đọc**, file nó
**phải sinh ra**, thời gian ước tính, và nó có cần mạng / API key hay không.
Notebook vì thế đọc được như một bản kê khai — nhìn cell là biết bước đó gọi
gì, ăn vào cái gì và phải đẻ ra cái gì.

Ba chốt chặn, theo đúng thứ tự `run()` kiểm:

1. **`requires`** — input chưa có thì dừng ngay và nói bước nào sinh ra nó,
   thay vì để script chết giữa chừng với một traceback không ai đọc được.
2. **`outputs` / `done_if`** — output đã có thì bỏ qua (xem `SKIP_EXISTING`).
3. **`outputs` sau khi chạy** — script bảo xong mà file không có thì báo ngay,
   không để bước sau nhận một bảng rỗng.

Chốt 1 là thứ mới so với bản trước. Nó có vì `merge_panel.py` **bỏ qua trong im
lặng** mọi bảng phụ không tìm thấy (`if not table: continue`) — một bước bị
quên sẽ không làm gì đổ vỡ, nó chỉ lặng lẽ cho ra một panel thiếu cột.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config, render


class StepFailed(RuntimeError):
    """Script trả về mã lỗi khác 0."""


class StepBlocked(RuntimeError):
    """Bước không chạy được vì thiếu điều kiện (input, API key, chế độ OFFLINE...)."""


#: Mọi Step được định nghĩa trong phiên này, theo thứ tự xuất hiện, khoá theo id.
#: `plan()` không tham số sẽ kê bảng từ đây — nhờ vậy bảng kê cuối notebook luôn
#: khớp với các cell ở trên, không phải một danh sách chép tay dễ lệch.
REGISTRY: dict[str, "Step"] = {}


@dataclass
class Step:
    """Một bước của pipeline.

    id       : tên ngắn, dùng đặt tên file log
    title    : mô tả một dòng, hiện ở đầu output
    cmd      : tham số truyền cho python, ví dụ ["scripts/build_spells.py"].
               Đường dẫn .py được giải theo gốc dự án (`notebook/`).
    outputs  : file/thư mục bước này phải sinh ra (tương đối gốc dự án).
               Dùng cho cả việc bỏ qua khi đã có, lẫn việc kiểm sau khi chạy.
    requires : file bước này phải đọc. Thiếu thì dừng trước khi gọi script.
    done_if  : file khác mà nếu đã có thì coi như bước này đã chạy rồi. Dùng cho
               bước sinh ra file tạm bị bước sau xoá đi (bước 27).
    minutes  : thời gian ước tính trên máy tham chiếu (8 GB RAM, WSL2).
    network  : có gọi API/tải file từ internet không.
    needs_key: có cần COMTRADE_PRIMARY_KEY trong .env không.
    optional : không bước nào phía sau đọc output của nó. Khi bị chặn (OFFLINE,
               thiếu key) thì bỏ qua êm thay vì dừng cả notebook.
    note     : ghi chú hiện kèm khi chạy.
    """

    id: str
    title: str
    cmd: list[str]
    outputs: list[str] = field(default_factory=list)
    minutes: float | None = None
    network: bool = False
    needs_key: bool = False
    note: str = ""
    done_if: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    optional: bool = False

    def __post_init__(self) -> None:
        REGISTRY[self.id] = self          # định nghĩa lại thì thay tại chỗ

    def done(self) -> bool:
        """Output (hoặc file thay thế của bước sau) đã có đủ chưa."""
        return ((bool(self.outputs) and all(config.exists(o) for o in self.outputs))
                or (bool(self.done_if) and all(config.exists(o) for o in self.done_if)))


@dataclass
class Result:
    step: Step
    skipped: bool
    elapsed: float
    returncode: int | None
    log_path: Path | None
    produced: list[Path] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)


def _output_table(step: Step) -> None:
    rows = [[o, config.exists(o),
             render.human_bytes(config._du(config.abs_path(o)))
             if config.exists(o) else "—"]
            for o in step.outputs]
    if rows:
        render.table(rows, ["Output", "Có", "Dung lượng"])


def _argv(step: Step) -> list[str]:
    argv = [config.PYTHON]
    for i, part in enumerate(step.cmd):
        argv.append(str(config.abs_path(part)) if i == 0 and part.endswith(".py")
                    else part)
    return argv


def preflight(step: Step) -> list[str]:
    """Những lý do bước này không chạy được ngay bây giờ."""
    problems = []

    missing_layout = config.check_layout()
    if missing_layout:
        problems.append(
            "Thiếu " + ", ".join(f"`{m}`" for m in missing_layout)
            + f" trong `{config.ROOT}`. Folder notebook chưa đầy đủ — xem README "
              "mục 'Folder này phải có gì'."
        )

    missing_in = [r for r in step.requires if not config.exists(r)]
    if missing_in:
        problems.append(
            "Thiếu input: " + ", ".join(f"`{m}`" for m in missing_in)
            + " — bước sinh ra chúng chưa chạy. Chạy lại các cell phía trên theo thứ tự."
        )

    if step.network and config.OFFLINE:
        problems.append(
            "`OFFLINE = True` mà bước này cần mạng. Đặt `nbtools.config.OFFLINE = False` "
            "nếu muốn gọi API, hoặc dùng `data/raw/` có sẵn."
        )

    if step.needs_key and not config.env_keys().get("COMTRADE_PRIMARY_KEY"):
        problems.append(
            f"Thiếu `COMTRADE_PRIMARY_KEY` trong `{config.rel(config.ENV_FILE)}` "
            "— xem README mục 'API key'."
        )

    if config.missing_packages():
        problems.append("Thiếu gói: " + ", ".join(config.missing_packages())
                        + " — `pip install -r requirements.txt`")
    return problems


def run(step: Step, force: bool | None = None, timeout: int | None = None) -> Result:
    """Chạy một bước. Trả về Result; ném StepFailed nếu script lỗi.

    force=None  -> theo `config.SKIP_EXISTING`
    force=True  -> chạy lại kể cả khi output đã có
    force=False -> bỏ qua nếu output đã có
    """
    render.md(f"### ▶ {step.id} — {step.title}")
    if step.note:
        render.note(step.note)

    argv = _argv(step)
    render.md("```bash\n" + " ".join(["python"] + [config.rel(a) for a in argv[1:]])
              + "\n```")

    if step.done() and (force is False or (force is None and config.SKIP_EXISTING)):
        have_all = bool(step.outputs) and all(config.exists(o) for o in step.outputs)
        why = ("output đã có sẵn trên đĩa" if have_all else
               "file của bước sau đã có (`" + "`, `".join(step.done_if) + "`)")
        render.md(f"⏭️ **Bỏ qua** — {why}. Chạy `run(step, force=True)` để dựng lại.")
        _output_table(step)
        return Result(step, True, 0.0, None, None,
                      [config.abs_path(o) for o in step.outputs], [])

    problems = preflight(step)
    if problems:
        for p in problems:
            render.fail(p) if not step.optional else render.warn(p)
        if step.optional:
            render.note("Bước này được đánh dấu **không bắt buộc** — không bước nào "
                        "phía sau đọc output của nó, nên notebook đi tiếp.")
            return Result(step, True, 0.0, None, None, [], [], problems)
        raise StepBlocked(problems[0])

    log_path = config.NB_LOGS / f"{step.id}.log"
    est = f" (ước tính ~{render.human_time(step.minutes * 60)})" if step.minutes else ""
    render.md(f"⏳ Đang chạy{est}. Log đầy đủ: `{config.rel(log_path)}`")

    env = dict(os.environ, PYTHONUNBUFFERED="1")
    started = time.time()
    lines_shown = 0
    tail: list[str] = []

    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            argv, cwd=config.ROOT, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                log.write(line)
                tail.append(line.rstrip("\n"))
                if len(tail) > 20:
                    tail.pop(0)
                if lines_shown < config.MAX_LOG_LINES:
                    print(line, end="", flush=True)
                    lines_shown += 1
                    if lines_shown == config.MAX_LOG_LINES:
                        print(f"\n... [{config.MAX_LOG_LINES} dòng đầu; phần còn lại "
                              f"chỉ ghi vào {config.rel(log_path)}]\n", flush=True)
            proc.wait(timeout=timeout)
        except KeyboardInterrupt:
            proc.terminate()
            raise
        except subprocess.TimeoutExpired:
            proc.kill()
            raise

    elapsed = time.time() - started
    if lines_shown >= config.MAX_LOG_LINES and tail:
        print("--- 20 dòng cuối ---")
        print("\n".join(tail))

    if proc.returncode != 0:
        render.fail(f"Lệnh thất bại (mã {proc.returncode}) sau {render.human_time(elapsed)}")
        render.md("20 dòng cuối:\n```\n" + "\n".join(tail) + "\n```")
        raise StepFailed(f"{step.id}: mã thoát {proc.returncode}; log: {log_path}")

    # `du` vừa cache dung lượng cũ của các thư mục output — bỏ đi để bảng dưới
    # hiện số thật sau khi chạy.
    config._DU_CACHE.clear()
    missing = [o for o in step.outputs if not config.exists(o)]
    if missing:
        render.fail("Chạy xong nhưng THIẾU output: " + ", ".join(f"`{m}`" for m in missing)
                    + " — đừng chạy tiếp, bước sau sẽ nhận bảng rỗng.")
    else:
        render.ok(f"Xong sau {render.human_time(elapsed)}")
    _output_table(step)
    return Result(step, False, elapsed, proc.returncode, log_path,
                  [config.abs_path(o) for o in step.outputs], missing)


def run_all(steps: list[Step], force: bool | None = None) -> list[Result]:
    """Chạy nhiều bước liên tiếp, dừng ngay khi có bước hỏng."""
    return [run(s, force=force) for s in steps]


def plan(steps: list[Step] | None = None) -> None:
    """Bảng kê các bước: trạng thái output, thời gian ước tính, cần mạng hay không.

    Không truyền gì thì kê mọi `Step` đã được định nghĩa trong phiên này, theo
    đúng thứ tự các cell ở trên đã định nghĩa chúng.
    """
    from_registry = steps is None
    steps = list(REGISTRY.values()) if from_registry else steps

    if from_registry and not steps:
        render.warn("Chưa cell nào định nghĩa bước nào trong phiên này. "
                    "Chạy **Run All** (hoặc các cell phía trên) rồi quay lại cell này.")
        return

    rows, total, tracked = [], 0.0, 0
    for s in steps:
        done = s.done()
        if not (s.outputs or s.done_if):
            state = "mỗi lần"          # không khai output: chạy lại mỗi lượt
        else:
            tracked += 1
            state = "có" if done else "chưa"
        if not done and s.minutes:
            total += s.minutes
        rows.append([s.id, s.title, state,
                     f"{s.minutes:g}'" if s.minutes else "—",
                     " ".join(t for t in ("mạng" if s.network else "",
                                          "key" if s.needs_key else "",
                                          "tuỳ chọn" if s.optional else "") if t)])
    render.table(rows, ["Bước", "Việc", "Output", "Ước tính", "Điều kiện"])
    render.note(f"{sum(1 for s in steps if s.done())}/{tracked} bước có khai output đã xong. "
                "Tổng thời gian của các bước **đã có ước tính** và chưa có output: "
                f"**~{render.human_time(total * 60)}**. Các bước ghi `—` thì chưa đo; "
                "phần nặng nhất là ba lượt tải Comtrade, tính bằng ngày vì quota.")
