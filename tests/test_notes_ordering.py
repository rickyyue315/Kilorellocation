"""Regression tests: Notes cumulative values align with final sorted order."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.post_processing import refresh_recommendation_fields
from services.prioritizer import PRIORITY_ORDER


def _dummy_note_fn(source, dest, current_received_qty, transfer_qty, mode):
    cumulative = current_received_qty + transfer_qty
    return f"累計{cumulative}件"


def _make_rec(article, transfer_site, receive_site, qty, priority_label, **kw):
    rec = {
        'Article': article,
        'Transfer Site': transfer_site,
        'Transfer OM': kw.get('transfer_om', 'OM1'),
        'Receive Site': receive_site,
        'Receive OM': kw.get('receive_om', 'OM1'),
        'Transfer Qty': qty,
        'Original Stock': 50,
        'Source Type': kw.get('source_type', 'RF過剩轉出'),
        'Source Priority': kw.get('source_priority', 5),
        'Destination Type': kw.get('dest_type', '緊急缺貨補貨'),
        'Destination Priority': kw.get('dest_priority', 5),
        'Target Qty': kw.get('target_qty', 0),
        'Safety Stock': kw.get('safety_stock', 3),
        'Receive Original Stock': 0,
        'Transfer Site Last Month Sold Qty': kw.get('src_last_month', 2),
        'Transfer Site MTD Sold Qty': kw.get('src_mtd', 1),
        'Receive Site Last Month Sold Qty': kw.get('dst_last_month', 3),
        'Receive Site MTD Sold Qty': kw.get('dst_mtd', 1),
        'Priority': priority_label,
    }
    rec.update(kw)
    return rec


class TestNotesCumulativeOrdering:
    def test_cumulative_values_match_sorted_order(self):
        article = "ART001"
        recv = "SITE_B"

        recs = [
            _make_rec(article, "SRC_A", recv, qty=10, priority_label='🔴高優先'),
            _make_rec(article, "SRC_B", recv, qty=5, priority_label='🟢低優先'),
            _make_rec(article, "SRC_C", recv, qty=8, priority_label='🟡中優先'),
        ]

        refresh_recommendation_fields(recs, 'A模式', _dummy_note_fn)

        recs.sort(key=lambda r: (
            PRIORITY_ORDER.get(r.get('Priority', '🟢低優先'), 99),
            -r.get('Transfer Qty', 0),
        ))

        refresh_recommendation_fields(recs, 'A模式', _dummy_note_fn)

        cum_values = []
        for r in recs:
            assert r['Article'] == article
            assert r['Receive Site'] == recv
            cum_values.append(r['Cumulative Received Qty'])

        for i in range(1, len(cum_values)):
            assert cum_values[i] > cum_values[i-1], (
                f"Cumulative value regressed: {cum_values[i-1]} -> {cum_values[i]} "
                f"at row {i}. Full cum seq: {cum_values}"
            )

        total_qty = sum(r['Transfer Qty'] for r in recs)
        assert cum_values[-1] == total_qty, (
            f"Final cumulative {cum_values[-1]} != total qty {total_qty}"
        )

    def test_notes_contain_monotonic_cumulative(self):
        article = "ART002"
        recv = "SITE_C"

        recs = [
            _make_rec(article, "SRC_X", recv, qty=7, priority_label='🟡中優先'),
            _make_rec(article, "SRC_Y", recv, qty=3, priority_label='🔴高優先'),
            _make_rec(article, "SRC_Z", recv, qty=12, priority_label='🟢低優先'),
        ]

        refresh_recommendation_fields(recs, 'B模式', _dummy_note_fn)

        recs.sort(key=lambda r: (
            PRIORITY_ORDER.get(r.get('Priority', '🟢低優先'), 99),
            -r.get('Transfer Qty', 0),
        ))

        refresh_recommendation_fields(recs, 'B模式', _dummy_note_fn)

        for i, r in enumerate(recs):
            note = r.get('Notes', '')
            assert '累計' in note, f"Row {i} Notes missing cumulative: {note}"

        prev_cum = 0
        for i, r in enumerate(recs):
            cum_in_note = r['Cumulative Received Qty']
            assert cum_in_note > prev_cum, (
                f"Row {i} cum {cum_in_note} <= prev {prev_cum}"
            )
            prev_cum = cum_in_note

    def test_multiple_article_groups_independent(self):
        recs = [
            _make_rec("A1", "SRC_A1", "SITE_X", qty=5, priority_label='🟢低優先'),
            _make_rec("A1", "SRC_B1", "SITE_X", qty=15, priority_label='🔴高優先'),
            _make_rec("A2", "SRC_A2", "SITE_Y", qty=10, priority_label='🔴高優先'),
            _make_rec("A2", "SRC_B2", "SITE_Y", qty=2, priority_label='🟢低優先'),
            _make_rec("A2", "SRC_C2", "SITE_Z", qty=8, priority_label='🟡中優先'),
        ]

        refresh_recommendation_fields(recs, 'A模式', _dummy_note_fn)

        recs.sort(key=lambda r: (
            PRIORITY_ORDER.get(r.get('Priority', '🟢低優先'), 99),
            -r.get('Transfer Qty', 0),
        ))

        refresh_recommendation_fields(recs, 'A模式', _dummy_note_fn)

        groups = {}
        for r in recs:
            key = (r['Article'], r['Receive Site'])
            groups.setdefault(key, []).append(r)

        for key, group in groups.items():
            cum_vals = [r['Cumulative Received Qty'] for r in group]
            for i in range(1, len(cum_vals)):
                assert cum_vals[i] > cum_vals[i-1], (
                    f"Group {key}: cum regressed {cum_vals[i-1]} -> {cum_vals[i]}"
                )
            total = sum(r['Transfer Qty'] for r in group)
            assert cum_vals[-1] == total, (
                f"Group {key}: final cum {cum_vals[-1]} != total {total}"
            )
