"""
NST (New Shop Target) 模式匹配策略 + Source/Dest 識別邏輯
基於 F2 模式, RF 轉出規則變更：
- 轉出後保留 ≥2 件
- 轉出上限為庫存的 75%
- 庫存 < 3 件不轉出
- 可設定同一 SKU 轉出店數上限
"""

from typing import Any, Callable, Dict, List, Optional, Set

import pandas as pd

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists
from services.source_dest_factory import make_source, make_dest, compute_max_protected_sold
from services.target_utils import parse_target_series
from config import NST_RF_RETAIN_STOCK, NST_RF_TRANSFER_CAP, NST_RF_MIN_STOCK_TO_SOURCE


def identify_sources_nst_mode(
    group_df: pd.DataFrame,
    mode: str,
    protected_sites: Optional[Set[str]],
) -> List[Dict]:
    sources: List[Dict] = []
    target_series = parse_target_series(group_df)

    nd_sources = group_df[group_df['RP Type'] == 'ND']
    for _, row in nd_sources.iterrows():
        target_value = target_series.loc[row.name]
        if pd.notna(target_value) and target_value > 0:
            continue
        if protected_sites:
            site_key = str(row['Site']).strip().upper()
            if site_key in protected_sites:
                continue
        net_stock = int(row['SaSa Net Stock'])
        if net_stock > 0:
            sources.append(make_source(row, net_stock, 1, 'NST模式ND轉出'))

    rf_sources = group_df[group_df['RP Type'] == 'RF']
    max_sold_qty = compute_max_protected_sold(rf_sources)

    for _, row in rf_sources.iterrows():
        target_value = target_series.loc[row.name]
        if pd.notna(target_value) and target_value > 0:
            continue
        if protected_sites:
            site_key = str(row['Site']).strip().upper()
            if site_key in protected_sites:
                continue
        net_stock = int(row['SaSa Net Stock'])
        effective_sold = int(row['Effective Sold Qty'])

        if net_stock < NST_RF_MIN_STOCK_TO_SOURCE:
            continue

        transferable_qty = min(int(net_stock * NST_RF_TRANSFER_CAP), net_stock - NST_RF_RETAIN_STOCK)
        if transferable_qty <= 0:
            continue

        if effective_sold >= max_sold_qty:
            continue

        sources.append(make_source(row, transferable_qty, 2, 'NST模式RF轉出'))

    sources.sort(key=lambda x: (x['priority'], x.get('effective_sold_qty', 0)))
    return sources


def identify_destinations_nst_mode(
    group_df: pd.DataFrame,
    mode: str,
) -> List[Dict]:
    destinations: List[Dict] = []
    target_series = parse_target_series(group_df)

    seen_target_sites = set()

    for idx, row in group_df.iterrows():
        target_value = target_series.loc[idx]

        if pd.notna(target_value) and target_value > 0:
            target_qty = int(target_value)
            site_key = str(row['Site']).strip().upper()
            if site_key in seen_target_sites:
                continue
            seen_target_sites.add(site_key)
            destinations.append(make_dest(row, target_qty, 1, 'NST模式目標接收', target_qty))

    destinations.sort(key=lambda x: x['priority'])
    return destinations


class NewShopTargetStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, nst_allow_hd_transfer=False,
                 f_fulfill_small_first=False, nst_max_source_shops=None):
        super().__init__(create_note)
        self._nst_allow_hd_transfer = nst_allow_hd_transfer
        self._f_fulfill_small_first = f_fulfill_small_first
        self._nst_max_source_shops = nst_max_source_shops

    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        return identify_sources_nst_mode(group_df, mode, protected_sites)

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        return identify_destinations_nst_mode(group_df, mode)

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

        temp_destinations.sort(key=lambda x: x['priority'])

        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])
        receive_sites = set()
        received_qty_by_site = {}

        total_needed = sum([int(d.get('needed_qty', 0)) for d in temp_destinations])
        remaining_demand = total_needed

        used_source_sites = set()

        def _sort_key(src, dest_om, dest_site=''):
            rp = str(src.get('rp_type', '')).upper()
            same_om = 1 if src.get('om') == dest_om else 2
            tier = 0 if rp == 'ND' else (1 if same_om == 1 else 2)
            hd_penalty = 0
            if (self._nst_allow_hd_transfer
                    and str(src.get('site', '')).upper().startswith('HD')
                    and dest_site.upper().startswith(('HA', 'HB', 'HC'))):
                hd_penalty = 10
            windy_penalty = 0
            if dest_om == 'Windy' and src.get('om') != 'Windy':
                windy_penalty = 5
            if self._f_fulfill_small_first:
                return (tier + hd_penalty + windy_penalty, -src.get('transferable_qty', 0))
            return (tier + hd_penalty + windy_penalty, src.get('effective_sold_qty', 0))

        for priority_level in [1, 2]:
            priority_dests = [d for d in temp_destinations if d['priority'] == priority_level]
            if priority_level == 1:
                if self._f_fulfill_small_first:
                    priority_dests.sort(key=lambda x: x['needed_qty'])
                else:
                    priority_dests.sort(key=lambda x: x['needed_qty'], reverse=True)

            for dest in priority_dests:
                if dest['needed_qty'] <= 0 or remaining_demand <= 0:
                    continue

                sorted_sources = sorted(
                    temp_sources,
                    key=lambda s: _sort_key(s, dest.get('om', ''), dest.get('site', ''))
                )

                for source in sorted_sources:
                    if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0 or remaining_demand <= 0:
                        continue

                    if not validate_pair(source, dest, transfer_sites,
                                         check_nd_receive=False,
                                         check_source_in_receive_sites=False,
                                         cross_om=True,
                                         allow_hd_to_hk=self._nst_allow_hd_transfer):
                        continue

                    if priority_level == 2:
                        if dest.get('rp_type') == 'ND':
                            continue
                        if source['om'] != dest['om']:
                            continue

                    if (self._nst_max_source_shops is not None
                            and source['site'] not in used_source_sites
                            and len(used_source_sites) >= self._nst_max_source_shops):
                        continue

                    transfer_qty = min(source['transferable_qty'], dest['needed_qty'], remaining_demand)
                    if transfer_qty <= 0:
                        continue

                    receive_site_key = f"{dest['site']}_{article}"
                    current_received_qty = received_qty_by_site.get(receive_site_key, 0)

                    notes = self._create_note(source, dest, current_received_qty, transfer_qty, mode) if self._create_note else ""
                    recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received_qty)
                    recommendations.append(recommendation)

                    apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received_qty)
                    remaining_demand -= transfer_qty

                    receive_sites.add(dest['site'])
                    used_source_sites.add(source['site'])

                    if dest.get('target_qty') is not None and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                        dest['needed_qty'] = 0

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)

        self._post_match_gap_fill(recommendations, temp_sources, temp_destinations, article, product_desc, mode, received_qty_by_site, transfer_sites, used_source_sites)

        return recommendations

    def _post_match_gap_fill(self, recommendations, temp_sources, temp_destinations,
                              article, product_desc, mode, received_qty_by_site, transfer_sites, used_source_sites):
        gap_dests = [d for d in temp_destinations
                     if d.get('priority') == 1
                     and d.get('target_qty') is not None and d.get('target_qty', 0) > 0
                     and d.get('needed_qty', 0) > 0]

        if not gap_dests:
            return

        for dest in sorted(gap_dests, key=lambda x: x['needed_qty']):
            if dest['needed_qty'] <= 0:
                continue

            receive_site_key = f"{dest['site']}_{article}"
            current_received = received_qty_by_site.get(receive_site_key, 0)
            if current_received >= dest['target_qty']:
                dest['needed_qty'] = 0
                continue

            leftover_sources = [s for s in temp_sources if s.get('transferable_qty', 0) > 0]

            for src in sorted(leftover_sources, key=lambda s: -s['transferable_qty']):
                if src['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue

                if src['site'] == dest['site']:
                    continue

                if dest['site'] in transfer_sites:
                    continue

                if not validate_pair(src, dest, transfer_sites,
                                     check_nd_receive=False,
                                     check_source_in_receive_sites=False,
                                     cross_om=True,
                                     allow_hd_to_hk=self._nst_allow_hd_transfer):
                    continue

                if (self._nst_max_source_shops is not None
                        and src['site'] not in used_source_sites
                        and len(used_source_sites) >= self._nst_max_source_shops):
                    continue

                transfer_qty = min(src['transferable_qty'], dest['needed_qty'])
                if transfer_qty <= 0:
                    continue

                notes = (self._create_note(src, dest, current_received, transfer_qty, mode)
                         if self._create_note else "")
                recommendation = build_recommendation(
                    article, product_desc, src, dest, transfer_qty, notes, current_received
                )
                recommendations.append(recommendation)

                apply_transfer(src, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received)
                current_received = received_qty_by_site[receive_site_key]
                used_source_sites.add(src['site'])

                if dest.get('target_qty') is not None and current_received >= dest['target_qty']:
                    dest['needed_qty'] = 0
