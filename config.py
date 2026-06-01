"""
集中配置模組 — 版本、環境偵測、Magic Numbers、配色方案、欄位定義
"""

import os

VERSION = "v2.17.0"

ZEABUR_ENV_KEYS = [
    'ZEABUR',
    'ZEABUR_PROJECT_ID',
    'ZEABUR_SERVICE_ID',
    'ZEABUR_DEPLOYMENT_ID',
]


def _is_zeabur_runtime() -> bool:
    return any(os.getenv(key) for key in ZEABUR_ENV_KEYS)


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name, '').strip()
    if not value:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


IS_ZEABUR_RUNTIME = _is_zeabur_runtime()
ZEABUR_RESULT_PREVIEW_LIMIT = _get_env_int('KILO_ZEABUR_RESULT_PREVIEW_LIMIT', 1000)

# ── Magic Numbers (business_logic.py) ──────────────────────────────

A_MODE_PERCENTAGE_CAP = 0.2
A_MODE_MIN_TRANSFER = 2

B_MODE_PERCENTAGE_CAP = 0.5
B_MODE_MIN_TRANSFER = 2

C_MODE_PERCENTAGE_CAP = 0.3
C_MODE_ABS_CAP = 3

C1_MODE_MIN_TRANSFER = 2

SAFETY_RECEIVE_MULTIPLIER = 2
MIN_RECEIVE_FLOOR = 3

F_TARGET_MULTIPLIER = 0.5
F_TARGET_FLOOR = 3

SIMPLIFIED_SKU_RECEIVE_MULTIPLIER = 2

ND_RECEIVE_MULTIPLIER = 2

# ── Magic Numbers (data_processor.py) ──────────────────────────────

OUTLIER_CAP = 100000
FILE_SIZE_LIMIT_BYTES = 50 * 1024 * 1024

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

# ── 配色方案 (i14 深色主題) ──────────────────────────────────────────

THEME = {
    'bg_primary': '#0a0a0f',
    'bg_secondary': '#12121a',
    'text_primary': '#ffffff',
    'text_secondary': '#888899',
    'accent': '#00d4ff',
    'accent_hover': '#0099cc',
    'success': '#10B981',
    'success_bg': '#064E3B',
    'success_text': '#D1FAE5',
    'info': '#3B82F6',
    'info_bg': '#0C1F3F',
    'info_text': '#DBEAFE',
    'warning': '#F59E0B',
    'warning_bg': '#4A2E08',
    'warning_text': '#FEF3C7',
    'error_bg': '#7F1D1D',
    'error_text': '#FEE2E2',
    'border': '#1e1e2e',
    'shadow': 'rgba(0,0,0,0.2)',
}
