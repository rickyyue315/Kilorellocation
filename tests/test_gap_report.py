# -*- coding: utf-8 -*-
"""
Tests for post-transfer gap report (store x SKU).
"""

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.statistics import (
    PreMatchSnapshot,
    capture_pre_match_snapshot,
    compute_gap_report,
)


# ---------------------------------------------------------------------------
# Helper: build source/dest dicts matching the real factory output
# ---------------------------------------------------------------------------

def _make_source(site: str, om: str, transferable_qty: int, source_type: str = 'RF過剩轉出',
                 priority: int = 2, original_stock: int = 10, safety_stock: int = 3) -> Dict:
    return {
        'site': site,
        'om': om,
        'rp_type': 'RF',
        'transferable_qty': transferable_qty,
        'priority': priority,
        'original_stock': original_stock,
        'effective_sold_qty': 5,
        'source_type': source_type,
        'store_type': '',
        'last_month_sold_qty': 3,
        'mtd_sold_qty': 2,
        'last_2_month_sold_qty': 3,
        'safety_stock': safety_stock,
        'supply_source': None,
    }


def _make_dest(site: str, om: str, needed_qty: int, dest_type: str = '緊急缺貨補貨',
               priority: int = 1, target_qty: int = 0, current_stock: int = 0,
               safety_stock: int = 3) -> Dict:
    return {
        'site': site,
        'om': om,
        'rp_type': 'RF',
        'needed_qty': needed_qty,
        'priority': priority,
        'current_stock': current_stock,
        'pending_received': 0,
        'safety_stock': safety_stock,
        'moq': 1,
        'effective_sold_qty': 3,
        'dest_type': dest_type,
        'target_qty': target_qty,
        'received_qty': 0,
        'last_month_sold_qty': 2,
        'mtd_sold_qty': 1,
    }


def _make_rec(article: str, transfer_site: str, receive_site: str,
              transfer_qty: int, transfer_om: str = 'OM1',
              receive_om: str = 'OM1') -> Dict:
    return {
        'Article': article,
        'Product Desc': 'Test Product',
        'Transfer OM': transfer_om,
        'Transfer Site': transfer_site,
        'Receive OM': receive_om,
        'Receive Site': receive_site,
        'Transfer Qty': transfer_qty,
        'Original Stock': 10,
        'After Transfer Stock': 7,
        'Safety Stock': 3,
        'MOQ': 1,
        'Source Type': 'RF過剩轉出',
        'Destination Type': '緊急缺貨補貨',
        'Notes': '',
        'Priority': '🔴高優先',
    }


# ===================================================================
# Tests: capture_pre_match_snapshot
# ===================================================================

class TestCapturePreMatchSnapshot:

    def test_basic_capture(self):
        sources = [_make_source('SITE01', 'OM1', 5)]
        dests = [_make_dest('SITE02', 'OM1', 3)]
        snap = capture_pre_match_snapshot(sources, dests, '000000000001', '保守轉貨')

        assert snap.article == '000000000001'
        assert snap.mode == '保守轉貨'
        assert len(snap.destinations) == 1
        assert len(snap.sources) == 1
        assert snap.destinations[0]['needed_qty'] == 3
        assert snap.sources[0]['transferable_qty'] == 5

    def test_empty_sources_or_dests(self):
        snap = capture_pre_match_snapshot([], [], '000000000001', 'A')
        assert len(snap.sources) == 0
        assert len(snap.destinations) == 0


# ===================================================================
# Tests: compute_gap_report
# ===================================================================

