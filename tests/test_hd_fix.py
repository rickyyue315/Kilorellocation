"""
測試 HD 店舖不能轉到 HA/HB/HC 的限制規則（使用模擬資料）
"""

import pytest
import pandas as pd
from business_logic import TransferLogic


def _build_cross_om_df():
    return pd.DataFrame([
        {
            'Article': '000000000001',
            'Article Description': 'HD Product',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD02',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 8,
            'Type': 'L',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'HD Product',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD03',
            'SaSa Net Stock': 15,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Type': 'T',
            'ALL': '*',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'HA Product',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA02',
            'SaSa Net Stock': 1,
            'Pending Received': 0,
            'Safety Stock': 4,
            'MOQ': 1,
            'Last Month Sold Qty': 6,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 8,
            'Type': 'T',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'HB Product',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HB10',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 4,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 6,
            'Type': 'T',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'HC Product',
            'OM': 'Eva',
            'RP Type': 'RF',
            'Site': 'HC02',
            'SaSa Net Stock': 2,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 4,
            'Type': 'L',
            'ALL': '',
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'Windy Dest',
            'OM': 'Windy',
            'RP Type': 'RF',
            'Site': 'HD09',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 4,
            'MOQ': 1,
            'Last Month Sold Qty': 7,
            'MTD Sold Qty': 3,
            'Effective Sold Qty': 10,
            'Type': 'T',
            'ALL': '',
            'Target': '',
        },
    ])


@pytest.mark.parametrize("mode", [
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加C2(跨OM重點補0)",
    "強制轉出(跨OM)",
    "目標優化",
    "F指定模式",
])
def test_hd_cannot_transfer_to_ha_hb_hc(mode):
    df = _build_cross_om_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode)

    hd_violations = [
        r for r in recommendations
        if r['Transfer Site'].upper().startswith('HD')
        and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))
    ]

    assert len(hd_violations) == 0, (
        f"Mode [{mode}]: Found {len(hd_violations)} HD→HA/HB/HC violations: "
        + ", ".join(
            f"{r['Transfer Site']}→{r['Receive Site']}"
            for r in hd_violations[:5]
        )
    )


def _build_f2_hd_test_df():
    return pd.DataFrame([
        {
            'Article': '000000000002',
            'Article Description': 'F2 HD Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HD01',
            'SaSa Net Stock': 20,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 1,
            'Target': '',
        },
        {
            'Article': '000000000002',
            'Article Description': 'F2 HD Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 7,
            'Target': 5,
        },
        {
            'Article': '000000000002',
            'Article Description': 'F2 HD Test',
            'OM': 'Eva',
            'RP Type': 'RF',
            'Site': 'HB01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 4,
            'MOQ': 1,
            'Last Month Sold Qty': 4,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 5,
            'Target': 3,
        },
    ])


def test_f2_default_hd_cannot_transfer():
    df = _build_f2_hd_test_df()
    logic = TransferLogic(f2_allow_hd_transfer=False)
    recommendations = logic.generate_transfer_recommendations(df, "F指定模式")

    hd_violations = [
        r for r in recommendations
        if r['Transfer Site'].upper().startswith('HD')
        and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))
    ]
    assert len(hd_violations) == 0, (
        f"F2 default: Found {len(hd_violations)} HD→HA/HB/HC violations"
    )


def test_f2_allow_hd_transfer_can_transfer():
    df = _build_f2_hd_test_df()
    logic = TransferLogic(f2_allow_hd_transfer=True)
    recommendations = logic.generate_transfer_recommendations(df, "F指定模式")

    hd_transfers = [
        r for r in recommendations
        if r['Transfer Site'].upper().startswith('HD')
        and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))
    ]
    assert len(hd_transfers) > 0, (
        "F2 with f2_allow_hd_transfer=True should allow HD→HA/HB/HC transfers when other sources insufficient"
    )


def test_f2_allow_hd_transfer_lowest_priority():
    df = pd.DataFrame([
        {
            'Article': '000000000003',
            'Article Description': 'F2 HD Priority Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HD01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 1,
            'Target': '',
        },
        {
            'Article': '000000000003',
            'Article Description': 'F2 HD Priority Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
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
            'Article': '000000000003',
            'Article Description': 'F2 HD Priority Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF02',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 6,
            'MTD Sold Qty': 4,
            'Effective Sold Qty': 10,
            'Target': '',
        },
        {
            'Article': '000000000003',
            'Article Description': 'F2 HD Priority Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'MOQ': 1,
            'Last Month Sold Qty': 5,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 7,
            'Target': 8,
        },
    ])
    logic = TransferLogic(f2_allow_hd_transfer=True)
    recommendations = logic.generate_transfer_recommendations(df, "F指定模式")

    ha01_transfers = [r for r in recommendations if r['Receive Site'] == 'HA01']
    assert len(ha01_transfers) > 0, "HA01 should receive stock"

    non_hd_transfers = [
        r for r in ha01_transfers
        if not r['Transfer Site'].upper().startswith('HD')
    ]
    hd_transfers = [
        r for r in ha01_transfers
        if r['Transfer Site'].upper().startswith('HD')
    ]

    assert len(non_hd_transfers) > 0, "RF01 should be used before HD01"
    assert len(hd_transfers) > 0, "HD01 should be used when RF01 is insufficient"

    non_hd_qty = sum(r['Transfer Qty'] for r in non_hd_transfers)
    assert non_hd_qty == 2, f"RF01 should transfer all 2 units, got {non_hd_qty}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
