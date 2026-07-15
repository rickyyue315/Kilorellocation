"""
ND1/ND2 模式單元測試
測試 ND 店舖互轉功能、銷量排序邏輯、接收上限等核心規則
"""

import pandas as pd
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic


def make_df(rows):
    """建立測試用 DataFrame"""
    df = pd.DataFrame(rows)
    # 補齊必要欄位
    for col in ['Pending Received', 'Safety Stock', 'MOQ']:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = df[col].fillna(0).astype(int)
    if 'Effective Sold Qty' not in df.columns:
        df['Effective Sold Qty'] = 0
    if 'Article Description' not in df.columns:
        df['Article Description'] = 'Test Product'
    if 'ALL' not in df.columns:
        df['ALL'] = ''
    if 'Target' not in df.columns:
        df['Target'] = ''
    if 'Type' not in df.columns:
        df['Type'] = ''
    # 計算 Effective Sold Qty (上月 + MTD)
    df['Effective Sold Qty'] = (
        df['Last Month Sold Qty'].fillna(0).astype(int)
        + df['MTD Sold Qty'].fillna(0).astype(int)
    )
    return df


def make_nd_limit_df(cross_om: bool = False):
    """建立測試 ND 接收店數限制用 DataFrame"""
    rows = [
        {
            'Article': '000000009999',
            'OM': 'Ivy',
            'Site': 'ND_SRC',
            'RP Type': 'ND',
            'SaSa Net Stock': 20,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
        }
    ]

    destination_oms = ['Ivy', 'Ivy', 'Ivy', 'Ivy'] if not cross_om else ['Ivy', 'Hippo', 'Violet', 'Eva']
    destination_sites = ['RF01', 'RF02', 'RF03', 'RF04']

    for site, om in zip(destination_sites, destination_oms):
        rows.append({
            'Article': '000000009999',
            'OM': om,
            'Site': site,
            'RP Type': 'RF',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 3,
            'Last Month Sold Qty': 2,
            'MTD Sold Qty': 1,
            'MOQ': 1,
        })

    return make_df(rows)


def assert_source_receive_site_limit(recommendations, max_sites):
    source_to_receive_sites = {}

    for rec in recommendations:
        source = rec['Transfer Site']
        source_to_receive_sites.setdefault(source, set()).add(rec['Receive Site'])

    for source, receive_sites in source_to_receive_sites.items():
        assert len(receive_sites) <= max_sites, (
            f"Source {source} matched to {len(receive_sites)} receive sites, exceeds limit {max_sites}."
        )


# =============================================
# ND1 模式測試
# =============================================

