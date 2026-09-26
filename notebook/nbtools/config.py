"""Đường dẫn, thiết lập và kiểm tra môi trường cho notebook Stage 1.

Gốc dự án là **chính thư mục `notebook/`**, không phải thư mục nào khác.

Đó không phải một quy ước tuỳ tiện: mọi script trong `scripts/` mở đầu bằng

    HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

nghĩa là chúng tự coi *thư mục cha của `scripts/`* là gốc, rồi đọc/ghi
`<gốc>/data/`, `<gốc>/selection/`, `<gốc>/docs/`, `<gốc>/.env`. Đặt `scripts/`
vào trong `notebook/` là `notebook/` trở thành gốc, và notebook với script nhìn
cùng một tập file — không có trường hợp "notebook đọc một đằng, script ghi một nẻo".

Mọi thứ trong folder này là file thật, không có symlink nào. Nhờ vậy gửi nó đi
bằng cách nào cũng được: copy, nén, upload Drive — và bên nhận chạy được ngay.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

# --- gốc dự án --------------------------------------------------------------

#: Gốc dự án = thư mục chứa notebook này (`nbtools/` nằm ngay trong nó).
ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = ROOT / "scripts"
SELECTION = ROOT / "selection"
DOCS = ROOT / "docs"
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
FINAL = DATA / "final"
NB_LOGS = ROOT / "logs"
ENV_FILE = ROOT / ".env"

#: Những thứ phải có mặt thì pipeline mới chạy được, kèm cách nhận ra chúng.
#: `data/raw` không nằm ở đây vì thiếu nó thì notebook vẫn đọc được, chỉ là
#: phải tải lại từ API — `check_data()` mới là chỗ nói về dữ liệu.
REQUIRED_LAYOUT = {
    "scripts/": (SCRIPTS / "build_spells.py",
                 "toàn bộ code của pipeline"),
    "selection/": (SELECTION / "importers_vn.csv",
                   "input làm tay: 147 nước nhập khẩu, mapping thuế EU, allowlist"),
    "data/": (DATA, "nơi raw/ interim/ final/ nằm"),
}

#: Có thì tốt, không có vẫn chạy được hết pipeline. `docs/` hay bị bỏ ra khi
#: đóng gói cho gọn; bước 30 tự tạo lại `docs/audit/` để ghi báo cáo kiểm định.
OPTIONAL_LAYOUT = {
    "docs/": (DOCS / "TU_DIEN_DU_LIEU_FINAL_DF.md",
              "tài liệu tham chiếu (từ điển 209 cột, khoá ghép, kế hoạch sửa lỗi)"),
}

#: Trình thông dịch chạy mọi script — chính là python đang chạy notebook, nên
#: môi trường của notebook và của pipeline không bao giờ lệch nhau.
PYTHON = sys.executable


def layout_report() -> list[dict]:
    """Từng thành phần bắt buộc: có mặt chưa, trỏ về đâu."""
    out = []
    for name, (probe, why) in REQUIRED_LAYOUT.items():
        out.append({"name": name, "ok": probe.exists(), "why": why,
                    "required": True})
    for name, (probe, why) in OPTIONAL_LAYOUT.items():
        out.append({"name": name, "ok": probe.exists(), "why": why,
                    "required": False})
    return out


def check_layout() -> list[str]:
    """Danh sách thành phần còn thiếu. Rỗng nghĩa là bố cục đủ điều kiện chạy."""
    return [r["name"] for r in layout_report() if r["required"] and not r["ok"]]


# --- các mốc dữ liệu --------------------------------------------------------

#: Theo thứ tự pipeline. Dùng để trả lời "chạy notebook này mất bao lâu".
DATA_MILESTONES = [
    ("raw · thương mại (bước 4-5)",
     ["raw/trade", "raw/trade_world", "raw/trade_mirror"]),
    ("raw · thuế (bước 6, 8)",
     ["raw/tariffs/mfn", "raw/tariffs/pref", "raw/eu_cn"]),
    ("raw · NTM (bước 7, 13)",
     ["raw/ntm/researcher", "raw/ntm/ave_gtap"]),
    ("raw · EVFTA + Mỹ (bước 9-10)",
     ["raw/evfta", "raw/us_tariffs_2025"]),
    ("raw · biến kiểm soát (bước 11-12)",
     ["raw/gravity", "raw/wdi", "raw/rta", "raw/ttbd", "raw/complexity",
      "raw/epi", "raw/shocks", "raw/cbam", "raw/concordance"]),
    ("interim · khoá + spell (bước 14-18)",
     ["interim/family_map.csv", "interim/spells.csv", "interim/episodes.csv"]),
    ("interim · module đặc trưng (bước 19-23)",
     ["interim/eu_tariff_panel.csv", "interim/evfta_staging_family.csv",
      "interim/ntm6_observed.csv", "interim/ntm_country.csv",
      "interim/macro_panel_v2.csv", "interim/glpi.csv",
      "interim/us_tariff_vn.csv"]),
    ("interim · data tổng (bước 24)",
     ["interim/panel_final.csv"]),
    ("final · panel Stage 1 (bước 28)",
     ["final/stage1_panel.parquet"]),
]

# --- thiết lập chạy ---------------------------------------------------------

#: True  = bước nào đã có đủ file output thì bỏ qua, không chạy lại.
#:         Trên máy trắng không file nào có sẵn, nên TOÀN BỘ pipeline vẫn chạy
#:         thật từ raw. Lần sau, notebook chạy lại trong vài giây.
#: False = luôn gọi script, kể cả khi output đã có (chạy lại thật sự).
SKIP_EXISTING = True

#: Chặn mọi bước có `network=True`. Bật lên khi chỉ có `data/raw/` và muốn dựng
#: lại phần tính toán mà không gọi API. Bước nào `optional=True` sẽ được bỏ qua
#: êm; bước nào bắt buộc sẽ dừng với lý do rõ ràng.
OFFLINE = False

#: Số dòng log tối đa in ra mỗi cell. Vượt ngưỡng thì chỉ ghi tiếp vào file log
#: và in 20 dòng cuối khi xong — để notebook không phình vài trăm MB.
MAX_LOG_LINES = 400

#: Gói bên thứ ba mà pipeline thật sự cần, kèm script dùng tới nó.
REQUIRED_PACKAGES = {
    "polars": "build_stage1_df.py, audit_stage1.py",
    "numpy": "build_glpi.py",
    "pdfplumber": "build_evfta_staging.py, build_eu_mfn_cn.py",
    "openpyxl": "families.py, build_covariates.py",
    "xlrd": "families.py, build_covariates.py",
}

#: Biến môi trường đọc từ `.env` ở gốc. Chỉ ba bước tải Comtrade cần tới; có
#: sẵn `data/raw/trade*/` thì không cần key nào.
REQUIRED_ENV_KEYS = ("COMTRADE_PRIMARY_KEY",)


# --- đường dẫn --------------------------------------------------------------


def abs_path(path) -> Path:
    """Đường dẫn tương đối (theo gốc dự án) -> tuyệt đối.

    Mọi cell trong notebook viết `data/...`, `selection/...`, `docs/...` như
    chính các script viết, và cả hai cùng hiểu là `notebook/...`.
    """
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path) -> str:
    """Đường dẫn rút gọn theo gốc dự án, để in cho gọn."""
    p = Path(path)
    if not p.is_absolute():
        return str(p)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def exists(path) -> bool:
    """Có file/thư mục đó chưa. Thư mục rỗng tính là CHƯA có."""
    p = abs_path(path)
    if p.is_dir():
        return any(p.iterdir())
    return p.exists()


# --- đo đạc -----------------------------------------------------------------

_DU_CACHE: dict[str, tuple[float, int]] = {}
#: Đo dung lượng một thư mục 765 MB tốn cả giây, mà nhiều cell hỏi lại cùng một
#: thư mục. Giữ kết quả trong ngần này giây rồi mới đo lại.
DU_TTL = 60.0


def _du(path: Path, use_cache: bool = True) -> int:
    """Dung lượng thư mục, bytes. Dùng `du` vì nhanh hơn walk trên WSL."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    import time
    key = str(path)
    hit = _DU_CACHE.get(key)
    if use_cache and hit and time.time() - hit[0] < DU_TTL:
        return hit[1]
    try:
        out = subprocess.run(["du", "-sbL", str(path)], capture_output=True,
                             text=True, timeout=120)
        size = int(out.stdout.split()[0])
    except Exception:
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    _DU_CACHE[key] = (time.time(), size)
    return size


