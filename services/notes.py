"""
Note generation service — pure formatting functions for transfer recommendation notes.
"""

from config import ND3_KEEP_STOCK


def _note_source_analysis(source, dest, mode, transfer_qty, mode_info):
    src_type = source['source_type']
    remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty

    if src_type == 'ND智能轉出':
        total_sales = source.get('last_month_sold_qty', 0) + source.get('mtd_sold_qty', 0)
        if total_sales == 0:
            return f"【轉出分析: ND智能轉出，0銷量店舖優先轉出，轉出後剩餘{remaining}件】"
        return f"【轉出分析: ND智能轉出，過去2個月銷量{total_sales}件(按銷量升序排序)，轉出後剩餘{remaining}件】"
    if src_type == 'ND3智能轉出(保留3件)':
        total_sales = source.get('last_month_sold_qty', 0) + source.get('mtd_sold_qty', 0)
        if total_sales == 0:
            return f"【轉出分析: ND3智能轉出(保留3件)，0銷量店舖優先轉出，保留{ND3_KEEP_STOCK}件庫存，轉出後剩餘{remaining}件】"
        return f"【轉出分析: ND3智能轉出(保留3件)，過去2個月銷量{total_sales}件(按銷量升序排序)，保留{ND3_KEEP_STOCK}件庫存，轉出後剩餘{remaining}件】"
    if src_type == 'ND轉出' and not mode_info['is_d_family']:
        return "【轉出分析: ND類型店鋪，無庫存限制，可全數轉出】"
    if src_type == 'F模式ND轉出':
        return "【轉出分析: F模式ND類型店鋪，無庫存限制，全數轉出】"
    if source['rp_type'] == 'ND' and mode_info['is_d_family']:
        mode_label = 'D2' if mode == mode_info['mode_d2'] else 'D'
        return f"【轉出分析: ND店鋪清貨(模式{mode_label})，轉出後剩餘庫存({remaining})件，已優化避免1件餘貨】"
    if src_type == 'F模式RF轉出':
        return f"【轉出分析: F模式RF轉出，可忽視最小庫存要求，轉出後剩餘庫存({remaining})件】"
    if src_type == 'E模式強制轉出':
        rp_type = source.get('rp_type', '')
        is_cross_om = mode == mode_info['mode_e2'] and source['om'] != dest['om']
        cross_om_desc = "跨OM" if is_cross_om else "同OM"
        return f"【轉出分析: E模式強制轉出({cross_om_desc}配對)，{rp_type}店鋪被標記為*ALL*全數轉出，原始庫存{source['original_stock']}件，轉出後剩餘{remaining}件】"
    if src_type == 'Local店舖全轉出':
        if mode_info['is_b_l_retain']:
            return "【轉出分析: Local店舖低銷量特例（附加B-L系列模式），保留2件後轉出】"
        return "【轉出分析: Local店舖全轉出（附加B系列模式），可全數轉出】"
    if src_type == 'RF過剩轉出':
        return f"【轉出分析: RF過剩轉出，轉出後剩餘庫存({remaining})仍高於安全庫存({source.get('safety_stock', 'N/A')})】"
    if src_type == 'RF加強轉出':
        return f"【轉出分析: RF加強轉出，轉出後剩餘庫存({remaining})可能低於安全庫存({source.get('safety_stock', 'N/A')})】"
    if src_type == '精簡SKU ND轉出':
        return f"【轉出分析: 精簡SKU模式ND轉出，全數可轉出，轉出後剩餘{remaining}件】"
    if src_type == '精簡SKU RF轉出':
        last_2m = source.get('last_2_month_sold_qty', 0)
        return f"【轉出分析: 精簡SKU模式RF轉出，超出Cap(Safety×2與過去2個月銷量×2取高者)部分轉出，過去2個月銷量{last_2m}件，轉出後剩餘{remaining}件】"
    return ""


def _note_dest_analysis(dest, current_received_qty, transfer_qty):
    dest_type = dest['dest_type']
    cumulative = current_received_qty + transfer_qty

    if dest_type in ('F模式目標接收', 'F指定模式目標接收'):
        target_qty = dest.get('target_qty', 0)
        prefix = "F指定模式目標接收，僅Target店舖可接收" if dest_type == 'F指定模式目標接收' else "F模式目標接收"
        return f"【接收分析: {prefix}，目標數量{target_qty}件，累計已接收{cumulative}件】"
    if dest_type == 'E模式接收' or str(dest_type).startswith('E1b'):
        target_qty = dest.get('target_qty', 0)
        safety_stock = dest.get('safety_stock', 0)
        current_stock = dest.get('current_stock', 0)
        pending = dest.get('pending_received', 0)
        total_available = current_stock + pending
        return f"【接收分析: E模式接收，RF店鋪當前總庫存{total_available}件(現有{current_stock}件+待收{pending}件)，安全庫存{safety_stock}件，接收上限為安全庫存2倍({target_qty}件)，累計已接收{cumulative}件】"
    if dest_type == '重點補0':
        if 'target_qty' in dest:
            return f"【接收分析: 重點補0，目標數量{dest['target_qty']}件，累計已接收{cumulative}件，缺口{abs(cumulative - dest['target_qty'])}件】"
        return "【接收分析: 重點補0，針對低庫存店鋪補貨】"
    if dest_type == 'ND潛在缺貨接收':
        total_sales = dest.get('total_sales', 0)
        max_receive = dest.get('max_receive_qty', total_sales * 2)
        return f"【接收分析: ND潛在缺貨接收，過去2個月銷量{total_sales}件，接收上限{max_receive}件(2×過去2個月銷量)，累計已接收{cumulative}件】"
    if dest_type == 'ND3補0接收':
        target_qty = dest.get('target_qty', 0)
        safety_stock = dest.get('safety_stock', 0)
        return f"【接收分析: ND3補0接收，以補0為目標，目標數量{target_qty}件(Safety Stock×0.5與3取高者)，零庫存ND店舖補貨，累計已接收{cumulative}件】"
    if dest_type == 'RF緊急缺貨補貨':
        return "【接收分析: RF緊急缺貨補貨，RF店鋪零庫存但有銷售記錄（ND模式優先滿足）】"
    if dest_type == '緊急缺貨補貨':
        return "【接收分析: 緊急缺貨補貨，該店鋪零庫存但有銷售記錄】"
    if dest_type == '潛在缺貨補貨':
        current_stock = dest.get('current_stock', 0)
        pending = dest.get('pending_received', 0)
        safety_stock = dest.get('safety_stock', 0)
        total_available = current_stock + pending
        shortage = safety_stock - total_available
        return f"【接收分析: 潛在缺貨補貨，庫存不足{shortage}件，補充至安全庫存{safety_stock}件】"
    if dest_type == '精簡SKU接收':
        target_qty = dest.get('target_qty', 0)
        return f"【接收分析: 精簡SKU接收，接收上限Cap=Max(Safety×2, 過去2個月銷量×2)={target_qty}件，累計已接收{cumulative}件】"
    return ""


