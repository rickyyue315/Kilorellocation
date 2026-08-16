"""
保底主體 Turnday 計算 — 以日銷速 × 自選日數取代 Safety Stock 保底值。

在 preprocess 之後、進入 TransferLogic 之前呼叫 apply_turnday_floor()，
把 Safety Stock 欄位值換成 Turnday 保底值（原值備份至 Original Safety Stock），
令全部 30 個調貨模式以同一套邏輯運行在 Turnday 基準上。

公式：
    覆蓋日數 = 上月日數 + 數據日期日號(MTD日數)
    日銷速   = Effective Sold Qty ÷ 覆蓋日數
    保底     = ceil(日銷速 × 自選日數 N)   （零銷量 → 0）
"""

import calendar
import logging
import math
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)


def compute_coverage_days(as_of_date: date) -> int:
    """
    計算銷速覆蓋日數：上月日數 + MTD日數（數據覆蓋至 as_of_date 當日）。

    例：as_of_date = 2026-08-15 → 7月31日 + 15日 = 46日
    """
    if as_of_date.month == 1:
        last_month_days = calendar.monthrange(as_of_date.year - 1, 12)[1]
    else:
        last_month_days = calendar.monthrange(as_of_date.year, as_of_date.month - 1)[1]
    return last_month_days + as_of_date.day


def describe_coverage(as_of_date: date) -> str:
    """產生 UI 核對用 caption 文字。"""
    if as_of_date.month == 1:
        last_month = f"{as_of_date.year - 1}年12月"
    else:
        last_month = f"{as_of_date.month - 1}月"
    mtd_days = as_of_date.day
    total = compute_coverage_days(as_of_date)
    return f"覆蓋日數核對：上月({last_month}){total - mtd_days}日 + MTD {mtd_days}日 = {total}日"


def apply_turnday_floor(df: pd.DataFrame, as_of_date: date, days: int) -> pd.DataFrame:
    """
    以 Turnday 保底值取代 Safety Stock 欄位（不改動原 df）。

    - 原值備份至 Original Safety Stock
    - 新增 Daily Sold Rate 欄（透明度）
    - Safety Stock = ceil(Effective Sold Qty ÷ 覆蓋日數 × days)，零銷量 = 0
    """
    if days < 1:
        raise ValueError(f"Turnday 日數必須 ≥ 1，收到 {days}")

    coverage_days = compute_coverage_days(as_of_date)
    result = df.copy()

    result['Original Safety Stock'] = result['Safety Stock']

    if 'Effective Sold Qty' in result.columns:
        effective_sold = pd.to_numeric(result['Effective Sold Qty'], errors='coerce').fillna(0)
    else:
        effective_sold = pd.Series(0, index=result.index)
    daily_rate = effective_sold / coverage_days
    result['Daily Sold Rate'] = daily_rate.round(2)

    turnday_stock = (daily_rate * days).apply(math.ceil).astype(int)
    result['Safety Stock'] = turnday_stock

    logger.info(
        "Turnday 保底套用完成：數據日期=%s 覆蓋日數=%d 日數=%d 行數=%d",
        as_of_date, coverage_days, days, len(result),
    )
    return result
