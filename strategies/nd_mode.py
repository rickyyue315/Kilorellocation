"""
ND1/ND2/ND3/ND4模式匹配策略 + Source/Dest 識別邏輯
"""

from typing import Any, Dict, List, Optional, Set

import pandas as pd

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair, is_hd_to_hk_restricted
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists
from services.source_dest_factory import (
    safe_get_last2m,
    make_source,
    make_dest,
    compute_max_protected_sold,
)
from config import ND_RECEIVE_MULTIPLIER, ND3_KEEP_STOCK, F_TARGET_MULTIPLIER, F_TARGET_FLOOR


def identify_sources_nd_mode(group_df: pd.DataFrame) -> List[Dict]:
    sources: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']
    max_nd_sold = compute_max_protected_sold(nd_stores)

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

        sources.append(make_source(row, net_stock, 1, 'ND轉出(按銷量)',
                                    total_sales_sort=total_sales))

    sources.sort(key=lambda x: x.get('total_sales_sort', 0))
    return sources


def identify_destinations_nd_mode(group_df: pd.DataFrame) -> List[Dict]:
    destinations: List[Dict] = []
    rf_stores = group_df[group_df['RP Type'] == 'RF']
    nd_stores = group_df[group_df['RP Type'] == 'ND']

    for _, row in rf_stores.iterrows():
        total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
        has_sales = int(row['Effective Sold Qty']) > 0
        if total_available == 0 and has_sales:
            safety_stock = int(row['Safety Stock'])
            needed_qty = safety_stock if safety_stock > 0 else 2
            destinations.append(make_dest(row, needed_qty, 1, 'RF緊急缺貨補貨', needed_qty,
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
        destinations.append(make_dest(row, needed_qty, 2, 'ND潛在缺貨接收', max_receive,
                                       max_receive_qty=max_receive,
                                       total_sales=total_sales))

    destinations.sort(key=lambda x: (x['priority'], -x.get('total_sales', 0)))
    return destinations


def identify_sources_nd3_mode(group_df: pd.DataFrame) -> List[Dict]:
    sources: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']
    max_nd_sold = compute_max_protected_sold(nd_stores)

    for _, row in nd_stores.iterrows():
        net_stock = int(row['SaSa Net Stock'])
        if net_stock <= ND3_KEEP_STOCK:
            continue
        effective_sold = int(row['Effective Sold Qty'])
        if effective_sold >= max_nd_sold:
            continue

        transferable_qty = net_stock - ND3_KEEP_STOCK
        last_month_sold = int(row['Last Month Sold Qty'])
        mtd_sold = int(row['MTD Sold Qty'])
        total_sales = last_month_sold + mtd_sold

        sources.append(make_source(row, transferable_qty, 1, 'ND3轉出(保留3件)',
                                    total_sales_sort=total_sales))

    sources.sort(key=lambda x: x.get('total_sales_sort', 0))
    return sources


def identify_sources_nd4_mode(group_df: pd.DataFrame) -> List[Dict]:
    sources: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']
    max_nd_sold = compute_max_protected_sold(nd_stores)

    for _, row in nd_stores.iterrows():
        net_stock = int(row['SaSa Net Stock'])
        last_month_sold = int(row['Last Month Sold Qty'])
        mtd_sold = int(row['MTD Sold Qty'])
        total_sales = last_month_sold + mtd_sold
        effective_sold = int(row['Effective Sold Qty'])
        if effective_sold >= max_nd_sold:
            continue

        if total_sales == 0:
            # 無銷量：不保留，全數轉出
            if net_stock <= 0:
                continue
            transferable_qty = net_stock
            src_type = 'ND4轉出(無銷量全轉)'
        else:
            # 有銷量：保留3件
            if net_stock <= ND3_KEEP_STOCK:
                continue
            transferable_qty = net_stock - ND3_KEEP_STOCK
            src_type = 'ND4轉出(保留3件)'

        sources.append(make_source(row, transferable_qty, 1, src_type,
                                    total_sales_sort=total_sales))

    sources.sort(key=lambda x: x.get('total_sales_sort', 0))
    return sources


def identify_destinations_nd3_mode(group_df: pd.DataFrame) -> List[Dict]:
    destinations: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']

    for _, row in nd_stores.iterrows():
        net_stock = int(row['SaSa Net Stock'])
        if net_stock > 0:
            continue
        safety_stock = int(row['Safety Stock']) if pd.notna(row.get('Safety Stock', 0)) else 0
        total_available = net_stock + int(row['Pending Received'])
        target_qty = max(int(safety_stock * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
        needed_qty = target_qty - total_available
        if needed_qty <= 0:
            continue

        last_month_sold = int(row['Last Month Sold Qty'])
        mtd_sold = int(row['MTD Sold Qty'])
        total_sales = last_month_sold + mtd_sold

        destinations.append(make_dest(row, needed_qty, 1, 'ND3補0接收', target_qty,
                                       max_receive_qty=target_qty,
                                       total_sales=total_sales))

    destinations.sort(key=lambda x: (x['priority'], -x.get('total_sales', 0)))
    return destinations


def identify_destinations_nd4_mode(group_df: pd.DataFrame) -> List[Dict]:
    destinations: List[Dict] = []
    nd_stores = group_df[group_df['RP Type'] == 'ND']

    for _, row in nd_stores.iterrows():
        net_stock = int(row['SaSa Net Stock'])
        if net_stock > 0:
            continue
        # ND4: only shops with sales records
        last_month_sold = int(row['Last Month Sold Qty'])
        mtd_sold = int(row['MTD Sold Qty'])
        total_sales = last_month_sold + mtd_sold
        if total_sales <= 0:
            continue
        safety_stock = int(row['Safety Stock']) if pd.notna(row.get('Safety Stock', 0)) else 0
        total_available = net_stock + int(row['Pending Received'])
        target_qty = max(int(safety_stock * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
        needed_qty = target_qty - total_available
        if needed_qty <= 0:
            continue

        destinations.append(make_dest(row, needed_qty, 1, 'ND4補0接收(有銷量)', target_qty,
                                       max_receive_qty=target_qty,
                                       total_sales=total_sales))

    destinations.sort(key=lambda x: (x['priority'], -x.get('total_sales', 0)))
    return destinations


class NDModeStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, max_receive_sites_per_source=None):
        super().__init__(create_note)
        self._max_receive_sites_per_source = max_receive_sites_per_source

    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        if mode == "ND限同OM轉貨(補0)":
            return identify_sources_nd3_mode(group_df)
        if mode == "ND限同OM轉貨(補0及有銷售記錄)":
            return identify_sources_nd4_mode(group_df)
        return identify_sources_nd_mode(group_df)

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        if mode == "ND限同OM轉貨(補0)":
            return identify_destinations_nd3_mode(group_df)
        if mode == "ND限同OM轉貨(補0及有銷售記錄)":
            return identify_destinations_nd4_mode(group_df)
        return identify_destinations_nd_mode(group_df)

    def match(
        self,
        sources: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        article: str,
        product_desc: str,
        mode: str,
        om: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cross_om = (mode == "ND混合OM轉貨")
        recommendations = []

        temp_sources, temp_destinations = prep_temp_lists(sources, destinations)

        transfer_sites = set(s['site'] for s in temp_sources if s['transferable_qty'] > 0)
        receive_sites = set()
        received_qty_by_site = {}
        source_to_receive_sites = {}
        max_receive_sites_per_source = self._max_receive_sites_per_source

        for dest in temp_destinations:
            if dest['needed_qty'] <= 0:
                continue

            for source in temp_sources:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                if not validate_pair(source, dest, transfer_sites, receive_sites,
                                     check_nd_receive=False,
                                     check_source_in_receive_sites=True,
                                     cross_om=cross_om,
                                     source_to_receive_sites=source_to_receive_sites,
                                     max_receive_sites_per_source=max_receive_sites_per_source):
                    continue
                if not cross_om and source['om'] != dest['om']:
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                receive_key = f"{dest['site']}_{article}"
                current_received = received_qty_by_site.get(receive_key, 0)
                max_receive = dest.get('max_receive_qty', float('inf'))

                if current_received >= max_receive:
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'], max_receive - current_received)
                if transfer_qty <= 0:
                    continue
                if mode in ("ND限同OM轉貨(補0)", "ND限同OM轉貨(補0及有銷售記錄)") and transfer_qty == 1:
                    continue

                notes = self._create_note(source, dest, current_received, transfer_qty, mode) if self._create_note else ""
                recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received)
                recommendations.append(recommendation)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_key, current_received)

                receive_sites.add(dest['site'])

                matched_sites = source_to_receive_sites.setdefault(source['site'], set())
                matched_sites.add(dest['site'])

                if received_qty_by_site[receive_key] >= max_receive:
                    dest['needed_qty'] = 0

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)
        return recommendations
