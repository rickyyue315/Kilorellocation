import json
import os
import sys
from unittest.mock import patch

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _make_recommendation(**overrides):
    defaults = {
        "Article": "000000000001",
        "Transfer OM": "Ivy",
        "Transfer Site": "HA01",
        "Receive OM": "Ivy",
        "Receive Site": "HA02",
        "Transfer Qty": 5,
        "Source Type": "RF過剩轉出",
        "Destination Type": "緊急缺貨補貨",
    }
    defaults.update(overrides)
    return defaults


def _make_statistics():
    return {
        "total_recommendations": 1,
        "total_transfer_qty": 5,
        "unique_articles": 1,
        "unique_oms": 1,
        "source_type_stats": {"RF過剩轉出": {"count": 1, "qty": 5}},
        "dest_type_stats": {"緊急缺貨補貨": {"count": 1, "qty": 5}},
    }


class TestBuildAuditPayload:
    def _build(self):
        from services.ai_auditor import build_audit_payload
        return build_audit_payload

    def test_payload_does_not_contain_full_recommendations(self):
        recs = [_make_recommendation(Article=f"ART{i:03d}") for i in range(100)]
        payload = self._build()(recs, _make_statistics(), True, [], "F")
        assert 'mode' in payload
        assert payload['total_recommendations'] == 100
        assert len(payload.get('large_qty_recommendations', [])) <= 10

    def test_capped_samples_not_exceed_max(self):
        recs = [_make_recommendation(Article=f"ART{i:03d}") for i in range(50)]
        payload = self._build()(recs, _make_statistics(), True, [], "A")
        assert len(payload.get('large_qty_recommendations', [])) <= 10
        assert len(payload.get('top_articles_by_qty', [])) <= 10
        assert len(payload.get('top_transfer_sites_by_qty', [])) <= 10
        assert len(payload.get('top_receive_sites_by_qty', [])) <= 10

    def test_cross_om_count(self):
        recs = [
            _make_recommendation(**{'Transfer OM': 'Ivy', 'Receive OM': 'Ivy'}),
            _make_recommendation(**{'Transfer OM': 'Ivy', 'Receive OM': 'Violet'}),
            _make_recommendation(**{'Transfer OM': 'Windy', 'Receive OM': 'Windy'}),
        ]
        payload = self._build()(recs, _make_statistics(), True, [], "B3")
        assert payload['cross_om_transfer_count'] == 1

    def test_quality_errors_capped(self):
        errors = [f"error {i}" for i in range(20)]
        payload = self._build()([_make_recommendation()], _make_statistics(), False, errors, "A")
        assert payload['quality_error_count'] == 20
        assert len(payload['quality_errors']) <= 10


class TestParseAuditResponse:
    def _parser(self):
        from services.ai_auditor import parse_audit_response
        return parse_audit_response

    def test_parse_pure_json(self):
        text = json.dumps({
            "risk_level": "中風險",
            "summary": "Some risks detected.",
            "warnings": [
                {"severity": "中", "title": "High concentration", "detail": "One source dominates", "suggested_check": "Verify distribution"}
            ],
            "positive_checks": ["All items have valid MOQ"],
        })
        result = self._parser()(text)
        assert result['risk_level'] == '中風險'
        assert result['summary'] == 'Some risks detected.'
        assert len(result['warnings']) == 1
        assert len(result['positive_checks']) == 1

    def test_parse_fenced_json(self):
        text = '```json\n{"risk_level": "低風險", "summary": "All good", "warnings": [], "positive_checks": ["Clean data"]}\n```'
        result = self._parser()(text)
        assert result['risk_level'] == '低風險'
        assert result['summary'] == 'All good'

    def test_invalid_json_fallback(self):
        result = self._parser()('not valid json at all')
        assert 'error' in result
        assert result['error'] == 'parse_failed'

    def test_invalid_risk_level_falls_back_to_low(self):
        text = '{"risk_level": "extreme", "summary": "", "warnings": [], "positive_checks": []}'
        result = self._parser()(text)
        assert result['risk_level'] == '低風險'


class TestAuditDoesNotMutate:
    def test_original_recommendations_unchanged(self):
        rc = _make_recommendation()
        recs = [rc]
        with patch('services.ai_auditor.chat_completion', return_value='{"risk_level":"低風險","summary":"","warnings":[],"positive_checks":[]}'):
            from services.ai_auditor import audit_recommendations
            audit_recommendations(recs, _make_statistics(), True, [], "A")
            assert recs[0]['Transfer Qty'] == 5
            assert len(recs) == 1


class TestAuditDisabled:
    def test_empty_response_no_crash(self):
        with patch('services.ai_auditor.chat_completion', return_value=''):
            from services.ai_auditor import audit_recommendations
            result = audit_recommendations([_make_recommendation()], _make_statistics(), True, [], "A")
            assert 'error' in result
            assert result['error'] == 'empty_response'
