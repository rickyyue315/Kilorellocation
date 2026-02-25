import os
import sys
from typing import Any, Dict, List

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic


def _build_dataset_for_mix_guard(cross_om: bool = False) -> pd.DataFrame:
    destination_om = 'OM2' if cross_om else 'OM1'
    return pd.DataFrame(
        [
            {
                'Article': '109249904201',
                'OM': 'OM1',
                'Site': 'MIX_SRC',
                'RP Type': 'RF',
                'SaSa Net Stock': 10,
                'Pending Received': 0,
                'Safety Stock': 1,
                'Last Month Sold Qty': 6,
                'MTD Sold Qty': 4,
                'MOQ': 1,
                'Effective Sold Qty': 1,
                'Article Description': 'Test Product Mix Guard',
                'Type': 'M',
            },
            {
                'Article': '109249904201',
                'OM': 'OM1',
                'Site': 'REG_SRC',
                'RP Type': 'RF',
                'SaSa Net Stock': 10,
                'Pending Received': 0,
                'Safety Stock': 1,
                'Last Month Sold Qty': 1,
                'MTD Sold Qty': 0,
                'MOQ': 1,
                'Effective Sold Qty': 0,
                'Article Description': 'Test Product Mix Guard',
                'Type': 'R',
            },
            {
                'Article': '109249904201',
                'OM': destination_om,
                'Site': 'LOW_DST',
                'RP Type': 'RF',
                'SaSa Net Stock': 0,
                'Pending Received': 0,
                'Safety Stock': 5,
                'Last Month Sold Qty': 1,
                'MTD Sold Qty': 1,
                'MOQ': 1,
                'Effective Sold Qty': 0,
                'Article Description': 'Test Product Mix Guard',
                'Type': 'T',
            },
        ]
    )


def _build_dataset_for_mix_allowed() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                'Article': '109249904202',
                'OM': 'OM1',
                'Site': 'MIX_SRC',
                'RP Type': 'RF',
                'SaSa Net Stock': 10,
                'Pending Received': 0,
                'Safety Stock': 1,
                'Last Month Sold Qty': 2,
                'MTD Sold Qty': 1,
                'MOQ': 1,
                'Effective Sold Qty': 1,
                'Article Description': 'Test Product Mix Allowed',
                'Type': 'M',
            },
            {
                'Article': '109249904202',
                'OM': 'OM1',
                'Site': 'HIGH_DST',
                'RP Type': 'RF',
                'SaSa Net Stock': 0,
                'Pending Received': 0,
                'Safety Stock': 5,
                'Last Month Sold Qty': 6,
                'MTD Sold Qty': 2,
                'MOQ': 1,
                'Effective Sold Qty': 6,
                'Article Description': 'Test Product Mix Allowed',
                'Type': 'T',
            },
        ]
    )


def test_mix_source_blocked_when_sales_higher_than_destination_b2_family():
    logic = TransferLogic()

    mode_to_cross_om = {
        logic.mode_b_special: False,
        logic.mode_b_special_a: False,
        logic.mode_b3: True,
        logic.mode_b3a: True,
    }

    for mode, cross_om in mode_to_cross_om.items():
        df = _build_dataset_for_mix_guard(cross_om=cross_om)
        recs = logic.generate_transfer_recommendations(df, mode)

        assert all(rec['Transfer Site'] != 'MIX_SRC' for rec in recs), (
            f"{mode}: Mix source should be blocked when source sales exceed destination sales."
        )
        assert any(rec['Transfer Site'] == 'REG_SRC' for rec in recs), (
            f"{mode}: Non-Mix source should remain eligible."
        )


def test_mix_source_allowed_when_destination_sales_not_lower():
    logic = TransferLogic()
    df = _build_dataset_for_mix_allowed()

    recs = logic.generate_transfer_recommendations(df, logic.mode_b_special)

    assert any(rec['Transfer Site'] == 'MIX_SRC' for rec in recs), (
        "Mix source should stay eligible when destination sales are not lower."
    )
