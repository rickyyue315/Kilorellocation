from typing import TypedDict

SourceCandidate = TypedDict('SourceCandidate', {
    'site': str,
    'om': str,
    'rp_type': str,
    'transferable_qty': int,
    'priority': int,
    'original_stock': int,
    'effective_sold_qty': int,
    'source_type': str,
    'store_type': str,
    'last_month_sold_qty': int,
    'mtd_sold_qty': int,
    'last_2_month_sold_qty': int,
    'total_sales_sort': int,
    'is_e_mode': bool,
    'total_transferred': int,
}, total=False)
