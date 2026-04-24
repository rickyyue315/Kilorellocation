import os
import sys
from typing import Any, Dict, List

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic


def _build_b2_like_dataset() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = [
        {
            'Article': '109249904101',
            'OM': 'OM1',
            'Site': 'SRC_T',
            'RP Type': 'RF',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'MOQ': 1,
            'Effective Sold Qty': 1,
            'Article Description': 'Test Product B2a',
            'Type': 'T',
        },
        {
            'Article': '109249904101',
            'OM': 'OM1',
            'Site': 'DST_M',
            'RP Type': 'RF',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'MOQ': 1,
            'Effective Sold Qty': 4,
            'Article Description': 'Test Product B2a',
            'Type': 'M',
        },
    ]
    return pd.DataFrame(rows)


def _build_b3_like_dataset() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = [
        {
            'Article': '109249904102',
            'OM': 'OM1',
            'Site': 'SRC_T_X',
            'RP Type': 'RF',
            'SaSa Net Stock': 10,
            'Pending Received': 0,
            'Safety Stock': 1,
            'Last Month Sold Qty': 1,
            'MTD Sold Qty': 0,
            'MOQ': 1,
            'Effective Sold Qty': 1,
            'Article Description': 'Test Product B3a',
            'Type': 'T',
        },
        {
            'Article': '109249904102',
            'OM': 'OM2',
            'Site': 'DST_M_X',
            'RP Type': 'RF',
            'SaSa Net Stock': 0,
            'Pending Received': 0,
            'Safety Stock': 5,
            'Last Month Sold Qty': 3,
            'MTD Sold Qty': 1,
            'MOQ': 1,
            'Effective Sold Qty': 4,
            'Article Description': 'Test Product B3a',
            'Type': 'M',
        },
    ]
    return pd.DataFrame(rows)


def test_b2a_tourist_type_t_not_source():
    logic = TransferLogic()
    df = _build_b2_like_dataset()

    recs_b2 = logic.generate_transfer_recommendations(df, logic.mode_b_special)
    recs_b2a = logic.generate_transfer_recommendations(df, logic.mode_b_special_a)

    assert any(rec['Transfer Site'] == 'SRC_T' for rec in recs_b2), "B2 baseline should allow Type=T source in this dataset."
    assert all(rec['Transfer Site'] != 'SRC_T' for rec in recs_b2a), "B2a must block Type=T source."


def test_b2la_tourist_type_t_not_source():
    logic = TransferLogic()
    df = _build_b2_like_dataset()

    recs_b2l = logic.generate_transfer_recommendations(df, logic.mode_b2l)
    recs_b2la = logic.generate_transfer_recommendations(df, logic.mode_b2la)

    assert any(rec['Transfer Site'] == 'SRC_T' for rec in recs_b2l), "B2L baseline should allow Type=T source in this dataset."
    assert all(rec['Transfer Site'] != 'SRC_T' for rec in recs_b2la), "B2La must block Type=T source."


def test_b3a_tourist_type_t_not_source():
    logic = TransferLogic()
    df = _build_b3_like_dataset()

    recs_b3 = logic.generate_transfer_recommendations(df, logic.mode_b3)
    recs_b3a = logic.generate_transfer_recommendations(df, logic.mode_b3a)

    assert any(rec['Transfer Site'] == 'SRC_T_X' for rec in recs_b3), "B3 baseline should allow Type=T source in this dataset."
    assert all(rec['Transfer Site'] != 'SRC_T_X' for rec in recs_b3a), "B3a must block Type=T source."


def test_b3la_tourist_type_t_not_source():
    logic = TransferLogic()
    df = _build_b3_like_dataset()

    recs_b3l = logic.generate_transfer_recommendations(df, logic.mode_b3l)
    recs_b3la = logic.generate_transfer_recommendations(df, logic.mode_b3la)

    assert any(rec['Transfer Site'] == 'SRC_T_X' for rec in recs_b3l), "B3L baseline should allow Type=T source in this dataset."
    assert all(rec['Transfer Site'] != 'SRC_T_X' for rec in recs_b3la), "B3La must block Type=T source."
