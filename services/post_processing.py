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


def _source_remaining_capacity(rec: Dict[str, Any]) -> int:
    """
    計算某筆建議的來源店（Article + Transfer Site + Transfer OM）在後處理增益前的剩餘可轉量。

    = 原始庫存 − 目前已排定的轉出量 − After Transfer Stock（0 表示無上限資訊）。

    例：來源庫存 10、可轉 5，首筆轉 5 後 After Transfer Stock = 5 → 後續增益只剩 5-5=0 件。
    """
    try:
        original = int(rec.get('Original Stock', 0) or 0)
        after = int(rec.get('After Transfer Stock', 0) or 0)
        qty = int(rec.get('Transfer Qty', 0) or 0)
    except (TypeError, ValueError):
        return 0
    if after <= 0:
        return 0
    return max(original - after - qty, 0)


def _cap_group_boosts_remaining(optimized: List[Dict]) -> List[Dict]:
    """
    過濾後處理「+1」增益：來源店累計轉出不得超過其可轉量。

    後處理（A1/ND4 消除餘 1 件）原本無視來源可轉上限，可能轉出超過
    可轉量甚至令店舖跌破安全庫存。此處按 (Article, Transfer Site, Transfer OM)
    群組依序套用增益；每組以 _source_remaining_capacity 判斷餘量，當 +1 會超出
    剩餘可轉量時自動降為可在上限內的最大增益（可能為 0），後續同組記錄不再增益。
    """
    if not optimized:
        return optimized

    group_remaining: Dict[Tuple[str, str, str], int] = {}
    for rec in optimized:
        key = (
            str(rec.get('Article', '')),
            str(rec.get('Transfer Site', '')),
            str(rec.get('Transfer OM', '')),
        )
        if key not in group_remaining:
            group_remaining[key] = _source_remaining_capacity(rec)

    for rec in reversed(optimized):
        key = (
            str(rec.get('Article', '')),
            str(rec.get('Transfer Site', '')),
            str(rec.get('Transfer OM', '')),
        )
        try:
            qty = int(rec.get('Transfer Qty', 0) or 0)
        except (TypeError, ValueError):
            qty = 0
        remaining = group_remaining.get(key, 0)
        if remaining > 0:
            added = min(1, remaining)
            rec['Transfer Qty'] = qty + added
            group_remaining[key] = remaining - added
        else:
            rec['Transfer Qty'] = qty

    return optimized


def optimize_single_piece_transfers(recommendations: List[Dict], mode: str, create_note_fn) -> List[Dict]:
    if not recommendations:
        return recommendations

    D_FAMILY_MODES = {'清貨轉貨', '清貨轉貨(ND限定)'}
    if mode in D_FAMILY_MODES:
        return recommendations

    receive_totals: Dict[Tuple[str, str], Dict] = {}
    for rec in recommendations:
        if int(rec.get('Transfer Qty', 0) or 0) <= 0:
            continue
        dest_key = (str(rec.get('Article', '')), str(rec.get('Receive Site', '')).strip().upper())
        if dest_key not in receive_totals:
            receive_totals[dest_key] = {'received': 0, 'target': rec.get('Target Qty')}
        receive_totals[dest_key]['received'] += int(rec.get('Transfer Qty', 0) or 0)

    def _can_add_to_dest(rec, delta):
        if delta <= 0:
            return True
        dest_key = (str(rec.get('Article', '')), str(rec.get('Receive Site', '')).strip().upper())
        info = receive_totals.get(dest_key)
        if info is None or info['target'] is None:
            return True
        return info['received'] + delta <= info['target']

    def _apply_qty_change(rec, old_qty, new_qty):
        if old_qty == new_qty:
            return
        dest_key = (str(rec.get('Article', '')), str(rec.get('Receive Site', '')).strip().upper())
        delta = new_qty - old_qty
        rec['Transfer Qty'] = new_qty
        if dest_key in receive_totals:
            receive_totals[dest_key]['received'] += delta

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
                    if not _can_add_to_dest(single_rec, 1):
                        continue
                    _apply_qty_change(donor, int(donor.get('Transfer Qty', 0) or 0),
                                      int(donor.get('Transfer Qty', 0) or 0) - 1)
                    _apply_qty_change(single_rec, 1, 2)
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
                        if not _can_add_to_dest(best_target, 1):
                            continue
                        _apply_qty_change(best_target,
                                          int(best_target.get('Transfer Qty', 0) or 0),
                                          int(best_target.get('Transfer Qty', 0) or 0) + 1)
                        _apply_qty_change(single_rec, 1, 0)
                        group_changed = True
                        has_change = True
                    else:
                        donor_ge3_for_boost = [r for r in other_recs if int(r.get('Transfer Qty', 0) or 0) >= 3]
                        if donor_ge3_for_boost and len(group_recs) >= 3:
                            donor = max(donor_ge3_for_boost, key=lambda r: int(r.get('Transfer Qty', 0) or 0))
                            if not _can_add_to_dest(single_rec, 1):
                                continue
                            _apply_qty_change(donor,
                                              int(donor.get('Transfer Qty', 0) or 0),
                                              int(donor.get('Transfer Qty', 0) or 0) - 1)
                            _apply_qty_change(single_rec, 1, 2)
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


