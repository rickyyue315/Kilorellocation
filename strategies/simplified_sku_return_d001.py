"""
精簡SKU(退D001)模式匹配策略
所有可轉出數量一律退回D001，不執行RF接收配對
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategies.base import BaseMatchStrategy
from services.recommendation_factory import build_recommendation
from services.matching_engine import prep_temp_lists


class SimplifiedSKUReturnD001Strategy(BaseMatchStrategy):
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
        temp_sources, _ = prep_temp_lists(sources, destinations)

        for source in temp_sources:
            remaining = source['transferable_qty']
            if remaining <= 0:
                continue

            supply_source = source.get('supply_source')
            if supply_source is not None and pd.notna(supply_source) and int(supply_source) in (1, 4):
                continue

            notes = f"精簡SKU(退D001)模式：{source['site']}轉出{remaining}件退回D001"
            rec = build_recommendation(
                article, product_desc, source, {}, remaining, notes, 0,
                is_d001_return=True, dest_priority_override=99,
            )
            recommendations.append(rec)

        return recommendations
