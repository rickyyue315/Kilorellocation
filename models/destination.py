from typing import TypedDict

DestinationCandidate = TypedDict('DestinationCandidate', {
    'site': str,
    'om': str,
    'rp_type': str,
    'needed_qty': int,
    'priority': int,
    'current_stock': int,
    'pending_received': int,
    'safety_stock': int,
    'moq': int,
    'effective_sold_qty': int,
    'dest_type': str,
    'target_qty': int,
    'received_qty': int,
    'last_month_sold_qty': int,
    'mtd_sold_qty': int,
    'max_receive_qty': int,
    'store_type': str,
    'last_2_month_sold_qty': int,
    'total_sales': int,
}, total=False)