def optimize_a1_avoid_one_remainder(recommendations: List[Dict]) -> bool:
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
        total_transferred = sum(int(r.get('Transfer Qty', 0) or 0) for r in group_recs)
        original_stock = int(group_recs[0].get('Original Stock', 0) or 0)
        remaining = original_stock - total_transferred
        if remaining != 1:
            continue

        candidates = []
        for rec in group_recs:
            qty = int(rec.get('Transfer Qty', 0) or 0)
            if qty <= 0:
                continue
            target_qty = rec.get('Target Qty')
            if target_qty is not None and int(target_qty) > 0:
                cumulative = int(rec.get('Cumulative Received Qty', 0) or 0)
                if cumulative + 1 > int(target_qty) + 1:
                    continue
            candidates.append(rec)

        if not candidates:
            continue

        best = max(candidates, key=lambda r: (
            int(r.get('Receive Site Last Month Sold Qty', 0) or 0)
            + int(r.get('Receive Site MTD Sold Qty', 0) or 0),
            int(r.get('Transfer Qty', 0) or 0),
        ))

        # 後處理增益不得超出來源可轉量（超量會令店舖跌破安全庫存且缺口報表無法察覺）
        before = int(best.get('Transfer Qty', 0) or 0)
        _cap_group_boosts_remaining([best])
        if int(best.get('Transfer Qty', 0) or 0) != before:
            has_change = True

    return has_change


def optimize_nd4_avoid_one_remainder(recommendations: List[Dict]) -> bool:
    """
    ND4-specific: if a source store ends with exactly 1 remaining after transfer,
    add 1 extra piece to the highest-sales destination line so source ends with 0.
    """
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
        total_transferred = sum(int(r.get('Transfer Qty', 0) or 0) for r in group_recs)
        original_stock = int(group_recs[0].get('Original Stock', 0) or 0)
        remaining = original_stock - total_transferred
        if remaining != 1:
            continue

        candidates = []
        for rec in group_recs:
            qty = int(rec.get('Transfer Qty', 0) or 0)
            if qty <= 0:
                continue
            target_qty = rec.get('Target Qty')
            if target_qty is not None and int(target_qty) > 0:
                cumulative = int(rec.get('Cumulative Received Qty', 0) or 0)
                if cumulative + 1 > int(target_qty):
                    continue
            candidates.append(rec)

        if not candidates:
            candidates = [r for r in group_recs if int(r.get('Transfer Qty', 0) or 0) > 0]
            if not candidates:
                continue

        best = max(candidates, key=lambda r: (
            int(r.get('Receive Site Last Month Sold Qty', 0) or 0)
            + int(r.get('Receive Site MTD Sold Qty', 0) or 0),
            int(r.get('Transfer Qty', 0) or 0),
        ))

        # 後處理增益不得超出來源可轉量（同 A1：避免超量轉出跌破安全庫存）
        before = int(best.get('Transfer Qty', 0) or 0)
        _cap_group_boosts_remaining([best])
        if int(best.get('Transfer Qty', 0) or 0) != before:
            has_change = True

    return has_change
