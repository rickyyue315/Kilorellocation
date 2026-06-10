"""
E1/E1b/E2模式（僅同OM配對）匹配策略 + Source/Dest 識別邏輯
"""

from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair, is_hd_to_hk_restricted
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists
from services.source_dest_factory import make_source, make_dest
from config import SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR


def identify_sources_e_mode(group_df: pd.DataFrame) -> List[Dict]:
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
            sources.append(make_source(row, net_stock, 1, 'E模式強制轉出',
                                        is_e_mode=True))
    sources.sort(key=lambda x: x['priority'])
    return sources


def identify_destinations_e_mode(group_df: pd.DataFrame, mode: str, mode_e1b: str) -> List[Dict]:
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

            if mode == mode_e1b:
                store_type = type_series.loc[row.name]
                if store_type == 'T':
                    priority, dest_type = (1, 'E1b遊客區店舖 高銷量優先') if sales_total > 0 else (3, 'E1b遊客區店舖 Safety優先')
                elif store_type == 'M':
                    priority, dest_type = (2, 'E1b混合型店舖 高銷量優先') if sales_total > 0 else (4, 'E1b混合型店舖 Safety優先')
                else:
                    priority, dest_type = 5, 'E1b其他類型店舖'
            else:
                priority, dest_type = 1, 'E模式接收'

            destinations.append(make_dest(row, int(needed_qty), priority, dest_type, max_can_receive,
                                           max_receive_qty=max_can_receive))

    if mode == mode_e1b:
        def e1b_sort_key(item: Dict) -> Tuple[int, int, int]:
            if item['priority'] in (1, 2):
                return (item['priority'], -int(item.get('effective_sold_qty', 0)), 0)
            return (item['priority'], -int(item.get('safety_stock', 0)), 0)
        destinations.sort(key=e1b_sort_key)
    else:
        destinations.sort(key=lambda x: x['priority'])
    return destinations


class E1ModeStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, max_receive_sites_per_source=None):
        super().__init__(create_note)
        self._max_receive_sites_per_source = max_receive_sites_per_source

    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        return identify_sources_e_mode(group_df)

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        return identify_destinations_e_mode(group_df, mode, mode_e1b="強制轉出(優先類型接收)")

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

        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])
        receive_sites = set()
        received_qty_by_site = {}
        source_to_receive_sites = {}
        max_receive_sites_per_source = self._max_receive_sites_per_source

        for source in temp_sources:
            if source['transferable_qty'] <= 0:
                continue

            same_om_dests = [d for d in temp_destinations
                           if d['om'] == source['om'] and d['needed_qty'] > 0]

            for dest in same_om_dests:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                if not validate_pair(source, dest, transfer_sites,
                                     check_nd_receive=True,
                                     check_source_in_receive_sites=False,
                                     cross_om=False,
                                     source_to_receive_sites=source_to_receive_sites,
                                     max_receive_sites_per_source=max_receive_sites_per_source):
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])

                receive_site_key = f"{dest['site']}_{article}"
                current_received = received_qty_by_site.get(receive_site_key, 0)
                max_receive = dest.get('max_receive_qty', dest.get('target_qty', float('inf')))
                if current_received >= max_receive:
                    continue
                transfer_qty = min(transfer_qty, max_receive - current_received)
                if transfer_qty <= 0:
                    continue

                notes = self._create_note(source, dest, current_received, transfer_qty, mode) if self._create_note else ""
                recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received)
                recommendations.append(recommendation)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received)

                receive_sites.add(dest['site'])

                matched = source_to_receive_sites.setdefault(source['site'], set())
                matched.add(dest['site'])

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)
        return recommendations
