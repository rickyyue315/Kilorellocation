"""
Target 欄位工具 — NFKC 正規化、數值解析、ND+Target 衝突偵測
"""

import unicodedata
from typing import Any

import numpy as np
import pandas as pd


def normalize_target_value(value: Any) -> Any:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "":
        return np.nan
    text = unicodedata.normalize('NFKC', text).replace(',', '')
    return text


def parse_target_for_ui_value(value: Any):
    normalized = normalize_target_value(value)
    if isinstance(normalized, float) and np.isnan(normalized):
        return float('nan')
    return pd.to_numeric(normalized, errors='coerce')


def parse_target_series(df: pd.DataFrame) -> pd.Series:
    if 'Target' not in df.columns:
        return pd.Series(np.nan, index=df.index)
    normalized = df['Target'].map(normalize_target_value)
    parsed = pd.to_numeric(normalized, errors='coerce')
    if isinstance(parsed, pd.Series):
        return parsed
    return pd.Series(parsed, index=df.index)


def find_f_mode_nd_target_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    if 'RP Type' not in df.columns or 'Target' not in df.columns:
        return pd.DataFrame()
    target_numeric = df['Target'].map(parse_target_for_ui_value)
    nd_mask = df['RP Type'].astype(str).str.strip().str.upper() == 'ND'
    target_mask = pd.Series(target_numeric, index=df.index).fillna(0) > 0
    conflicts = df[nd_mask & target_mask].copy()
    if conflicts.empty:
        return conflicts
    conflicts['Target Numeric'] = target_numeric[conflicts.index]
    return conflicts
