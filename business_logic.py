"""
業務邏輯模組 v2.13.0
實現調貨規則、源/目的地識別和匹配算法
支持二十四模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B特別模式-T遊客鋪不出貨)/B2L(附加B特別模式-Type=L保留2件)/B2La(附加B特別模式-Type=L保留2件-T遊客鋪不出貨)/B3(附加B跨OM特別模式)/B3a(附加B跨OM特別模式-T遊客鋪不出貨)/B3L(附加B跨OM特別模式-Type=L保留2件)/B3La(附加B跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)/C(重點補0)/C1(重點補0-只補0/1)/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/精簡SKU(限同OM)/精簡SKU(跨OM)
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Tuple, Optional, Set  # noqa: F401 — Set used in signature defaults
import logging

from config import (
    A_MODE_PERCENTAGE_CAP, A_MODE_MIN_TRANSFER,
    B_MODE_PERCENTAGE_CAP, B_MODE_MIN_TRANSFER,
    C_MODE_PERCENTAGE_CAP, C_MODE_ABS_CAP,
    C1_MODE_MIN_TRANSFER,
    SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR,
    F_TARGET_MULTIPLIER, F_TARGET_FLOOR,
    SIMPLIFIED_SKU_RECEIVE_MULTIPLIER,
    ND_RECEIVE_MULTIPLIER,
)
from services.recommendation_factory import build_recommendation, apply_transfer
from services.target_utils import parse_target_series
from services.matching_engine import (
    compute_transfer_qty as _compute_transfer_qty_impl,
    can_transfer as _can_transfer_impl,
    match_by_priority as _match_by_priority_impl,
    match_general_mode as _match_general_mode_impl,
)
from services.post_processing import (
    get_record_sales_total as _get_record_sales_total_impl,
    infer_source_rp_type as _infer_source_rp_type_impl,
    refresh_recommendation_fields as _refresh_recommendation_fields_impl,
    optimize_single_piece_transfers as _optimize_single_piece_transfers_impl,
)
from strategies.predicates import is_hd_to_hk_restricted

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _safe_get_last2m(row) -> int:
    if 'Last 2 Month Sold Qty' in row.index:
        return int(row['Last 2 Month Sold Qty'])
    return int(row['Last Month Sold Qty'])


def _make_source(row, transferable_qty: int, priority: int, source_type: str, **extra) -> Dict:
    source = {
        'site': row['Site'],
        'om': row['OM'],
        'rp_type': row['RP Type'],
        'transferable_qty': transferable_qty,
        'priority': priority,
        'original_stock': int(row['SaSa Net Stock']),
        'effective_sold_qty': int(row['Effective Sold Qty']) if pd.notna(row.get('Effective Sold Qty', 0)) else 0,
        'source_type': source_type,
        'store_type': '',
        'last_month_sold_qty': int(row['Last Month Sold Qty']) if pd.notna(row.get('Last Month Sold Qty', 0)) else 0,
        'mtd_sold_qty': int(row['MTD Sold Qty']) if pd.notna(row.get('MTD Sold Qty', 0)) else 0,
        'last_2_month_sold_qty': _safe_get_last2m(row),
    }
    source.update(extra)
    return source


def _make_dest(row, needed_qty: int, priority: int, dest_type: str,
               target_qty: int, max_receive_qty: Optional[int] = None, **extra) -> Dict:
    dest = {
        'site': row['Site'],
        'om': row['OM'],
        'rp_type': row['RP Type'],
        'needed_qty': needed_qty,
        'priority': priority,
        'current_stock': int(row['SaSa Net Stock']),
        'pending_received': int(row['Pending Received']),
        'safety_stock': int(row['Safety Stock']) if pd.notna(row.get('Safety Stock', 0)) else 0,
        'moq': int(row['MOQ']) if pd.notna(row.get('MOQ', 0)) else 0,
        'effective_sold_qty': int(row['Effective Sold Qty']) if pd.notna(row.get('Effective Sold Qty', 0)) else 0,
        'dest_type': dest_type,
        'target_qty': target_qty,
        'received_qty': 0,
        'last_month_sold_qty': int(row['Last Month Sold Qty']) if pd.notna(row.get('Last Month Sold Qty', 0)) else 0,
        'mtd_sold_qty': int(row['MTD Sold Qty']) if pd.notna(row.get('MTD Sold Qty', 0)) else 0,
    }
    if max_receive_qty is not None:
        dest['max_receive_qty'] = max_receive_qty
    dest.update(extra)
    return dest


def _compute_max_protected_sold(df) -> float:
    if df.empty:
        return 0
    max_sold = df['Effective Sold Qty'].max()
    if len(df) == 1 or max_sold == 0 or (df['Effective Sold Qty'] == max_sold).sum() >= len(df):
        return float('inf')
    return max_sold


class TransferLogic:
    """調貨業務邏輯類 v2.13.0"""
    
    def __init__(self, b_special_max_receive_sites_per_source: Optional[int] = None,
                 f2_allow_hd_transfer: bool = False):
        self.transfer_recommendations = []
        self.quality_check_passed = True
        self.quality_errors = []
        self.b_special_max_receive_sites_per_source = (
            b_special_max_receive_sites_per_source
            if isinstance(b_special_max_receive_sites_per_source, int) and b_special_max_receive_sites_per_source > 0
            else None
        )
        self.f2_allow_hd_transfer = f2_allow_hd_transfer
        self.mode_a = "保守轉貨"  # A模式
        self.mode_b = "加強轉貨"  # B模式
        self.mode_b_special = "附加B(特別模式)"  # B2模式
        self.mode_b_special_a = "附加B2a(特別模式-T遊客鋪不出貨)"  # B2a模式
        self.mode_b2l = "附加B2L(特別模式-Type=L保留2件)"  # B2L模式
        self.mode_b2la = "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)"  # B2La模式
        self.mode_b3 = "附加B3(跨OM特別模式)"  # B3模式
        self.mode_b3a = "附加B3a(跨OM特別模式-T遊客鋪不出貨)"  # B3a模式
        self.mode_b3l = "附加B3L(跨OM特別模式-Type=L保留2件)"  # B3L模式
        self.mode_b3la = "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)"  # B3La模式
        self.mode_c = "重點補0"  # C模式
        self.mode_c1 = "重點補0-只補0/1"  # C1模式
        self.mode_c2 = "附加C2(跨OM重點補0)"  # C2模式
        self.mode_d = "清貨轉貨"  # D模式
        self.mode_d2 = "清貨轉貨(ND限定)"  # D2模式：僅ND清貨轉出，RF不做轉出
        self.mode_e1 = "強制轉出"  # E1模式（僅同OM）
        self.mode_e1b = "強制轉出(優先類型接收)"  # E1b模式（僅同OM，接收優先Type=T/M）
        self.mode_e2 = "強制轉出(跨OM)"  # E2模式（跨OM）
        self.mode_f = "目標優化"  # F模式
        self.mode_f_target_only = "F指定模式"  # F2模式（僅Target店舖接收）
        self.mode_nd1 = "ND同OM轉貨"   # ND1模式（ND同OM互轉，智能銷量排序）
        self.mode_nd2 = "ND混合OM轉貨"  # ND2模式（ND跨OM互轉，Windy只轉Windy）
        self.mode_simplified_sku_same = "精簡SKU(限同OM)"
        self.mode_simplified_sku_cross = "精簡SKU(跨OM)"

        # 模式家族映射（v2.11.2 優化）- 避免重複的 _is_*_mode() 邏輯
        self.MODE_FAMILIES = {
            'b_special': {
                self.mode_b_special, self.mode_b_special_a,
                self.mode_b2l, self.mode_b2la,
                self.mode_b3, self.mode_b3a,
                self.mode_b3l, self.mode_b3la,
            },
            'b3_family': {self.mode_b3, self.mode_b3a, self.mode_b3l, self.mode_b3la},
            'b_tourist_no_source': {self.mode_b_special_a, self.mode_b2la, self.mode_b3a, self.mode_b3la},
            'b_l_retain': {self.mode_b2l, self.mode_b2la, self.mode_b3l, self.mode_b3la},
            'd_family': {self.mode_d, self.mode_d2},
            'nd_transfer': {self.mode_nd1, self.mode_nd2},
            'simplified_sku': {self.mode_simplified_sku_same, self.mode_simplified_sku_cross},
        }

        b_special = self.MODE_FAMILIES['b_special']
        b3_family = self.MODE_FAMILIES['b3_family']
        simplified = self.MODE_FAMILIES['simplified_sku']

        self._ALL_MODES = (
            {self.mode_a, self.mode_b}
            | b_special
            | {self.mode_c, self.mode_c1, self.mode_c2}
            | self.MODE_FAMILIES['d_family']
            | {self.mode_e1, self.mode_e1b, self.mode_e2}
            | {self.mode_f, self.mode_f_target_only}
            | self.MODE_FAMILIES['nd_transfer']
            | simplified
        )

        self._CROSS_OM_GROUPING_MODES = (
            {self.mode_e2, self.mode_f, self.mode_f_target_only,
             self.mode_c2, self.mode_nd2}
            | b3_family
        )

        self._SOURCE_FILTER_MODES = (
            {self.mode_e1, self.mode_e1b, self.mode_e2,
             self.mode_f, self.mode_f_target_only, self.mode_c2,
             self.mode_nd1, self.mode_nd2}
            | b_special | simplified
        )

        self._CROSS_OM_MATCHING_MODES = (
            {self.mode_e2, self.mode_f, self.mode_f_target_only,
             self.mode_c2, self.mode_nd2}
            | b3_family
            | {self.mode_simplified_sku_cross}
        )

        self._strategies = self._init_strategies()

    def _init_strategies(self):
        from strategies.simplified_sku import SimplifiedSKUStrategy
        from strategies.c2_mode import C2ModeStrategy
        from strategies.f_mode import FModeStrategy
        from strategies.e1_mode import E1ModeStrategy
        from strategies.e2_mode import E2ModeStrategy
        from strategies.nd_mode import NDModeStrategy
        from strategies.b_special import BSpecialStrategy
        return {
            'simplified_sku': SimplifiedSKUStrategy(),
            'c2_mode': C2ModeStrategy(),
            'f_mode': FModeStrategy(
                create_note=self._create_recommendation_note,
                f2_allow_hd_transfer=self.f2_allow_hd_transfer,
            ),
            'e1_mode': E1ModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
            'e2_mode': E2ModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
            'nd_mode': NDModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
            'b_special': BSpecialStrategy(
                match_by_priority=self._match_by_priority,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
        }

    def _is_b_special_mode(self, mode: str) -> bool:
        """檢查是否為 B 特別系列模式（B2/B2a/B2L/B2La/B3/B3a/B3L/B3La）"""
        return mode in self.MODE_FAMILIES.get('b_special', set())

    def _is_b3_family_mode(self, mode: str) -> bool:
        """檢查是否為 B3 系列模式"""
        return mode in self.MODE_FAMILIES.get('b3_family', set())

    def _is_b_tourist_no_source_mode(self, mode: str) -> bool:
        """檢查是否為 T遊客鋪不出貨模式"""
        return mode in self.MODE_FAMILIES.get('b_tourist_no_source', set())

    def _is_b_l_retain_mode(self, mode: str) -> bool:
        """檢查是否為 L保留2件模式"""
        return mode in self.MODE_FAMILIES.get('b_l_retain', set())

    def _is_d_family_mode(self, mode: str) -> bool:
        """D/D2 模式家族判斷"""
        return mode in self.MODE_FAMILIES.get('d_family', set())

    def _is_nd_transfer_mode(self, mode: str) -> bool:
        """ND1/ND2 模式：ND 店舖可互相調貨（打破全局 ND 不可接收規則）"""
        return mode in self.MODE_FAMILIES.get('nd_transfer', set())

    def _is_simplified_sku_mode(self, mode: str) -> bool:
        """檢查是否為精簡SKU模式"""
        return mode in self.MODE_FAMILIES.get('simplified_sku', set())

    def _get_b_special_sales_total(self, data: Dict) -> int:
        return int(data.get('last_month_sold_qty', 0) or 0) + int(data.get('mtd_sold_qty', 0) or 0)

    def _parse_target_series(self, df: pd.DataFrame) -> pd.Series:
        return parse_target_series(df)
    
    def identify_sources(self, group_df: pd.DataFrame, mode: str, protected_sites: Optional[Set[str]] = None) -> List[Dict]:
        """
        識別轉出候選店鋪

        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式

        Returns:
            轉出候選店鋪列表
        """
        if self._is_simplified_sku_mode(mode):
            return self._sources_simplified_sku(group_df)
        if self._is_nd_transfer_mode(mode):
            return self._sources_nd_mode(group_df)
        if mode in (self.mode_f, self.mode_f_target_only):
            return self._sources_f_mode(group_df, mode, protected_sites)
        if mode in (self.mode_e1, self.mode_e1b, self.mode_e2):
            return self._sources_e_mode(group_df)
        return self._sources_general(group_df, mode)

    def _sources_simplified_sku(self, group_df: pd.DataFrame) -> List[Dict]:
        sources: List[Dict] = []
        nd_stores = group_df[group_df['RP Type'] == 'ND']
        for _, row in nd_stores.iterrows():
            net_stock = int(row['SaSa Net Stock'])
            if net_stock <= 0:
                continue
            sources.append(_make_source(row, net_stock, 1, '精簡SKU ND轉出'))

        rf_sources = group_df[group_df['RP Type'] == 'RF']
        max_sold_qty = _compute_max_protected_sold(rf_sources)

        for _, row in rf_sources.iterrows():
            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            last_two_month_sold = _safe_get_last2m(row)
            cap = max(safety_stock * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last_two_month_sold * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)
            effective_sold = int(row['Effective Sold Qty'])

            if effective_sold >= max_sold_qty:
                continue
            if total_available <= cap:
                continue

            transferable_qty = min(total_available - cap, int(row['SaSa Net Stock']))
            if transferable_qty <= 0:
                continue

            sources.append(_make_source(row, transferable_qty, 2, '精簡SKU RF轉出'))

        sources.sort(key=lambda x: x['priority'])
        return sources

    def _sources_nd_mode(self, group_df: pd.DataFrame) -> List[Dict]:
        sources: List[Dict] = []
        nd_stores = group_df[group_df['RP Type'] == 'ND']
        max_nd_sold = _compute_max_protected_sold(nd_stores)

        for _, row in nd_stores.iterrows():
            net_stock = int(row['SaSa Net Stock'])
            if net_stock <= 0:
                continue
            effective_sold = int(row['Effective Sold Qty'])
            if effective_sold >= max_nd_sold:
                continue

            last_month_sold = int(row['Last Month Sold Qty'])
            mtd_sold = int(row['MTD Sold Qty'])
            total_sales = last_month_sold + mtd_sold

            sources.append(_make_source(row, net_stock, 1, 'ND智能轉出',
                                        total_sales_sort=total_sales))

        sources.sort(key=lambda x: x.get('total_sales_sort', 0))
        return sources

    def _sources_f_mode(self, group_df: pd.DataFrame, mode: str, protected_sites: Optional[Set[str]]) -> List[Dict]:
        sources: List[Dict] = []
        target_series = self._parse_target_series(group_df)

        nd_sources = group_df[group_df['RP Type'] == 'ND']
        for _, row in nd_sources.iterrows():
            target_value = target_series.loc[row.name]
            if pd.notna(target_value) and target_value > 0:
                continue
            if mode == self.mode_f_target_only and protected_sites:
                site_key = str(row['Site']).strip().upper()
                if site_key in protected_sites:
                    continue
            net_stock = int(row['SaSa Net Stock'])
            if net_stock > 0:
                sources.append(_make_source(row, net_stock, 1, 'F模式ND轉出'))

        rf_sources = group_df[group_df['RP Type'] == 'RF']
        max_sold_qty = _compute_max_protected_sold(rf_sources)

        for _, row in rf_sources.iterrows():
            target_value = target_series.loc[row.name]
            if pd.notna(target_value) and target_value > 0:
                continue
            if mode == self.mode_f_target_only and protected_sites:
                site_key = str(row['Site']).strip().upper()
                if site_key in protected_sites:
                    continue
            net_stock = int(row['SaSa Net Stock'])
            effective_sold = int(row['Effective Sold Qty'])

            if net_stock <= 0:
                continue
            if effective_sold >= max_sold_qty:
                continue

            sources.append(_make_source(row, net_stock, 2, 'F模式RF轉出'))

        sources.sort(key=lambda x: (x['priority'], x.get('effective_sold_qty', 0)))
        return sources

    def _sources_e_mode(self, group_df: pd.DataFrame) -> List[Dict]:
        sources: List[Dict] = []
        if 'ALL' not in group_df.columns:
            return sources
        all_marked = group_df[
            (group_df['ALL'].notna()) & 
            (group_df['ALL'].astype(str).str.strip() != '')
        ]
        for _, row in all_marked.iterrows():
            net_stock = int(row['SaSa Net Stock'])
            if net_stock > 0:
                sources.append(_make_source(row, net_stock, 1, 'E模式強制轉出',
                                            is_e_mode=True))
        sources.sort(key=lambda x: x['priority'])
        return sources

    def _sources_general(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        sources: List[Dict] = []
        if self._is_b_special_mode(mode):
            if 'Type' in group_df.columns:
                type_series = group_df['Type'].astype(str).str.upper()
            else:
                type_series = pd.Series("", index=group_df.index)
        else:
            type_series = None

        nd_sources = group_df[group_df['RP Type'] == 'ND']
        for _, row in nd_sources.iterrows():
            if self._is_b_tourist_no_source_mode(mode) and type_series is not None and type_series.loc[row.name] == 'T':
                continue
            if row['SaSa Net Stock'] > 0:  # 只考慮有庫存的店鋪
                # D模式特殊處理：檢查是否為清貨對象（銷量為0）
                last_month_sold = int(row['Last Month Sold Qty'])
                mtd_sold = int(row['MTD Sold Qty'])
                
                if self._is_d_family_mode(mode) and last_month_sold == 0 and mtd_sold == 0:
                    # D/D2模式：清貨轉貨，針對無銷售記錄的ND店鋪
                    source_type = 'ND清貨轉出'
                elif mode == self.mode_d2:
                    # D2模式：僅清貨轉出(無銷售記錄)，有銷售的ND不轉出
                    continue
                else:
                    # 其他模式：正常ND轉出
                    source_type = 'ND轉出'

                source_store_type = type_series.loc[row.name] if type_series is not None else ''
                
                sources.append(_make_source(row, int(row['SaSa Net Stock']), 1, source_type,
                                            store_type=source_store_type))

        # B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式特殊處理：Type=L 低銷量特例
        if self._is_b_special_mode(mode):

            type_l_sources = group_df[(type_series == 'L') & (group_df['RP Type'] == 'RF')]
            for _, row in type_l_sources.iterrows():
                last_month_sold = int(row['Last Month Sold Qty'])
                mtd_sold = int(row['MTD Sold Qty'])
                if max(last_month_sold, mtd_sold) > 2:
                    continue

                net_stock = int(row['SaSa Net Stock'])
                if self._is_b_l_retain_mode(mode):
                    transferable_qty = max(net_stock - 2, 0)
                else:
                    transferable_qty = net_stock

                if transferable_qty > 0:
                    sources.append(_make_source(row, transferable_qty, 2, 'Local店舖全轉出',
                                                store_type=type_series.loc[row.name]))

        # D2模式：RF完全不做轉出，僅ND清貨轉出
        if mode == self.mode_d2:
            sources.sort(key=lambda x: x['priority'])
            return sources

        # 優先級2：RF類型轉出
        rf_sources = group_df[group_df['RP Type'] == 'RF']

        # 找出該Article+OM組合中的最高有效銷量（用於避免從最高動銷店轉出）
        max_sold_qty = _compute_max_protected_sold(rf_sources)

        rf_source_count_before_filter = 0
        rf_source_count_after_filter = 0

        for _, row in rf_sources.iterrows():
            rf_source_count_before_filter += 1

            if self._is_b_tourist_no_source_mode(mode) and type_series is not None and type_series.loc[row.name] == 'T':
                continue

            if self._is_b_special_mode(mode) and type_series is not None:
                if type_series.loc[row.name] == 'L':
                    last_month_sold = int(row['Last Month Sold Qty'])
                    mtd_sold = int(row['MTD Sold Qty'])
                    if max(last_month_sold, mtd_sold) <= 2:
                        continue
            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            effective_sold = int(row['Effective Sold Qty'])

            # 條件1：(庫存+在途) > Safety Stock
            is_stock_above_safety = total_available > safety_stock

            # 條件2：不是最高銷量店鋪（保護最高動銷店）
            is_not_highest_sold = effective_sold < max_sold_qty

            # 不符合前置條件則略過
            # C1微調：允許低於Safety，但必須可在轉後保留至少2件。
            if mode == self.mode_c1:
                if not (int(row['SaSa Net Stock']) > 2 and is_not_highest_sold):
                    continue
            else:
                if not (is_stock_above_safety and is_not_highest_sold):
                    continue

            rf_source_count_after_filter += 1

            # 根據模式計算可轉出數量（已明確階梯：A < C < B）
            if mode == self.mode_a:
                # A模式(保守轉貨)
                # 僅動用明顯過剩庫存，嚴格不跌破 Safety Stock
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限：20% total_available，至少 2 件
                upper_limit = max(int(total_available * A_MODE_PERCENTAGE_CAP), A_MODE_MIN_TRANSFER)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 僅當仍維持 >= Safety Stock 才允許轉出
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                    # 若轉出僅1件且淨庫存餘3件以上，上調至2件 (避免單件調貨；放寬Safety Stock -1)
                    if actual_transferable == 1 and remaining_stock >= 3:
                        bump_remaining = int(row['SaSa Net Stock']) - 2
                        # 放寬安全線: bump_remaining >= safety_stock - 1
                        # 等價於 remaining_stock >= safety_stock (原始已通過), 故此處僅檢查上限
                        if 2 <= upper_limit:
                            actual_transferable = 2
                            remaining_stock = bump_remaining
                else:
                    continue

            elif mode in (self.mode_c, self.mode_c1, self.mode_c2):
                # C模式(重點補0) / C1模式(只補0/1) / C2模式(附加C跨OM重點補0)
                # 中等強度，小量精準支援 0 / 低庫存店，不做大規模抽貨。
                if mode == self.mode_c1:
                    # C1：允許低於Safety Stock，以淨庫存-2為基準（至少保留2件）
                    base_transferable = int(row['SaSa Net Stock']) - 2
                else:
                    base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限設計：
                # - 比例：最多 30% total_available
                # - 件數：最多 3 件
                # - 並允許至少 1 件（支援補0微調貨）
                ratio_cap = int(total_available * C_MODE_PERCENTAGE_CAP)
                abs_cap = C_MODE_ABS_CAP
                # 有效上限不能為負
                capped_ratio = max(ratio_cap, 0)
                raw_upper = min(capped_ratio, abs_cap) if capped_ratio > 0 else abs_cap
                upper_limit = max(2, raw_upper) if mode == self.mode_c1 else max(1, raw_upper)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 類型標記：
                # - 若仍 >= Safety → RF過剩轉出（風險低）
                # - 若略低於 Safety → RF加強轉出（為重點補0作有限犧牲）
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                else:
                    source_type = 'RF加強轉出'

            else:
                # B模式(加強轉貨) / B2模式(附加B) / B3模式(附加B跨OM)
                # 最 aggressive：最大釋放，多於 C 模式，並可在可控範圍下下探 Safety。
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                # 上限：最多 50% total_available，至少 2 件
                upper_limit = max(int(total_available * B_MODE_PERCENTAGE_CAP), B_MODE_MIN_TRANSFER)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable <= 0:
                    continue

                remaining_stock = int(row['SaSa Net Stock']) - actual_transferable

                # 類型標記：
                # - 若仍 >= Safety → RF過剩轉出
                # - 若 < Safety → RF加強轉出（接受更強調撥出）
                if remaining_stock >= safety_stock:
                    source_type = 'RF過剩轉出'
                else:
                    source_type = 'RF加強轉出'

            # 加入可轉出來源（所有模式共用）
            if actual_transferable > 0:
                # C1模式：避免只可轉出1件的來源參與配對
                if mode == self.mode_c1 and actual_transferable < 2:
                    continue

                last_month_sold = int(row['Last Month Sold Qty'])
                sources.append(_make_source(row, int(actual_transferable), 2, source_type,
                                            store_type=type_series.loc[row.name] if type_series is not None else ''))

        if rf_source_count_before_filter > 0 and rf_source_count_after_filter == 0:
            logger.warning(
                f"[P1-1] RF sources全部被過濾: Article={group_df['Article'].iloc[0] if not group_df.empty else '?'}, "
                f"mode={mode}, RF總數={rf_source_count_before_filter}, "
                f"max_sold_qty={'inf' if max_sold_qty == float('inf') else max_sold_qty}"
            )

        # 按優先級排序（ND優先，RF其次）
        sources.sort(key=lambda x: x['priority'])

        return sources
    
    def identify_destinations(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        識別接收候選店鋪
        
        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式

        Returns:
            接收候選店鋪列表
        """
        if self._is_simplified_sku_mode(mode):
            return self._dests_simplified_sku(group_df)
        if self._is_nd_transfer_mode(mode):
            return self._dests_nd_mode(group_df)
        if mode in (self.mode_f, self.mode_f_target_only):
            return self._dests_f_mode(group_df, mode)
        if mode in (self.mode_e1, self.mode_e1b, self.mode_e2):
            return self._dests_e_mode(group_df, mode)
        if self._is_b_special_mode(mode):
            return self._dests_b_special(group_df)
        if self._is_d_family_mode(mode):
            return self._dests_d_mode(group_df)
        if mode == self.mode_c1:
            return self._dests_c1_mode(group_df)
        return self._dests_general(group_df, mode)

    def _dests_simplified_sku(self, group_df: pd.DataFrame) -> List[Dict]:
        destinations: List[Dict] = []
        rf_stores = group_df[group_df['RP Type'] == 'RF']
        for _, row in rf_stores.iterrows():
            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            last_two_month_sold = _safe_get_last2m(row)
            cap = max(safety_stock * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last_two_month_sold * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)
            if total_available >= cap:
                continue
            needed_qty = cap - total_available
            if needed_qty <= 0:
                continue
            destinations.append(_make_dest(row, needed_qty, 1, '精簡SKU接收', cap,
                                            max_receive_qty=needed_qty))
        destinations.sort(key=lambda x: x['priority'])
        return destinations

    def _dests_nd_mode(self, group_df: pd.DataFrame) -> List[Dict]:
        destinations: List[Dict] = []
        rf_stores = group_df[group_df['RP Type'] == 'RF']
        nd_stores = group_df[group_df['RP Type'] == 'ND']

        for _, row in rf_stores.iterrows():
            is_no_stock = int(row['SaSa Net Stock']) == 0
            has_sales = int(row['Effective Sold Qty']) > 0
            if is_no_stock and has_sales:
                needed_qty = int(row['Safety Stock'])
                if needed_qty <= 0:
                    needed_qty = 2
                destinations.append(_make_dest(row, needed_qty, 1, 'RF緊急缺貨補貨', needed_qty,
                                                max_receive_qty=needed_qty,
                                                total_sales=int(row['Last Month Sold Qty']) + int(row['MTD Sold Qty'])))

        for _, row in nd_stores.iterrows():
            last_month_sold = int(row['Last Month Sold Qty'])
            mtd_sold = int(row['MTD Sold Qty'])
            total_sales = last_month_sold + mtd_sold
            if total_sales <= 0:
                continue
            max_receive = ND_RECEIVE_MULTIPLIER * total_sales
            current_stock = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            if current_stock >= max_receive:
                continue
            needed_qty = max_receive - current_stock
            destinations.append(_make_dest(row, needed_qty, 2, 'ND潛在缺貨接收', max_receive,
                                            max_receive_qty=max_receive,
                                            total_sales=total_sales))

        destinations.sort(key=lambda x: (x['priority'], -x.get('total_sales', 0)))
        return destinations

    def _dests_f_mode(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        destinations: List[Dict] = []
        target_series = self._parse_target_series(group_df)

        for idx, row in group_df.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            target_value = target_series.loc[idx]
            rp_type = row['RP Type']

            if pd.notna(target_value) and target_value > 0:
                target_qty = int(target_value)
                dest_type = 'F指定模式目標接收' if mode == self.mode_f_target_only else 'F模式目標接收'
                destinations.append(_make_dest(row, target_qty, 1, dest_type, target_qty))
                continue

            if rp_type == 'ND':
                continue
            if mode == self.mode_f_target_only:
                continue

            if total_available <= 1 and (int(row['Safety Stock']) > 0 or int(row['Effective Sold Qty']) > 0):
                target_qty = max(int(row['Safety Stock'] * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
                needed_qty = target_qty - total_available
                if needed_qty > 0:
                    destinations.append(_make_dest(row, needed_qty, 2, '重點補0', target_qty))

        destinations.sort(key=lambda x: x['priority'])
        return destinations

    def _dests_e_mode(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        destinations: List[Dict] = []
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        if 'Type' in rf_destinations.columns:
            type_series = rf_destinations['Type'].astype(str).str.upper()
        else:
            type_series = pd.Series("", index=rf_destinations.index)

        for _, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            safety_stock = int(row['Safety Stock'])
            max_can_receive = max(int(safety_stock * SAFETY_RECEIVE_MULTIPLIER), MIN_RECEIVE_FLOOR)

            if total_available < max_can_receive:
                needed_qty = max_can_receive - total_available
                sales_total = int(row['Last Month Sold Qty']) + int(row['MTD Sold Qty'])

                if mode == self.mode_e1b:
                    store_type = type_series.loc[row.name]
                    if store_type == 'T':
                        priority, dest_type = (1, 'E1b遊客區店舖 高銷量優先') if sales_total > 0 else (3, 'E1b遊客區店舖 Safety優先')
                    elif store_type == 'M':
                        priority, dest_type = (2, 'E1b混合型店舖 高銷量優先') if sales_total > 0 else (4, 'E1b混合型店舖 Safety優先')
                    else:
                        priority, dest_type = 5, 'E1b其他類型店舖'
                else:
                    priority, dest_type = 1, 'E模式接收'

                destinations.append(_make_dest(row, int(needed_qty), priority, dest_type, max_can_receive,
                                                max_receive_qty=max_can_receive))

        if mode == self.mode_e1b:
            def e1b_sort_key(item: Dict) -> Tuple[int, int, int]:
                if item['priority'] in (1, 2):
                    return (item['priority'], -int(item.get('effective_sold_qty', 0)), 0)
                return (item['priority'], -int(item.get('safety_stock', 0)), 0)
            destinations.sort(key=e1b_sort_key)
        else:
            destinations.sort(key=lambda x: x['priority'])
        return destinations

    def _dests_b_special(self, group_df: pd.DataFrame) -> List[Dict]:
        destinations: List[Dict] = []
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        if 'Type' in rf_destinations.columns:
            type_series = rf_destinations['Type'].astype(str).str.upper()
        else:
            type_series = pd.Series("", index=rf_destinations.index)

        for idx, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            safety_stock = int(row['Safety Stock'])
            max_can_receive = max(safety_stock * SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR)

            if total_available >= safety_stock:
                continue

            sales_total = int(row['Last Month Sold Qty']) + int(row['MTD Sold Qty'])
            store_type = type_series.loc[idx]

            if store_type == 'T':
                priority, dest_type = (1, '遊客區店舖 高銷量優先') if sales_total > 0 else (3, '遊客區店舖 Safety優先')
            elif store_type == 'M':
                priority, dest_type = (2, '混合型店舖 高銷量優先') if sales_total > 0 else (4, '混合型店舖 Safety優先')
            else:
                priority, dest_type = 4, '其他類型 Safety優先'

            needed_qty = safety_stock - total_available
            needed_qty = min(needed_qty, max_can_receive - total_available)
            if needed_qty <= 0:
                continue

            destinations.append(_make_dest(row, int(needed_qty), priority, dest_type, max_can_receive,
                                            max_receive_qty=max_can_receive,
                                            store_type=store_type))

        def b2_sort_key(item: Dict) -> Tuple[int, int, int]:
            if item['priority'] in (1, 2):
                return (item['priority'], -int(item.get('effective_sold_qty', 0)), 0)
            return (item['priority'], -int(item.get('safety_stock', 0)), 0)

        destinations.sort(key=b2_sort_key)
        return destinations

    def _dests_d_mode(self, group_df: pd.DataFrame) -> List[Dict]:
        destinations: List[Dict] = []
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        for _, row in rf_destinations.iterrows():
            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            is_no_stock = int(row['SaSa Net Stock']) == 0
            has_sales_history = int(row['Effective Sold Qty']) > 0

            if is_no_stock and has_sales_history:
                needed_qty = max(safety_stock, 2) - total_available
                if needed_qty <= 0:
                    continue
                max_receive = max(safety_stock, 2)
                destinations.append(_make_dest(row, needed_qty, 1, '緊急缺貨補貨', max_receive,
                                                max_receive_qty=max_receive))
                continue

            is_insufficient_stock = total_available < safety_stock
            if is_insufficient_stock:
                needed_qty = safety_stock - total_available
                destinations.append(_make_dest(row, needed_qty, 2, '潛在缺貨補貨', safety_stock,
                                                max_receive_qty=safety_stock))

        destinations.sort(key=lambda x: x['priority'])
        return destinations

    def _dests_c1_mode(self, group_df: pd.DataFrame) -> List[Dict]:
        destinations: List[Dict] = []
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        for _, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            if total_available > 1:
                continue
            if int(row['Safety Stock']) <= 0 and int(row['Effective Sold Qty']) <= 0:
                continue
            target_qty = max(int(row['Safety Stock'] * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
            needed_qty = target_qty - total_available
            if needed_qty <= 0:
                continue
            destinations.append(_make_dest(row, int(needed_qty), 1, '重點補0', int(target_qty)))
        destinations.sort(key=lambda x: x['priority'])
        return destinations

    def _dests_general(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        destinations: List[Dict] = []
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        
        for _, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            
            if mode in (self.mode_c, self.mode_c2) and total_available <= 1 and (int(row['Safety Stock']) > 0 or int(row['Effective Sold Qty']) > 0):
                target_qty = max(int(row['Safety Stock'] * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
                needed_qty = target_qty - total_available
                if needed_qty > 0:
                    destinations.append(_make_dest(row, int(needed_qty), 1, '重點補0', int(target_qty)))
                continue
            
            is_no_stock = row['SaSa Net Stock'] == 0
            has_sales_history = row['Effective Sold Qty'] > 0
            
            if is_no_stock and has_sales_history:
                needed_qty = row['Safety Stock']
                destinations.append(_make_dest(row, int(needed_qty), 1, '緊急缺貨補貨', int(needed_qty)))
                continue
            
            is_insufficient_stock = total_available < row['Safety Stock']
            if is_insufficient_stock:
                needed_qty = row['Safety Stock'] - total_available
                destinations.append(_make_dest(row, int(needed_qty), 2, '潛在缺貨補貨', int(row['Safety Stock'])))
        
        destinations.sort(key=lambda x: x['priority'])
        return destinations
    
    def match_transfers(self, article: str, om: str, sources: List[Dict], 
                       destinations: List[Dict], product_desc: str, mode: str) -> List[Dict]:
        """
        執行轉出與接收的匹配
        
        Args:
            article: 商品編號
            om: OM編號
            sources: 轉出候選店鋪列表
            destinations: 接收候選店鋪列表
            product_desc: 商品描述
            mode: 轉貨模式
            
        Returns:
            匹配成功的調貨建議列表
        """
        if self._is_b_special_mode(mode):
            return self._strategies['b_special'].match(sources, destinations, article, product_desc, mode)

        if mode in (self.mode_f, self.mode_f_target_only):
            return self._strategies['f_mode'].match(sources, destinations, article, product_desc, mode)
        
        if mode == self.mode_c2:
            return self._strategies['c2_mode'].match(sources, destinations, article, product_desc, mode)

        if self._is_simplified_sku_mode(mode):
            return self._strategies['simplified_sku'].match(sources, destinations, article, product_desc, mode)

        return _match_general_mode_impl(self, sources, destinations, article, om, product_desc, mode)

    def _compute_transfer_qty(self, source: Dict, dest: Dict, mode: str, current_received_qty: int) -> int:
        return _compute_transfer_qty_impl(self, source, dest, mode, current_received_qty)

    def _can_transfer(self, source: Dict, dest: Dict, mode: str, article: str,
                      transfer_sites: set, receive_sites: set, 
                      source_to_receive_sites: Dict, received_qty_by_site: Dict,
                      source_type_filter: Optional[str] = None) -> bool:
        return _can_transfer_impl(self, source, dest, mode, article, transfer_sites, receive_sites,
                                  source_to_receive_sites, received_qty_by_site, source_type_filter)

    def _match_by_priority(self, sources: List[Dict], destinations: List[Dict], 
                          recommendations: List[Dict], article: str, group_id: str, 
                          product_desc: str, source_priority: int, dest_priority: int,
                          transfer_sites: set, received_qty_by_site: Dict,
                          mode: str,
                          source_type_filter: Optional[str] = None,
                          dest_type_filter: Optional[str] = None,
                          receive_sites: set = None,
                          source_to_receive_sites: Optional[Dict[str, set]] = None,
                          max_receive_sites_per_source: Optional[int] = None):
        _match_by_priority_impl(self, sources, destinations, recommendations, article, group_id,
                                product_desc, source_priority, dest_priority, transfer_sites,
                                received_qty_by_site, mode, source_type_filter, dest_type_filter,
                                receive_sites, source_to_receive_sites, max_receive_sites_per_source)

    def _get_record_sales_total(self, rec: Dict[str, Any], prefix: str) -> int:
        return _get_record_sales_total_impl(rec, prefix)

    def _infer_source_rp_type(self, source_type: str) -> str:
        return _infer_source_rp_type_impl(source_type)

    def _refresh_recommendation_fields(self, recommendations: List[Dict], mode: str) -> None:
        _refresh_recommendation_fields_impl(recommendations, mode, self._create_recommendation_note)

    def _optimize_single_piece_transfers(self, recommendations: List[Dict], mode: str) -> List[Dict]:
        return _optimize_single_piece_transfers_impl(recommendations, mode, self._create_recommendation_note)
    
    def generate_transfer_recommendations(self, df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        生成所有調貨建議
        
        Args:
            df: 預處理後的DataFrame
            mode: A模式(保守轉貨)、B模式(加強轉貨)、B2模式(附加B特別模式)、B3模式(附加B跨OM特別模式)、C模式(重點補0)、D模式(清貨轉貨)、E1模式(強制轉出)、E1b模式(強制轉出優先類型接收)、E2模式(強制轉出跨OM)、F模式(目標優化)或F2模式(F指定模式)
            
        Returns:
            調貨建議列表
        """
        logger.info(f"開始生成調貨建議 - {mode}")
        
        # 驗證模式
        if mode not in self._ALL_MODES:
            raise ValueError(f"無效的轉貨模式: {mode}")

        # E模式必須存在ALL欄位；若不存在則直接拋出明確錯誤
        if mode in (self.mode_e1, self.mode_e1b, self.mode_e2) and 'ALL' not in df.columns:
            raise ValueError("E模式需要ALL欄位")
        
        # 根據模式選擇分組方式
        if mode in self._CROSS_OM_GROUPING_MODES:
            grouped = df.groupby(['Article'])
        else:
            grouped = df.groupby(['Article', 'OM'])
        
        all_recommendations = []

        # 預先建立全局 (Article, Site) → Safety Stock / MOQ 索引，避免迴圈內重複建立（效能優化）
        _index_cols = [c for c in ['Safety Stock', 'MOQ'] if c in df.columns]
        if _index_cols:
            article_site_index = df.set_index(['Article', 'Site'])[_index_cols]
        else:
            article_site_index = pd.DataFrame(index=pd.MultiIndex.from_tuples([]))
        
        # F2模式：預先計算全域有Target>0的店舖集合，避免Target店舖任何Article成為轉出源
        target_stores = set()
        if mode == self.mode_f_target_only:
            target_series_full = self._parse_target_series(df)
            if 'Target' in df.columns:
                target_mask = target_series_full > 0
                target_stores = set(
                    df.loc[target_mask.fillna(False), 'Site']
                    .astype(str).str.strip().str.upper()
                )
        
        for group_keys, group_df in grouped:
            # 獲取商品描述
            product_desc = group_df['Article Description'].iloc[0] if 'Article Description' in group_df.columns else ""

            # 獲取品牌（Product Hierarchy = Brand = 品牌）
            product_brand = ""
            for brand_col in ['Product Hierarchy', 'Brand', '品牌']:
                if brand_col in group_df.columns:
                    brand_series = group_df[brand_col].dropna().astype(str).str.strip()
                    brand_series = brand_series[brand_series != '']
                    if not brand_series.empty:
                        product_brand = brand_series.iloc[0]
                        break
            
            # 識別轉出候選店鋪
            sources = self.identify_sources(
                group_df, mode,
                protected_sites=target_stores if mode == self.mode_f_target_only else None
            )
            
            # 識別接收候選店鋪
            destinations = self.identify_destinations(group_df, mode)
            
            # 特殊模式處理：從destinations中過濾掉同時作為轉出源的店鋪
            if mode in self._SOURCE_FILTER_MODES:
                source_sites = set([s['site'] for s in sources])
                destinations = [d for d in destinations if d['site'] not in source_sites]
            
            # 執行匹配
            if mode in self._CROSS_OM_MATCHING_MODES:
                article = group_keys[0] if isinstance(group_keys, (list, tuple)) else group_keys
                om = "Multiple"  # 跨OM模式下OM由source/dest決定
            else:
                article, om = group_keys
            
            # E1/E1b模式：僅同OM配對
            if mode in (self.mode_e1, self.mode_e1b):
                recommendations = self._strategies['e1_mode'].match(sources, destinations, article, product_desc, mode, om=om)
            # E2模式：跨OM強制轉出
            elif mode == self.mode_e2:
                recommendations = self._strategies['e2_mode'].match(
                    sources, destinations, article, product_desc, mode, om=om, group_df=group_df)
            elif mode in (self.mode_f, self.mode_f_target_only):
                recommendations = self._strategies['f_mode'].match(sources, destinations, article, product_desc, mode)
            elif mode == self.mode_c2:
                recommendations = self._strategies['c2_mode'].match(sources, destinations, article, product_desc, mode)
            # ND1 模式：同 OM 配對
            elif mode == self.mode_nd1:
                recommendations = self._strategies['nd_mode'].match(sources, destinations, article, product_desc, mode, om=om)
            # ND2 模式：跨 OM 配對 + Windy 限制
            elif mode == self.mode_nd2:
                recommendations = self._strategies['nd_mode'].match(sources, destinations, article, product_desc, mode, om=om)
            # 精簡SKU模式
            elif self._is_simplified_sku_mode(mode):
                recommendations = self._strategies['simplified_sku'].match(sources, destinations, article, product_desc, mode)
            else:
                recommendations = self.match_transfers(article, om, sources, destinations, product_desc, mode)
            
            for rec in recommendations:
                # 統一補上品牌欄位，供Excel輸出使用
                rec['Product Hierarchy'] = product_brand
                rec['Brand'] = product_brand

            # 更新安全庫存和MOQ信息（使用迴圈外預建索引，O(1) 查詢）
            if recommendations and not article_site_index.empty:
                for rec in recommendations:
                    key = (rec['Article'], rec['Transfer Site'])
                    if key in article_site_index.index:
                        if 'Safety Stock' in article_site_index.columns:
                            rec['Safety Stock'] = article_site_index.at[key, 'Safety Stock']
                        if 'MOQ' in article_site_index.columns:
                            rec['MOQ'] = article_site_index.at[key, 'MOQ']
            
            all_recommendations.extend(recommendations)
        
        all_recommendations = self._optimize_single_piece_transfers(all_recommendations, mode)

        logger.info(f"共生成 {len(all_recommendations)} 條調貨建議")
        
        self.transfer_recommendations = all_recommendations
        return all_recommendations
    
    def perform_quality_checks(self, df: pd.DataFrame, mode: str = '') -> bool:
        from services.quality_checks import run_quality_checks
        logger.info("開始執行質量檢查")
        skip_nd_check = self._is_nd_transfer_mode(mode) or mode in (self.mode_f, self.mode_f_target_only)
        passed, errors = run_quality_checks(self.transfer_recommendations, df, skip_nd_check)
        self.quality_check_passed = passed
        self.quality_errors = errors
        if passed:
            logger.info("質量檢查通過")
        else:
            logger.error(f"質量檢查失敗，發現 {len(errors)} 個錯誤")
            for error in errors:
                logger.error(error)
        return passed

    def get_transfer_statistics(self) -> Dict:
        from services.statistics import compute_transfer_statistics
        return compute_transfer_statistics(self.transfer_recommendations)

    def _create_recommendation_note(self, source: Dict, dest: Dict, current_received_qty: int, transfer_qty: int, mode: str) -> str:
        from services.notes import create_recommendation_note
        mode_info = {
            'is_d_family': self._is_d_family_mode(mode),
            'is_b_special': self._is_b_special_mode(mode),
            'is_b_l_retain': self._is_b_l_retain_mode(mode),
            'is_simplified_sku': self._is_simplified_sku_mode(mode),
            'mode_e1': self.mode_e1,
            'mode_e1b': self.mode_e1b,
            'mode_e2': self.mode_e2,
            'mode_d2': self.mode_d2,
            'mode_simplified_sku_same': self.mode_simplified_sku_same,
        }
        return create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode, mode_info)
