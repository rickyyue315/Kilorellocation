"""Tests for services/prioritizer.py — deterministic priority rule engine."""

import pytest
from services.prioritizer import assign_priority, PRIORITY_ORDER


def _make_rec(overrides: dict) -> dict:
    defaults = {
        'Transfer Qty': 10,
        'Source Priority': 5,
        'Destination Priority': 5,
        'Source Type': 'RF過剩轉出',
        'Destination Type': '一般接收',
        'Notes': '',
    }
    defaults.update(overrides)
    return defaults


class TestPriorityOrder:
    def test_order_definition(self):
        assert PRIORITY_ORDER['🔴高優先'] < PRIORITY_ORDER['🟡中優先']
        assert PRIORITY_ORDER['🟡中優先'] < PRIORITY_ORDER['🟢低優先']


class TestHighPriority:
    def test_qty_100_or_more(self):
        assert assign_priority(_make_rec({'Transfer Qty': 100})) == '🔴高優先'

    def test_qty_above_100(self):
        assert assign_priority(_make_rec({'Transfer Qty': 999})) == '🔴高優先'

    def test_source_priority_1(self):
        assert assign_priority(_make_rec({'Source Priority': 1})) == '🔴高優先'

    def test_source_priority_2(self):
        assert assign_priority(_make_rec({'Source Priority': 2})) == '🔴高優先'

    def test_dest_priority_1(self):
        assert assign_priority(_make_rec({'Destination Priority': 1})) == '🔴高優先'

    def test_d001_return_destination_type(self):
        assert assign_priority(_make_rec({'Destination Type': '退回D001'})) == '🔴高優先'

    def test_d001_return_in_notes(self):
        assert assign_priority(_make_rec({'Notes': '退D001', 'Destination Type': '一般接收'})) == '🔴高優先'

    def test_forced_transfer_source_type(self):
        assert assign_priority(_make_rec({
            'Source Type': '強制轉出',
            'Transfer Qty': 5,
            'Source Priority': 5,
        })) == '🔴高優先'


class TestMediumPriority:
    def test_qty_30(self):
        assert assign_priority(_make_rec({'Transfer Qty': 30})) == '🟡中優先'

    def test_qty_between_30_and_99(self):
        assert assign_priority(_make_rec({'Transfer Qty': 50})) == '🟡中優先'

    def test_dest_priority_3(self):
        assert assign_priority(_make_rec({'Destination Priority': 3, 'Transfer Qty': 5})) == '🟡中優先'

    def test_target_optimization_dest_type(self):
        assert assign_priority(_make_rec({
            'Destination Type': '目標優化',
            'Transfer Qty': 5,
            'Source Priority': 5,
        })) == '🟡中優先'

    def test_key_supplement_dest_type(self):
        assert assign_priority(_make_rec({
            'Destination Type': '重點補0',
            'Transfer Qty': 5,
        })) == '🟡中優先'


class TestLowPriority:
    def test_small_qty_normal(self):
        assert assign_priority(_make_rec({'Transfer Qty': 5})) == '🟢低優先'

    def test_qty_29(self):
        assert assign_priority(_make_rec({'Transfer Qty': 29})) == '🟢低優先'

    def test_zero_qty(self):
        assert assign_priority(_make_rec({'Transfer Qty': 0})) == '🟢低優先'

    def test_default_priority(self):
        assert assign_priority(_make_rec({})) == '🟢低優先'


class TestEdgeCases:
    def test_high_beats_medium_when_qty_high_but_dest_prio_medium(self):
        """高件數優先級應蓋過目的地優先級"""
        assert assign_priority(_make_rec({
            'Transfer Qty': 100,
            'Destination Priority': 3,
        })) == '🔴高優先'

    def test_high_beats_medium_when_source_prio_low(self):
        assert assign_priority(_make_rec({
            'Source Priority': 2,
            'Transfer Qty': 10,
        })) == '🔴高優先'

    def test_medium_beats_low_on_qty(self):
        assert assign_priority(_make_rec({'Transfer Qty': 30})) != '🟢低優先'

    def test_all_fields_missing(self):
        assert assign_priority({}) == '🟢低優先'
