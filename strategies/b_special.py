"""
B特別模式匹配策略（委派給 _match_by_priority 引擎）
"""

from typing import Any, Callable, Dict, List, Optional

from strategies.base import BaseMatchStrategy


class BSpecialStrategy(BaseMatchStrategy):
    def __init__(self, match_by_priority: Optional[Callable] = None,
                 max_receive_sites_per_source: Optional[int] = None):
        super().__init__()
        self._match_by_priority = match_by_priority
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

        temp_sources = [s.copy() for s in sources]
        for s in temp_sources:
            s['total_transferred'] = 0
        temp_destinations = [d.copy() for d in destinations]

        transfer_sites = set()
        receive_sites = set()
        received_qty_by_site = {}
        source_to_receive_sites = {}
        max_receive_sites_per_source = self._max_receive_sites_per_source

        mp = self._match_by_priority
        if mp is None:
            return recommendations

        rounds = [
            (1, 1, None), (1, 2, None),
            (2, 1, 'Local店舖全轉出'), (2, 2, 'Local店舖全轉出'),
            (2, 1, 'RF過剩轉出'), (2, 2, 'RF過剩轉出'),
            (2, 1, 'RF加強轉出'), (2, 2, 'RF加強轉出'),
        ]

        for src_priority, dst_priority, source_type_filter in rounds:
            mp(
                temp_sources, temp_destinations, recommendations,
                article, om, product_desc,
                src_priority, dst_priority,
                transfer_sites, received_qty_by_site, mode,
                source_type_filter=source_type_filter,
                receive_sites=receive_sites,
                source_to_receive_sites=source_to_receive_sites,
                max_receive_sites_per_source=max_receive_sites_per_source,
            )

        return recommendations
