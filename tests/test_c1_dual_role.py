import pytest
import pandas as pd
from business_logic import TransferLogic


def _make_df(rows):
    return pd.DataFrame(rows)


def test_c1_mode_no_dual_role():
    df = _make_df([
        {
            'Article': '000000000001',
            'Article Description': 'Test SKU',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 7,
        },
        {
            'Article': '000000000001',
            'Article Description': 'Test SKU',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF02',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 7,
        },
        {
            'Article': '000000000001',
            'Article Description': 'Test SKU',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF03',
            'SaSa Net Stock': 8,
            'Pending Received': 0,
            'Safety Stock': 2,
            'MOQ': 1,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 4,
        },
        {
            'Article': '000000000001',
            'Article Description': 'Test SKU',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF04',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 4,
            'MOQ': 1,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 4,
        },
    ])

    logic = TransferLogic()
    mode_c1 = logic.mode_c1

    recommendations = logic.generate_transfer_recommendations(df, mode_c1)

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
        assert not overlap, f"Dual role detected for article {art} at sites {overlap} in C1 mode"


if __name__ == '__main__':
    pytest.main([__file__])
