"""
集中配置模組 — 版本、環境偵測、Magic Numbers、配色方案、欄位定義
"""

import os

VERSION = "v2.13.0"

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
]

INTEGER_COLUMNS = [
    'SaSa Net Stock', 'Pending Received', 'Safety Stock',
    'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ',
]

STRING_COLUMNS = ['OM', 'RP Type', 'Site']

# ── 配色方案 (淺色模式) ────────────────────────────────────────────

THEME = {
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#F8F9FA',
    'text_primary': '#212529',
    'text_secondary': '#6C757D',
    'accent': '#4A90E2',
    'accent_hover': '#357ABD',
    'success': '#28A745',
    'success_bg': '#D4EDDA',
    'success_text': '#155724',
    'info': '#17A2B8',
    'info_bg': '#D1ECF1',
    'info_text': '#0C5460',
    'warning': '#FFC107',
    'warning_bg': '#FFF3CD',
    'warning_text': '#856404',
    'error_bg': '#F8D7DA',
    'error_text': '#721C24',
    'border': '#DEE2E6',
    'shadow': 'rgba(0,0,0,0.05)',
}
