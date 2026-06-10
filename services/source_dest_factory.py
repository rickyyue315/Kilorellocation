"""
Shared factory functions for building source/dest dicts and computing protected sold.
Extracted from business_logic.py to break circular import risk.
"""

from typing import Dict, Optional, Tuple

import pandas as pd


def safe_get_last2m(row) -> int:
    if 'Last 2 Month Sold Qty' in row.index:
        return int(row['Last 2 Month Sold Qty'])
    return int(row['Last Month Sold Qty'])


def make_source(row, transferable_qty: int, priority: int, source_type: str, **extra) -> Dict:
    source = {
        'site': row['Site'],
        'om': row['OM'],
        'rp_type': row['RP Type'],
        'transferable_qty': transferable_qty,
        'priority': priority,
        'original_stock': int(row['SaSa Net Stock']),
        'effective_sold_qty': int(row['Effective Sold Qty']) if pd.notna(row.get('Effective Sold Qty', 0)) else 0,
        'source_type': source_type,
        'store_type': '',
        'last_month_sold_qty': int(row['Last Month Sold Qty']) if pd.notna(row.get('Last Month Sold Qty', 0)) else 0,
        'mtd_sold_qty': int(row['MTD Sold Qty']) if pd.notna(row.get('MTD Sold Qty', 0)) else 0,
        'last_2_month_sold_qty': safe_get_last2m(row),
        'safety_stock': int(row['Safety Stock']) if pd.notna(row.get('Safety Stock', 0)) else 0,
        'supply_source': row.get('Supply source'),
    }
    source.update(extra)
    return source


def make_dest(row, needed_qty: int, priority: int, dest_type: str,
              target_qty: int, max_receive_qty: Optional[int] = None, **extra) -> Dict:
    dest = {
        'site': row['Site'],
        'om': row['OM'],
        'rp_type': row['RP Type'],
        'needed_qty': needed_qty,
        'priority': priority,
        'current_stock': int(row['SaSa Net Stock']),
        'pending_received': int(row['Pending Received']),
        'safety_stock': int(row['Safety Stock']) if pd.notna(row.get('Safety Stock', 0)) else 0,
        'moq': int(row['MOQ']) if pd.notna(row.get('MOQ', 0)) else 0,
        'effective_sold_qty': int(row['Effective Sold Qty']) if pd.notna(row.get('Effective Sold Qty', 0)) else 0,
        'dest_type': dest_type,
        'target_qty': target_qty,
        'received_qty': 0,
        'last_month_sold_qty': int(row['Last Month Sold Qty']) if pd.notna(row.get('Last Month Sold Qty', 0)) else 0,
        'mtd_sold_qty': int(row['MTD Sold Qty']) if pd.notna(row.get('MTD Sold Qty', 0)) else 0,
    }
    if max_receive_qty is not None:
        dest['max_receive_qty'] = max_receive_qty
    dest.update(extra)
    return dest


def compute_max_protected_sold(df) -> float:
    if df.empty:
        return 0
    max_sold = df['Effective Sold Qty'].max()
    if len(df) == 1 or max_sold == 0 or (df['Effective Sold Qty'] == max_sold).sum() >= len(df):
        return float('inf')
    return max_sold