def data_status() -> list[dict]:
    """Từng mốc dữ liệu: có đủ chưa, thiếu file nào, nặng bao nhiêu."""
    out = []
    for label, paths in DATA_MILESTONES:
        present, missing, size = [], [], 0
        for rp in paths:
            f = abs_path("data/" + rp)
            ok = exists(f)
            (present if ok else missing).append(rp)
            if ok:
                size += _du(f)
        out.append({"label": label, "n": len(paths), "present": present,
                    "missing": missing, "bytes": size})
    return out


def env_keys() -> dict[str, bool]:
    """Các key trong .env và việc chúng có giá trị hay không (không lộ giá trị)."""
    found = {k: False for k in REQUIRED_ENV_KEYS}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            if k.strip() in found:
                found[k.strip()] = bool(v.strip())
    return found


# --- môi trường -------------------------------------------------------------

_PKG_CACHE: dict[str, str | None] = {}


def _pkg_version(name: str) -> str | None:
    if name not in _PKG_CACHE:
        try:
            _PKG_CACHE[name] = getattr(importlib.import_module(name),
                                       "__version__", "?")
        except Exception:
            _PKG_CACHE[name] = None
    return _PKG_CACHE[name]


def missing_packages() -> list[str]:
    """Gói còn thiếu. Rẻ: kết quả import được nhớ lại, không import lại mỗi lần."""
    return [n for n in REQUIRED_PACKAGES if _pkg_version(n) is None]


