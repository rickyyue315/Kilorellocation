"""
F3 模式（目標性補0）專屬測試
"""

import pytest
import pandas as pd
from business_logic import TransferLogic


def _build_f3_rf_retain_df():
    return pd.DataFrame([
        {
            'Article': '000000000001',
            'Article Description': 'F3 Retain Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Target': '',
        },
        {
            'Article': '000000000001',
            'Article Description': 'F3 Retain Test',
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
    ])


@pytest.mark.parametrize("mode_name,mode_param", [
    ("F指定模式", "F指定模式"),
    ("目標性補0", "目標性補0"),
])
def test_f2_f3_target_only_reception(mode_name, mode_param):
    df = _build_f3_rf_retain_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, mode_param)
    target_recv = [r for r in recommendations if r['Receive Site'] == 'HA01']
    assert len(target_recv) > 0, f"{mode_name}: HA01 should receive"


def test_f3_rf_retain_2_units():
    df = _build_f3_rf_retain_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    rf01_transfers = [r for r in recommendations if r['Transfer Site'] == 'RF01']
    rf01_total = sum(r['Transfer Qty'] for r in rf01_transfers)

    assert rf01_total <= 8, (
        f"F3 RF01 should transfer at most 8 units (10-2), got {rf01_total}"
    )


def test_f3_rf_retain_2_units_f2_comparison():
    df = pd.DataFrame([
        {
            'Article': '000000000010',
            'Article Description': 'F3 Retain Comparison',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Target': '',
        },
        {
            'Article': '000000000010',
            'Article Description': 'F3 Retain Comparison',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 20,
            'MOQ': 1,
            'Last Month Sold Qty': 20,
            'MTD Sold Qty': 10,
            'Effective Sold Qty': 30,
            'Target': 15,
        },
    ])

    f2_logic = TransferLogic()
    f2_recs = f2_logic.generate_transfer_recommendations(df, "F指定模式")
    rf01_f2 = sum(r['Transfer Qty'] for r in f2_recs if r['Transfer Site'] == 'RF01')

    f3_logic = TransferLogic()
    f3_recs = f3_logic.generate_transfer_recommendations(df, "目標性補0")
    rf01_f3 = sum(r['Transfer Qty'] for r in f3_recs if r['Transfer Site'] == 'RF01')

    assert rf01_f2 == 10, f"F2 RF01 should transfer all 10 units, got {rf01_f2}"
    assert rf01_f3 == 8, f"F3 RF01 should transfer max 8 units (10-2), got {rf01_f3}"
    assert rf01_f2 > rf01_f3, (
        f"F3 RF01 should transfer less than F2 (F2={rf01_f2}, F3={rf01_f3})"
    )


def _build_f3_rf_stock_le_2_df():
    return pd.DataFrame([
        {
            'Article': '000000000002',
            'Article Description': 'F3 Low Stock Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 2,
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
            'Article Description': 'F3 Low Stock Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF02',
            'SaSa Net Stock': 1,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 1,
            'Target': '',
        },
        {
            'Article': '000000000002',
            'Article Description': 'F3 Low Stock Test',
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
    ])


def test_f3_rf_stock_le_2_does_not_transfer():
    df = _build_f3_rf_stock_le_2_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")
    rf_sources = [r for r in recommendations if r['Transfer Site'] in ('RF01', 'RF02')]
    assert len(rf_sources) == 0, (
        f"F3 RF01(net=2) and RF02(net=1) should not transfer, got {len(rf_sources)} transfers"
    )


def _build_f3_cross_om_no_penalty_df():
    return pd.DataFrame([
        {
            'Article': '000000000003',
            'Article Description': 'F3 Cross OM Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'IV01',
            'SaSa Net Stock': 10,
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
            'Article Description': 'F3 Cross OM Test',
            'OM': 'Violet',
            'RP Type': 'RF',
            'Site': 'VI01',
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
            'Article Description': 'F3 Cross OM Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 10,
            'MOQ': 1,
            'Last Month Sold Qty': 10,
            'MTD Sold Qty': 5,
            'Effective Sold Qty': 15,
            'Target': 15,
        },
    ])


def test_f3_cross_om_rf_equal_tier():
    df = _build_f3_cross_om_no_penalty_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    ha01_transfers = [r for r in recommendations if r['Receive Site'] == 'HA01']
    iv_cross_om = [r for r in ha01_transfers if r['Transfer Site'] == 'VI01']
    iv_same_om = [r for r in ha01_transfers if r['Transfer Site'] == 'IV01']

    assert len(iv_same_om) > 0, "Same-OM RF (IV01) should be used"
    assert len(iv_cross_om) > 0, (
        "F3: Cross-OM RF (VI01) should be used (no cross-OM penalty)"
    )


def test_f2_cross_om_rf_not_used_first():
    df = _build_f3_cross_om_no_penalty_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "F指定模式")

    ha01_transfers = [r for r in recommendations if r['Receive Site'] == 'HA01']
    iv_same_om = [r for r in ha01_transfers if r['Transfer Site'] == 'IV01']

    iv01_total = sum(r['Transfer Qty'] for r in iv_same_om)
    assert iv01_total == 10, (
        f"F2: Same-OM RF01 should be fully used first (transfer all 10 units), got {iv01_total}"
    )


