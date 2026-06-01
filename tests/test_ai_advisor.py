import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _make_minimal_df(**kw):
    data = {
        'Article': ['ART001', 'ART001', 'ART002'],
        'OM': ['Ivy', 'Ivy', 'Ivy'],
        'RP Type': ['RF', 'RF', 'ND'],
        'Site': ['HA01', 'HA02', 'HA03'],
        'SaSa Net Stock': [10, 0, 5],
        'Pending Received': [2, 0, 0],
        'Safety Stock': [3, 3, 3],
        'Last Month Sold Qty': [5, 2, 0],
        'MTD Sold Qty': [3, 1, 0],
        'MOQ': [2, 2, 2],
    }
    data.update(kw)
    return pd.DataFrame(data)


class TestBuildDFSummary:
    def test_no_row_level_records(self):
        df = _make_minimal_df()
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert 'Article' not in summary
        assert summary['total_rows'] == 3

    def test_rp_type_counts(self):
        df = _make_minimal_df()
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert summary['rp_type_counts'] == {'RF': 2, 'ND': 1}
        assert summary['nd_ratio'] == pytest.approx(0.333)
        assert summary['rf_ratio'] == pytest.approx(0.667)

    def test_target_positive(self):
        df = _make_minimal_df(Target=[5, 3, 0])
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert summary['has_target_column'] is True
        assert summary['target_positive_rows'] == 2
        assert summary['target_positive_sites'] == 2

    def test_all_marked(self):
        df = _make_minimal_df(ALL=['*', '*', None])
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert summary['has_all_column'] is True
        assert summary['all_marked_rows'] == 2

    def test_type_counts(self):
        df = _make_minimal_df(Type=['L', 'M', 'T'])
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert summary['has_type_column'] is True
        assert summary['type_counts'] == {'L': 1, 'M': 1, 'T': 1}

    def test_stock_counts(self):
        df = _make_minimal_df()
        summary = __import__('services.ai_advisor', fromlist=['build_df_summary']).build_df_summary(df)
        assert summary['zero_stock_count'] == 1
        low = summary['low_stock_count']
        assert low >= 1


class TestBuildModeOptions:
    def test_count_matches_mode_defs(self):
        from models.mode_registry import MODE_DEFS
        builder = __import__('services.ai_advisor', fromlist=['build_mode_options'])
        options = builder.build_mode_options()
        assert len(options) == len(MODE_DEFS)

    def test_each_option_has_required_keys(self):
        builder = __import__('services.ai_advisor', fromlist=['build_mode_options'])
        for opt in builder.build_mode_options():
            assert 'code' in opt
            assert 'name' in opt
            assert 'description' in opt
            assert 'cross_om_matching' in opt
            assert 'receive_site_limit' in opt
            assert 'required_columns' in opt


class TestParseAdvisorResponse:
    def parser(self):
        return __import__('services.ai_advisor', fromlist=['parse_advisor_response']).parse_advisor_response

    def test_parse_pure_json(self):
        text = json.dumps({
            'mode_code': 'F2',
            'mode_name': 'F指定模式',
            'confidence': 'medium',
            'reasons': ['Has Target column', 'Cross-OM matches needed'],
            'warnings': ['Verify data completeness'],
        })
        result = self.parser()(text)
        assert result['mode_code'] == 'F2'
        assert result['mode_name'] == 'F指定模式'
        assert result['confidence'] == 'medium'
        assert len(result['reasons']) == 2

    def test_parse_fenced_json(self):
        text = '```json\n{\n  "mode_code": "C",\n  "mode_name": "重點補0",\n  "confidence": "high",\n  "reasons": ["Low stock detected"],\n  "warnings": []\n}\n```'
        result = self.parser()(text)
        assert result['mode_code'] == 'C'
        assert result['mode_name'] == '重點補0'
        assert result['confidence'] == 'high'

    def test_parse_json_with_wrapper_text(self):
        text = 'Based on analysis, here is the recommendation:\n{"mode_code": "A", "mode_name": "保守轉貨", "confidence": "low", "reasons": ["Safe strategy"], "warnings": []}'
        result = self.parser()(text)
        assert result['mode_code'] == 'A'

    def test_invalid_mode_code_returns_error(self):
        text = '{"mode_code": "ZZ99", "mode_name": "Fake", "confidence": "high", "reasons": [], "warnings": []}'
        result = self.parser()(text)
        assert 'error' in result
        assert result['error'] == 'invalid_mode_code'

    def test_invalid_confidence_falls_back_to_low(self):
        text = '{"mode_code": "A", "mode_name": "保守轉貨", "confidence": "super_sure", "reasons": [], "warnings": []}'
        result = self.parser()(text)
        assert result['confidence'] == 'low'

    def test_empty_response_returns_error(self):
        result = self.parser()('')
        assert 'error' in result
        assert result['error'] == 'empty_response'


class TestRecommendModeFallback:
    def test_chat_empty_response_returns_error(self):
        with patch('services.ai_client.chat_completion', return_value=''):
            from services.ai_advisor import recommend_mode
            result = recommend_mode(_make_minimal_df())
            assert 'error' in result