def interpreter_kind() -> str:
    """Python đang chạy notebook thuộc loại nào — để biết có bị lẫn môi trường không."""
    if os.environ.get("CONDA_DEFAULT_ENV"):
        return f"conda ({os.environ['CONDA_DEFAULT_ENV']})"
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return "venv"
    return "python hệ thống"


def environment_report(with_sizes: bool = True) -> dict:
    """Thu thập mọi thứ cần biết trước khi bấm Run All.

    `with_sizes=False` bỏ phần đo dung lượng — phần duy nhất tốn thời gian.
    """
    import shutil as _shutil
    usage = _shutil.disk_usage(ROOT)
    sizes = ({k: _du(v) for k, v in
              {"data/raw": RAW, "data/interim": INTERIM, "data/final": FINAL}.items()}
             if with_sizes else {})
    return {
        "root": ROOT,
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "interpreter": interpreter_kind(),
        "packages": {n: _pkg_version(n) for n in REQUIRED_PACKAGES},
        "missing_packages": missing_packages(),
        "env_keys": env_keys(),
        "disk_free_gb": usage.free / 1e9,
        "layout": layout_report(),
        "missing_layout": check_layout(),
        "data": sizes,
        "settings": {
            "SKIP_EXISTING": SKIP_EXISTING,
            "OFFLINE": OFFLINE,
            "MAX_LOG_LINES": MAX_LOG_LINES,
        },
    }


def _ensure(d: Path) -> None:
    """Tạo thư mục nếu chưa có, và im lặng nếu không tạo được.

    Không tạo được nghĩa là có gì đó bất thường ở chỗ đó. `check_environment()`
    mới là chỗ báo việc ấy ra, chứ không phải lúc import.
    """
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


# Khung thư mục phải có mặt ngay cả khi gói gửi đi không kèm dữ liệu, để người
# nhận biết chỗ mà bỏ `raw/` vào.
_ensure(NB_LOGS)
for _d in (RAW, INTERIM, FINAL):
    _ensure(_d)