def _build_f3_hd_test_df():
    return pd.DataFrame([
        {
            'Article': '000000000004',
            'Article Description': 'F3 HD Test',
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
            'Article': '000000000004',
            'Article Description': 'F3 HD Test',
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
    ])


def test_f3_default_hd_cannot_transfer():
    df = _build_f3_hd_test_df()
    logic = TransferLogic(f2_allow_hd_transfer=False)
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    hd_violations = [
        r for r in recommendations
        if r['Transfer Site'].upper().startswith('HD')
        and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))
    ]
    assert len(hd_violations) == 0, (
        f"F3 default: Found {len(hd_violations)} HD→HA/HB/HC violations"
    )


def test_f3_allow_hd_transfer_can_transfer():
    df = _build_f3_hd_test_df()
    logic = TransferLogic(f2_allow_hd_transfer=True)
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    hd_transfers = [
        r for r in recommendations
        if r['Transfer Site'].upper().startswith('HD')
        and r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))
    ]
    assert len(hd_transfers) > 0, (
        "F3 with f2_allow_hd_transfer=True should allow HD→HA/HB/HC transfers"
    )


def _build_f3_nd_full_transfer_df():
    return pd.DataFrame([
        {
            'Article': '000000000005',
            'Article Description': 'F3 ND Test',
            'OM': 'Ivy',
            'RP Type': 'ND',
            'Site': 'ND01',
            'SaSa Net Stock': 6,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 0,
            'Target': '',
        },
        {
            'Article': '000000000005',
            'Article Description': 'F3 ND Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 8,
            'MOQ': 1,
            'Last Month Sold Qty': 8,
            'MTD Sold Qty': 4,
            'Effective Sold Qty': 12,
            'Target': 5,
        },
    ])


def test_f3_nd_full_transfer():
    df = _build_f3_nd_full_transfer_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    nd01_transfers = [r for r in recommendations if r['Transfer Site'] == 'ND01']
    nd01_total = sum(r['Transfer Qty'] for r in nd01_transfers)
    assert nd01_total == 5, (
        f"F3 ND01 should transfer all 5 units (limited by HA01 need), got {nd01_total}"
    )


def _build_f3_target_protected_df():
    return pd.DataFrame([
        {
            'Article': '000000000006',
            'Article Description': 'F3 Target Protected Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'Effective Sold Qty': 3,
            'Target': 5,
        },
        {
            'Article': '000000000006',
            'Article Description': 'F3 Target Protected Test',
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
            'Target': '',
        },
    ])


def test_f3_target_protected():
    df = _build_f3_target_protected_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    rf01_as_source = [r for r in recommendations if r['Transfer Site'] == 'RF01']
    assert len(rf01_as_source) == 0, (
        "F3 RF01 has Target>0 and should be protected from being a source"
    )


def _build_f3_rf_sort_priority_df():
    return pd.DataFrame([
        {
            'Article': '000000000007',
            'Article Description': 'F3 Sort Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF01',
            'SaSa Net Stock': 5,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 4,
            'MTD Sold Qty': 2,
            'Effective Sold Qty': 6,
            'Target': '',
        },
        {
            'Article': '000000000007',
            'Article Description': 'F3 Sort Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'RF02',
            'SaSa Net Stock': 8,
            'Pending Received': 0,
            'Safety Stock': 3,
            'MOQ': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'Effective Sold Qty': 1,
            'Target': '',
        },
        {
            'Article': '000000000007',
            'Article Description': 'F3 Sort Test',
            'OM': 'Ivy',
            'RP Type': 'RF',
            'Site': 'HA01',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 15,
            'MOQ': 1,
            'Last Month Sold Qty': 15,
            'MTD Sold Qty': 5,
            'Effective Sold Qty': 20,
            'Target': 12,
        },
    ])


def test_f3_rf_highest_stock_priority():
    df = _build_f3_rf_sort_priority_df()
    logic = TransferLogic()
    recommendations = logic.generate_transfer_recommendations(df, "目標性補0")

    ha01_transfers = [r for r in recommendations if r['Receive Site'] == 'HA01']
    rf02_first = any(
        r for r in ha01_transfers
        if r['Transfer Site'] == 'RF02'
    )
    rf01_first = any(
        r for r in ha01_transfers
        if r['Transfer Site'] == 'RF01'
    )
    assert rf02_first, (
        "F3: Higher stock RF02(8) should be used before RF01(5)"
    )


def test_f3_mode_registered():
    from models.mode_registry import get_mode_def_by_code
    f3_def = get_mode_def_by_code("F3")
    assert f3_def is not None, "F3 should be registered in MODE_DEFS"
    assert f3_def.name == "目標性補0", f"F3 name should be 目標性補0, got {f3_def.name}"
    assert f3_def.strategy_key == 'f_mode', "F3 should use f_mode strategy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
