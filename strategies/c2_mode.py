"""
C2模式（跨OM重點補0）匹配策略
"""

from typing import Any, Dict, List, Optional

from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted
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

        transfer_sites = set([s['site'] for s in temp_sources if s['transferable_qty'] > 0])
        receive_sites = set()
        received_qty_by_site = {}

        temp_destinations.sort(key=lambda x: x['priority'])

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
                if dest.get('rp_type') == 'ND':
                    continue
                if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
                    continue
                if is_hd_to_hk_restricted(source['site'], dest['site']):
                    continue

                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                if transfer_qty <= 0:
                    continue

                receive_site_key = f"{dest['site']}_{article}"
                current_received_qty = received_qty_by_site.get(receive_site_key, 0)

                notes = _make_c2_note(source, dest, current_received_qty, transfer_qty)
                recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received_qty)
                recommendations.append(recommendation)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received_qty)

                receive_sites.add(dest['site'])

                if dest.get('dest_type') == '重點補0' and 'target_qty' in dest:
                    if received_qty_by_site[receive_site_key] >= dest['target_qty']:
                        dest['needed_qty'] = 0

        return recommendations


def _make_c2_note(source, dest, current_received, transfer_qty):
    return (f"【C2跨OM重點補0】"
            f"{source['site']}→{dest['site']} {transfer_qty}件")
