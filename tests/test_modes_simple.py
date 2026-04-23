"""
Pytest 測試：檢查所有模式下是否出現同源店舖同時接收和轉出的情況
"""

import os
import sys
from collections import defaultdict
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic
from data_processor import DataProcessor

FILE_PATH = "PIP_JosephJoey_09Feb2026.XLSX"

def _build_mock_df() -> pd.DataFrame:
    data = {
        'Article': ['109249904001'] * 6 + ['109249904002'] * 6,
        'OM': ['OM1'] * 6 + ['OM2'] * 6,
        'Site': ['HB25', 'HC25', 'HC63', 'HB10', 'HA02', 'HA06'] +
                ['HB25', 'HC25', 'HC63', 'HB10', 'HA02', 'HA06'],
        'RP Type': ['RF', 'RF', 'RF', 'RF', 'ND', 'RF'] * 2,
        'SaSa Net Stock': [5, 3, 0, 10, 8, 2] * 2,
        'Pending Received': [0, 0, 0, 0, 0, 0] * 2,
        'Safety Stock': [3, 5, 4, 5, 2, 3] * 2,
        'Last Month Sold Qty': [1, 1, 3, 5, 2, 1] * 2,
        'MTD Sold Qty': [0, 1, 2, 3, 1, 0] * 2,
        'Effective Sold Qty': [1, 2, 5, 8, 3, 1] * 2,
        'MOQ': [1, 1, 1, 1, 1, 1] * 2,
        'Article Description': ['Test Product A'] * 6 + ['Test Product B'] * 6,
        'Type': ['L', 'L', 'R', 'R', 'M', 'T'] * 2,
    }
    return pd.DataFrame(data)


def _load_test_df() -> pd.DataFrame:
    if os.path.exists(FILE_PATH):
        processor = DataProcessor()
        df, _ = processor.preprocess_data(FILE_PATH)
        return df
    return _build_mock_df()

MODES = [
    "保守轉貨",
    "加強轉貨", 
    "附加B(特別模式)",
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "重點補0",
    "重點補0-只補0/1",
    "附加C2(跨OM重點補0)",
    "清貨轉貨",
    "清貨轉貨(ND限定)",
    "強制轉出",
    "目標優化",
    "F指定模式",
]

def check_mode(df: pd.DataFrame, mode: str):
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode)

    article_sources = defaultdict(set)
    article_dests = defaultdict(set)

    for rec in recommendations:
        article = rec["Article"]
        article_sources[article].add(rec["Transfer Site"])
        article_dests[article].add(rec["Receive Site"])

    violations = []
    for article in article_sources:
        overlap = article_sources[article] & article_dests[article]
        if overlap:
            violations.append((article, overlap))

    return violations, len(recommendations)


@pytest.mark.parametrize("mode", MODES)
def test_no_dual_role_in_all_modes(mode: str):
    df = _load_test_df()
    violations, total = check_mode(df, mode)
    assert not violations, f"模式[{mode}] 發現同源衝突: {violations[:5]} (建議數: {total})"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])