import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


SAMPLE_RECS = [
    {
        'Article': '900123456789',
        'Product Desc': 'Test Product',
        'Transfer Site': 'HA12',
        'Transfer OM': 'Ivy',
        'Receive Site': 'HA45',
        'Receive OM': 'Ivy',
        'Transfer Qty': 5,
        'Source Type': 'ND轉出',
        'Destination Type': '遊客區店舖 高銷量優先',
        'Source Original Stock': 8,
        'Source After Transfer Stock': 3,
        'source_original_stock': 8,
        'source_after_transfer': 3,
        'source_last_month_sold_qty': 0,
        'source_mtd_sold_qty': 0,
        'dest_original_stock': 0,
        'dest_cumulative_received_qty': 5,
        'dest_safety_stock': 3,
        'dest_last_month_sold_qty': 4,
        'dest_mtd_sold_qty': 2,
        'Notes': '【轉出分類: ND轉出】 | 【接收分類: 遊客區店舖 高銷量優先】',
    }
]

SAMPLE_AI_RESPONSE = json.dumps([
    {
        "id": 0,
        "ai_note": "ND零銷量店清貨至零庫存遊客區高銷量店，配對合理，轉出後仍餘3件安全",
        "risk": "🟢",
        "needs_review": False,
    }
], ensure_ascii=False)


class TestEnrichDisabled:
    def test_enrich_disabled(self):
        with patch('config.AI_BATCH_NOTES_ENABLED', False), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=True):
            from services.ai_batch_notes import enrich_notes_with_ai
            recs = [dict(r) for r in SAMPLE_RECS]
            enrich_notes_with_ai(recs, 'B2')
            assert recs[0]['Notes'] == SAMPLE_RECS[0]['Notes']
            assert 'AI Risk' not in recs[0]

    def test_enrich_no_api_key(self):
        with patch('config.AI_BATCH_NOTES_ENABLED', True), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=False):
            from services.ai_batch_notes import enrich_notes_with_ai
            recs = [dict(r) for r in SAMPLE_RECS]
            enrich_notes_with_ai(recs, 'B2')
            assert recs[0]['Notes'] == SAMPLE_RECS[0]['Notes']
            assert 'AI Risk' not in recs[0]


class TestBuildBatchContext:
    def test_build_batch_context(self):
        from services.ai_batch_notes import _build_batch_context
        context = _build_batch_context('900123456789', SAMPLE_RECS, 'B2')
        assert context['article'] == '900123456789'
        assert context['product_desc'] == 'Test Product'
        assert context['mode'] == 'B2'
        assert len(context['recommendations']) == 1
        rec = context['recommendations'][0]
        assert rec['id'] == 0
        assert rec['from_site'] == 'HA12'
        assert rec['to_site'] == 'HA45'
        assert rec['qty'] == 5
        assert rec['is_cross_om'] is False
        assert context['summary']['total_out_qty'] == 5
        assert context['summary']['total_sources'] == 1
        assert context['summary']['has_cross_om'] is False


class TestParseAIResponse:
    def test_parse_valid_json(self):
        from services.ai_batch_notes import _parse_ai_response
        results = _parse_ai_response(SAMPLE_AI_RESPONSE, SAMPLE_RECS)
        assert len(results) == 1
        assert 0 in results
        assert results[0]['ai_note'].startswith('ND零銷量店')
        assert results[0]['risk'] == '🟢'
        assert results[0]['needs_review'] is False

    def test_parse_invalid_json(self):
        from services.ai_batch_notes import _parse_ai_response
        results = _parse_ai_response('not valid json', SAMPLE_RECS)
        assert results == {}

    def test_parse_partial_json(self):
        from services.ai_batch_notes import _parse_ai_response
        partial = json.dumps([
            {"id": 0, "ai_note": "valid note", "risk": "🟢", "needs_review": False},
            {"id": 5, "ai_note": "out of range", "risk": "🟡", "needs_review": False},
        ])
        results = _parse_ai_response(partial, SAMPLE_RECS)
        assert len(results) == 1
        assert 0 in results
        assert results[0]['ai_note'] == 'valid note'

    def test_parse_empty_response(self):
        from services.ai_batch_notes import _parse_ai_response
        assert _parse_ai_response('', SAMPLE_RECS) == {}
        assert _parse_ai_response('   ', SAMPLE_RECS) == {}


class TestNotesAppended:
    def test_notes_appended_not_replaced(self):
        from services.ai_batch_notes import _process_one_article
        with patch('services.ai_batch_notes.chat_completion', return_value=SAMPLE_AI_RESPONSE):
            results = _process_one_article('900123456789', SAMPLE_RECS, 'B2')
            assert len(results) == 1
            assert 0 in results

    def test_ai_risk_field_added(self):
        from services.ai_batch_notes import enrich_notes_with_ai
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            'choices': [{'message': {'content': SAMPLE_AI_RESPONSE}}]
        }
        mock_response.status_code = 200

        with patch('config.AI_BATCH_NOTES_ENABLED', True), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=True), \
             patch('httpx.Client') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            recs = [dict(r) for r in SAMPLE_RECS]
            recs[0]['Notes'] = '【轉出分類: ND轉出】'
            enrich_notes_with_ai(recs, 'B2')
            assert 'AI Risk' in recs[0]
            assert recs[0]['AI Risk'] == '🟢'
            assert 'AI Needs Review' in recs[0]
            assert recs[0]['AI Needs Review'] is False
            assert '【AI分析:' in recs[0]['Notes']
            assert '【AI風險:' in recs[0]['Notes']
            assert '【轉出分類: ND轉出】' in recs[0]['Notes']


class TestEdgeCases:
    def test_empty_recommendations(self):
        from services.ai_batch_notes import enrich_notes_with_ai
        with patch('config.AI_BATCH_NOTES_ENABLED', True), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=True):
            enrich_notes_with_ai([], 'B2')

    def test_single_article_group(self):
        from services.ai_batch_notes import enrich_notes_with_ai
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            'choices': [{'message': {'content': SAMPLE_AI_RESPONSE}}]
        }
        mock_response.status_code = 200

        with patch('config.AI_BATCH_NOTES_ENABLED', True), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=True), \
             patch('httpx.Client') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            recs = [dict(r) for r in SAMPLE_RECS]
            enrich_notes_with_ai(recs, 'B2')
            assert 'AI Risk' in recs[0]

    def test_api_failure_graceful(self):
        from services.ai_batch_notes import enrich_notes_with_ai
        with patch('config.AI_BATCH_NOTES_ENABLED', True), \
             patch('services.ai_batch_notes.is_ai_enabled', return_value=True), \
             patch('services.ai_batch_notes.chat_completion', return_value=''):
            recs = [dict(r) for r in SAMPLE_RECS]
            original_notes = recs[0]['Notes']
            enrich_notes_with_ai(recs, 'B2')
            assert recs[0]['Notes'] == original_notes
            assert 'AI Risk' not in recs[0]
