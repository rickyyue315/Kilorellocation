"""
ND1/ND2模式匹配策略
"""

from typing import Any, Dict, List, Optional

from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists


class NDModeStrategy(BaseMatchStrategy):
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
                if source['site'] == dest['site']:
                    continue
                if dest['site'] in transfer_sites:
                    continue
                if source['site'] in receive_sites:
                    continue

                if not cross_om and source['om'] != dest['om']:
                    continue
                if cross_om and source.get('om') == 'Windy' and dest.get('om') != 'Windy':
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                if max_receive_sites_per_source is not None:
                    matched_sites = source_to_receive_sites.get(source['site'], set())
                    if dest['site'] not in matched_sites and len(matched_sites) >= max_receive_sites_per_source:
                        continue

                receive_key = f"{dest['site']}_{article}"
                current_received = received_qty_by_site.get(receive_key, 0)
                max_receive = dest.get('max_receive_qty', float('inf'))

                if current_received >= max_receive:
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'], max_receive - current_received)
                if transfer_qty <= 0:
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

        return recommendations
