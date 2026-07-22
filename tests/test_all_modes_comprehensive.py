# -*- coding: utf-8 -*-
"""
全面測試所有模式的邏輯正確性

針對每個模式檢查：
  1. 通用規則（ND只能轉出、最高動銷店保護、禁止雙重角色、Article格式）
  2. 各模式特定的轉出/接收條件與上限
  3. 跨OM/HD/Windy限制
  4. D模式避免1件餘貨
  5. E模式ALL標記與Phase 3回退
  6. B2系列Type=L全轉出、Mix高銷量保護、接收優先級
    7. F模式Target優先
    8. F2模式僅Target接收
  8. 質量檢查全通過
"""

import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Set

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic

# ---------------------------------------------------------------------------
# Helper: 建構 DataFrame 的共用工具
# ---------------------------------------------------------------------------

def _make_row(**overrides) -> Dict[str, Any]:
    """產生一筆預設的 store 記錄，可用 overrides 覆寫任何欄位。"""
    defaults: Dict[str, Any] = {
        'Article': '000000000001',
        'Article Description': 'Test Product',
        'OM': 'OM1',
        'Site': 'SITE01',
        'RP Type': 'RF',
        'SaSa Net Stock': 10,
        'Pending Received': 0,
        'Safety Stock': 3,
        'Last Month Sold Qty': 2,
        'MTD Sold Qty': 1,
        'Last 2 Month Sold Qty': 2,
        'MOQ': 1,
        'Effective Sold Qty': 3,
        'Type': 'R',
    }
    defaults.update(overrides)
    return defaults


