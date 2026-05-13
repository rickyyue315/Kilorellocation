"""
E2模式（強制轉出跨OM）匹配策略
支持優先同OM配對、跨OM回退、Phase 3 C模式回退
"""
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from config import C_MODE_PERCENTAGE_CAP, C_MODE_ABS_CAP
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


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
    }
    source.update(extra)
    return source


def _compute_max_protected_sold(df) -> float:
    if df.empty:
        return 0
    max_sold = df['Effective Sold Qty'].max()
    if len(df) == 1 or max_sold == 0 or (df['Effective Sold Qty'] == max_sold).sum() >= len(df):
        return float('inf')
    return max_sold


class E2ModeStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, max_receive_sites_per_source=None):
        super().__init__(create_note)
        self._max_receive_sites_per_source = max_receive_sites_per_source

    def match(
        self,
        sources: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        article: str,
        product_desc: str,
        mode: str,
        om: Optional[str] = None,
        group_df: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        from services.recommendation_factory import build_recommendation, apply_transfer

        recommendations: List[Dict] = []

        temp_sources = [s.copy() for s in sources]
        for s in temp_sources:
            s['total_transferred'] = 0
        temp_destinations = [d.copy() for d in destinations]

        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])
        receive_sites: Set[str] = set()
        received_qty_by_site: Dict[str, int] = {}
        source_to_receive_sites: Dict[str, set] = {}
        max_recv = self._max_receive_sites_per_source
        e_mode_source_oms = set([s['om'] for s in temp_sources])

        # Phase 1: 同 OM 配對，Phase 2: 跨 OM 回退（統一邏輯）
        for same_om_only in (True, False):
            self._match_e_mode_phase(
                temp_sources, temp_destinations, recommendations,
                article, product_desc, mode, same_om_only,
                transfer_sites, receive_sites, received_qty_by_site,
                source_to_receive_sites, max_recv,
                build_recommendation, apply_transfer,
            )

        # Phase 3: C 模式回退
        if group_df is not None:
            self._phase3_c_fallback(
                group_df, temp_destinations, e_mode_source_oms,
                transfer_sites, receive_sites, received_qty_by_site,
                recommendations, article, product_desc,
                build_recommendation, apply_transfer,
            )

        return recommendations

    def _match_e_mode_phase(
        self,
        temp_sources, temp_destinations, recommendations,
        article, product_desc, mode, same_om_only,
        transfer_sites, receive_sites, received_qty_by_site,
        source_to_receive_sites, max_receive_sites_per_source,
        build_recommendation, apply_transfer,
    ):
        for source in temp_sources:
            if source['transferable_qty'] <= 0:
                continue

            if same_om_only:
                candidate_dests = [d for d in temp_destinations
                                   if d['om'] == source['om'] and d['needed_qty'] > 0]
            else:
                candidate_dests = [d for d in temp_destinations
                                   if d['om'] != source['om'] and d['needed_qty'] > 0]

            for dest in candidate_dests:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if dest.get('rp_type') == 'ND':
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                if max_receive_sites_per_source is not None:
                    matched_sites = source_to_receive_sites.get(source['site'], set())
                    if dest['site'] not in matched_sites and len(matched_sites) >= max_receive_sites_per_source:
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
                rec = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received)
                recommendations.append(rec)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received)
                receive_sites.add(dest['site'])

                matched = source_to_receive_sites.setdefault(source['site'], set())
                matched.add(dest['site'])

            if not same_om_only and source['transferable_qty'] <= 0:
                continue

    def _phase3_c_fallback(
        self,
        group_df, temp_destinations, e_mode_source_oms,
        transfer_sites, receive_sites, received_qty_by_site,
        recommendations, article, product_desc,
        build_recommendation, apply_transfer,
    ):
        non_e_mode_receiving_sites = set([d['site'] for d in temp_destinations
                                           if d['om'] not in e_mode_source_oms and d['needed_qty'] > 0])

        unfulfilled_dests = [d for d in temp_destinations
                             if d['needed_qty'] > 0
                             and d['om'] not in e_mode_source_oms
                             and d['site'] not in transfer_sites]

        if not unfulfilled_dests:
            return

        c_mode_sources = []
        for _, row in group_df[(group_df['RP Type'] == 'RF')].iterrows():
            if row['OM'] in e_mode_source_oms:
                continue
            if row['Site'] in transfer_sites:
                continue
            if row['Site'] in receive_sites:
                continue
            if row['Site'] in non_e_mode_receiving_sites:
                continue

            total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
            safety_stock = int(row['Safety Stock'])
            effective_sold = int(row['Effective Sold Qty'])

            om_rf_stores = group_df[(group_df['RP Type'] == 'RF') & (group_df['OM'] == row['OM'])]
            max_sold_qty = _compute_max_protected_sold(om_rf_stores)

            is_stock_above_safety = total_available > safety_stock
            is_not_highest_sold = effective_sold < max_sold_qty

            if is_stock_above_safety and is_not_highest_sold:
                base_transferable = total_available - safety_stock
                if base_transferable <= 0:
                    continue

                ratio_cap = int(total_available * C_MODE_PERCENTAGE_CAP)
                abs_cap = C_MODE_ABS_CAP
                capped_ratio = max(ratio_cap, 0)
                raw_upper = min(capped_ratio, abs_cap) if capped_ratio > 0 else abs_cap
                upper_limit = max(1, raw_upper)

                actual_transferable = min(base_transferable, upper_limit, int(row['SaSa Net Stock']))
                if actual_transferable > 0:
                    remaining_stock = int(row['SaSa Net Stock']) - actual_transferable
                    source_type = 'RF過剩轉出(C模式回退)' if remaining_stock >= safety_stock else 'RF加強轉出(C模式回退)'
                    c_mode_sources.append(_make_source(row, actual_transferable, 2, source_type,
                                                        total_transferred=0))

        for source in c_mode_sources:
            if source['transferable_qty'] <= 0:
                continue
            transfer_sites.add(source['site'])

            for dest in unfulfilled_dests:
                if dest['needed_qty'] <= 0:
                    continue
                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if dest['site'] in receive_sites:
                    continue
                if dest.get('rp_type') == 'ND':
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                receive_site_key = f"{dest['site']}_{article}"
                current_received = received_qty_by_site.get(receive_site_key, 0)

                if dest.get('dest_type') == 'E模式接收':
                    max_receive = dest.get('max_receive_qty', dest.get('target_qty', float('inf')))
                    if current_received >= max_receive:
                        continue
                    remaining_capacity = max_receive - current_received
                    transfer_qty = min(source['transferable_qty'], dest['needed_qty'], remaining_capacity)
                else:
                    transfer_qty = min(source['transferable_qty'], dest['needed_qty'])

                if transfer_qty <= 0:
                    continue

                notes = 'E模式Phase3 - C模式回退（非E模式OM的重點補0）'
                rec = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received)
                recommendations.append(rec)
                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received)
                receive_sites.add(dest['site'])

                if source['transferable_qty'] <= 0:
                    break
