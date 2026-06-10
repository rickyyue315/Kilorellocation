"""
Note generation service — pure formatting functions for transfer recommendation notes.
"""

from config import ND3_KEEP_STOCK


def _note_source_analysis(source, dest, mode, transfer_qty, mode_info):
    src_type = source['source_type']
    remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
    safety = source.get('safety_stock', 0)

    if src_type == 'ND智能轉出':
        total_sales = source.get('last_month_sold_qty', 0) + source.get('mtd_sold_qty', 0)
        if total_sales == 0:
            return f"剩{remaining}件(ND智能,0銷優先)"
        return f"剩{remaining}件(ND智能,近2月銷{total_sales})"
    if src_type == 'ND3智能轉出(保留3件)':
        total_sales = source.get('last_month_sold_qty', 0) + source.get('mtd_sold_qty', 0)
        if total_sales == 0:
            return f"剩{remaining}件(ND3保留3件,0銷優先)"
        return f"剩{remaining}件(ND3保留3件,近2月銷{total_sales})"
    if src_type == 'ND轉出' and not mode_info['is_d_family']:
        return f"剩{remaining}件(ND全轉)"
    if src_type == 'F模式ND轉出':
        return f"剩{remaining}件(F-ND全轉)"
    if source['rp_type'] == 'ND' and mode_info['is_d_family']:
        mode_label = 'D2' if mode == mode_info['mode_d2'] else 'D'
        suffix = ""
        if mode == mode_info['mode_d2'] and mode_info.get('d2_enable_2site_limit'):
            suffix = "(收≤2間,量×200%)"
        return f"剩{remaining}件(ND清貨{mode_label}{suffix})"
    if src_type == 'F模式RF轉出':
        return f"剩{remaining}件(F-RF轉)"
    if src_type == 'F3模式RF轉出(保留2件)':
        return f"剩{remaining}件(F3-RF保留2)"
    if src_type == 'E模式強制轉出':
        rp_type = source.get('rp_type', '')
        is_cross_om = mode == mode_info['mode_e2'] and source['om'] != dest['om']
        om_desc = "跨OM" if is_cross_om else "同OM"
        return f"剩{remaining}件(E強制{om_desc},{rp_type} ALL)"
    if src_type == 'Local店舖全轉出':
        if mode_info['is_b_l_retain']:
            return f"剩{remaining}件(Local保留2)"
        return f"剩{remaining}件(Local全轉)"
    if 'RF過剩轉出' in src_type:
        return f"剩{remaining}件>Safety({safety})"
    if 'RF加強轉出' in src_type:
        return f"剩{remaining}件<Safety({safety})"
    if src_type == '精簡SKU ND轉出':
        return f"剩{remaining}件(SKU-ND)"
    if src_type == '精簡SKU RF轉出':
        last_2m = source.get('last_2_month_sold_qty', 0)
        return f"剩{remaining}件(SKU-RF,超Cap,近2月銷{last_2m})"
    return ""


def _note_dest_analysis(dest, current_received_qty, transfer_qty):
    dest_type = dest['dest_type']
    cumulative = current_received_qty + transfer_qty

    if dest_type in ('F模式目標接收', 'F指定模式目標接收'):
        target_qty = dest.get('target_qty', 0)
        return f"目標{target_qty},已收{cumulative}"
    if dest_type == 'E模式接收' or str(dest_type).startswith('E1b'):
        target_qty = dest.get('target_qty', 0)
        safety_stock = dest.get('safety_stock', 0)
        current_stock = dest.get('current_stock', 0)
        pending = dest.get('pending_received', 0)
        total_available = current_stock + pending
        return f"總庫存{total_available}(現{current_stock}+待{pending}),S×2={target_qty},已收{cumulative}"
    if dest_type == '重點補0':
        if 'target_qty' in dest:
            needed = max(dest['target_qty'] - cumulative, 0)
            return f"目標{dest['target_qty']},已收{cumulative},欠{needed}"
        return "重點補0"
    if dest_type == 'ND潛在缺貨接收':
        total_sales = dest.get('total_sales', 0)
        max_receive = dest.get('max_receive_qty', total_sales * 2)
        return f"近2月銷{total_sales},上限{max_receive},已收{cumulative}"
    if dest_type == 'ND3補0接收':
        target_qty = dest.get('target_qty', 0)
        return f"目標{target_qty}(S×0.5),已收{cumulative}"
    if dest_type == 'RF緊急缺貨補貨':
        return f"RF零庫存有銷量,已收{cumulative}"
    if dest_type == '緊急缺貨補貨':
        return f"零庫存有銷量,已收{cumulative}"
    if dest_type == '潛在缺貨補貨':
        current_stock = dest.get('current_stock', 0)
        pending = dest.get('pending_received', 0)
        safety_stock = dest.get('safety_stock', 0)
        total_available = current_stock + pending
        shortage = safety_stock - total_available
        return f"不足{shortage},補至S={safety_stock},已收{cumulative}"
    if dest_type == '精簡SKU接收':
        target_qty = dest.get('target_qty', 0)
        return f"Cap=Max(S×2,銷×2)={target_qty},已收{cumulative}"
    return ""


