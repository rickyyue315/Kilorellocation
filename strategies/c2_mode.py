"""
C2模式（跨OM重點補0）匹配策略
使用多回合優先制，與 C 模式對稱，支援跨OM配對
"""

from typing import Any, Dict, List, Optional

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists


class C2ModeStrategy(BaseMatchStrategy):
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

        rounds = [
            (1, 1, '重點補0'),
            (1, 1, None),
            (1, 2, None),
            (2, 1, '重點補0', 'RF過剩轉出'),
            (2, 1, None, 'RF過剩轉出'),
            (2, 2, None, 'RF過剩轉出'),
            (2, 1, '重點補0', 'RF加強轉出'),
            (2, 1, None, 'RF加強轉出'),
            (2, 2, None, 'RF加強轉出'),
        ]

        for round_config in rounds:
            if len(round_config) == 3:
                src_priority, dst_priority, dest_type_filter = round_config
                source_type_filter = None
            else:
                src_priority, dst_priority, dest_type_filter, source_type_filter = round_config

            self._match_round(
                temp_sources, temp_destinations, recommendations,
                article, product_desc, mode,
                src_priority, dst_priority,
                source_type_filter, dest_type_filter,
                transfer_sites, receive_sites, received_qty_by_site,
            )

        self._log_match_stats(recommendations, temp_sources, temp_destinations, article, mode)
        return recommendations

    def _match_round(
        self,
        temp_sources, temp_destinations, recommendations,
        article, product_desc, mode,
        src_priority, dst_priority,
        source_type_filter, dest_type_filter,
        transfer_sites, receive_sites, received_qty_by_site,
    ):
        filtered_sources = [
            s for s in temp_sources
            if s['priority'] == src_priority
            and s['transferable_qty'] > 0
            and (source_type_filter is None or s['source_type'] == source_type_filter)
        ]

        filtered_destinations = [
            d for d in temp_destinations
            if d['priority'] == dst_priority
            and d['needed_qty'] > 0
            and (dest_type_filter is None or d['dest_type'] == dest_type_filter)
        ]

        for source in filtered_sources:
            if source['transferable_qty'] <= 0:
                continue

            for dest in filtered_destinations:
                if dest['needed_qty'] <= 0:
                    continue
                if not validate_pair(source, dest, transfer_sites, receive_sites,
                                     check_nd_receive=True,
                                     check_source_in_receive_sites=True,
                                     cross_om=True):
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                if transfer_qty <= 0:
                    continue

                receive_site_key = f"{dest['site']}_{article}"
                current_received_qty = received_qty_by_site.get(receive_site_key, 0)

                if dest.get('dest_type') == '重點補0' and 'target_qty' in dest:
                    transfer_qty = min(transfer_qty, max(dest['target_qty'] - current_received_qty, 0))
                    if transfer_qty <= 0:
                        continue

                if transfer_qty == 1 and source['transferable_qty'] >= 2:
                    if source['source_type'] in ('ND轉出', 'ND清貨轉出', 'RF加強轉出', 'RF過剩轉出'):
                        if dest['needed_qty'] >= 2:
                            transfer_qty = 2

                notes = _make_c2_note(source, dest, current_received_qty, transfer_qty)
                recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received_qty)
                recommendations.append(recommendation)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received_qty)

                transfer_sites.add(source['site'])
                receive_sites.add(dest['site'])

                if dest.get('dest_type') == '重點補0' and 'target_qty' in dest:
                    if received_qty_by_site[receive_site_key] >= dest['target_qty']:
                        dest['needed_qty'] = 0


def _make_c2_note(source, dest, current_received, transfer_qty):
    return (f"【C2跨OM重點補0】"
            f"{source['site']}→{dest['site']} {transfer_qty}件")
