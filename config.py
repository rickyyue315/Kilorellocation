"""
集中配置模組 — 版本、環境偵測、Magic Numbers、配色方案、欄位定義
"""

import os

VERSION = "v2.38.3"

# ── 執行環境偵測（Streamlit Community Cloud / 其他雲端容器 / 本機）──────

# Streamlit Community Cloud 未提供官方環境變數，社群通用做法為檢查 repo 掛載路徑
# /mount/src（Community Cloud 容器固定把 repo 掛載於此）。
STREAMLIT_CLOUD_MOUNT_PATH = '/mount/src'
STREAMLIT_CLOUD_ENV_KEYS = [
    'IS_STREAMLIT_CLOUD',
    'STREAMLIT_CLOUD',
    'STREAMLIT_SHARING_MODE',
]

# Zeabur 環境變數（服務已結束，僅保留偵測以相容既有部署紀錄）
ZEABUR_ENV_KEYS = [
    'ZEABUR',
    'ZEABUR_PROJECT_ID',
    'ZEABUR_SERVICE_ID',
    'ZEABUR_DEPLOYMENT_ID',
]


def get_setting(name: str, default=None):
    """讀取設定值：環境變數優先，其次 st.secrets（Streamlit Community Cloud 的 Secrets 面板）。

    Community Cloud 只提供 Secrets（TOML）輸入框；根層級的字串／數字鍵值在 Streamlit
    解析 secrets 時會同步寫入 os.environ，此函式同時涵蓋「secrets 尚未被解析」與
    「本機以環境變數啟動」兩種情況。
    """
    value = os.getenv(name)
    if value not in (None, ''):
        return value

    try:
        import streamlit as st

        if st.runtime.exists() and name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # 非 Streamlit runtime（例如純 pytest）或 secrets 不存在
        pass

    return default


def _get_env_int(name: str, default: int) -> int:
    value = str(get_setting(name, '')).strip()
    if not value:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    value = str(get_setting(name, '')).strip().lower()
    if not value:
        return default
    return value in ('1', 'true', 'yes', 'y', 'on')


def _is_streamlit_cloud_runtime() -> bool:
    if any(os.getenv(key) for key in STREAMLIT_CLOUD_ENV_KEYS):
        return True
    return os.path.isdir(STREAMLIT_CLOUD_MOUNT_PATH)


def _is_zeabur_runtime() -> bool:
    return any(os.getenv(key) for key in ZEABUR_ENV_KEYS)


def _is_cloud_runtime() -> bool:
    """是否於雲端部署環境執行；可用 KILO_RUNTIME=cloud|local 強制指定。"""
    override = str(os.getenv('KILO_RUNTIME', '')).strip().lower()
    if override in ('cloud', 'local'):
        return override == 'cloud'
    return _is_streamlit_cloud_runtime() or _is_zeabur_runtime()


IS_CLOUD_RUNTIME = _is_cloud_runtime()

# ── 雲端資源防護（Streamlit Community Cloud 免費方案約 1GB RAM、共享 CPU）──
# 實測（純 Python、未含 Streamlit server 開銷）：2 萬行 ≈ 172MB 峰值、20 萬行 ≈ 748MB 峰值。
# 因此雲端採用較保守的上傳上限與行數守衛；本機開發不受影響。
#   0 = 停用該項限制（本機 FILE_SIZE_LIMIT_BYTES 固定 50MB、無行數上限）
CLOUD_MAX_UPLOAD_MB = _get_env_int('KILO_CLOUD_MAX_UPLOAD_MB', 8)
CLOUD_MAX_ROWS = _get_env_int('KILO_CLOUD_MAX_ROWS', 120000)

# 雲端結果表預覽上限（0 = 不限制）；舊變數名 KILO_ZEABUR_RESULT_PREVIEW_LIMIT 仍相容
CLOUD_RESULT_PREVIEW_LIMIT = _get_env_int(
    'KILO_CLOUD_RESULT_PREVIEW_LIMIT',
    _get_env_int('KILO_ZEABUR_RESULT_PREVIEW_LIMIT', 1000),
)

# 向後相容別名（Zeabur 時期命名）
IS_ZEABUR_RUNTIME = IS_CLOUD_RUNTIME
ZEABUR_RESULT_PREVIEW_LIMIT = CLOUD_RESULT_PREVIEW_LIMIT

# ── Magic Numbers (business_logic.py) ──────────────────────────────

A_MODE_PERCENTAGE_CAP = 0.2
A_MODE_MIN_TRANSFER = 2

B_MODE_PERCENTAGE_CAP = 0.5
B_MODE_MIN_TRANSFER = 2

C_MODE_PERCENTAGE_CAP = 0.3
C_MODE_ABS_CAP = 3

C1_MODE_MIN_TRANSFER = 2
C1_MODE_DEFAULT_THRESHOLD = 1
C1_MODE_DEFAULT_CEILING = 3

SAFETY_RECEIVE_MULTIPLIER = 2
MIN_RECEIVE_FLOOR = 3

F_TARGET_MULTIPLIER = 0.5
F_TARGET_FLOOR = 3

SIMPLIFIED_SKU_RECEIVE_MULTIPLIER = 2

ND_RECEIVE_MULTIPLIER = 2

ND3_KEEP_STOCK = 3

D2_MAX_RECEIVE_SITES_PER_SOURCE = 2
D2_NEEDED_QTY_MULTIPLIER = 2

NST_RF_RETAIN_STOCK = 2
NST_RF_TRANSFER_CAP = 0.75
NST_RF_MIN_STOCK_TO_SOURCE = 3

# ── 保底主體 (Safety / Turnday) ─────────────────────────────────────

FLOOR_BODY_SAFETY = "safety"
FLOOR_BODY_TURNDAY = "turnday"

TURNDAY_DEFAULT_DAYS = 14
TURNDAY_MIN_DAYS = 3
TURNDAY_MAX_DAYS = 60

# ── Magic Numbers (data_processor.py) ──────────────────────────────

OUTLIER_CAP = 100000

# 上傳上限：本機 50MB；雲端採較保守上限（1GB 容器）
LOCAL_MAX_UPLOAD_MB = 50
MAX_UPLOAD_MB = CLOUD_MAX_UPLOAD_MB if IS_CLOUD_RUNTIME else LOCAL_MAX_UPLOAD_MB
FILE_SIZE_LIMIT_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# 行數守衛：僅雲端啟用（0 = 不限制）；超過即中止，避免容器 OOM
MAX_ROWS = CLOUD_MAX_ROWS if IS_CLOUD_RUNTIME else 0

# ── 欄位定義 (data_processor.py) ──────────────────────────────────

REQUIRED_COLUMNS = [
    'Article', 'OM', 'RP Type', 'Site',
    'SaSa Net Stock', 'Pending Received', 'Safety Stock',
    'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ',
]

OPTIONAL_COLUMNS = [
    'Article Description',
    'Article Long Text (60 Chars)',
    'ALL',
    'Target',
    'Type',
    'Supply source',
]

INTEGER_COLUMNS = [
    'SaSa Net Stock', 'Pending Received', 'Safety Stock',
    'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ',
]

STRING_COLUMNS = ['OM', 'RP Type', 'Site']
