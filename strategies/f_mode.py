"""
F/F2模式匹配策略
"""

from typing import Any, Dict, List, Optional

from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists


class FModeStrategy(BaseMatchStrategy):
    def __init__(self, create_note=None, f2_allow_hd_transfer=False):
        super().__init__(create_note)
        self._f2_allow_hd_transfer = f2_allow_hd_transfer

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

        is_f2 = (mode == "F指定模式")

        def _sort_key(src, dest_om, dest_site=''):
            rp = str(src.get('rp_type', '')).upper()
            same_om = 1 if src.get('om') == dest_om else 2
            tier = 0 if rp == 'ND' else (1 if same_om == 1 else 2)
            hd_penalty = 0
            if (is_f2 and self._f2_allow_hd_transfer
                    and str(src.get('site', '')).upper().startswith('HD')
                    and dest_site.upper().startswith(('HA', 'HB', 'HC'))):
                hd_penalty = 10
            windy_penalty = 0
            if is_f2 and dest_om == 'Windy' and src.get('om') != 'Windy':
                windy_penalty = 5
            return (tier + hd_penalty + windy_penalty, src.get('effective_sold_qty', 0))

        for priority_level in [1, 2]:
            priority_dests = [d for d in temp_destinations if d['priority'] == priority_level]
            if priority_level == 1:
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

                    if source['site'] == dest['site']:
                        continue
                    if dest['site'] in transfer_sites:
                        continue

                    if priority_level == 2:
                        if dest.get('rp_type') == 'ND':
                            continue
                        if source['om'] != dest['om']:
                            continue

                    if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
                        continue

                    if is_hd_to_hk_restricted(source['site'], dest['site']):
                        if not (is_f2 and self._f2_allow_hd_transfer):
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

                    if dest.get('target_qty') is not None and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                        dest['needed_qty'] = 0

        return recommendations
