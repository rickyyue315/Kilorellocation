"""
精簡SKU模式匹配策略
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategies.base import BaseMatchStrategy
from strategies.predicates import validate_pair
from services.recommendation_factory import build_recommendation, apply_transfer
from services.matching_engine import prep_temp_lists


class SimplifiedSKUStrategy(BaseMatchStrategy):
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
            if supply_source is not None and pd.notna(supply_source) and int(supply_source) in (1, 4):
                continue

            if remaining == 1 and source['source_type'] == '精簡SKU RF轉出':
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
