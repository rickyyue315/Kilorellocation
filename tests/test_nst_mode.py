"""
NST 模式測試 — New Shop Target調貨
"""

import numpy as np
import pandas as pd
import pytest

from business_logic import TransferLogic
from models.mode_registry import MODE_DEFS


def _make_nst_df(rows):
    columns = [
        'Article', 'OM', 'RP Type', 'Site', 'SaSa Net Stock',
        'Pending Received', 'Safety Stock', 'Last Month Sold Qty',
        'MTD Sold Qty', 'MOQ', 'Target', 'Article Description',
    ]
    df = pd.DataFrame(rows, columns=columns)
    df['Target'] = pd.to_numeric(df['Target'], errors='coerce')
    df['Effective Sold Qty'] = df['Last Month Sold Qty'] + df['MTD Sold Qty']
    return df


def _get_nst_recs(df, nst_max_source_shops=None):
    logic = TransferLogic(nst_max_source_shops=nst_max_source_shops)
    return logic.generate_transfer_recommendations(df, "New Shop Target調貨")


class TestNSTModeRegistry:
    def test_mode_registered(self):
        nst_def = next((d for d in MODE_DEFS if d.code == "NST"), None)
        assert nst_def is not None
        assert nst_def.name == "New Shop Target調貨"
        assert nst_def.cross_om_grouping is True
        assert nst_def.cross_om_matching is True
        assert nst_def.strategy_key == 'nst_mode'
        assert 'nst_shop_limit' in nst_def.extra_ui_options


class TestNSTRFSourceRules:
    def test_rf_stock_below_3_not_source(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'ND', 'N001', 10, 0, 0, 0, 0, 1, None, 'ND with stock'],
            ['10001', 'Ivy', 'RF', 'HD001', 2, 0, 2, 1, 0, 1, None, 'RF low stock'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 10, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        sources = set(r['Transfer Site'] for r in recs)
        assert 'N001' in sources
        assert 'HD001' not in sources

    def test_rf_stock_10_transfer_capped(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', 'HD001', 10, 0, 2, 0, 0, 1, None, 'RF high stock'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 8, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        assert len(recs) > 0
        total_transferred = sum(r['Transfer Qty'] for r in recs)
        assert total_transferred <= 7

    def test_rf_stock_4_transfer_2(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', 'HD001', 4, 0, 2, 0, 0, 1, None, 'RF medium stock'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 5, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        assert len(recs) > 0
        total_transferred = sum(r['Transfer Qty'] for r in recs)
        assert total_transferred <= 2

    def test_rf_stock_3_transfer_1(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', 'HD001', 3, 0, 2, 0, 0, 1, None, 'RF stock 3'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 5, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        total_transferred = sum(r['Transfer Qty'] for r in recs if r['Transfer Site'] == 'HD001')
        assert total_transferred <= 1


class TestNSTNDSourceRules:
    def test_nd_full_transfer(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'ND', 'N001', 8, 0, 0, 0, 0, 1, None, 'ND stock'],
            ['10001', 'Ivy', 'RF', 'HD001', 0, 0, 2, 5, 0, 1, 8, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        sources = set(r['Transfer Site'] for r in recs)
        assert 'N001' in sources


class TestNSTTargetReception:
    def test_target_only_receives(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'ND', 'N001', 10, 0, 0, 0, 0, 1, None, 'ND stock'],
            ['10001', 'Ivy', 'RF', 'HD001', 0, 0, 2, 0, 0, 1, None, 'RF no target'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 8, 'Target store'],
        ])
        recs = _get_nst_recs(df)
        receive_sites = set(r['Receive Site'] for r in recs)
        assert 'HD002' in receive_sites
        assert 'HD001' not in receive_sites

    def test_target_nd_can_receive(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', 'HD001', 10, 0, 2, 0, 0, 1, None, 'RF stock'],
            ['10001', 'Ivy', 'ND', 'N001', 0, 0, 0, 0, 0, 1, 5, 'ND target store'],
        ])
        recs = _get_nst_recs(df)
        receive_sites = set(r['Receive Site'] for r in recs)
        assert 'N001' in receive_sites


class TestNSTShopLimit:
    def test_shop_limit_10_allows(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', f'S{i:02d}', 10, 0, 2, 0, 0, 1, None, f'Source {i}']
            for i in range(12)
        ] + [
            ['10001', 'Ivy', 'RF', 'HD100', 0, 0, 2, 5, 0, 1, 120, 'Big target'],
        ])
        recs = _get_nst_recs(df, nst_max_source_shops=10)
        source_sites = set(r['Transfer Site'] for r in recs)
        assert len(source_sites) <= 10

    def test_shop_limit_unlimited(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', f'S{i:02d}', 10, 0, 2, 0, 0, 1, None, f'Source {i}']
            for i in range(15)
        ] + [
            ['10001', 'Ivy', 'RF', 'HD100', 0, 0, 2, 5, 0, 1, 150, 'Big target'],
        ])
        recs = _get_nst_recs(df, nst_max_source_shops=None)
        source_sites = set(r['Transfer Site'] for r in recs)
        assert len(source_sites) >= 5


class TestNSTTargetProtectedSource:
    def test_target_store_not_source(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'RF', 'HD001', 10, 0, 2, 0, 0, 1, 5, 'Has target'],
            ['10001', 'Ivy', 'RF', 'HD002', 10, 0, 2, 0, 0, 1, None, 'No target'],
            ['10001', 'Ivy', 'RF', 'HD003', 0, 0, 2, 5, 0, 1, 8, 'Target store 2'],
        ])
        recs = _get_nst_recs(df)
        source_sites = set(r['Transfer Site'] for r in recs)
        assert 'HD001' not in source_sites
        assert 'HD002' in source_sites


class TestNSTNotes:
    def test_source_note(self):
        df = _make_nst_df([
            ['10001', 'Ivy', 'ND', 'N001', 5, 0, 0, 0, 0, 1, None, 'ND'],
            ['10001', 'Ivy', 'RF', 'HD001', 10, 0, 2, 0, 0, 1, None, 'RF'],
            ['10001', 'Ivy', 'RF', 'HD002', 0, 0, 2, 5, 0, 1, 20, 'Target'],
        ])
        recs = _get_nst_recs(df)
        assert len(recs) > 0
        for r in recs:
            assert 'Notes' in r or 'note' in str(r.keys()).lower()
