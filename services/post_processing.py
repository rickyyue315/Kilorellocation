"""
後處理模組 — 單件調貨優化、欄位刷新、銷量計算
"""

from typing import Any, Dict, List, Tuple


def get_record_sales_total(rec: Dict[str, Any], prefix: str) -> int:
    last_month = int(rec.get(f'{prefix} Last Month Sold Qty', 0) or 0)
    mtd = int(rec.get(f'{prefix} MTD Sold Qty', 0) or 0)
    return last_month + mtd


def infer_source_rp_type(source_type: str) -> str:
    return 'ND' if 'ND' in str(source_type) else 'RF'


def refresh_recommendation_fields(recommendations: List[Dict], mode: str, create_note_fn) -> None:
    source_running: Dict[Tuple[str, str, str], int] = {}
    receive_running: Dict[Tuple[str, str], int] = {}

    for rec in recommendations:
        qty = int(rec.get('Transfer Qty', 0) or 0)
        rec['Transfer Qty'] = qty

        source_key = (
            str(rec.get('Article', '')),
            str(rec.get('Transfer Site', '')),
            str(rec.get('Transfer OM', '')),
        )
        receive_key = (
            str(rec.get('Article', '')),
            str(rec.get('Receive Site', '')),
        )

        source_before = source_running.get(source_key, 0)
        receive_before = receive_running.get(receive_key, 0)
        original_stock = int(rec.get('Original Stock', 0) or 0)

        rec['After Transfer Stock'] = original_stock - (source_before + qty)
        rec['Cumulative Received Qty'] = receive_before + qty

        source_running[source_key] = source_before + qty
        receive_running[receive_key] = receive_before + qty

        source_info = {
            'source_type': rec.get('Source Type', ''),
            'priority': int(rec.get('Source Priority', 2) or 2),
            'rp_type': infer_source_rp_type(str(rec.get('Source Type', ''))),
            'original_stock': original_stock,
            'total_transferred': source_before,
            'last_month_sold_qty': int(rec.get('Transfer Site Last Month Sold Qty', 0) or 0),
            'mtd_sold_qty': int(rec.get('Transfer Site MTD Sold Qty', 0) or 0),
            'om': rec.get('Transfer OM', ''),
        }
        dest_info = {
            'dest_type': rec.get('Destination Type', ''),
            'priority': int(rec.get('Destination Priority', 2) or 2),
            'target_qty': int(rec.get('Target Qty', 0) or 0),
            'safety_stock': int(rec.get('Safety Stock', 0) or 0),
            'current_stock': int(rec.get('Receive Original Stock', 0) or 0),
            'pending_received': 0,
            'rp_type': 'RF',
            'last_month_sold_qty': int(rec.get('Receive Site Last Month Sold Qty', 0) or 0),
            'mtd_sold_qty': int(rec.get('Receive Site MTD Sold Qty', 0) or 0),
            'om': rec.get('Receive OM', ''),
        }
        rec['Notes'] = create_note_fn(source_info, dest_info, receive_before, qty, mode)


def optimize_single_piece_transfers(recommendations: List[Dict], mode: str, create_note_fn) -> List[Dict]:
    if not recommendations:
        return recommendations

    D_FAMILY_MODES = {'清貨轉貨', '清貨轉貨(ND限定)'}
    if mode in D_FAMILY_MODES:
        return recommendations

    groups: Dict[Tuple[str, str, str], List[Dict]] = {}
    for rec in recommendations:
        key = (
            str(rec.get('Article', '')),
            str(rec.get('Transfer Site', '')),
            str(rec.get('Transfer OM', '')),
        )
        groups.setdefault(key, []).append(rec)

    has_change = False

    for group_recs in groups.values():
        if len(group_recs) <= 1:
            continue

        total_qty = sum(int(r.get('Transfer Qty', 0) or 0) for r in group_recs)
        if total_qty <= 1:
            continue

        max_iterations = len(group_recs) + 2
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            singles = [r for r in group_recs if int(r.get('Transfer Qty', 0) or 0) == 1]
            if not singles:
                break

            group_changed = False

            for single_rec in singles:
                if int(single_rec.get('Transfer Qty', 0) or 0) != 1:
                    continue

                other_recs = [r for r in group_recs if r is not single_rec and int(r.get('Transfer Qty', 0) or 0) > 0]
                if not other_recs:
                    continue

                donors_ge3 = [r for r in other_recs if int(r.get('Transfer Qty', 0) or 0) >= 3]
                if donors_ge3:
                    donor = max(
                        donors_ge3,
                        key=lambda r: (
                            int(r.get('Transfer Qty', 0) or 0),
                            get_record_sales_total(r, 'Receive Site'),
                        ),
                    )
                    donor['Transfer Qty'] = int(donor.get('Transfer Qty', 0) or 0) - 1
                    single_rec['Transfer Qty'] = 2
                    group_changed = True
                    has_change = True
                    continue

                merge_targets = [r for r in other_recs if int(r.get('Transfer Qty', 0) or 0) >= 2]
                if merge_targets:
                    best_target = max(
                        merge_targets,
                        key=lambda r: (
                            get_record_sales_total(r, 'Receive Site'),
                            int(r.get('Transfer Qty', 0) or 0),
                        ),
                    )
                    single_sales = get_record_sales_total(single_rec, 'Receive Site')
                    target_sales = get_record_sales_total(best_target, 'Receive Site')

                    if len(group_recs) == 2 or single_sales <= target_sales:
                        best_target['Transfer Qty'] = int(best_target.get('Transfer Qty', 0) or 0) + 1
                        single_rec['Transfer Qty'] = 0
                        group_changed = True
                        has_change = True
                    else:
                        donor_ge2 = [r for r in other_recs if int(r.get('Transfer Qty', 0) or 0) >= 2]
                        if donor_ge2 and len(group_recs) >= 3:
                            donor = max(donor_ge2, key=lambda r: int(r.get('Transfer Qty', 0) or 0))
                            donor['Transfer Qty'] = int(donor.get('Transfer Qty', 0) or 0) - 1
                            single_rec['Transfer Qty'] = 2
                            group_changed = True
                            has_change = True

            group_recs[:] = [r for r in group_recs if int(r.get('Transfer Qty', 0) or 0) > 0]

            if not group_changed or len(group_recs) <= 1:
                break

    if not has_change:
        return recommendations

    optimized = [r for r in recommendations if int(r.get('Transfer Qty', 0) or 0) > 0]
    refresh_recommendation_fields(optimized, mode, create_note_fn)
    return optimized
