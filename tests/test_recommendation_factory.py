"""Tests for services/recommendation_factory.build_recommendation Type propagation."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.recommendation_factory import build_recommendation


def _make_source(**overrides):
    source = {
        'site': 'HA02',
        'om': 'Ivy',
        'rp_type': 'RF',
        'transferable_qty': 5,
        'priority': 2,
        'original_stock': 10,
        'effective_sold_qty': 2,
        'source_type': 'RF過剩轉出',
        'store_type': 'T',
        'last_month_sold_qty': 2,
        'mtd_sold_qty': 1,
        'safety_stock': 3,
        'supply_source': None,
    }
    source.update(overrides)
    return source


def _make_dest(**overrides):
    dest = {
        'site': 'HA03',
        'om': 'Ivy',
        'rp_type': 'RF',
        'needed_qty': 5,
        'priority': 1,
        'current_stock': 0,
        'pending_received': 0,
        'safety_stock': 5,
        'moq': 1,
        'effective_sold_qty': 3,
        'dest_type': '緊急缺貨補貨',
        'target_qty': 5,
        'received_qty': 0,
        'last_month_sold_qty': 3,
        'mtd_sold_qty': 1,
        'store_type': 'M',
    }
    dest.update(overrides)
    return dest


class TestBuildRecommendationTypeFields:
    def test_propagates_store_type(self):
        rec = build_recommendation(
            '000000000001', 'Test Product',
            _make_source(), _make_dest(), 5, 'note', 0,
        )
        assert rec['Transfer Site Type'] == 'T'
        assert rec['Receive Site Type'] == 'M'

    def test_missing_store_type_defaults_empty(self):
        source = _make_source()
        dest = _make_dest()
        source.pop('store_type')
        dest.pop('store_type')
        rec = build_recommendation(
            '000000000001', 'Test Product', source, dest, 5, 'note', 0,
        )
        assert rec['Transfer Site Type'] == ''
        assert rec['Receive Site Type'] == ''

    def test_d001_return_receive_type_empty(self):
        rec = build_recommendation(
            '000000000001', 'Test Product',
            _make_source(), _make_dest(), 5, 'note', 0,
            is_d001_return=True,
        )
        assert rec['Transfer Site Type'] == 'T'
        assert rec['Receive Site Type'] == ''
