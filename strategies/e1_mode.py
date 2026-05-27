"""
E1/E1b/E2模式（僅同OM配對）匹配策略
"""

from typing import Any, Dict, List, Optional

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair, is_hd_to_hk_restricted
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists


class E1ModeStrategy(BaseMatchStrategy):
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