def _df(rows: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 通用斷言
# ---------------------------------------------------------------------------

def assert_no_dual_role(recs: List[Dict], label: str = ""):
    """同一SKU下轉出店不可同時為接收店"""
    by_article_src: Dict[str, Set[str]] = defaultdict(set)
    by_article_dst: Dict[str, Set[str]] = defaultdict(set)
    for r in recs:
        by_article_src[r['Article']].add(r['Transfer Site'])
        by_article_dst[r['Article']].add(r['Receive Site'])
    for art in by_article_src:
        overlap = by_article_src[art] & by_article_dst.get(art, set())
        assert not overlap, f"{label} Article {art} dual-role: {overlap}"


def assert_nd_never_receives(recs: List[Dict], df: pd.DataFrame, label: str = ""):
    """ND店鋪永遠不能做接收"""
    nd_sites = set(df.loc[df['RP Type'] == 'ND', 'Site'])
    for r in recs:
        assert r['Receive Site'] not in nd_sites, (
            f"{label} ND site {r['Receive Site']} received Article {r['Article']}")


def assert_transfer_qty_positive(recs: List[Dict], label: str = ""):
    for r in recs:
        assert r['Transfer Qty'] > 0, f"{label} Transfer Qty <= 0: {r}"


def assert_no_self_transfer(recs: List[Dict], label: str = ""):
    for r in recs:
        assert r['Transfer Site'] != r['Receive Site'], (
            f"{label} self-transfer: {r['Transfer Site']}")


def assert_cumulative_not_exceeds_stock(recs: List[Dict], df: pd.DataFrame, label: str = ""):
    """累計轉出量不得超過原始 SaSa Net Stock"""
    cum: Dict = defaultdict(int)
    for r in recs:
        cum[(r['Article'], r['Transfer Site'])] += r['Transfer Qty']
    indexed = df.set_index(['Article', 'Site'])
    for (art, site), total in cum.items():
        if (art, site) in indexed.index:
            stock = int(indexed.at[(art, site), 'SaSa Net Stock'])
            assert total <= stock, (
                f"{label} cumulative {total} > stock {stock} for {art}/{site}")


def assert_quality_check_passes(logic: TransferLogic, df: pd.DataFrame, label: str = ""):
    passed = logic.perform_quality_checks(df)
    assert passed, f"{label} quality check failed: {logic.quality_errors}"


def run_common_assertions(recs, df, logic, label):
    assert_no_dual_role(recs, label)
    assert_nd_never_receives(recs, df, label)
    assert_transfer_qty_positive(recs, label)
    assert_no_self_transfer(recs, label)
    assert_cumulative_not_exceeds_stock(recs, df, label)
    assert_quality_check_passes(logic, df, label)


# ===========================================================================
# 模式 A：保守轉貨
# ===========================================================================

class TestModeA:

    def _base_df(self):
        """ND轉出 + RF過剩轉出場景"""
        return _df([
            _make_row(Site='ND01', **{'RP Type': 'ND'}, **{'SaSa Net Stock': 6, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Safety Stock': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 20, 'Pending Received': 0,
                       'Safety Stock': 5, 'Effective Sold Qty': 2}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Pending Received': 0,
                       'Safety Stock': 5, 'Effective Sold Qty': 10,
                       'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        ])

    def test_basic_transfer(self):
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        assert len(recs) > 0, "A模式應產生建議"
        run_common_assertions(recs, df, logic, "A模式")

    def test_rf_remaining_above_safety(self):
        """A模式：RF轉出後庫存仍 >= Safety Stock"""
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        for r in recs:
            if r['Source Type'] == 'RF過剩轉出':
                assert r['After Transfer Stock'] >= r['Safety Stock'], (
                    f"A模式 RF轉出後庫存({r['After Transfer Stock']}) < Safety({r['Safety Stock']})")

    def test_transfer_upper_limit_20pct(self):
        """A模式：RF轉出上限為 20% total_available (至少2件)"""
        logic = TransferLogic()
        # 特殊場景：大庫存、大 safety stock 差距
        df = _df([
            _make_row(Site='RF_BIG', **{'SaSa Net Stock': 100, 'Pending Received': 0,
                       'Safety Stock': 10, 'Effective Sold Qty': 1}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Pending Received': 0,
                       'Safety Stock': 50, 'Effective Sold Qty': 20,
                       'Last Month Sold Qty': 10, 'MTD Sold Qty': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        for r in recs:
            if r['Source Type'] == 'RF過剩轉出':
                total_avail = 100  # SaSa Net Stock + Pending Received
                upper = max(int(total_avail * 0.2), 2)
                assert r['Transfer Qty'] <= upper, (
                    f"A模式 transfer qty {r['Transfer Qty']} > upper {upper}")

    def test_highest_sold_protected(self):
        """A模式下最高動銷RF店不應作為轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_HIGH', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
            _make_row(Site='RF_LOW', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        src_sites = {r['Transfer Site'] for r in recs}
        assert 'RF_HIGH' not in src_sites, "A模式最高動銷店不應轉出"


# ===========================================================================
# 模式 A1：保守轉貨(轉出店舖不餘存貨1件)
# ===========================================================================

class TestModeA1:

    def test_basic_transfer(self):
        """A1模式基本流程"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 6,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 2}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 10, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a1)
        assert len(recs) > 0, "A1模式應產生建議"
        run_common_assertions(recs, df, logic, "A1模式")

    def test_avoids_one_remainder_nd_source(self):
        """A1模式：ND源店轉出後不應剩1件（多1件給接收或保留2件）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HC62', **{'RP Type': 'ND', 'SaSa Net Stock': 7,
                       'Safety Stock': 2, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='HB24', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a1)
        assert len(recs) > 0, "A1模式應產生建議"
        run_common_assertions(recs, df, logic, "A1-NDremainder")

        cum: Dict = defaultdict(int)
        for r in recs:
            cum[(r['Article'], r['Transfer Site'])] += r['Transfer Qty']
        for (art, site), total in cum.items():
            orig = int(recs[0]['Original Stock']) if all(r['Transfer Site'] == site for r in recs if r['Transfer Site'] == site) else 0
            for r in recs:
                if r['Transfer Site'] == site:
                    orig = r['Original Stock']
                    break
            remaining = orig - total
            assert remaining != 1, f"A1模式下 {site} 不應剩1件（剩{remaining}）"

    def test_nd_shop_no_force_zero(self):
        """A1模式：ND Shop不強制至0（若接收無法+1則保留2件）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HC62', **{'RP Type': 'ND', 'SaSa Net Stock': 7,
                       'Safety Stock': 2, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='HB24', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a1)
        assert len(recs) > 0
        run_common_assertions(recs, df, logic, "A1-noForceZero")
        cum: Dict = defaultdict(int)
        for r in recs:
            cum[(r['Article'], r['Transfer Site'])] += r['Transfer Qty']
        for (art, site), total in cum.items():
            for r in recs:
                if r['Transfer Site'] == site:
                    remaining = r['Original Stock'] - total
                    if remaining == 1:
                        # If remaining is 1, check if the receiving site has target_qty and couldn't accept +1
                        for rec in recs:
                            if rec['Transfer Site'] == site:
                                target_qty = rec.get('Target Qty', 0)
                                cumul = total
                                if target_qty and cumul >= target_qty + 1:
                                    pytest.fail(f"{site} 剩1件但接收已超target+1")
                    break

    def test_rf_transfer_no_one_remainder(self):
        """A1模式：RF源店轉出後不應剩1件"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', **{'SaSa Net Stock': 12, 'Safety Stock': 3,
                       'Effective Sold Qty': 2, 'Last Month Sold Qty': 1, 'MTD Sold Qty': 1}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Safety Stock': 8,
                       'Effective Sold Qty': 10, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a1)
        run_common_assertions(recs, df, logic, "A1-RF")
        cum: Dict = defaultdict(int)
        for r in recs:
            cum[(r['Article'], r['Transfer Site'])] += r['Transfer Qty']
        for (art, site), total in cum.items():
            for r in recs:
                if r['Transfer Site'] == site:
                    remaining = r['Original Stock'] - total
                    assert remaining != 1, f"A1模式下RF源店 {site} 不應剩1件（剩{remaining}）"
                    break

    def test_a1_same_as_a_sources(self):
        """A1模式使用與A相同的RF源店計算邏輯（20%上限、最低2件）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_BIG', **{'SaSa Net Stock': 100, 'Safety Stock': 10,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 50,
                       'Effective Sold Qty': 20, 'Last Month Sold Qty': 10, 'MTD Sold Qty': 10}),
        ])
        recs_a = logic.generate_transfer_recommendations(df, logic.mode_a)
        recs_a1 = logic.generate_transfer_recommendations(df, logic.mode_a1)
        assert len(recs_a1) > 0
        run_common_assertions(recs_a1, df, logic, "A1-20pct")
        for r in recs_a1:
            if r['Source Type'] == 'RF過剩轉出':
                upper = max(int(100 * 0.2), 2)
                assert r['Transfer Qty'] <= upper, (
                    f"A1模式 transfer qty {r['Transfer Qty']} > upper {upper}")

    def test_highest_sold_protected(self):
        """A1模式下最高動銷RF店不應作為轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_HIGH', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
            _make_row(Site='RF_LOW', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a1)
        src_sites = {r['Transfer Site'] for r in recs}
        assert 'RF_HIGH' not in src_sites, "A1模式最高動銷店不應轉出"


# ===========================================================================
# 模式 B：加強轉貨
# ===========================================================================

class TestModeB:

    def _base_df(self):
        return _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 2}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 10, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        ])

    def test_basic(self):
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b)
        assert len(recs) > 0
        run_common_assertions(recs, df, logic, "B模式")

    def test_allows_enhanced_transfer(self):
        """B模式允許RF加強轉出（庫存可低於Safety Stock）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', **{'SaSa Net Stock': 8, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 10, 'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b)
        source_types = {r['Source Type'] for r in recs}
        # B模式應產生加強轉出或過剩轉出
        assert source_types & {'RF過剩轉出', 'RF加強轉出'}, "B模式應產生RF轉出"

    def test_transfer_upper_limit_50pct(self):
        """B模式上限 50% total_available (至少2件)"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_BIG', **{'SaSa Net Stock': 100, 'Safety Stock': 10,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 80,
                       'Effective Sold Qty': 20, 'Last Month Sold Qty': 10, 'MTD Sold Qty': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b)
        for r in recs:
            if r['Source Type'] in ('RF過剩轉出', 'RF加強轉出'):
                total_avail = 100
                upper = max(int(total_avail * 0.5), 2)
                assert r['Transfer Qty'] <= upper, (
                    f"B模式 transfer qty {r['Transfer Qty']} > upper {upper}")


# ===========================================================================
# 模式 B2：附加B特別模式
# ===========================================================================

class TestModeB2:

    def _base_df(self):
        return _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='L_LOW_SALE', **{'SaSa Net Stock': 8, 'Safety Stock': 3,
                       'Effective Sold Qty': 1, 'Last Month Sold Qty': 1,
                       'MTD Sold Qty': 0, 'Type': 'L'}),
            _make_row(Site='DST_T', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])

    def test_basic(self):
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        assert len(recs) > 0
        run_common_assertions(recs, df, logic, "B2模式")

    def test_type_l_full_transfer(self):
        """B2模式：Type=L 且 max(LastMonth, MTD)<=2 全數轉出"""
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        l_recs = [r for r in recs if r['Transfer Site'] == 'L_LOW_SALE']
        if l_recs:
            total_transferred = sum(r['Transfer Qty'] for r in l_recs)
            # 應該全送或至少很大比例
            assert any(r['Source Type'] == 'Local店舖全轉出' for r in l_recs), \
                "B2 Type=L低銷量應為Local店舖全轉出"

    def test_type_l_high_sales_not_full(self):
        """B2模式：Type=L 但 max(LastMonth, MTD)>2 應走B模式RF規則"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='L_HIGH_SALE', **{'SaSa Net Stock': 15, 'Safety Stock': 3,
                       'Effective Sold Qty': 1, 'Last Month Sold Qty': 5,
                       'MTD Sold Qty': 3, 'Type': 'L'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 10, 'Last Month Sold Qty': 5,
                       'MTD Sold Qty': 5, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        for r in recs:
            if r['Transfer Site'] == 'L_HIGH_SALE':
                assert r['Source Type'] != 'Local店舖全轉出', \
                    "B2 Type=L高銷量不應全轉出"

    def test_receive_cap_safety_x2(self):
        """B2模式：接收上限為 Safety Stock x 2"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 30,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        cum = defaultdict(int)
        for r in recs:
            cum[r['Receive Site']] += r['Transfer Qty']
        for site, total in cum.items():
            # 接收上限 = max(safety*2, 3)
            assert total <= max(5 * 2, 3), f"B2接收超限: {site} 累計 {total}"

    def test_mix_sales_guard(self):
        """B2模式：Mix (Type=M) source 銷量高於 dest 時應被阻擋"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='MIX_SRC', **{'SaSa Net Stock': 10, 'Safety Stock': 1,
                       'Effective Sold Qty': 1, 'Last Month Sold Qty': 6,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
            _make_row(Site='LOW_DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 1,
                       'MTD Sold Qty': 1, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        assert all(r['Transfer Site'] != 'MIX_SRC' for r in recs), \
            "B2 Mix source高銷量應被阻擋"


# ===========================================================================
# 模式 B2a：Type=T不出貨
# ===========================================================================

class TestModeB2a:

    def test_tourist_type_blocked(self):
        """B2a：Type=T 店舖不能做轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='T_SRC', **{'SaSa Net Stock': 10, 'Safety Stock': 1,
                       'Effective Sold Qty': 1, 'Type': 'T'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special_a)
        assert all(r['Transfer Site'] != 'T_SRC' for r in recs), \
            "B2a Type=T不應作為轉出"

    def test_nd_type_t_also_blocked(self):
        """B2a：ND的Type=T也不能轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND_T', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Safety Stock': 0, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'T'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special_a)
        assert all(r['Transfer Site'] != 'ND_T' for r in recs), \
            "B2a ND Type=T也不應轉出"

    def test_common_rules(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special_a)
        run_common_assertions(recs, df, logic, "B2a模式")


# ===========================================================================
# 模式 B3：跨OM特別模式
# ===========================================================================

class TestModeB3:

    def test_cross_om_allowed(self):
        """B3模式允許跨OM"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='DST', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b3)
        assert len(recs) > 0, "B3應允許跨OM轉貨"
        assert recs[0]['Transfer OM'] != recs[0]['Receive OM'], "B3應有跨OM建議"

    def test_hd_cannot_to_ha_hb_hc(self):
        """B3模式：HD不能轉到HA/HB/HC"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HD01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='HA01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b3)
        hd_to_ha = [r for r in recs if r['Transfer Site'] == 'HD01' and
                     r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))]
        assert len(hd_to_ha) == 0, "B3 HD不應轉到HA/HB/HC"

    def test_windy_only_to_windy(self):
        """B3模式：Windy只轉到Windy"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND_W', OM='Windy', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='DST_W', OM='Windy', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
            _make_row(Site='DST_O', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b3)
        windy_src = [r for r in recs if r['Transfer OM'] == 'Windy']
        for r in windy_src:
            assert r['Receive OM'] == 'Windy', f"B3 Windy source只能到Windy, got {r['Receive OM']}"

    def test_common_rules(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='DST', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b3)
        run_common_assertions(recs, df, logic, "B3模式")


# ===========================================================================
# 模式 B3a：跨OM + T不出貨
# ===========================================================================

class TestModeB3a:

    def test_tourist_blocked(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='T_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Safety Stock': 1,
                       'Effective Sold Qty': 1, 'Type': 'T'}),
            _make_row(Site='DST', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b3a)
        assert all(r['Transfer Site'] != 'T_SRC' for r in recs), "B3a Type=T禁止轉出"


# ===========================================================================
# 模式 B2L/B2La/B3L/B3La：Type=L 保留2件系列
# ===========================================================================

class TestModeBLSeries:

    def test_b2l_type_l_low_sales_retain_two(self):
        """B2L：Type=L 且低銷量時，保留2件後轉出。"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='L_SRC', **{'SaSa Net Stock': 8, 'Safety Stock': 1,
                       'Last Month Sold Qty': 1, 'MTD Sold Qty': 0,
                       'Effective Sold Qty': 1, 'Type': 'L'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])

        sources = logic.identify_sources(df, logic.mode_b2l)
        l_sources = [s for s in sources if s['site'] == 'L_SRC']
        assert l_sources, "B2L 應識別 L_SRC 為來源"
        assert l_sources[0]['transferable_qty'] == 6, "B2L 應為 8-2=6 件可轉出"

    def test_b2l_type_l_stock_le_two_no_transfer(self):
        """B2L：Type=L 低銷量且淨庫存<=2時，不轉出。"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='L_SRC_LOW', **{'SaSa Net Stock': 2, 'Safety Stock': 1,
                       'Last Month Sold Qty': 1, 'MTD Sold Qty': 0,
                       'Effective Sold Qty': 1, 'Type': 'L'}),
            _make_row(Site='DST', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])

        recs = logic.generate_transfer_recommendations(df, logic.mode_b2l)
        assert all(r['Transfer Site'] != 'L_SRC_LOW' for r in recs), "B2L 庫存<=2應不轉出"

    def test_b3l_cross_om_allowed(self):
        """B3L：應保有跨OM配對能力。"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='L_SRC_X', OM='OM1', **{'SaSa Net Stock': 8, 'Safety Stock': 1,
                       'Last Month Sold Qty': 1, 'MTD Sold Qty': 0,
                       'Effective Sold Qty': 1, 'Type': 'L'}),
            _make_row(Site='DST_X', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])

        recs = logic.generate_transfer_recommendations(df, logic.mode_b3l)
        assert len(recs) > 0, "B3L 應允許跨OM"
        assert any(r['Transfer OM'] != r['Receive OM'] for r in recs), "B3L 應有跨OM建議"

    def test_b2la_b3la_type_t_not_source(self):
        """B2La/B3La：Type=T 不可作為出貨來源。"""
        logic = TransferLogic()
        df_same_om = _df([
            _make_row(Site='T_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Safety Stock': 1,
                       'Effective Sold Qty': 1, 'Type': 'T'}),
            _make_row(Site='DST', OM='OM1', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
        ])
        recs_b2la = logic.generate_transfer_recommendations(df_same_om, logic.mode_b2la)
        assert all(r['Transfer Site'] != 'T_SRC' for r in recs_b2la), "B2La Type=T禁止轉出"

        df_cross_om = _df([
            _make_row(Site='T_SRC_X', OM='OM1', **{'SaSa Net Stock': 10, 'Safety Stock': 1,
                       'Effective Sold Qty': 1, 'Type': 'T'}),
            _make_row(Site='DST_X', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'M'}),
        ])
        recs_b3la = logic.generate_transfer_recommendations(df_cross_om, logic.mode_b3la)
        assert all(r['Transfer Site'] != 'T_SRC_X' for r in recs_b3la), "B3La Type=T禁止轉出"