def create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode, mode_info):
    notes_parts = []

    # Section 1: compact source→dest header
    notes_parts.append(f"【{source['source_type']}→{dest['dest_type']}】")

    # Section 2: source status (concise)
    src_status = _note_source_analysis(source, dest, mode, transfer_qty, mode_info)
    if src_status:
        notes_parts.append(src_status)

    # Section 3: dest status (concise)
    dest_status = _note_dest_analysis(dest, current_received_qty, transfer_qty)
    if dest_status:
        notes_parts.append(dest_status)

    # Section 4: mode-specific caps (concise)
    if mode_info['is_b_special'] and 'target_qty' in dest:
        notes_parts.append(f"B上限S×2={dest['target_qty']},累收{current_received_qty + transfer_qty}")
    if mode in (mode_info['mode_e1'], mode_info['mode_e1b'], mode_info['mode_e2']) and 'target_qty' in dest:
        notes_parts.append(f"E上限S×2(≥3)={dest['target_qty']},累收{current_received_qty + transfer_qty}")

    # Section 5: transfer qty + limiting factor + post-status (merged)
    src_available = source.get('transferable_qty', 0)
    dest_needed = dest.get('needed_qty', 0)
    target_qty = dest.get('target_qty')
    cum_received = current_received_qty + transfer_qty
    remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty

    reasons = []
    if transfer_qty == 2 and source.get('original_stock', 0) == 1:
        reasons.append("已優化至2件")
    elif transfer_qty == 1:
        reasons.append("最小1件")
    if target_qty is not None and cum_received >= target_qty:
        reasons.append("已達接收上限")
    elif src_available < dest_needed:
        reasons.append(f"來源僅可轉{src_available}")
    elif src_available >= dest_needed:
        reasons.append("缺口已滿足")

    reason_str = f"({','.join(reasons)})" if reasons else ""
    notes_parts.append(f"轉{transfer_qty}件{reason_str}|出剩{remaining}|收累{cum_received}")

    # Section 6: compact markers
    markers = []
    if source.get('source_type') in ('RF加強轉出',):
        markers.append("加強轉出")
    if '(C模式回退)' in source.get('source_type', ''):
        markers.append("E2-C回退")
    if source.get('source_type') == 'E模式強制轉出':
        if mode == mode_info['mode_e1']:
            markers.append("E1:ALL全轉,同OM")
        elif mode == mode_info['mode_e1b']:
            markers.append("E1b:ALL全轉,同OM,T/M優先")
        elif mode == mode_info['mode_e2']:
            om_info = "同OM優先" if source['om'] == dest['om'] else "跨OM"
            markers.append(f"E2:ALL全轉,{om_info}")
    if dest.get('dest_type') in ('重點補0',):
        markers.append("最低保障")
    if dest.get('dest_type') == 'E模式接收' or str(dest.get('dest_type', '')).startswith('E1b'):
        markers.append("E接收")
    if mode_info['is_simplified_sku']:
        if dest.get('dest_type') == '退回D001':
            markers.append("SKU退D001")
        elif dest.get('dest_type') == '精簡SKU接收':
            mode_variant = "同OM" if mode == mode_info['mode_simplified_sku_same'] else "跨OM"
            markers.append(f"SKU({mode_variant})")

    if markers:
        notes_parts.append("【" + "|".join(markers) + "】")

    return " | ".join(notes_parts)
