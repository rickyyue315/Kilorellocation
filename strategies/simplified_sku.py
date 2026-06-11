"""
精簡SKU模式匹配策略 + Source/Dest 識別邏輯
"""

from typing import Any, Dict, List, Optional, Set

import pandas as pd

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists
from services.source_dest_factory import (
    safe_get_last2m,
    make_source,
    make_dest,
    compute_max_protected_sold,
)
from config import SIMPLIFIED_SKU_RECEIVE_MULTIPLIER


def identify_sources_simplified_sku(group_df: pd.DataFrame) -> List[Dict]:
    sources: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']
    for _, row in nd_stores.iterrows():
        net_stock = int(row['SaSa Net Stock'])
        if net_stock <= 0:
            continue
        sources.append(make_source(row, net_stock, 1, '精簡SKU ND轉出'))

    rf_sources = group_df[group_df['RP Type'] == 'RF']
    max_sold_qty = compute_max_protected_sold(rf_sources)

    for _, row in rf_sources.iterrows():
        total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
        safety_stock = int(row['Safety Stock'])
        last_two_month_sold = safe_get_last2m(row)
        cap = max(safety_stock * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last_two_month_sold * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)
        effective_sold = int(row['Effective Sold Qty'])

        if effective_sold >= max_sold_qty:
            continue
        if total_available <= cap:
            continue

        transferable_qty = min(total_available - cap, int(row['SaSa Net Stock']))
        if transferable_qty <= 0:
            continue

        sources.append(make_source(row, transferable_qty, 2, '精簡SKU RF轉出'))

    sources.sort(key=lambda x: x['priority'])
    return sources


def identify_destinations_simplified_sku(group_df: pd.DataFrame) -> List[Dict]:
    destinations: List[Dict] = []
    rf_stores = group_df[group_df['RP Type'] == 'RF']
    for _, row in rf_stores.iterrows():
        total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
        safety_stock = int(row['Safety Stock'])
        last_two_month_sold = safe_get_last2m(row)
        cap = max(safety_stock * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last_two_month_sold * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)
        if total_available >= cap:
            continue
        needed_qty = cap - total_available
        if needed_qty <= 0:
            continue
        destinations.append(make_dest(row, needed_qty, 1, '精簡SKU接收', cap,
                                       max_receive_qty=needed_qty))
    destinations.sort(key=lambda x: x['priority'])
    return destinations


class SimplifiedSKUStrategy(BaseMatchStrategy):
    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        return identify_sources_simplified_sku(group_df)

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        return identify_destinations_simplified_sku(group_df)

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
        cross_om = (mode == "精簡SKU(跨OM)")

        temp_sources, temp_destinations = prep_temp_lists(sources, destinations)

        transfer_sites = set()
        receive_sites = set()
        received_qty_by_site = {}

        pending_sources = sorted(
            [s for s in temp_sources if s['transferable_qty'] >= 2],
            key=lambda x: -x['transferable_qty']
        )

        for source in pending_sources:
            source_added_to_transfer = False
            for dest in temp_destinations:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                if not validate_pair(source, dest, transfer_sites, receive_sites,
                                     check_nd_receive=True,
                                     check_source_in_receive_sites=True,
                                     cross_om=cross_om):
                    continue
                if not cross_om and source['om'] != dest['om']:
                    continue

                receive_site_key = f"{dest['site']}_{article}"
                current_received = received_qty_by_site.get(receive_site_key, 0)
                max_receive = dest.get('max_receive_qty', float('inf'))
                if current_received >= max_receive:
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'], max_receive - current_received)
                if transfer_qty <= 0:
                    continue

                notes = _make_sku_note(source, dest, current_received, transfer_qty, mode)
                rec = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received)
                recommendations.append(rec)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received)

                if not source_added_to_transfer:
                    transfer_sites.add(source['site'])
                    source_added_to_transfer = True
                receive_sites.add(dest['site'])

        for source in temp_sources:
            remaining = source['transferable_qty']
            if remaining <= 0:
                continue

            supply_source = source.get('supply_source')
            if supply_source is not None and pd.notna(supply_source):
                try:
                    supply_num = pd.to_numeric(supply_source, errors='coerce')
                    if pd.notna(supply_num):
                        supply_val = int(supply_num)
                        if supply_val in (1, 4):
                            continue
                except (ValueError, TypeError):
                    pass

            if remaining == 1 and source['source_type'] in ('精簡SKU RF轉出', '精簡SKU ND轉出'):
                continue

            notes = f"精簡SKU模式：剩餘庫存{remaining}件退回D001"
            rec = build_recommendation(
                article, product_desc, source, {}, remaining, notes, 0,
                is_d001_return=True, dest_priority_override=99,
            )
            recommendations.append(rec)

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)
        return recommendations


def _make_sku_note(source, dest, current_received, transfer_qty, mode):
    """Generate note for simplified SKU transfers."""
    mode_variant = "限同OM" if mode == "精簡SKU(限同OM)" else "跨OM"
    return (f"【精簡SKU模式({mode_variant})】"
            f"{source['site']}→{dest['site']} {transfer_qty}件, "
            f"RF存貨上限=Max(Safety×2, 過去2個月銷量×2)")
