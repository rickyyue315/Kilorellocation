"""
B特別模式匹配策略（委派給 _match_by_priority 引擎）+ Source/Dest 識別邏輯
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pandas as pd

from strategies.base import BaseMatchStrategy
from services.matching_engine import prep_temp_lists
from services.source_dest_factory import make_source, make_dest
from config import SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR


def identify_nd_sources(
    group_df: pd.DataFrame,
    mode: str,
    type_series,
    is_b_tourist_no_source: bool,
    is_d_family: bool,
    mode_d2: str,
) -> List[Dict]:
    sources = []
    nd_sources = group_df[group_df['RP Type'] == 'ND']
    for _, row in nd_sources.iterrows():
        if is_b_tourist_no_source and type_series is not None and type_series.loc[row.name] == 'T':
            continue
        if row['SaSa Net Stock'] > 0:
            last_month_sold = int(row['Last Month Sold Qty'])
            mtd_sold = int(row['MTD Sold Qty'])

            if is_d_family and last_month_sold == 0 and mtd_sold == 0:
                source_type = 'ND清貨轉出'
            elif mode == mode_d2:
                continue
            else:
                source_type = 'ND轉出'

            source_store_type = type_series.loc[row.name] if type_series is not None else ''
            sources.append(make_source(row, int(row['SaSa Net Stock']), 1, source_type,
                                        store_type=source_store_type))
    return sources


def identify_b_special_type_l_sources(
    group_df: pd.DataFrame,
    mode: str,
    type_series,
    is_b_l_retain: bool,
) -> List[Dict]:
    sources = []
    type_l_sources = group_df[(type_series == 'L') & (group_df['RP Type'] == 'RF')]
    for _, row in type_l_sources.iterrows():
        last_month_sold = int(row['Last Month Sold Qty'])
        mtd_sold = int(row['MTD Sold Qty'])
        if max(last_month_sold, mtd_sold) > 2:
            continue

        net_stock = int(row['SaSa Net Stock'])
        if is_b_l_retain:
            transferable_qty = max(net_stock - 2, 0)
        else:
            transferable_qty = net_stock

        if transferable_qty > 0:
            sources.append(make_source(row, transferable_qty, 2, 'Local店舖全轉出',
                                        store_type=type_series.loc[row.name]))
    return sources


def identify_destinations_b_special(group_df: pd.DataFrame) -> List[Dict]:
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

        destinations.append(make_dest(row, int(needed_qty), priority, dest_type, max_can_receive,
                                       max_receive_qty=max_can_receive,
                                       store_type=store_type))

    def b2_sort_key(item: Dict) -> Tuple[int, int, int]:
        if item['priority'] in (1, 2):
            return (item['priority'], -int(item.get('effective_sold_qty', 0)), 0)
        return (item['priority'], -int(item.get('safety_stock', 0)), 0)

    destinations.sort(key=b2_sort_key)
    return destinations


class BSpecialStrategy(BaseMatchStrategy):
    def __init__(self, match_by_priority: Optional[Callable] = None,
                 max_receive_sites_per_source: Optional[int] = None,
                 is_b_tourist_no_source_fn: Optional[Callable] = None,
                 is_b_l_retain_fn: Optional[Callable] = None,
                 is_d_family_fn: Optional[Callable] = None,
                 mode_d2_name: str = ""):
        super().__init__()
        self._match_by_priority = match_by_priority
        self._max_receive_sites_per_source = max_receive_sites_per_source
        self._is_b_tourist_no_source_fn = is_b_tourist_no_source_fn or (lambda m: False)
        self._is_b_l_retain_fn = is_b_l_retain_fn or (lambda m: False)
        self._is_d_family_fn = is_d_family_fn or (lambda m: False)
        self._mode_d2_name = mode_d2_name

    def _get_type_series(self, group_df: pd.DataFrame):
        if 'Type' in group_df.columns:
            return group_df['Type'].astype(str).str.upper()
        return pd.Series("", index=group_df.index)

    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        type_series = self._get_type_series(group_df)
        sources = []
        sources.extend(identify_nd_sources(
            group_df, mode, type_series,
            is_b_tourist_no_source=self._is_b_tourist_no_source_fn(mode),
            is_d_family=self._is_d_family_fn(mode),
            mode_d2=self._mode_d2_name,
        ))
        sources.extend(identify_b_special_type_l_sources(
            group_df, mode, type_series,
            is_b_l_retain=self._is_b_l_retain_fn(mode),
        ))
        sources.sort(key=lambda x: x['priority'])
        return sources

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        return identify_destinations_b_special(group_df)

    def match(
        self,
        sources: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        article: str,
        product_desc: str,
        mode: str,
        om: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        recommendations = []

        temp_sources, temp_destinations = prep_temp_lists(sources, destinations)

        transfer_sites = set()
        receive_sites = set()
        received_qty_by_site = {}
        source_to_receive_sites = {}
        max_receive_sites_per_source = self._max_receive_sites_per_source

        mp = self._match_by_priority
        if mp is None:
            return recommendations

        rounds = [
            (1, 1, None), (1, 2, None),
            (2, 1, 'RF過剩轉出'), (2, 2, 'RF過剩轉出'),
            (2, 1, 'Local店舖全轉出'), (2, 2, 'Local店舖全轉出'),
            (2, 1, 'RF加強轉出'), (2, 2, 'RF加強轉出'),
        ]

        for src_priority, dst_priority, source_type_filter in rounds:
            mp(
                temp_sources, temp_destinations, recommendations,
                article, om, product_desc,
                src_priority, dst_priority,
                transfer_sites, received_qty_by_site, mode,
                source_type_filter=source_type_filter,
                receive_sites=receive_sites,
                source_to_receive_sites=source_to_receive_sites,
                max_receive_sites_per_source=max_receive_sites_per_source,
            )

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)
        return recommendations
