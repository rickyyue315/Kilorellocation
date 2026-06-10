"""
C1模式 (重點補0-只補0/1) 接收端識別邏輯
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategies.base import BaseMatchStrategy
from services.source_dest_factory import make_dest
from config import F_TARGET_MULTIPLIER, F_TARGET_FLOOR


def identify_destinations_c1_mode(group_df: pd.DataFrame, threshold: int = 1) -> List[Dict]:
    destinations: List[Dict] = []
    rf_destinations = group_df[group_df['RP Type'] == 'RF']
    for _, row in rf_destinations.iterrows():
        total_available = row['SaSa Net Stock'] + row['Pending Received']
        if total_available > threshold:
            continue
        if int(row['Safety Stock']) <= 0 and int(row['Effective Sold Qty']) <= 0:
            continue
        target_qty = max(int(row['Safety Stock'] * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
        needed_qty = target_qty - total_available
        if needed_qty <= 0:
            continue
        needed_qty = int(needed_qty)
        if needed_qty < 2:
            needed_qty = 2
        destinations.append(make_dest(row, needed_qty, 1, '重點補0', int(target_qty)))
    destinations.sort(key=lambda x: x['priority'])
    return destinations