class TestComputeGapReport:

    def test_no_snapshots(self):
        result = compute_gap_report([], [])
        assert result['summary']['total_dest_gaps'] == 0
        assert result['summary']['total_gap_qty'] == 0
        assert result['summary']['total_source_remaining'] == 0
        assert len(result['details']) == 0

    def test_basic_gap_dest_only(self):
        """Single destination needing 3, receiving 1 → gap = 2"""
        sources = [_make_source('SITE01', 'OM1', 10)]
        dests = [_make_dest('SITE02', 'OM1', 3)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 1)]

        result = compute_gap_report([snap], recs)
        summary = result['summary']

        assert summary['total_dest_count'] == 1
        assert summary['total_dest_gaps'] == 1
        assert summary['total_gap_qty'] == 2  # 3 - 1
        assert summary['total_source_count'] == 1
        assert summary['total_source_remaining'] == 1  # 9 of 10 transferable unused → remaining
        assert summary['total_remaining_qty'] == 9     # 10 - 1

        # Check detail
        dest_details = [d for d in result['details'] if d['role'] == '目的地']
        assert len(dest_details) == 1
        assert dest_details[0]['gap_or_remaining'] == 2
        assert dest_details[0]['status'] == '未滿足(缺口2件)'

    def test_full_fulfillment(self):
        """Destination needing 3, receiving 3 → gap = 0 (已滿足)"""
        sources = [_make_source('SITE01', 'OM1', 10)]
        dests = [_make_dest('SITE02', 'OM1', 3)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 3)]

        result = compute_gap_report([snap], recs)
        summary = result['summary']

        assert summary['total_dest_gaps'] == 0
        assert summary['total_gap_qty'] == 0
        assert summary['total_dest_count'] == 1

        dest_details = [d for d in result['details'] if d['role'] == '目的地']
        assert dest_details[0]['gap_or_remaining'] == 0
        assert dest_details[0]['status'] == '已滿足'

    def test_source_remaining(self):
        """Source has 5 transferable, only 2 transferred → remaining = 3"""
        sources = [_make_source('SITE01', 'OM1', 5)]
        dests = [_make_dest('SITE02', 'OM1', 10)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 2)]

        result = compute_gap_report([snap], recs)
        summary = result['summary']

        assert summary['total_source_count'] == 1
        assert summary['total_source_remaining'] == 1
        assert summary['total_remaining_qty'] == 3  # 5 - 2

        src_details = [d for d in result['details'] if d['role'] == '來源']
        assert src_details[0]['gap_or_remaining'] == 3
        assert src_details[0]['status'] == '尚有剩餘(剩3件)'

    def test_source_fully_depleted(self):
        """Source has 5 transferable, 5 transferred → remaining = 0"""
        sources = [_make_source('SITE01', 'OM1', 5)]
        dests = [_make_dest('SITE02', 'OM1', 10)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 5)]

        result = compute_gap_report([snap], recs)
        src_details = [d for d in result['details'] if d['role'] == '來源']
        assert src_details[0]['gap_or_remaining'] == 0
        assert src_details[0]['status'] == '已配完'

    def test_e_mode_dest_na(self):
        """E-mode (強制轉出) destinations should be marked as not applicable."""
        sources = [_make_source('SITE01', 'OM1', 10)]
        dests = [_make_dest('SITE02', 'OM1', 5)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '強制轉出')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 3)]

        result = compute_gap_report([snap], recs)
        dest_details = [d for d in result['details'] if d['role'] == '目的地']
        assert len(dest_details) == 1
        assert dest_details[0]['status'] == '不適用(強制調撥)'
        assert dest_details[0]['gap_or_remaining'] == 0

    def test_d_mode_no_dest_gap(self):
        """D mode has sources but destinations may exist; gap works normally."""
        sources = [_make_source('SITE01', 'OM1', 10, source_type='ND清貨轉出',
                                original_stock=10)]
        dests = [_make_dest('SITE02', 'OM1', 5)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '清貨轉貨')

        recs = [_make_rec('ART001', 'SITE01', 'SITE02', 5)]

        result = compute_gap_report([snap], recs)
        assert result['summary']['total_dest_gaps'] == 0  # fully fulfilled

    def test_multiple_articles(self):
        """Multiple articles in snapshot should be handled correctly."""
        snap1 = capture_pre_match_snapshot(
            [_make_source('S01', 'OM1', 10)],
            [_make_dest('S02', 'OM1', 5)],
            'ART001', '保守轉貨',
        )
        snap2 = capture_pre_match_snapshot(
            [_make_source('S03', 'OM2', 8)],
            [_make_dest('S04', 'OM2', 4)],
            'ART002', '加強轉貨',
        )

        recs = [
            _make_rec('ART001', 'S01', 'S02', 3),
            _make_rec('ART002', 'S03', 'S04', 4),
        ]

        result = compute_gap_report([snap1, snap2], recs)
        assert result['summary']['total_dest_count'] == 2
        assert result['summary']['total_gap_qty'] == 2  # ART001 gap=2, ART002 gap=0
        assert result['summary']['total_dest_gaps'] == 1  # only ART001

        # Check by_mode grouping
        assert '保守轉貨' in result['by_mode']
        assert '加強轉貨' in result['by_mode']
        assert len(result['by_mode']['保守轉貨']['details']) == 2  # 1 dest + 1 source
        assert len(result['by_mode']['加強轉貨']['details']) == 2

    def test_same_site_different_role(self):
        """Same site can be destination for one article and source for another."""
        snap1 = capture_pre_match_snapshot(
            [_make_source('S01', 'OM1', 10)],
            [_make_dest('S02', 'OM1', 5)],
            'ART001', '保守轉貨',
        )
        snap2 = capture_pre_match_snapshot(
            [_make_source('S02', 'OM1', 7)],
            [_make_dest('S03', 'OM1', 3)],
            'ART002', '保守轉貨',
        )

        recs = [
            _make_rec('ART001', 'S01', 'S02', 5),
            _make_rec('ART002', 'S02', 'S03', 3),
        ]

        result = compute_gap_report([snap1, snap2], recs)
        assert result['summary']['total_dest_count'] == 2
        assert result['summary']['total_source_count'] == 2
        # S02 is both destination (ART001) and source (ART002) — no conflict since articles differ

    def test_summary_counts(self):
        """Verify summary aggregation counts."""
        snap1 = capture_pre_match_snapshot(
            [_make_source('S01', 'OM1', 10)],
            [_make_dest('S02', 'OM1', 5), _make_dest('S03', 'OM1', 3)],
            'ART001', '保守轉貨',
        )

        recs = [
            _make_rec('ART001', 'S01', 'S02', 2),
            _make_rec('ART001', 'S01', 'S03', 0),  # no transfer to S03
        ]
        # Actually S03 has 0 received, which means it won't appear in recommendations
        # But the gap report compares pre-match needs with actual received
        # S03 has need=3, received=0 → gap=3
        recs = [_make_rec('ART001', 'S01', 'S02', 2)]

        result = compute_gap_report([snap1], recs)
        summary = result['summary']
        assert summary['total_dest_count'] == 2
        assert summary['total_dest_gaps'] == 2  # both have gaps
        assert summary['total_gap_qty'] == (5-2) + (3-0)  # 3 + 3 = 6
        assert summary['total_source_count'] == 1
        assert summary['total_source_remaining'] == 1  # 8 of 10 transferable unused
        assert summary['total_remaining_qty'] == 8     # 10 - 2

    def test_fulfillment_rate(self):
        """Verify fulfillment rate calculation."""
        snap = capture_pre_match_snapshot(
            [_make_source('S01', 'OM1', 10)],
            [_make_dest('S02', 'OM1', 10), _make_dest('S03', 'OM1', 10)],
            'ART001', '保守轉貨',
        )
        recs = [
            _make_rec('ART001', 'S01', 'S02', 10),
            # S03 receives nothing
        ]
        result = compute_gap_report([snap], recs)
        # 1 of 2 fulfilled = 50%
        assert result['summary']['fulfillment_rate'] == 50.0

    def test_zero_need_edge_case(self):
        """Destination with needed_qty=0 should not cause division errors."""
        sources = [_make_source('S01', 'OM1', 10)]
        dests = [_make_dest('S02', 'OM1', 0)]  # need=0 is unusual but possible
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'S01', 'S02', 0)]

        result = compute_gap_report([snap], recs)
        # Should not crash; gap_pct should be 0
        dest_details = [d for d in result['details'] if d['role'] == '目的地']
        assert dest_details[0]['gap_pct'] == 0.0

    def test_dest_type_label_preserved(self):
        """The dest_type label from the snapshot should appear in the report."""
        sources = [_make_source('S01', 'OM1', 10)]
        dests = [_make_dest('S02', 'OM1', 5, dest_type='重點補0')]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'S01', 'S02', 2)]

        result = compute_gap_report([snap], recs)
        dest_details = [d for d in result['details'] if d['role'] == '目的地']
        assert dest_details[0]['type_label'] == '重點補0'

    def test_source_type_label_preserved(self):
        """The source_type label from the snapshot should appear in the report."""
        sources = [_make_source('S01', 'OM1', 10, source_type='ND清貨轉出')]
        dests = [_make_dest('S02', 'OM1', 5)]
        snap = capture_pre_match_snapshot(sources, dests, 'ART001', '保守轉貨')

        recs = [_make_rec('ART001', 'S01', 'S02', 2)]

        result = compute_gap_report([snap], recs)
        src_details = [d for d in result['details'] if d['role'] == '來源']
        assert src_details[0]['type_label'] == 'ND清貨轉出'
