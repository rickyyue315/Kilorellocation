import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic


def _base_rec(transfer_site: str, receive_site: str, qty: int, recv_last: int, recv_mtd: int) -> Dict[str, Any]:
    return {
        'Article': '100000000001',
        'Product Desc': 'Test Product',
        'Transfer OM': 'Queenie',
        'Transfer Site': transfer_site,
        'Receive OM': 'Queenie',
        'Receive Site': receive_site,
        'Transfer Qty': qty,
        'Original Stock': 20,
        'After Transfer Stock': 0,
        'Safety Stock': 0,
        'MOQ': 1,
        'Source Priority': 1,
        'Destination Priority': 1,
        'Source Type': 'ND轉出',
        'Destination Type': '緊急缺貨補貨',
        'Notes': '',
        'Transfer Site Last Month Sold Qty': 0,
        'Transfer Site MTD Sold Qty': 0,
        'Receive Site Last Month Sold Qty': recv_last,
        'Receive Site MTD Sold Qty': recv_mtd,
        'Receive Original Stock': 0,
    }


def test_optimize_single_qty_rebalance_to_avoid_one_piece():
    logic = TransferLogic()

    recs: List[Dict[str, Any]] = [
        _base_rec('HA42', 'HA32', 11, 6, 4),
        _base_rec('HA42', 'HA44', 1, 2, 1),
    ]

    optimized = logic._optimize_single_piece_transfers(recs, logic.mode_b)

    qty_by_receive = {r['Receive Site']: r['Transfer Qty'] for r in optimized}
    assert qty_by_receive.get('HA32') == 10
    assert qty_by_receive.get('HA44') == 2


def test_optimize_single_qty_merge_to_higher_sales_destination():
    logic = TransferLogic()

    recs: List[Dict[str, Any]] = [
        _base_rec('HC62', 'HC49', 2, 8, 5),
        _base_rec('HC62', 'HC61', 1, 1, 0),
    ]

    optimized = logic._optimize_single_piece_transfers(recs, logic.mode_e1)

    assert len(optimized) == 1
    assert optimized[0]['Receive Site'] == 'HC49'
    assert optimized[0]['Transfer Qty'] == 3