class TestND1Mode:
    """ND1 模式：ND 同 OM 互轉"""

    def _logic(self):
        return TransferLogic()

    def test_nd_can_receive_in_nd1(self):
        """ND1 模式下 ND 店舖可以接收"""
        logic = self._logic()
        df = make_df([
            # 轉出源：ND 店舖，0銷量
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 接收方：ND 店舖，有銷量（可接收）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        assert len(recs) > 0, "ND1 模式下 ND 店舖應可互相調貨"
        assert recs[0]['Transfer Site'] == 'ND01'
        assert recs[0]['Receive Site'] == 'ND02'

    def test_zero_sales_nd_transfers_first(self):
        """0銷量 ND 店舖優先轉出"""
        logic = self._logic()
        df = make_df([
            # ND01: 0銷量（最優先轉出）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 5, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # ND02: 有銷量（次選轉出）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 8, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 3},
            # ND03: 接收方（高銷量）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND03', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 10, 'MTD Sold Qty': 8},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        assert len(recs) > 0
        # 第一筆應來自 ND01（0銷量）
        transfer_sites = [r['Transfer Site'] for r in recs]
        assert 'ND01' in transfer_sites, "0銷量店舖應優先轉出"

    def test_receive_cap_2x_two_month_sales(self):
        """接收量不超過 2×過去2個月銷量"""
        logic = self._logic()
        df = make_df([
            # 轉出源：ND 店舖，0銷量，大量庫存
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 50, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 接收方：過去2個月銷量 = 3，接收上限 = 6
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        if recs:
            total_received = sum(r['Transfer Qty'] for r in recs if r['Receive Site'] == 'ND02')
            assert total_received <= 6, f"接收量 {total_received} 不應超過 2×(2+1)=6"

    def test_zero_sales_nd_cannot_receive(self):
        """過去2個月銷量=0 的 ND 店舖不可接收"""
        logic = self._logic()
        df = make_df([
            # 轉出源
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 0銷量接收方（不應接收）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 5, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        # ND02（0銷量）不應作為接收方
        for r in recs:
            assert r['Receive Site'] != 'ND02', "0銷量 ND 店舖不應作為接收方"

    def test_same_om_restriction(self):
        """ND1 模式僅同 OM 配對"""
        logic = self._logic()
        df = make_df([
            # Ivy OM 的轉出 ND 店舖
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 不同 OM (Hippo) 的 ND 接收店舖
            {'Article': '000000000001', 'OM': 'Hippo', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 3},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        # 不同 OM，不應有配對
        assert len(recs) == 0, "ND1 不允許跨 OM 配對"

    def test_rf_emergency_has_priority_over_nd(self):
        """RF 緊急缺貨比 ND 潛在缺貨優先接收"""
        logic = self._logic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 5, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # RF 緊急缺貨（0庫存有銷售）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'RF01', 'RP Type': 'RF',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 3,
             'Safety Stock': 3},
            # ND 潛在缺貨
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        if recs:
            # 第一筆應是轉給 RF01（緊急缺貨）
            assert recs[0]['Receive Site'] == 'RF01', "RF 緊急缺貨應優先接收"

    def test_source_cannot_be_destination(self):
        """轉出店舖不可同時作為接收店舖"""
        logic = self._logic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        transfer_sites = {r['Transfer Site'] for r in recs}
        receive_sites = {r['Receive Site'] for r in recs}
        overlap = transfer_sites & receive_sites
        assert len(overlap) == 0, f"轉出店不可同時是接收店: {overlap}"

    def test_quality_check_allows_nd_receive_in_nd1(self):
        """quality check 在 ND1 模式下允許 ND 接收"""
        logic = self._logic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        if recs:
            passed = logic.perform_quality_checks(df, logic.mode_nd1)
            assert passed, f"ND1 模式質量檢查應通過: {logic.quality_errors}"

    def test_nd1_source_receive_site_limit_max_one(self):
        """ND1 模式可限制單一 source 最多只配對 1 間接收店"""
        logic = TransferLogic(b_special_max_receive_sites_per_source=1)
        df = make_nd_limit_df(cross_om=False)

        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)

        assert_source_receive_site_limit(recs, max_sites=1)

    def test_nd1_source_receive_site_limit_unlimited_can_exceed_two(self):
        """ND1 模式未限制時，單一 source 可配對超過 2 間接收店"""
        logic = TransferLogic(b_special_max_receive_sites_per_source=None)
        df = make_nd_limit_df(cross_om=False)

        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)

        source_to_receive_sites = {}
        for rec in recs:
            source = rec['Transfer Site']
            source_to_receive_sites.setdefault(source, set()).add(rec['Receive Site'])

        assert any(len(receive_sites) > 2 for receive_sites in source_to_receive_sites.values()), (
            "Unlimited mode should allow a source site to match more than 2 receive sites in ND1 mode."
        )


# =============================================
# ND2 模式測試
# =============================================

class TestND2Mode:
    """ND2 模式：ND 跨 OM 互轉"""

    def _logic(self):
        return TransferLogic()

    def test_cross_om_allowed_in_nd2(self):
        """ND2 允許跨 OM 配對"""
        logic = self._logic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            {'Article': '000000000001', 'OM': 'Hippo', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd2)
        assert len(recs) > 0, "ND2 模式應允許跨 OM 配對"

    def test_windy_restriction_in_nd2(self):
        """ND2 模式 Windy 來源只能轉到 Windy"""
        logic = self._logic()
        df = make_df([
            # Windy OM 的轉出 ND 店舖
            {'Article': '000000000001', 'OM': 'Windy', 'Site': 'HD01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 非 Windy OM 的接收店舖（不應被轉到）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
            # Windy OM 的接收店舖（可以被轉到）
            {'Article': '000000000001', 'OM': 'Windy', 'Site': 'HD02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 3},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd2)
        for r in recs:
            if r['Transfer Site'] == 'HD01':
                assert r['Receive OM'] == 'Windy', "Windy 轉出只能到 Windy"

    def test_nd2_does_not_affect_other_modes(self):
        """確認 ND2 模式不影響其他模式（ND 在 A 模式仍不可接收）"""
        logic = TransferLogic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND01', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND02', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2},
        ])
        logic_a = TransferLogic()
        recs_a = logic_a.generate_transfer_recommendations(df, logic_a.mode_a)
        # A 模式下 ND 不可接收（ND01/ND02 均無 RF 緊急缺貨目標）
        for r in recs_a:
            assert r['Receive Site'] not in ('ND01', 'ND02'), "A 模式下 ND 不可接收"

    def test_nd2_source_receive_site_limit_max_two(self):
        """ND2 模式可限制單一 source 最多只配對 2 間接收店"""
        logic = TransferLogic(b_special_max_receive_sites_per_source=2)
        df = make_nd_limit_df(cross_om=True)

        recs = logic.generate_transfer_recommendations(df, logic.mode_nd2)

        assert_source_receive_site_limit(recs, max_sites=2)


# =============================================
# 算法邏輯測試
# =============================================

class TestNDAlgorithmLogic:
    """調貨算法邏輯測試"""

    def test_highest_sales_nd_protected_from_transfer(self):
        """最高銷量 ND 店舖不可轉出"""
        logic = TransferLogic()
        df = make_df([
            # 最高銷量 ND（應被保護）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_HIGH', 'RP Type': 'ND',
             'SaSa Net Stock': 15, 'Last Month Sold Qty': 20, 'MTD Sold Qty': 15},
            # 0銷量 ND（應轉出）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_ZERO', 'RP Type': 'ND',
             'SaSa Net Stock': 8, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 接收方
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_RECV', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 3},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        for r in recs:
            assert r['Transfer Site'] != 'ND_HIGH', "最高銷量 ND 店舖不應轉出"

    def test_high_sales_nd_receives_first(self):
        """高銷量 ND 店舖優先接收"""
        logic = TransferLogic()
        df = make_df([
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_SRC', 'RP Type': 'ND',
             'SaSa Net Stock': 10, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0},
            # 高銷量 ND（優先接收）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_HIGH', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 10, 'MTD Sold Qty': 8},
            # 低銷量 ND（次序接收）
            {'Article': '000000000001', 'OM': 'Ivy', 'Site': 'ND_LOW', 'RP Type': 'ND',
             'SaSa Net Stock': 0, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1},
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_nd1)
        if recs:
            # 高銷量應先被接收
            first_receiver = recs[0]['Receive Site']
            assert first_receiver == 'ND_HIGH', f"高銷量 ND 應優先接收，但第一筆接收是 {first_receiver}"

    def test_nd1_nd2_mode_constants(self):
        """驗證模式常數設定正確"""
        logic = TransferLogic()
        assert logic.mode_nd1 == "ND同OM轉貨"
        assert logic.mode_nd2 == "ND混合OM轉貨"
        assert logic._is_nd_transfer_mode(logic.mode_nd1)
        assert logic._is_nd_transfer_mode(logic.mode_nd2)
        assert not logic._is_nd_transfer_mode(logic.mode_a)
        assert not logic._is_nd_transfer_mode(logic.mode_d)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