# ===========================================================================
# 模式 C：重點補0
# ===========================================================================

class TestModeC:

    def _base_df(self):
        return _df([
            _make_row(Site='RF_SRC', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 2}),
            _make_row(Site='RF_ZERO', **{'SaSa Net Stock': 0, 'Pending Received': 0,
                       'Safety Stock': 6, 'Effective Sold Qty': 5,
                       'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            # 另一個最高銷量店 - 保護用
            _make_row(Site='RF_HIGH', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
        ])

    def test_basic(self):
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_c)
        assert len(recs) > 0
        run_common_assertions(recs, df, logic, "C模式")

    def test_only_targets_low_stock(self):
        """C模式只補 total_available <= 1 的"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_SRC', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_ZERO', **{'SaSa Net Stock': 0, 'Pending Received': 1,
                       'Safety Stock': 6, 'Effective Sold Qty': 5}),
            _make_row(Site='RF_HAS_STOCK', **{'SaSa Net Stock': 2, 'Pending Received': 0,
                       'Safety Stock': 6, 'Effective Sold Qty': 8,
                       'Last Month Sold Qty': 5, 'MTD Sold Qty': 3}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c)
        dest_sites = {r['Receive Site'] for r in recs}
        assert 'RF_ZERO' in dest_sites, "C模式應補total_available<=1的店"
        # RF_HAS_STOCK total_avail=2 > 1, C模式重點補0不該補它 (除非它符合緊急/潛在缺貨但那需要更高銷量)
        c_zero_recs = [r for r in recs if r['Destination Type'] == '重點補0']
        c_zero_dsts = {r['Receive Site'] for r in c_zero_recs}
        assert 'RF_HAS_STOCK' not in c_zero_dsts, "C模式重點補0不應補total_available>1的店"

    def test_transfer_cap_30pct_3items(self):
        """C模式：轉出上限 30% + 最多3件"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_SRC', **{'SaSa Net Stock': 50, 'Safety Stock': 10,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_ZERO', **{'SaSa Net Stock': 0, 'Safety Stock': 10,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='RF_HIGH', **{'SaSa Net Stock': 50, 'Safety Stock': 10,
                       'Effective Sold Qty': 20}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c)
        for r in recs:
            if r['Transfer Site'] == 'RF_SRC' and r['Source Type'] in ('RF過剩轉出', 'RF加強轉出'):
                assert r['Transfer Qty'] <= 3, f"C模式轉出超過3件: {r['Transfer Qty']}"

    def test_cumulative_receive_not_exceed_target(self):
        """C模式：累計接收不超過目標"""
        logic = TransferLogic()
        df = _df([
            _make_row(Article='000000000001', Site='SRC1', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Article='000000000001', Site='SRC2', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 2}),
            _make_row(Article='000000000001', Site='ZERO', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Article='000000000001', Site='HIGH', **{'SaSa Net Stock': 30, 'Safety Stock': 5,
                       'Effective Sold Qty': 20}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c)
        cum = defaultdict(int)
        for r in recs:
            if r['Destination Type'] == '重點補0':
                cum[(r['Article'], r['Receive Site'])] += r['Transfer Qty']
        for key, total in cum.items():
            target = max(int(6 * 0.5), 3)  # safety_stock=6
            assert total <= target, f"C模式累計接收{total} > 目標{target}: {key}"


# ===========================================================================
# 模式 C1：重點補0-只補0/1 (或自選數量)
# ===========================================================================

class TestModeC1:

    def test_only_targets_zero_or_one_stock(self):
        """C1模式只允許 total_available <= 1 的店舖接收"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_SRC', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_ZERO', **{'SaSa Net Stock': 0, 'Pending Received': 1,
                       'Safety Stock': 6, 'Effective Sold Qty': 5,
                       'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='RF_TWO', **{'SaSa Net Stock': 2, 'Pending Received': 0,
                       'Safety Stock': 6, 'Effective Sold Qty': 9,
                       'Last Month Sold Qty': 5, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c1)
        dest_sites = {r['Receive Site'] for r in recs}
        assert 'RF_ZERO' in dest_sites, "C1模式應補 total_available<=1 的店"
        assert 'RF_TWO' not in dest_sites, "C1模式不應補 total_available=2 的店"

    def test_not_fallback_to_general_shortage_rules(self):
        """C1模式不應落入一般緊急缺貨或潛在缺貨接收分支"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_SRC', **{'SaSa Net Stock': 18, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF_NO_STOCK', **{'SaSa Net Stock': 0, 'Pending Received': 0,
                       'Safety Stock': 6, 'Effective Sold Qty': 6,
                       'Last Month Sold Qty': 4, 'MTD Sold Qty': 2}),
            _make_row(Site='RF_LOW_NOT_C1', **{'SaSa Net Stock': 2, 'Pending Received': 0,
                       'Safety Stock': 6, 'Effective Sold Qty': 10,
                       'Last Month Sold Qty': 6, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c1)
        receive_types = {(r['Receive Site'], r['Destination Type']) for r in recs}
        assert ('RF_NO_STOCK', '重點補0') in receive_types
        assert ('RF_LOW_NOT_C1', '緊急缺貨補貨') not in receive_types
        assert ('RF_LOW_NOT_C1', '潛在缺貨補貨') not in receive_types


# ===========================================================================
# 模式 C2：跨OM重點補0
# ===========================================================================

class TestModeC2:

    def test_cross_om(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='SRC', OM='OM1', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='ZERO', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='HIGH', OM='OM1', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c2)
        assert len(recs) > 0, "C2應產生跨OM建議"
        cross_om = [r for r in recs if r['Transfer OM'] != r['Receive OM']]
        assert len(cross_om) > 0, "C2應有跨OM配對"

    def test_hd_windy_restrictions(self):
        """C2: HD不轉HA/HB/HC、Windy只轉Windy"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HD01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Safety Stock': 0, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='HA01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='ND_W', OM='Windy', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Safety Stock': 0, 'Effective Sold Qty': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='DST_O', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c2)
        for r in recs:
            if r['Transfer Site'].upper().startswith('HD'):
                assert not r['Receive Site'].upper().startswith(('HA', 'HB', 'HC')), \
                    f"C2 HD→HA/HB/HC violation: {r['Transfer Site']}→{r['Receive Site']}"
            if r['Transfer OM'] == 'Windy':
                assert r['Receive OM'] == 'Windy', \
                    f"C2 Windy should only transfer to Windy, got {r['Receive OM']}"

    def test_common_rules(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='SRC', OM='OM1', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='ZERO', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='HIGH', OM='OM1', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_c2)
        run_common_assertions(recs, df, logic, "C2模式")


# ===========================================================================
# 模式 D：清貨轉貨
# ===========================================================================

class TestModeD:

    def test_nd_clearance_no_sales(self):
        """D模式：ND無銷售記錄 → ND清貨轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 3,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_d)
        assert len(recs) > 0
        assert any(r['Source Type'] == 'ND清貨轉出' for r in recs), "D模式應產生ND清貨轉出"
        run_common_assertions(recs, df, logic, "D模式")

    def test_avoid_exactly_one_remaining(self):
        """D模式：避免ND轉出後剩餘恰好1件"""
        logic = TransferLogic()
        # ND有4件，目標需要3件 → 轉3件剩1件，應調整
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 4,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 3,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_d)
        for r in recs:
            if r['Source Type'] in ('ND清貨轉出', 'ND轉出') and r['Transfer Site'] == 'ND01':
                remaining = r['After Transfer Stock']
                assert remaining != 1, (
                    f"D模式 ND轉出後不應剩1件, 剩 {remaining}")

    def test_d_relaxed_destination(self):
        """D模式接收條件放寬：不需要最高銷量限制"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 1, 'Safety Stock': 5,
                       'Effective Sold Qty': 3, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 1, 'Safety Stock': 5,
                       'Effective Sold Qty': 2, 'Last Month Sold Qty': 1, 'MTD Sold Qty': 1}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_d)
        # D模式不需要最高銷量限制，兩個RF都可能接收
        assert len(recs) > 0, "D模式應該有推薦"


# ===========================================================================
# 模式 E1：強制轉出（僅同OM）
# ===========================================================================

class TestModeE1:

    def _base_df(self):
        return _df([
            _make_row(Site='E_SRC', **{'SaSa Net Stock': 10, 'Safety Stock': 5,
                       'Effective Sold Qty': 3, 'ALL': 'Y'}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 2, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])

    def test_only_marked_rows_transfer(self):
        """E1：只有ALL標記的行可以轉出"""
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        assert len(recs) > 0
        for r in recs:
            # 除了C模式回退外，所有轉出都應來自標記行
            assert r['Source Type'] == 'E模式強制轉出', \
                f"E1模式非標記來源: {r['Source Type']}"

    def test_same_om_only(self):
        """E1：僅同OM配對"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 3,
                       'ALL': 'Y'}),
            _make_row(Site='RF01', OM='OM1', **{'SaSa Net Stock': 2, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
            _make_row(Site='RF02', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        for r in recs:
            assert r['Transfer OM'] == r['Receive OM'], f"E1不允許跨OM: {r['Transfer OM']}→{r['Receive OM']}"

    def test_full_transfer(self):
        """E1：全數轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', **{'SaSa Net Stock': 10, 'Safety Stock': 5,
                       'Effective Sold Qty': 3, 'ALL': 'Y'}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 10,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        total_out = sum(r['Transfer Qty'] for r in recs if r['Transfer Site'] == 'E_SRC')
        assert total_out == 10, f"E1全數轉出應為10, 實際{total_out}"

    def test_hd_restriction(self):
        """E1：HD不能轉到HA/HB/HC"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HD01', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 3, 'ALL': 'Y'}),
            _make_row(Site='HA01', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        hd_to_ha = [r for r in recs if r['Transfer Site'] == 'HD01' and
                     r['Receive Site'].upper().startswith(('HA', 'HB', 'HC'))]
        assert len(hd_to_ha) == 0, "E1 HD→HA/HB/HC 禁止"

    def test_common_rules(self):
        logic = TransferLogic()
        df = self._base_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        run_common_assertions(recs, df, logic, "E1模式")

    def test_receive_cap_safety_x2(self):
        """E1接收上限 = max(Safety * 2, 3)"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', **{'SaSa Net Stock': 100, 'Effective Sold Qty': 3, 'ALL': 'Y'}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 4,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1)
        cum = defaultdict(int)
        for r in recs:
            cum[r['Receive Site']] += r['Transfer Qty']
        for site, total in cum.items():
            cap = max(4 * 2, 3)
            assert total <= cap, f"E1接收超限: {site} total {total} > cap {cap}"


# ===========================================================================
# 模式 E1b：強制轉出（優先類型接收）
# ===========================================================================

class TestModeE1b:

    def test_priority_t_then_m(self):
        """E1b接收優先: T(高銷量) > M(高銷量) > T(Safety) > M(Safety)"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', **{'SaSa Net Stock': 30, 'Effective Sold Qty': 1, 'ALL': 'Y'}),
            _make_row(Site='T_SALES', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4,
                       'Type': 'T'}),
            _make_row(Site='M_SALES', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 7, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 3,
                       'Type': 'M'}),
            _make_row(Site='T_NOSALE', **{'SaSa Net Stock': 0, 'Safety Stock': 8,
                       'Effective Sold Qty': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0,
                       'Type': 'T'}),
            _make_row(Site='M_NOSALE', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0,
                       'Type': 'M'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1b)
        if recs:
            # 第一筆接收應為T類型高銷量
            first_rec = recs[0]
            assert first_rec['Receive Site'] == 'T_SALES', \
                f"E1b第一接收應為T_SALES, got {first_rec['Receive Site']}"

    def test_same_om_only(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='RF01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4,
                       'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e1b)
        for r in recs:
            assert r['Transfer OM'] == r['Receive OM'], "E1b僅同OM"


# ===========================================================================
# 模式 E2：強制轉出（跨OM）
# ===========================================================================

class TestModeE2:

    def test_cross_om_allowed(self):
        """E2允許跨OM"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='RF01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e2)
        assert len(recs) > 0, "E2應允許跨OM"

    def test_prefers_same_om(self):
        """E2優先同OM"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 5, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='RF_SAME', OM='OM1', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
            _make_row(Site='RF_CROSS', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e2)
        if recs:
            # 前面的建議應為同OM
            first = recs[0]
            assert first['Transfer OM'] == first['Receive OM'], "E2應先同OM配對"

    def test_hd_cannot_to_ha_hb_hc(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HD01', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='HA01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e2)
        for r in recs:
            if r['Transfer Site'].upper().startswith('HD'):
                assert not r['Receive Site'].upper().startswith(('HA', 'HB', 'HC')), \
                    "E2 HD→HA/HB/HC禁止"

    def test_phase3_c_mode_fallback(self):
        """E2 Phase3: 當其他OM的店舖未涉及強制轉出時，啟用C模式回退"""
        logic = TransferLogic()
        df = _df([
            # OM1: E模式強制轉出
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='RF01', OM='OM1', **{'SaSa Net Stock': 2, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
            # OM2: 未涉及E模式，但有零庫存店
            _make_row(Site='SRC_OM2', OM='OM2', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                       'Effective Sold Qty': 1}),
            _make_row(Site='ZERO_OM2', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
            _make_row(Site='HIGH_OM2', OM='OM2', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e2)
        # 可能會有Phase3回退
        phase3 = [r for r in recs if 'C模式回退' in str(r.get('Source Type', '')) or
                  'C模式回退' in str(r.get('Notes', ''))]
        # Phase3 不一定觸發（取決於是否有未滿足的非E-OM需求），只確認無違規
        run_common_assertions(recs, df, logic, "E2模式")

    def test_common_rules(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='E_SRC', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1,
                       'ALL': 'Y'}),
            _make_row(Site='RF01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_e2)
        run_common_assertions(recs, df, logic, "E2模式")

    def test_no_all_column_raises_error(self):
        """E2: 無ALL欄位時應拋出 ValueError（P0-漏洞4修正：改為明確錯誤提示）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', OM='OM1', **{'SaSa Net Stock': 10, 'Effective Sold Qty': 1}),
            _make_row(Site='RF02', OM='OM1', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        # P0-漏洞4修正：缺 ALL 欄位應拋出明確 ValueError，而非靜默輸出空結果
        with pytest.raises(ValueError, match="ALL"):
            logic.generate_transfer_recommendations(df, logic.mode_e2)


# ===========================================================================
# 模式 F：目標優化
# ===========================================================================

class TestModeF:

    def test_target_priority(self):
        """F模式：Target有數字的店優先接收"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 20,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='TGT', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
            _make_row(Site='ZERO', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 3, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 1,
                       'Target': 0}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        assert len(recs) > 0, "F模式應產生建議"
        tgt_recs = [r for r in recs if r['Receive Site'] == 'TGT']
        assert len(tgt_recs) > 0, "F模式Target店應接收"

    def test_target_fullwidth_digits_supported(self):
        """F模式：Target 支援全形數字輸入（例如：１０）"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 20,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='TGT', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': '１０'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        tgt_recs = [r for r in recs if r['Receive Site'] == 'TGT']
        assert len(tgt_recs) > 0, "F模式應能解析全形Target並調貨至目標店"

    def test_cross_om_with_target(self):
        """F模式允許跨OM"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 20,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='TGT', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        cross_om = [r for r in recs if r['Transfer OM'] != r['Receive OM']]
        assert len(cross_om) > 0, "F模式應允許跨OM"

    def test_hd_restriction(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='HD01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='HA01', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        for r in recs:
            if r['Transfer Site'].upper().startswith('HD'):
                assert not r['Receive Site'].upper().startswith(('HA', 'HB', 'HC')), \
                    "F模式 HD→HA/HB/HC禁止"

    def test_rf_highest_sold_protected(self):
        """F模式RF最高銷量店保護"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF_HIGH', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 10, 'Target': 0}),
            _make_row(Site='RF_LOW', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                       'Effective Sold Qty': 1, 'Target': 0}),
            _make_row(Site='TGT', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        rf_src = {r['Transfer Site'] for r in recs if r['Source Type'] == 'F模式RF轉出'}
        assert 'RF_HIGH' not in rf_src, "F模式RF最高銷量應被保護"

    def test_common_rules(self):
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 10,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='TGT', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f)
        run_common_assertions(recs, df, logic, "F模式")

    def test_f2_target_only_receiving(self):
        """F2模式：僅Target店舖可接收，非Target RF店舖不應接收"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 20,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Target': 0}),
            _make_row(Site='TGT', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2,
                       'Target': 10}),
            _make_row(Site='ZERO', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 6,
                       'Effective Sold Qty': 4, 'Last Month Sold Qty': 2, 'MTD Sold Qty': 2,
                       'Target': 0}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_f_target_only)
        assert len(recs) > 0, "F2模式應產生建議"

        receive_sites = {r['Receive Site'] for r in recs}
        assert 'TGT' in receive_sites, "F2模式Target店應接收"
        assert 'ZERO' not in receive_sites, "F2模式非Target店不應接收"
        run_common_assertions(recs, df, logic, "F2模式")


# ===========================================================================
# 跨模式通用規則整合測試
# ===========================================================================

ALL_SAME_OM_MODES = [
    "保守轉貨", "加強轉貨", "附加B(特別模式)",
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "重點補0", "重點補0-只補0/1 (或自選數量)", "清貨轉貨", "清貨轉貨(ND限定)",
]

ALL_CROSS_OM_MODES = [
    "附加B3(跨OM特別模式)", "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加C2(跨OM重點補0)", "目標優化", "F指定模式",
]


def _build_multi_store_df():
    """建構含多種店鋪類型的測試資料"""
    return _df([
        # OM1
        _make_row(Site='ND01', OM='OM1', **{'RP Type': 'ND', 'SaSa Net Stock': 8,
                   'Effective Sold Qty': 0, 'Safety Stock': 0,
                   'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
        _make_row(Site='RF01', OM='OM1', **{'SaSa Net Stock': 20, 'Safety Stock': 5,
                   'Effective Sold Qty': 2, 'Type': 'L',
                   'Last Month Sold Qty': 1, 'MTD Sold Qty': 1}),
        _make_row(Site='RF02', OM='OM1', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                   'Effective Sold Qty': 10, 'Type': 'T',
                   'Last Month Sold Qty': 5, 'MTD Sold Qty': 5}),
        # OM2
        _make_row(Site='RF03', OM='OM2', **{'SaSa Net Stock': 15, 'Safety Stock': 5,
                   'Effective Sold Qty': 1, 'Type': 'M'}),
        _make_row(Site='RF04', OM='OM2', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                   'Effective Sold Qty': 8, 'Type': 'T',
                   'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
    ])


class TestCrossModeSameOM:

    @pytest.mark.parametrize("mode", ALL_SAME_OM_MODES)
    def test_same_om_no_cross_om(self, mode):
        """同OM模式不應產生跨OM建議"""
        logic = TransferLogic()
        df = _build_multi_store_df()
        recs = logic.generate_transfer_recommendations(df, mode)
        for r in recs:
            assert r['Transfer OM'] == r['Receive OM'], \
                f"{mode} 不允許跨OM: {r['Transfer OM']}→{r['Receive OM']}"

    @pytest.mark.parametrize("mode", ALL_SAME_OM_MODES)
    def test_common_rules(self, mode):
        logic = TransferLogic()
        df = _build_multi_store_df()
        recs = logic.generate_transfer_recommendations(df, mode)
        run_common_assertions(recs, df, logic, mode)


class TestCrossModeCrossOM:

    @pytest.mark.parametrize("mode", ALL_CROSS_OM_MODES)
    def test_common_rules(self, mode):
        logic = TransferLogic()
        df = _build_multi_store_df()
        recs = logic.generate_transfer_recommendations(df, mode)
        run_common_assertions(recs, df, logic, mode)


# ===========================================================================
# E 模式 ALL 欄位邊界情況
# ===========================================================================

class TestEModeAllColumn:

    @pytest.mark.parametrize("mode", ["強制轉出", "強制轉出(優先類型接收)", "強制轉出(跨OM)"])
    def test_various_all_markers(self, mode):
        """ANY 非空字元都應視為標記"""
        for marker in ['Y', 'X', '1', '✓', 'all', 'ALL', 'yes']:
            logic = TransferLogic()
            df = _df([
                _make_row(Site='E_SRC', **{'SaSa Net Stock': 5, 'Effective Sold Qty': 1,
                           'ALL': marker}),
                _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                           'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
            ])
            recs = logic.generate_transfer_recommendations(df, mode)
            assert len(recs) > 0, f"E模式 marker '{marker}' 應觸發轉出"

    @pytest.mark.parametrize("mode", ["強制轉出", "強制轉出(優先類型接收)", "強制轉出(跨OM)"])
    def test_empty_all_no_transfer(self, mode):
        """ALL欄位存在但全為空白時不應有E模式強制轉出；若ALL欄位不存在則應拋出 ValueError"""
        # Case 1: ALL欄位存在但值為空字串或空白 → 不應觸發強制轉出（靜默允許）
        for blank in ['', ' ']:
            logic = TransferLogic()
            row = _make_row(Site='E_SRC', **{'SaSa Net Stock': 5, 'Effective Sold Qty': 1})
            row['ALL'] = blank
            df = _df([
                row,
                _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                           'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
            ])
            recs = logic.generate_transfer_recommendations(df, mode)
            e_recs = [r for r in recs if r['Source Type'] == 'E模式強制轉出']
            assert len(e_recs) == 0, f"E模式空白ALL不應觸發: '{blank}'"

        # Case 2: ALL欄位不存在 → 應拋出 ValueError（P0-漏洞4修正）
        logic = TransferLogic()
        row_no_all = _make_row(Site='E_SRC', **{'SaSa Net Stock': 5, 'Effective Sold Qty': 1})
        df_no_all = _df([
            row_no_all,
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4, 'MTD Sold Qty': 4}),
        ])
        with pytest.raises(ValueError, match="ALL"):
            logic.generate_transfer_recommendations(df_no_all, mode)


# ===========================================================================
# 所有模式完整性測試（用同一數據集跑全部模式）
# ===========================================================================

ALL_MODES_WITH_ALL = [
    "保守轉貨", "加強轉貨",
    "附加B(特別模式)", "附加B2a(特別模式-T遊客鋪不出貨)",
    "附加B3(跨OM特別模式)", "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "重點補0", "重點補0-只補0/1 (或自選數量)", "附加C2(跨OM重點補0)",
    "清貨轉貨", "清貨轉貨(ND限定)",
    "強制轉出", "強制轉出(優先類型接收)", "強制轉出(跨OM)",
    "目標優化", "F指定模式",
]


def _build_full_scenario_df():
    """完整場景：包含ND、RF各種Type、ALL標記、Target"""
    return _df([
        # OM1 - ND
        _make_row(Article='000000000001', Site='ND01', OM='OM1',
                  **{'RP Type': 'ND', 'SaSa Net Stock': 8, 'Effective Sold Qty': 0,
                     'Safety Stock': 0, 'Last Month Sold Qty': 0, 'MTD Sold Qty': 0,
                     'Type': 'R', 'ALL': 'Y', 'Target': 0}),
        # OM1 - RF Type=L 低銷量
        _make_row(Article='000000000001', Site='RF_L1', OM='OM1',
                  **{'SaSa Net Stock': 10, 'Safety Stock': 3, 'Effective Sold Qty': 1,
                     'Last Month Sold Qty': 1, 'MTD Sold Qty': 0, 'Type': 'L',
                     'ALL': '', 'Target': 0}),
        # OM1 - RF Type=T 高銷量
        _make_row(Article='000000000001', Site='RF_T1', OM='OM1',
                  **{'SaSa Net Stock': 0, 'Safety Stock': 5, 'Effective Sold Qty': 10,
                     'Last Month Sold Qty': 5, 'MTD Sold Qty': 5, 'Type': 'T',
                     'ALL': '', 'Target': 8}),
        # OM1 - RF Type=M
        _make_row(Article='000000000001', Site='RF_M1', OM='OM1',
                  **{'SaSa Net Stock': 15, 'Safety Stock': 5, 'Effective Sold Qty': 3,
                     'Last Month Sold Qty': 2, 'MTD Sold Qty': 1, 'Type': 'M',
                     'ALL': '', 'Target': 0}),
        # OM2 - RF
        _make_row(Article='000000000001', Site='RF_T2', OM='OM2',
                  **{'SaSa Net Stock': 0, 'Safety Stock': 5, 'Effective Sold Qty': 8,
                     'Last Month Sold Qty': 4, 'MTD Sold Qty': 4, 'Type': 'T',
                     'ALL': '', 'Target': 6}),
        _make_row(Article='000000000001', Site='RF_R2', OM='OM2',
                  **{'SaSa Net Stock': 20, 'Safety Stock': 5, 'Effective Sold Qty': 1,
                     'Last Month Sold Qty': 1, 'MTD Sold Qty': 0, 'Type': 'R',
                     'ALL': '', 'Target': 0}),
    ])


@pytest.mark.parametrize("mode", ALL_MODES_WITH_ALL)
def test_full_scenario_common_rules(mode):
    """全場景下所有模式的通用規則驗證"""
    logic = TransferLogic()
    df = _build_full_scenario_df()
    recs = logic.generate_transfer_recommendations(df, mode)
    # 某些模式可能無建議（如E模式只處理ALL標記行）
    if recs:
        run_common_assertions(recs, df, logic, f"全場景-{mode}")


# ===========================================================================
# 邊界情況測試
# ===========================================================================

class TestEdgeCases:

    def test_all_rf_same_sold_qty_no_protection(self):
        """所有RF銷量相同時，不保護任何店"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', **{'SaSa Net Stock': 10, 'Safety Stock': 3,
                       'Effective Sold Qty': 5}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 10, 'Safety Stock': 3,
                       'Effective Sold Qty': 5}),
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        # 當所有RF銷量相同，max_sold_qty 設為 inf，兩個都可以轉
        src_sites = {r['Transfer Site'] for r in recs}
        assert len(src_sites & {'RF01', 'RF02'}) >= 1, "銷量相同時應有RF店可轉出"

    def test_all_rf_zero_sold_no_protection(self):
        """所有RF銷量為0時，不保護任何店"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', **{'SaSa Net Stock': 10, 'Safety Stock': 3,
                       'Effective Sold Qty': 0}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 10, 'Safety Stock': 3,
                       'Effective Sold Qty': 0}),
            # 需要一個有銷售record的receive
            _make_row(Site='RF_NEED', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                       'Effective Sold Qty': 1, 'Last Month Sold Qty': 1, 'MTD Sold Qty': 0}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b)
        src_sites = {r['Transfer Site'] for r in recs}
        assert len(src_sites & {'RF01', 'RF02'}) >= 1, "銷量全0時不保護任何店"

    def test_zero_stock_source_not_selected(self):
        """庫存為0的店不應作為轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 3,
                       'Effective Sold Qty': 1}),
            _make_row(Site='RF02', **{'SaSa Net Stock': 0, 'Safety Stock': 3,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        assert len(recs) == 0, "全部零庫存不應產生建議"

    def test_single_store_no_transfer(self):
        """只有一間店時不應有建議"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ONLY_ONE', **{'SaSa Net Stock': 10, 'Safety Stock': 3,
                       'Effective Sold Qty': 5}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_a)
        assert len(recs) == 0, "單店無法調貨"

    def test_b2_receive_must_be_below_safety(self):
        """B2/B3接收店庫存必須低於 Safety Stock"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 20,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
            _make_row(Site='RF_FULL', **{'SaSa Net Stock': 10, 'Safety Stock': 5,
                       'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                       'MTD Sold Qty': 4, 'Type': 'T'}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        dst_sites = {r['Receive Site'] for r in recs}
        assert 'RF_FULL' not in dst_sites, "B2 total >= safety 的店不應接收"

    def test_d_nd_with_sales_not_clearance(self):
        """D模式：ND有銷售記錄時，非清貨轉出"""
        logic = TransferLogic()
        df = _df([
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 5,
                       'Effective Sold Qty': 3, 'Safety Stock': 0,
                       'Last Month Sold Qty': 2, 'MTD Sold Qty': 1}),
            _make_row(Site='RF01', **{'SaSa Net Stock': 0, 'Safety Stock': 3,
                       'Effective Sold Qty': 5, 'Last Month Sold Qty': 3, 'MTD Sold Qty': 2}),
        ])
        recs = logic.generate_transfer_recommendations(df, logic.mode_d)
        for r in recs:
            if r['Transfer Site'] == 'ND01':
                assert r['Source Type'] == 'ND轉出', \
                    f"D模式ND有銷售應為ND轉出, got {r['Source Type']}"


# ===========================================================================
# B2系列接收店數限制
# ===========================================================================

class TestB2ReceiveSiteLimit:

    def _multi_dst_df(self):
        rows = [
            _make_row(Site='ND01', **{'RP Type': 'ND', 'SaSa Net Stock': 30,
                       'Effective Sold Qty': 0, 'Safety Stock': 0,
                       'Last Month Sold Qty': 0, 'MTD Sold Qty': 0, 'Type': 'R'}),
        ]
        for i in range(5):
            rows.append(
                _make_row(Site=f'DST{i:02d}', **{'SaSa Net Stock': 0, 'Safety Stock': 5,
                           'Effective Sold Qty': 8, 'Last Month Sold Qty': 4,
                           'MTD Sold Qty': 4, 'Type': 'T'})
            )
        return _df(rows)

    def test_limit_1(self):
        logic = TransferLogic(b_special_max_receive_sites_per_source=1)
        df = self._multi_dst_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        src_to_dst: Dict[str, Set[str]] = defaultdict(set)
        for r in recs:
            src_to_dst[r['Transfer Site']].add(r['Receive Site'])
        for src, dsts in src_to_dst.items():
            assert len(dsts) <= 1, f"B2 limit=1: {src} → {len(dsts)} sites"

    def test_limit_2(self):
        logic = TransferLogic(b_special_max_receive_sites_per_source=2)
        df = self._multi_dst_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        src_to_dst: Dict[str, Set[str]] = defaultdict(set)
        for r in recs:
            src_to_dst[r['Transfer Site']].add(r['Receive Site'])
        for src, dsts in src_to_dst.items():
            assert len(dsts) <= 2, f"B2 limit=2: {src} → {len(dsts)} sites"

    def test_unlimited(self):
        logic = TransferLogic(b_special_max_receive_sites_per_source=None)
        df = self._multi_dst_df()
        recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)
        # 無限制模式下，應能配對更多店
        src_to_dst: Dict[str, Set[str]] = defaultdict(set)
        for r in recs:
            src_to_dst[r['Transfer Site']].add(r['Receive Site'])
        # 至少要能配超過1間
        any_multi = any(len(dsts) > 1 for dsts in src_to_dst.values())
        assert any_multi, "B2 unlimited 應能配對超過1間"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
