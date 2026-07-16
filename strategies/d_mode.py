"""
D/D2模式 (清貨轉貨) 接收端識別邏輯
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategies.base import BaseMatchStrategy
from services.source_dest_factory import make_dest
from config import D2_NEEDED_QTY_MULTIPLIER


def identify_destinations_d_mode(group_df: pd.DataFrame) -> List[Dict]:
    destinations: List[Dict] = []
    rf_destinations = group_df[group_df['RP Type'] == 'RF']
    for _, row in rf_destinations.iterrows():
        total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
        safety_stock = int(row['Safety Stock'])
        is_no_stock = int(row['SaSa Net Stock']) == 0
        has_sales_history = int(row['Effective Sold Qty']) > 0

        if is_no_stock and has_sales_history:
            needed_qty = max(safety_stock, 2) - total_available
            if needed_qty <= 0:
                continue
            max_receive = max(safety_stock, 2)
            destinations.append(make_dest(row, needed_qty, 1, '緊急缺貨補貨', max_receive,
                                           max_receive_qty=max_receive))
            continue

        is_insufficient_stock = total_available < safety_stock
        if is_insufficient_stock:
            needed_qty = safety_stock - total_available
            destinations.append(make_dest(row, needed_qty, 2, '潛在缺貨補貨', safety_stock,
                                           max_receive_qty=safety_stock))

    destinations.sort(key=lambda x: (
        x['priority'],
        -(int(x.get('last_month_sold_qty', 0)) + int(x.get('mtd_sold_qty', 0))),
    ))
    return destinations


def identify_destinations_d2_mode(group_df: pd.DataFrame, enable_2site_limit: bool = False) -> List[Dict]:
    destinations: List[Dict] = []
    rf_destinations = group_df[group_df['RP Type'] == 'RF']
    m = D2_NEEDED_QTY_MULTIPLIER
    for _, row in rf_destinations.iterrows():
        total_available = int(row['SaSa Net Stock']) + int(row['Pending Received'])
        safety_stock = int(row['Safety Stock'])
        is_no_stock = int(row['SaSa Net Stock']) == 0
        has_sales_history = int(row['Effective Sold Qty']) > 0

        if is_no_stock and has_sales_history:
            target_qty = max(safety_stock * m, 2 * m)
            needed_qty = target_qty - total_available
            if needed_qty <= 0:
                continue
            destinations.append(make_dest(row, needed_qty, 1, '緊急缺貨補貨', target_qty,
                                           max_receive_qty=target_qty))
            continue

        is_insufficient_stock = total_available < safety_stock
        if is_insufficient_stock:
            target_qty = safety_stock * m
            needed_qty = target_qty - total_available
            destinations.append(make_dest(row, needed_qty, 2, '潛在缺貨補貨', target_qty,
                                           max_receive_qty=target_qty))

    destinations.sort(key=lambda x: x['priority'])
    return destinations
