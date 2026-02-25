import os
import sys
from typing import Any, Dict, List, Set, cast

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_logic import TransferLogic


def _build_b2_dataset() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = [
        {
            'Article': '109249904001',
            'OM': 'OM1',
            'Site': 'SRC01',
            'RP Type': 'ND',
            'SaSa Net Stock': 20,
            'Pending Received': 0,
            'Safety Stock': 0,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
            'MOQ': 1,
            'Effective Sold Qty': 0,
            'Article Description': 'Test Product',
            'Type': 'R',
        }
    ]

    for site in ['DST01', 'DST02', 'DST03', 'DST04']:
        rows.append(
            {
                'Article': '109249904001',
                'OM': 'OM1',
                'Site': site,
                'RP Type': 'RF',
                'SaSa Net Stock': 0,
                'Pending Received': 0,
                'Safety Stock': 5,
                'Last Month Sold Qty': 3,
                'MTD Sold Qty': 1,
                'MOQ': 1,
                'Effective Sold Qty': 4,
                'Article Description': 'Test Product',
                'Type': 'T',
            }
        )

    return pd.DataFrame(rows)


def _build_b3_dataset() -> pd.DataFrame:
    rows: List[Dict[str, Any]] = [
        {
            'Article': '109249904002',
            'OM': 'OM1',
            'Site': 'SRC02',
            'RP Type': 'ND',
            'SaSa Net Stock': 20,
            'Pending Received': 0,
            'Safety Stock': 0,
            'Last Month Sold Qty': 0,
            'MTD Sold Qty': 0,
            'MOQ': 1,
            'Effective Sold Qty': 0,
            'Article Description': 'Test Product',
            'Type': 'R',
        }
    ]

    destination_rows = [
        ('DST11', 'OM1'),
        ('DST12', 'OM1'),
        ('DST13', 'OM2'),
        ('DST14', 'OM2'),
    ]

    for site, om in destination_rows:
        rows.append(
            {
                'Article': '109249904002',
                'OM': om,
                'Site': site,
                'RP Type': 'RF',
                'SaSa Net Stock': 0,
                'Pending Received': 0,
                'Safety Stock': 5,
                'Last Month Sold Qty': 2,
                'MTD Sold Qty': 1,
                'MOQ': 1,
                'Effective Sold Qty': 3,
                'Article Description': 'Test Product',
                'Type': 'T',
            }
        )

    return pd.DataFrame(rows)


def _assert_source_receive_site_limit(recommendations: List[Dict[str, Any]], max_sites: int = 2) -> None:
    source_to_receive_sites: Dict[str, Set[str]] = {}

    for rec in recommendations:
        source = rec['Transfer Site']
        source_to_receive_sites.setdefault(source, set()).add(rec['Receive Site'])

    for source, receive_sites in source_to_receive_sites.items():
        assert len(receive_sites) <= max_sites, (
            f"Source {source} matched to {len(receive_sites)} receive sites, exceeds limit {max_sites}."
        )


def test_b2_source_receive_site_limit_max_two():
    logic = TransferLogic(b_special_max_receive_sites_per_source=2)
    df = _build_b2_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b_special))

    _assert_source_receive_site_limit(recommendations, max_sites=2)


def test_b2_source_receive_site_limit_max_one():
    logic = TransferLogic(b_special_max_receive_sites_per_source=1)
    df = _build_b2_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b_special))

    _assert_source_receive_site_limit(recommendations, max_sites=1)


def test_b2a_source_receive_site_limit_max_one():
    logic = TransferLogic(b_special_max_receive_sites_per_source=1)
    df = _build_b2_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b_special_a))

    _assert_source_receive_site_limit(recommendations, max_sites=1)



def test_b3_source_receive_site_limit_max_two():
    logic = TransferLogic(b_special_max_receive_sites_per_source=2)
    df = _build_b3_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b3))

    _assert_source_receive_site_limit(recommendations, max_sites=2)


def test_b3a_source_receive_site_limit_max_one():
    logic = TransferLogic(b_special_max_receive_sites_per_source=1)
    df = _build_b3_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b3a))

    _assert_source_receive_site_limit(recommendations, max_sites=1)


def test_b2_source_receive_site_unlimited_can_exceed_two():
    logic = TransferLogic(b_special_max_receive_sites_per_source=None)
    df = _build_b2_dataset()

    recommendations = cast(List[Dict[str, Any]], logic.generate_transfer_recommendations(df, logic.mode_b_special))

    source_to_receive_sites: Dict[str, Set[str]] = {}
    for rec in recommendations:
        source = rec['Transfer Site']
        source_to_receive_sites.setdefault(source, set()).add(rec['Receive Site'])

    assert any(len(receive_sites) > 2 for receive_sites in source_to_receive_sites.values()), (
        "Unlimited mode should allow a source site to match more than 2 receive sites."
    )
