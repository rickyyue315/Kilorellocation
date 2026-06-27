"""
業務邏輯模組 v2.26.0
實現調貨規則、源/目的地識別和匹配算法
支持二十八模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C1(重點補0-只補0/1(或自選數量))/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/F3(目標性補0)/NST(New Shop Target調貨)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/ND3(ND限同OM轉貨補0)/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001)
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Tuple, Optional, Set  # noqa: F401 — Set used in signature defaults
import logging

from config import (
    A_MODE_PERCENTAGE_CAP, A_MODE_MIN_TRANSFER,
    B_MODE_PERCENTAGE_CAP, B_MODE_MIN_TRANSFER,
    C_MODE_PERCENTAGE_CAP, C_MODE_ABS_CAP,
    C1_MODE_MIN_TRANSFER, C1_MODE_DEFAULT_CEILING,
    SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR,
    F_TARGET_MULTIPLIER, F_TARGET_FLOOR,
    SIMPLIFIED_SKU_RECEIVE_MULTIPLIER,
    ND_RECEIVE_MULTIPLIER,
    ND3_KEEP_STOCK,
    D2_MAX_RECEIVE_SITES_PER_SOURCE, D2_NEEDED_QTY_MULTIPLIER,
)
from services.recommendation_factory import build_recommendation, apply_transfer
from services.target_utils import parse_target_series
from services.prioritizer import assign_priority, PRIORITY_ORDER
from services.matching_engine import (
    compute_transfer_qty as _compute_transfer_qty_impl,
    can_transfer as _can_transfer_impl,
    match_by_priority as _match_by_priority_impl,
    match_general_mode as _match_general_mode_impl,
    match_d2_mode as _match_d2_mode_impl,
)
from services.post_processing import (
    get_record_sales_total as _get_record_sales_total_impl,
    infer_source_rp_type as _infer_source_rp_type_impl,
    refresh_recommendation_fields as _refresh_recommendation_fields_impl,
    optimize_single_piece_transfers as _optimize_single_piece_transfers_impl,
)
from services.statistics import capture_pre_match_snapshot
from strategies.predicates import is_hd_to_hk_restricted
from models.mode_registry import (
    MODE_DEFS,
    get_mode_families,
    get_all_mode_names,
    get_cross_om_grouping_names,
    get_cross_om_matching_names,
    get_source_filter_names,
    get_codes_needing_column,
)
from services.perf_timer import perf_timer
from services.source_dest_factory import (
    safe_get_last2m,
    make_source as _make_source,
    make_dest as _make_dest,
    compute_max_protected_sold as _compute_max_protected_sold,
)

# 設置日誌
logger = logging.getLogger(__name__)


class TransferLogic:
    """調貨業務邏輯類 v2.26.0"""
    
    def __init__(self, b_special_max_receive_sites_per_source: Optional[int] = None,
                 f2_allow_hd_transfer: bool = False,
                 d2_site_limit_mode: str = "unlimited",
                 c1_threshold: int = 1,
                 c1_ceiling: int = C1_MODE_DEFAULT_CEILING,
                 f_fulfill_small_first: bool = False,
                 nst_max_source_shops: Optional[int] = None):
        self.transfer_recommendations = []
        self._pre_match_snapshots = []
        self.quality_check_passed = True
        self.quality_errors = []
        self.b_special_max_receive_sites_per_source = (
            b_special_max_receive_sites_per_source
            if isinstance(b_special_max_receive_sites_per_source, int) and b_special_max_receive_sites_per_source > 0
            else None
        )
        self.f2_allow_hd_transfer = f2_allow_hd_transfer
        self.d2_site_limit_mode = d2_site_limit_mode
        self.c1_threshold = c1_threshold
        self.c1_ceiling = c1_ceiling
        self.f_fulfill_small_first = f_fulfill_small_first
        self.nst_max_source_shops = (
            nst_max_source_shops
            if isinstance(nst_max_source_shops, int) and nst_max_source_shops > 0
            else None
        )
        self._mode_by_name = {d.name: d for d in MODE_DEFS}
        self._mode_by_code = {d.code: d for d in MODE_DEFS}
        for d in MODE_DEFS:
            setattr(self, d.attr_name, d.name)

        self.MODE_FAMILIES = get_mode_families()

        self._mode_info_cache = {}
        for d in MODE_DEFS:
            families = d.families
            self._mode_info_cache[d.name] = {
                'is_d_family': 'd_family' in families,
                'is_b_special': 'b_special' in families,
                'is_b_l_retain': 'b_l_retain' in families,
                'is_simplified_sku': 'simplified_sku' in families,
                'mode_e1': self.mode_e1,
                'mode_e1b': self.mode_e1b,
                'mode_e2': self.mode_e2,
                'mode_d2': self.mode_d2,
                'mode_simplified_sku_same': self.mode_simplified_sku_same,
                'mode_simplified_sku_return_d001': self.mode_simplified_sku_return_d001,
                'd2_site_limit_mode': self.d2_site_limit_mode,
            }

        self._ALL_MODES = get_all_mode_names()
        self._CROSS_OM_GROUPING_MODES = get_cross_om_grouping_names()
        self._SOURCE_FILTER_MODES = get_source_filter_names()
        self._CROSS_OM_MATCHING_MODES = get_cross_om_matching_names()

        self._strategies = self._init_strategies()

    def _init_strategies(self):
        from strategies.simplified_sku import SimplifiedSKUStrategy
        from strategies.simplified_sku_return_d001 import SimplifiedSKUReturnD001Strategy
        from strategies.c2_mode import C2ModeStrategy
        from strategies.f_mode import FModeStrategy
        from strategies.nst_mode import NewShopTargetStrategy
        from strategies.e1_mode import E1ModeStrategy
        from strategies.e2_mode import E2ModeStrategy
        from strategies.nd_mode import NDModeStrategy
        from strategies.b_special import BSpecialStrategy
        return {
            'simplified_sku': SimplifiedSKUStrategy(),
            'simplified_sku_return_d001': SimplifiedSKUReturnD001Strategy(),
            'c2_mode': C2ModeStrategy(),
            'f_mode': FModeStrategy(
                create_note=self._create_recommendation_note,
                f2_allow_hd_transfer=self.f2_allow_hd_transfer,
                f_fulfill_small_first=self.f_fulfill_small_first,
            ),
            'nst_mode': NewShopTargetStrategy(
                create_note=self._create_recommendation_note,
                nst_allow_hd_transfer=self.f2_allow_hd_transfer,
                f_fulfill_small_first=self.f_fulfill_small_first,
                nst_max_source_shops=self.nst_max_source_shops,
            ),
            'e1_mode': E1ModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
            'e2_mode': E2ModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
                c1_ceiling=self.c1_ceiling,
            ),
            'nd_mode': NDModeStrategy(
                create_note=self._create_recommendation_note,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
            ),
            'b_special': BSpecialStrategy(
                match_by_priority=self._match_by_priority,
                max_receive_sites_per_source=self.b_special_max_receive_sites_per_source,
                is_b_tourist_no_source_fn=self._is_b_tourist_no_source_mode,
                is_b_l_retain_fn=self._is_b_l_retain_mode,
                is_d_family_fn=self._is_d_family_mode,
                mode_d2_name=self.mode_d2,
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

    @perf_timer("identify_sources")
    def identify_sources(self, group_df: pd.DataFrame, mode: str, protected_sites: Optional[Set[str]] = None) -> List[Dict]:
        mode_def = self._mode_by_name.get(mode)
        if mode_def and mode_def.source_method:
            if mode_def.strategy_key:
                strategy = self._strategies[mode_def.strategy_key]
                return strategy.identify_sources(group_df, mode, protected_sites)
            method = getattr(self, mode_def.source_method)
            return method(group_df)
        return self._sources_general(group_df, mode)

    def _compute_rf_transferable(self, row, mode: str, total_available: int,
                                  safety_stock: int) -> Optional[Tuple[int, str]]:
        if mode == self.mode_a:
            base_transferable = total_available - safety_stock
            if base_transferable <= 0:
                return None

            upper_limit = max(int(total_available * A_MODE_PERCENTAGE_CAP), A_MODE_MIN_TRANSFER)
            actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
            if actual_transferable <= 0:
                return None

            remaining_stock = int(row['SaSa Net Stock']) - actual_transferable
            if remaining_stock >= safety_stock:
                source_type = 'RF過剩轉出'
                if actual_transferable == 1 and remaining_stock >= 3:
                    actual_transferable = 2
            else:
                return None
            return (actual_transferable, source_type)

        elif mode in (self.mode_c, self.mode_c1, self.mode_c2):
            if mode == self.mode_c1:
                base_transferable = int(row['SaSa Net Stock']) - 2
            else:
                base_transferable = total_available - safety_stock
            if base_transferable <= 0:
                return None

            ratio_cap = int(total_available * C_MODE_PERCENTAGE_CAP)
            abs_cap = self.c1_ceiling if mode in (self.mode_c, self.mode_c1, self.mode_c2) else C_MODE_ABS_CAP
            capped_ratio = max(ratio_cap, 0)
            raw_upper = min(capped_ratio, abs_cap) if capped_ratio > 0 else abs_cap
            upper_limit = max(2, raw_upper) if mode == self.mode_c1 else max(1, raw_upper)

            actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
            if actual_transferable <= 0:
                return None

            remaining_stock = int(row['SaSa Net Stock']) - actual_transferable
            source_type = 'RF過剩轉出' if remaining_stock >= safety_stock else 'RF加強轉出'
            return (actual_transferable, source_type)

        else:
            base_transferable = total_available - safety_stock
            if base_transferable <= 0:
                return None

            upper_limit = max(int(total_available * B_MODE_PERCENTAGE_CAP), B_MODE_MIN_TRANSFER)
            actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
            if actual_transferable <= 0:
                return None

            remaining_stock = int(row['SaSa Net Stock']) - actual_transferable
            source_type = 'RF過剩轉出' if remaining_stock >= safety_stock else 'RF加強轉出'
            return (actual_transferable, source_type)

    def _sources_general(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        sources: List[Dict] = []
        if self._is_b_special_mode(mode):
            if 'Type' in group_df.columns:
                type_series = group_df['Type'].astype(str).str.upper()
            else:
                type_series = pd.Series("", index=group_df.index)
        else:
            type_series = None

        from strategies.b_special import identify_nd_sources, identify_b_special_type_l_sources

        sources.extend(identify_nd_sources(
            group_df, mode, type_series,
            is_b_tourist_no_source=self._is_b_tourist_no_source_mode(mode),
            is_d_family=self._is_d_family_mode(mode),
            mode_d2=self.mode_d2,
        ))

        if self._is_b_special_mode(mode):
            sources.extend(identify_b_special_type_l_sources(
                group_df, mode, type_series,
                is_b_l_retain=self._is_b_l_retain_mode(mode),
            ))

        if mode == self.mode_d2:
            sources.sort(key=lambda x: x['priority'])
            return sources

        rf_sources = group_df[group_df['RP Type'] == 'RF']
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

            is_stock_above_safety = total_available > safety_stock
            is_not_highest_sold = effective_sold < max_sold_qty

            if mode == self.mode_c1:
                if not (int(row['SaSa Net Stock']) > 2 and is_not_highest_sold):
                    continue
            else:
                if not (is_stock_above_safety and is_not_highest_sold):
                    continue

            rf_source_count_after_filter += 1

            result = self._compute_rf_transferable(row, mode, total_available, safety_stock)
            if result is None:
                continue

            actual_transferable, source_type = result

            if actual_transferable > 0:
                if mode == self.mode_c1 and actual_transferable < C1_MODE_MIN_TRANSFER:
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

        sources.sort(key=lambda x: x['priority'])
        return sources

    @perf_timer("identify_destinations")
    def identify_destinations(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        mode_def = self._mode_by_name.get(mode)
        if mode_def and mode_def.dest_method:
            if mode_def.strategy_key and mode_def.dest_method in ('_dests_f_mode', '_dests_e_mode', '_dests_b_special', '_dests_simplified_sku', '_dests_nd_mode', '_dests_nd3_mode'):
                strategy = self._strategies[mode_def.strategy_key]
                result = strategy.identify_destinations(group_df, mode)
                if result is not None:
                    return result
            if mode == self.mode_d2:
                if self.d2_site_limit_mode == "2site_optimized":
                    # 限制2間店舖接收（優化版）：target_qty 放大至 200%
                    from strategies.d_mode import identify_destinations_d2_mode
                    return identify_destinations_d2_mode(group_df, True)
                # 不限店舖數量（原有設定）或 限制2間店舖接收（原有設定）：target_qty 正常值
                from strategies.d_mode import identify_destinations_d_mode
                return identify_destinations_d_mode(group_df)
            if mode_def.dest_method == '_dests_d_mode':
                from strategies.d_mode import identify_destinations_d_mode
                return identify_destinations_d_mode(group_df)
            if mode_def.dest_method == '_dests_c1_mode':
                from strategies.c1_mode import identify_destinations_c1_mode
                return identify_destinations_c1_mode(group_df, self.c1_threshold)
        return self._dests_general(group_df, mode)

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
    
    @perf_timer("match_transfers")
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

        if mode in (self.mode_f, self.mode_f_target_only, self.mode_f3, self.mode_nst):
            if mode == self.mode_nst:
                return self._strategies['nst_mode'].match(sources, destinations, article, product_desc, mode)
            return self._strategies['f_mode'].match(sources, destinations, article, product_desc, mode)
        
        if mode == self.mode_c2:
            return self._strategies['c2_mode'].match(sources, destinations, article, product_desc, mode)

        if self._is_simplified_sku_mode(mode):
            return self._strategies['simplified_sku'].match(sources, destinations, article, product_desc, mode)

        if mode == self.mode_d2 and self.d2_site_limit_mode != "unlimited":
            # 限制2間店舖接收（原有設定/優化版）：使用 match_d2_mode（max_receive=2）
            return _match_d2_mode_impl(self, sources, destinations, article, om, product_desc, mode)

        # 不限店舖數量（原有設定）：使用 match_general_mode（無限制）
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
    
    @perf_timer("generate_transfer_recommendations")
    def generate_transfer_recommendations(self, df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        生成所有調貨建議
        
        Args:
            df: 預處理後的DataFrame
            mode: A模式(保守轉貨)、B模式(加強轉貨)、B2模式(附加B特別模式)、B3模式(附加B跨OM特別模式)、C模式(重點補0)、D模式(清貨轉貨)、E1模式(強制轉出)、E1b模式(強制轉出優先類型接收)、E2模式(強制轉出跨OM)、F模式(目標優化)、F2模式(F指定模式)、F3模式(目標性補0)、NST模式(New Shop Target調貨)、ND1模式(ND同OM轉貨)、ND2模式(ND混合OM轉貨)、ND3模式(ND限同OM轉貨補0)、精簡SKU模式
            
        Returns:
            調貨建議列表
        """
        logger.info(f"開始生成調貨建議 - {mode}")
        
        # 驗證模式
        if mode not in self._ALL_MODES:
            raise ValueError(f"無效的轉貨模式: {mode}")

        # E模式必須存在ALL欄位；若不存在則直接拋出明確錯誤
        mode_def = self._mode_by_name[mode]
        for col in mode_def.required_columns:
            if col not in df.columns:
                raise ValueError(f"{mode_def.code}模式需要{col}欄位")
        
        # 根據模式選擇分組方式
        if mode in self._CROSS_OM_GROUPING_MODES:
            grouped = df.groupby(['Article'])
        else:
            grouped = df.groupby(['Article', 'OM'])
        
        all_recommendations = []
        self._pre_match_snapshots = []

        # 預先建立全局 (Article, Site) → Safety Stock 索引，避免迴圈內重複建立（效能優化）
        _index_cols = [c for c in ['Safety Stock'] if c in df.columns]
        if _index_cols:
            temp = df.copy()
            temp['_site_key'] = temp['Site'].astype(str).str.strip().str.upper()
            article_site_index = temp.set_index(['Article', '_site_key'])[_index_cols]
        else:
            article_site_index = pd.DataFrame(index=pd.MultiIndex.from_tuples([]))
        
        # F2模式：預先計算全域有Target>0的店舖集合，避免Target店舖任何Article成為轉出源
        target_stores = set()
        if mode in (self.mode_f_target_only, self.mode_f3, self.mode_nst):
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
                protected_sites=target_stores if mode in (self.mode_f_target_only, self.mode_f3, self.mode_nst) else None
            )
            
            # 識別接收候選店鋪
            destinations = self.identify_destinations(group_df, mode)
            
            # 特殊模式處理：從destinations中過濾掉同時作為轉出源的店鋪
            if mode in self._SOURCE_FILTER_MODES:
                source_sites = set([s['site'] for s in sources])
                destinations = [d for d in destinations if d['site'] not in source_sites]
            
            # 解析 article 和 om（快照和匹配都需要用到 article）
            if mode in self._CROSS_OM_MATCHING_MODES:
                article = group_keys[0] if isinstance(group_keys, (list, tuple)) else group_keys
                om = "Multiple"  # 跨OM模式下OM由source/dest決定
            else:
                article, om = group_keys
            
            # 拍攝 pre-match 快照（用於缺口報表）
            snap = capture_pre_match_snapshot(sources, destinations, article, mode)
            self._pre_match_snapshots.append(snap)

            # 執行匹配
            strategy_key = mode_def.strategy_key
            if strategy_key:
                strategy = self._strategies[strategy_key]
                kwargs = {}
                if strategy_key in ('e1_mode', 'e2_mode', 'nd_mode'):
                    kwargs['om'] = om
                if strategy_key == 'e2_mode':
                    kwargs['group_df'] = group_df
                recommendations = strategy.match(sources, destinations, article, product_desc, mode, **kwargs)
            else:
                recommendations = self.match_transfers(article, om, sources, destinations, product_desc, mode)
            
            for rec in recommendations:
                # 統一補上品牌欄位，供Excel輸出使用
                rec['Product Hierarchy'] = product_brand
                rec['Brand'] = product_brand

            # 更新安全庫存信息（使用迴圈外預建索引，O(1) 查詢）
            if recommendations and not article_site_index.empty:
                for rec in recommendations:
                    transfer_key = (rec['Article'], str(rec['Transfer Site']).strip().upper())
                    if transfer_key in article_site_index.index:
                        if 'Safety Stock' in article_site_index.columns:
                            rec['Safety Stock'] = article_site_index.at[transfer_key, 'Safety Stock']
                    # 查找接收店舖的 Safety Stock
                    receive_key = (rec['Article'], str(rec['Receive Site']).strip().upper())
                    if receive_key in article_site_index.index:
                        if 'Safety Stock' in article_site_index.columns:
                            rec['Receive Safety Stock'] = article_site_index.at[receive_key, 'Safety Stock']
            
            all_recommendations.extend(recommendations)
        
        all_recommendations = self._optimize_single_piece_transfers(all_recommendations, mode)

        for rec in all_recommendations:
            rec['Priority'] = assign_priority(rec)

        all_recommendations.sort(
            key=lambda r: (
                PRIORITY_ORDER.get(r.get('Priority', '🟢低優先'), 99),
                -r.get('Transfer Qty', 0),
            )
        )

        self._refresh_recommendation_fields(all_recommendations, mode)

        logger.info(f"共生成 {len(all_recommendations)} 條調貨建議")
        
        self.transfer_recommendations = all_recommendations
        return all_recommendations
    
    def perform_quality_checks(self, df: pd.DataFrame, mode: str = '') -> bool:
        from services.quality_checks import run_quality_checks
        logger.info("開始執行質量檢查")
        skip_nd_check = self._is_nd_transfer_mode(mode) or mode in (self.mode_f, self.mode_f_target_only, self.mode_f3, self.mode_nst)
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

    def get_gap_report(self) -> Dict:
        from services.statistics import compute_gap_report
        return compute_gap_report(self._pre_match_snapshots, self.transfer_recommendations)

    def _create_recommendation_note(self, source: Dict, dest: Dict, current_received_qty: int, transfer_qty: int, mode: str) -> str:
        from services.notes import create_recommendation_note
        mode_info = self._mode_info_cache.get(mode)
        if mode_info is None:
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
                'mode_simplified_sku_return_d001': self.mode_simplified_sku_return_d001,
            }
            self._mode_info_cache[mode] = mode_info
        return create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode, mode_info)
