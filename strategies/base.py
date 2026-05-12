"""
Base match strategy abstract class
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMatchStrategy(ABC):
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
