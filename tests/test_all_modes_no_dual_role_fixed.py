"""
檢查所有模式下是否出現同一SKU的店舖同時做轉出與接收（使用模擬資料）
"""

import pytest
import pandas as pd
from business_logic import TransferLogic


def _build_test_df():
    rows = [
        {
            'Article': '000000000001',
            'Article Description': 'Product A',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA02',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Type': 'T',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'Product A',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA06',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 4,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 6,
            'Type': 'M',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'Product A',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA15',
            'SaSa Net Stock': 8,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 4,
            'Type': 'M',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'Product A',
            'OM': 'Ivy',
            'RP Type': 'ND',
            'Site': 'HA19',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 0,
            'Type': 'L',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000002',
            'Article Description': 'Product B',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD02',
            'SaSa Net Stock': 12,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 6,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 8,
            'Type': 'L',
            'ALL': '*',
            'Target': '',
        },
        {
            'Article': '000000000002',
            'Article Description': 'Product B',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD03',
            'SaSa Net Stock': 1,
            'Pending Received': 0,
            'Safety Stock': 4,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Type': 'T',
            'ALL': '',
            'Target': '5',
        },
    ]
    return pd.DataFrame(rows)


MODES_SAME_OM = [
    "保守轉貨",
    "加強轉貨",
    "附加B(特別模式)",
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "重點補0",
    "重點補0-只補0/1",
    "清貨轉貨",
    "清貨轉貨(ND限定)",
    "強制轉出",
    "強制轉出(優先類型接收)",
    "目標優化",
    "F指定模式",
    "ND同OM轉貨",
    "精簡SKU(限同OM)",
]

MODES_CROSS_OM = [
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加C2(跨OM重點補0)",
    "強制轉出(跨OM)",
    "ND混合OM轉貨",
    "精簡SKU(跨OM)",
]


@pytest.mark.parametrize("mode", MODES_SAME_OM + MODES_CROSS_OM)
def test_no_dual_role_all_modes(mode):
    df = _build_test_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode)

    article_sources = {}
    article_dests = {}

    for rec in recommendations:
        art = rec['Article']
        src = rec['Transfer Site']
        dst = rec['Receive Site']

        if art not in article_sources:
            article_sources[art] = set()
        if art not in article_dests:
            article_dests[art] = set()

        article_sources[art].add(src)
        article_dests[art].add(dst)

    for art in article_sources:
        overlap = article_sources[art] & article_dests[art]
        assert not overlap, (
            f"Mode [{mode}]: dual role for article {art} at sites {overlap}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
