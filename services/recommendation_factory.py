"""
Recommendation factory — 統一的 recommendation dict 構建與配對後記帳
"""

from typing import Any, Dict


def build_recommendation(
    article: str,
    product_desc: str,
    source: Dict[str, Any],
    dest: Dict[str, Any],
    transfer_qty: int,
    notes: str,
    current_received: int = 0,
    *,
    is_d001_return: bool = False,
    dest_priority_override: int = None,
) -> Dict[str, Any]:
    rec = {
        'Article': article,
        'Product Desc': product_desc,
        'Transfer OM': source['om'],
        'Transfer Site': source['site'],
        'Receive OM': source['om'] if is_d001_return else dest['om'],
        'Receive Site': 'D001' if is_d001_return else dest['site'],
        'Transfer Qty': transfer_qty,
        'Original Stock': source['original_stock'],
        'After Transfer Stock': (
            source['original_stock']
            - source.get('total_transferred', 0)
            - transfer_qty
        ),
        'Safety Stock': 0,
        'MOQ': 0,
        'Source Priority': source['priority'],
        'Destination Priority': (
            dest_priority_override
            if dest_priority_override is not None
            else dest.get('priority', 99)
        ),
        'Source Type': source['source_type'],
        'Destination Type': '退回D001' if is_d001_return else dest.get('dest_type', ''),
        'Notes': notes,
        'Transfer Site Last Month Sold Qty': source.get('last_month_sold_qty', 0),
        'Transfer Site MTD Sold Qty': source.get('mtd_sold_qty', 0),
        'Receive Site Last Month Sold Qty': (
            0 if is_d001_return else dest.get('last_month_sold_qty', 0)
        ),
        'Receive Site MTD Sold Qty': (
            0 if is_d001_return else dest.get('mtd_sold_qty', 0)
        ),
        'Receive Original Stock': (
            0 if is_d001_return else dest.get('current_stock', 0)
        ),
    }
    if not is_d001_return and 'target_qty' in dest:
        rec['Target Qty'] = dest['target_qty']
    if is_d001_return:
        rec['Target Qty'] = 0
    rec['Cumulative Received Qty'] = current_received + transfer_qty
    return rec


def apply_transfer(
    source: Dict[str, Any],
    dest: Dict[str, Any],
    transfer_qty: int,
    received_qty_by_site: Dict[str, int],
    receive_site_key: str,
    current_received: int,
):
    source['total_transferred'] = (
        source.get('total_transferred', 0) + transfer_qty
    )
    source['transferable_qty'] = (
        source.get('transferable_qty', 0) - transfer_qty
    )
    if dest.get('needed_qty', 0) > 0:
        dest['needed_qty'] = dest['needed_qty'] - transfer_qty
        if dest['needed_qty'] <= 0:
            dest['needed_qty'] = 0
    received_qty_by_site[receive_site_key] = current_received + transfer_qty
