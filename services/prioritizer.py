"""
Priority assignment engine — deterministic rules, zero API dependency.
Assigns 🔴/🟡/🟢 priority to each recommendation dict.
"""

from typing import Any, Dict

PRIORITY_ORDER = {'🔴高優先': 0, '🟡中優先': 1, '🟢低優先': 2}


def assign_priority(rec: Dict[str, Any]) -> str:
    qty = rec.get('Transfer Qty', 0)
    src_pri = rec.get('Source Priority', 99)
    dst_pri = rec.get('Destination Priority', 99)
    src_type = rec.get('Source Type', '')
    dst_type = rec.get('Destination Type', '')
    notes = rec.get('Notes', '')

    if qty >= 100:
        return '🔴高優先'
    if src_pri <= 1:
        return '🔴高優先'
    if dst_pri <= 1:
        return '🔴高優先'
    if dst_type == '退回D001' or 'D001' in notes:
        return '🔴高優先'
    if '強制' in src_type:
        return '🔴高優先'

    if qty >= 30:
        return '🟡中優先'
    if dst_pri <= 3:
        return '🟡中優先'
    if '重點補0' in dst_type or '目標優化' in dst_type or '目標性' in dst_type:
        return '🟡中優先'

    return '🟢低優先'
