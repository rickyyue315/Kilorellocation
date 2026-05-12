"""
測試 B2 模式接收優先排序：
1) 遊客區店舖 (Type T) 高銷量優先
2) 混合型店舖 (Type M) 高銷量優先
3) 遊客區店舖 (Type T) Safety 優先
4) 混合型店舖 (Type M) Safety 優先
"""

import pandas as pd

from business_logic import TransferLogic


def test_b2_destination_priority_order():
    logic = TransferLogic()

    data = {
        'Article': ['109249904001'] * 8,
        'OM': ['OM1'] * 8,
        'Site': ['T1', 'T2', 'M1', 'M2', 'T3', 'T4', 'M3', 'M4'],
        'RP Type': ['RF'] * 8,
        'SaSa Net Stock': [1, 1, 1, 1, 1, 1, 1, 1],
        'Pending Received': [0, 0, 0, 0, 0, 0, 0, 0],
        'Safety Stock': [10, 9, 8, 7, 12, 8, 11, 7],
        'Last Month Sold Qty': [7, 4, 6, 2, 0, 0, 0, 0],
        'MTD Sold Qty': [3, 2, 3, 2, 0, 0, 0, 0],
        'MOQ': [1] * 8,
        'Effective Sold Qty': [10, 6, 9, 4, 0, 0, 0, 0],
        'Article Description': ['Test Product'] * 8,
        'Type': ['T', 'T', 'M', 'M', 'T', 'T', 'M', 'M'],
    }

    df = pd.DataFrame(data)

    destinations = logic.identify_destinations(df, logic.mode_b_special)
    ordered_sites = [d['site'] for d in destinations]

    expected_order = ['T1', 'T2', 'M1', 'M2', 'T3', 'T4', 'M3', 'M4']

    assert ordered_sites == expected_order, \
        f"B2 優先排序不符: expected {expected_order}, got {ordered_sites}"


if __name__ == '__main__':
    test_b2_destination_priority_order()