def create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode, mode_info):
    notes_parts = []

    notes_parts.append(f"【轉出分類: {source['source_type']}】")
    notes_parts.append(f"【接收分類: {dest['dest_type']}】")

    if source['source_type'] == 'ND智能轉出':
        priority_desc = "ND智能轉出(按銷量排序優先級)"
    elif source['source_type'] == 'ND3智能轉出(保留3件)':
        priority_desc = f"ND3智能轉出(保留{ND3_KEEP_STOCK}件，按銷量排序)"
    elif source['priority'] == 1:
        priority_desc = "ND轉出(最高優先級)"
    else:
        priority_desc = "RF轉出"
    notes_parts.append(f"【轉出優先級: {priority_desc}】")

    if dest['priority'] == 1:
        priority_desc = "接收(最高優先級)"
    else:
        priority_desc = "接收(一般優先級)"
    notes_parts.append(f"【接收優先級: {priority_desc}】")

    notes_parts.append(_note_source_analysis(source, dest, mode, transfer_qty, mode_info))
    notes_parts.append(_note_dest_analysis(dest, current_received_qty, transfer_qty))

    if mode_info['is_b_special'] and 'target_qty' in dest:
        notes_parts.append(f"【接收上限: 附加B系列模式接收上限為安全庫存2倍({dest['target_qty']}件)，累計已接收{current_received_qty + transfer_qty}件】")

    if mode in (mode_info['mode_e1'], mode_info['mode_e1b'], mode_info['mode_e2']) and 'target_qty' in dest:
        notes_parts.append(f"【接收上限: E模式接收上限為安全庫存2倍(最少3件)，目標{dest['target_qty']}件，累計已接收{current_received_qty + transfer_qty}件】")

    if transfer_qty == 2 and source.get('original_stock', 0) == 1:
        notes_parts.append("【數量說明: 已優化至2件，最小轉移單位】")
    elif transfer_qty == 1:
        notes_parts.append("【數量說明: 最小轉移單位1件】")
    else:
        notes_parts.append(f"【數量說明: 轉移{transfer_qty}件】")

    remaining_stock = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
    notes_parts.append(f"【轉移後狀況: 轉出店鋪剩餘庫存{remaining_stock}件，接收店鋪累計接收{current_received_qty + transfer_qty}件】")

    if source['source_type'] in ['RF加強轉出']:
        notes_parts.append("【特殊標記: 加強轉出類型，需注意轉出後庫存狀況】")
    if source['source_type'] == 'E模式強制轉出':
        if mode == mode_info['mode_e1']:
            notes_parts.append("【特殊標記: E1模式強制轉出，僅同OM配對，店鋪被標記為*ALL*必須全數轉出】")
        elif mode == mode_info['mode_e1b']:
            notes_parts.append("【特殊標記: E1b模式強制轉出，僅同OM配對，接收端優先Type=T(遊客區)與Type=M(混合型)店舖】")
        elif mode == mode_info['mode_e2']:
            if source['om'] == dest['om']:
                notes_parts.append("【特殊標記: E2模式強制轉出，優先同OM配對，店鋪被標記為*ALL*必須全數轉出】")
            else:
                notes_parts.append("【特殊標記: E2模式強制轉出，跨OM配對(同OM無法接收)，店鋪被標記為*ALL*必須全數轉出】")
    if dest['dest_type'] == '重點補0':
        notes_parts.append("【特殊標記: 重點補0類型，確保最低保障標準】")
    if dest['dest_type'] == 'E模式接收' or str(dest.get('dest_type', '')).startswith('E1b'):
        notes_parts.append("【特殊標記: E模式接收，RF店鋪可接受來自標記為*ALL*的強制轉出】")
    if mode_info['is_simplified_sku']:
        if dest.get('dest_type') == '退回D001':
            notes_parts.append("【特殊標記: 精簡SKU模式，剩餘庫存退回D001】")
        elif dest.get('dest_type') == '精簡SKU接收':
            mode_variant = "限同OM" if mode == mode_info['mode_simplified_sku_same'] else "跨OM"
            notes_parts.append(f"【特殊標記: 精簡SKU模式({mode_variant})，RF存貨上限=Max(Safety×2, 過去2個月銷量×2)，參考C1模式最少2件起轉】")

    return " | ".join(notes_parts)
