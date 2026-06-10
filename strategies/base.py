"""
Base match strategy abstract class
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaseMatchStrategy(ABC):
    def __init__(self, create_note: Optional[Callable] = None):
        self._create_note = create_note

    @abstractmethod
    def match(
        self,
        sources: List[Dict[str, Any]],
        destinations: List[Dict[str, Any]],
        article: str,
        product_desc: str,
        mode: str,
        om: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def identify_sources(
        self,
        group_df: pd.DataFrame,
        mode: str,
        protected_sites: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def identify_destinations(
        self,
        group_df: pd.DataFrame,
        mode: str,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def _log_match_stats(self, recommendations: List[Dict[str, Any]],
                         sources: List[Dict[str, Any]],
                         destinations: List[Dict[str, Any]],
                         article: str, mode: str) -> None:
        remaining_supply = sum(s['transferable_qty'] for s in sources)
        remaining_demand = sum(d['needed_qty'] for d in destinations)
        logger.debug(
            f"[{mode}] Article={article}: {len(recommendations)} matches, "
            f"remaining_supply={remaining_supply}, remaining_demand={remaining_demand}"
        )
