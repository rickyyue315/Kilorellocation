from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TransferStatistics:
    total_recommendations: int = 0
    total_transfer_qty: int = 0
    unique_articles: int = 0
    unique_oms: int = 0
    article_stats: Dict = field(default_factory=dict)
    source_type_stats: Dict = field(default_factory=dict)
    dest_type_stats: Dict = field(default_factory=dict)
    om_stats: Dict = field(default_factory=dict)
