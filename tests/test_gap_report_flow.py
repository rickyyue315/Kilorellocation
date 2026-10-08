# -*- coding: utf-8 -*-
"""
維運驗證：調貨缺口分析相關修正（真實 generate → gap report → Target達成 / 品質檢查 全流程）

涵蓋：
1. F 模式：「Target達成分析」不再把系統自動「重點補0」目標當成使用者 Target，
   與「調貨缺口分析」結論一致（{target}-{received} vs {needed}-{received}）。
2. A1 後處理「消除餘 1 件」不得超出來源可轉量（不跌破安全庫存）。
3. E 模式：目的地數值欄為「不適用」，不會顯示 0／100% 假象。
4. D 模式：目的地的真實未滿足需求如實顯示。
"""

import pandas as pd
from business_logic import TransferLogic
from services.statistics import TARGET_DEST_TYPES, compute_target_fulfillment_stats


def _row(site, stock, safety, eff, last=0, mtd=0, target='', rp='RF', om='Ivy',
         all_flag='', pending=0, article='000000000001'):
    return {
        'Article': article, 'Article Description': 'Flow Test', 'OM': om,
        'RP Type': rp, 'Site': site, 'SaSa Net Stock': stock,
        'Pending Received': pending, 'Safety Stock': safety, 'MOQ': 1,
        'Last Month Sold Qty': last, 'MTD Sold Qty': mtd,
        'Effective Sold Qty': eff, 'Target': target, 'ALL': all_flag,
    }


def _gap_row(gap_report, site):
    rows = [d for d in gap_report['details'] if d['site'] == site]
    assert rows, f"gap report 缺少 {site}"
    return rows[0]


class TestTargetFulfillmentConsistency:

    def test_auto_zero_refill_not_treated_as_user_target(self):
        """F 模式：自動重點補0目標（需求2、實收2）不應在 Target達成分析顯示缺口。"""
        df = pd.DataFrame([
            _row('RF01', 10, 3, 1, last=1),
            _row('RF02', 1, 2, 7, last=4, mtd=3),
            _row('HA01', 0, 5, 7, last=5, mtd=2, target=5),
        ])
        logic = TransferLogic()
        recs = logic.generate_transfer_recommendations(df, '目標優化')
        assert recs, "F 模式應生成建議"

        # 缺口分析：RF02 需求 2、實收 2 → 已滿足
        gap = logic.get_gap_report()
        rf02 = _gap_row(gap, 'RF02')
        assert rf02['original_need_or_surplus'] == 2
        assert rf02['actual_qty'] == 2
        assert rf02['gap_or_remaining'] == 0

        # Target達成分析（過濾使用者目標）：不含 RF02 自動補0目標
        filtered = compute_target_fulfillment_stats(
            recs, df, target_dest_types=TARGET_DEST_TYPES
        )
        filtered_sites = {d['receive_site'] for d in filtered['details']}
        assert 'RF02' not in filtered_sites
        assert 'HA01' in filtered_sites
        assert filtered['total_gap'] == 0  # HA01 目標 5、實收 5

        # 未過濾（舊行為）仍會計入 RF02 並產生與缺口分析矛盾的缺口 1
        unfiltered = compute_target_fulfillment_stats(recs, df)
        unfiltered_sites = {d['receive_site'] for d in unfiltered['details']}
        assert 'RF02' in unfiltered_sites
        assert unfiltered['total_gap'] == 1


class TestSourceTransferCapGuard:

    def test_a1_postprocess_boost_respects_transferable_cap(self):
        """A1：後處理 +1 不得令來源超出可轉量、跌破安全庫存。"""
        df = pd.DataFrame([
            _row('RF01', 3, 1, 1, last=1),
            _row('XX01', 1, 2, 5, last=3, mtd=2),
            _row('YY01', 1, 2, 5, last=1, mtd=1),
        ])
        mode = '保守轉貨(轉出店舖不餘存貨1件)'
        logic = TransferLogic()
        recs = logic.generate_transfer_recommendations(df, mode)

        total_out = sum(r['Transfer Qty'] for r in recs if r['Transfer Site'] == 'RF01')
        gap = logic.get_gap_report()
        rf01 = _gap_row(gap, 'RF01')

        # 可轉量 = total_available(3) - safety(1) = 2（20% 上限 max(0.6,2)=2）
        assert rf01['original_need_or_surplus'] == 2
        assert total_out <= 2, f"來源轉出 {total_out} 超出可轉量 2"
        assert rf01['after_transfer_stock'] >= 1, "轉出後不應跌破安全庫存 1"
        assert rf01['over_transferred_qty'] == 0
        assert gap['summary']['total_over_transferred_qty'] == 0
        assert gap['summary']['source_transfer_rate'] <= 100.0

        passed = logic.perform_quality_checks(df, mode)
        assert passed, f"品質檢查不應失敗: {logic.quality_errors}"


class TestModeDisplayValueSemantics:

    def test_e_mode_dest_not_applicable_values(self):
        """E 模式：目的地缺口值為 None、狀態標示不適用、不計入分母。"""
        df = pd.DataFrame([
            _row('RF01', 10, 3, 1, last=1, all_flag='Y'),
            _row('RF02', 0, 3, 5, last=3, mtd=2),
        ])
        logic = TransferLogic()
        logic.generate_transfer_recommendations(df, '強制轉出')
        gap = logic.get_gap_report()

        rf02 = _gap_row(gap, 'RF02')
        assert rf02['role'] == '目的地'
        assert rf02['gap_or_remaining'] is None
        assert rf02['gap_pct'] is None
        assert rf02['status'] == '不適用(強制調撥)'
        assert gap['summary']['total_dest_count'] == 0
        # 來源轉出率仍照常計算（10 可轉、實轉 6）
        assert gap['summary']['source_transfer_rate'] == 60.0

    def test_d_mode_partial_dest_shows_real_gap(self):
        """D 模式：目的地未滿足需求如實顯示（缺口 > 0）。"""
        df = pd.DataFrame([
            _row('ND01', 10, 0, 0, last=0, mtd=0, rp='ND'),
            _row('RF02', 0, 2, 5, last=3, mtd=2),
        ])
        logic = TransferLogic()
        recs = logic.generate_transfer_recommendations(df, '清貨轉貨')

        total_in = sum(r['Transfer Qty'] for r in recs if r['Receive Site'] == 'RF02')
        gap = logic.get_gap_report()
        rf02 = _gap_row(gap, 'RF02')

        assert rf02['role'] == '目的地'
        assert rf02['original_need_or_surplus'] == 2   # 緊急缺貨補貨：max(safety,2)-0
        assert rf02['actual_qty'] == total_in
        expected_gap = 2 - total_in
        assert rf02['gap_or_remaining'] == expected_gap
        assert gap['summary']['total_dest_gaps'] == (1 if expected_gap > 0 else 0)
