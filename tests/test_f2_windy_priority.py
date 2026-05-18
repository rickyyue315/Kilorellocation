import pytest
import pandas as pd
from business_logic import TransferLogic


def _build_windy_priority_df():
    return pd.DataFrame([
        {
            'Article': '000000000010',
            'Article Description': 'F2 Windy Priority Test',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD02',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 2,
            'Target': '',
        },
        {
            'Article': '000000000010',
            'Article Description': 'F2 Windy Priority Test',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD03',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Target': 4,
        },
        {
            'Article': '000000000010',
            'Article Description': 'F2 Windy Priority Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 6,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 9,
            'Target': '',
        },
    ])


def test_f2_windy_source_prioritized_over_non_windy():
    df = _build_windy_priority_df()
    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "F指定模式")

    hd03_transfers = [r for r in recs if r['Receive Site'] == 'HD03']
    assert len(hd03_transfers) > 0, "HD03 should receive stock"

    hd02_transfers = [r for r in hd03_transfers if r['Transfer Site'] == 'HD02']
    assert len(hd02_transfers) > 0, "Windy source HD02 should be used first"

    total_from_hd02 = sum(r['Transfer Qty'] for r in hd02_transfers)
    total_from_rf01 = sum(
        r['Transfer Qty'] for r in hd03_transfers if r['Transfer Site'] == 'RF01'
    )

    assert total_from_hd02 == 4, (
        f"Windy source HD02 should fulfill target 4 units, got {total_from_hd02}"
    )
    assert total_from_rf01 == 0, (
        f"Non-Windy source RF01 should not be used when Windy source has enough, got {total_from_rf01}"
    )


def test_f2_windy_falls_back_to_non_windy_when_insufficient():
    df = pd.DataFrame([
        {
            'Article': '000000000011',
            'Article Description': 'F2 Windy Fallback Test',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD02',
            'SaSa Net Stock': 2,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Target': '',
        },
        {
            'Article': '000000000011',
            'Article Description': 'F2 Windy Fallback Test',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD03',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Target': 6,
        },
        {
            'Article': '000000000011',
            'Article Description': 'F2 Windy Fallback Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 1,
            'Target': '',
        },
    ])
    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "F指定模式")

    hd03_transfers = [r for r in recs if r['Receive Site'] == 'HD03']
    assert len(hd03_transfers) > 0, "HD03 should receive stock"

    hd02_transfers = [r for r in hd03_transfers if r['Transfer Site'] == 'HD02']
    rf01_transfers = [r for r in hd03_transfers if r['Transfer Site'] == 'RF01']

    assert len(hd02_transfers) > 0, "Windy source HD02 should be used first"
    assert len(rf01_transfers) > 0, (
        "Non-Windy source RF01 should be used when Windy source is insufficient"
    )

    total_received = sum(r['Transfer Qty'] for r in hd03_transfers)
    assert total_received == 6, f"HD03 should receive all 6 units, got {total_received}"


def test_f2_windy_nd_source_prioritized_over_non_windy_nd():
    df = pd.DataFrame([
        {
            'Article': '000000000012',
            'Article Description': 'F2 Windy ND Priority Test',
            'OM': 'Windy',
            'RP Type': 'ND',
            'Site': 'HD02',
            'SaSa Net Stock': 8,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Target': '',
        },
        {
            'Article': '000000000012',
            'Article Description': 'F2 Windy ND Priority Test',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD03',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Target': 5,
        },
        {
            'Article': '000000000012',
            'Article Description': 'F2 Windy ND Priority Test',
            'OM': 'Ivy',
            'RP Type': 'ND',
            'Site': 'ND01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 1,
            'Target': '',
        },
    ])
    logic = TransferLogic()
    recs = logic.generate_transfer_recommendations(df, "F指定模式")

    hd03_transfers = [r for r in recs if r['Receive Site'] == 'HD03']
    assert len(hd03_transfers) > 0, "HD03 should receive stock"

    hd02_transfers = [r for r in hd03_transfers if r['Transfer Site'] == 'HD02']
    assert len(hd02_transfers) > 0, "Windy ND source HD02 should be used first"

    total_from_hd02 = sum(r['Transfer Qty'] for r in hd02_transfers)
    assert total_from_hd02 == 5, (
        f"Windy ND source HD02 should fulfill all 5 units, got {total_from_hd02}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
