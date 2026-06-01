import io
import os
import sys

import pandas as pd
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from excel_generator import ExcelGenerator


def _make_recommendation(**overrides):
    defaults = {
        "Article": "000000000001",
        "Product Desc": "Test Product",
        "Transfer OM": "Ivy",
        "Transfer Site": "HA02",
        "Receive OM": "Ivy",
        "Receive Site": "HA03",
        "Transfer Qty": 5,
        "Original Stock": 10,
        "After Transfer Stock": 5,
        "Safety Stock": 3,
        "MOQ": 1,
        "Source Type": "RF過剩轉出",
        "Destination Type": "緊急缺貨補貨",
        "Notes": "Test note",
        "Transfer Site Last Month Sold Qty": 2,
        "Transfer Site MTD Sold Qty": 1,
        "Receive Site Last Month Sold Qty": 3,
        "Receive Site MTD Sold Qty": 1,
        "Receive Original Stock": 0,
    }
    defaults.update(overrides)
    return defaults


def _make_statistics():
    return {
        "total_recommendations": 1,
        "total_transfer_qty": 5,
        "unique_articles": 1,
        "unique_oms": 1,
        "article_stats": {
            "000000000001": {"total_qty": 5, "count": 1, "om_count": 1}
        },
        "om_stats": {
            "Ivy": {"total_qty": 5, "receive_qty": 5, "count": 1, "article_count": 1}
        },
        "source_type_stats": {
            "RF過剩轉出": {"count": 1, "qty": 5}
        },
        "dest_type_stats": {
            "緊急缺貨補貨": {"count": 1, "qty": 5}
        },
    }


@pytest.fixture
def generator():
    return ExcelGenerator()


class TestGenerateFilename:
    def test_filename_format(self, generator):
        filename = generator.generate_filename()
        assert filename.startswith("調貨建議_")
        assert filename.endswith(".xlsx")
        assert generator.output_filename == filename

    def test_filename_contains_timestamp(self, generator):
        filename = generator.generate_filename()
        parts = filename.replace("調貨建議_", "").replace(".xlsx", "")
        date_part, time_part = parts.split("_")
        assert len(date_part) == 8
        assert len(time_part) == 6


class TestGenerateRemark:
    def test_remark_format(self, generator):
        remark = generator._generate_remark("RF過剩轉出", "緊急缺貨補貨")
        assert remark == "RF過剩轉出 → 緊急缺貨補貨"


class TestGenerateExcelFile:
    def test_returns_bytes(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_xlsx_can_be_read_back(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats)
        df = pd.read_excel(io.BytesIO(result), sheet_name="調貨建議 (Transfer Recommendations)")
        assert len(df) == 1
        assert df.iloc[0]["Transfer Qty"] == 5

    def test_both_sheets_exist(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats)
        xl = pd.ExcelFile(io.BytesIO(result))
        sheet_names = xl.sheet_names
        assert "調貨建議 (Transfer Recommendations)" in sheet_names
        assert "統計摘要 (Summary Dashboard)" in sheet_names

    def test_empty_recommendations(self, generator):
        result = generator.generate_excel_file([], {})
        assert isinstance(result, bytes)
        df = pd.read_excel(io.BytesIO(result), sheet_name="調貨建議 (Transfer Recommendations)")
        assert len(df) == 0

    def test_recommendation_columns(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats)
        df = pd.read_excel(io.BytesIO(result), sheet_name="調貨建議 (Transfer Recommendations)")
        expected_cols = [
            "Article", "Transfer Site", "Receive Site", "Transfer Qty",
            "Remark", "Notes",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_missing_optional_keys_no_crash(self, generator):
        recs = [_make_recommendation()]
        del recs[0]["Notes"]
        del recs[0]["Source Type"]
        result = generator.generate_excel_file(recs, {})
        assert isinstance(result, bytes)

    def test_empty_statistics_no_crash(self, generator):
        recs = [_make_recommendation()]
        result = generator.generate_excel_file(recs, {})
        assert isinstance(result, bytes)


class TestGenerateExcelFileWithAIReport:
    def test_no_ai_report_still_has_two_sheets(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats, ai_report=None)
        xl = pd.ExcelFile(io.BytesIO(result))
        sheet_names = xl.sheet_names
        assert "調貨建議 (Transfer Recommendations)" in sheet_names
        assert "統計摘要 (Summary Dashboard)" in sheet_names
        assert len(sheet_names) == 2

    def test_with_ai_report_adds_ai_sheet(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        ai_report = {
            'advisor': {
                'mode_code': 'F2', 'mode_name': 'F指定模式',
                'confidence': 'medium', 'reasons': ['Reason 1'], 'warnings': [],
            },
            'audit': {
                'risk_level': 'low', 'summary': 'All good',
                'warnings': [],
                'positive_checks': ['Check 1'],
            },
            'model': 'test-model',
        }
        result = generator.generate_excel_file(recs, stats, ai_report=ai_report)
        xl = pd.ExcelFile(io.BytesIO(result))
        sheet_names = xl.sheet_names
        assert "AI分析摘要" in sheet_names
        assert len(sheet_names) == 3

    def test_ai_warnings_readable(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        ai_report = {
            'advisor': {},
            'audit': {
                'risk_level': 'high', 'summary': 'Many risks',
                'warnings': [
                    {'severity': 'high', 'title': 'Test Warning', 'detail': 'Detail text', 'suggested_check': 'Verify'},
                ],
                'positive_checks': [],
            },
            'model': 'test',
        }
        result = generator.generate_excel_file(recs, stats, ai_report=ai_report)
        xl = pd.ExcelFile(io.BytesIO(result))
        assert "AI分析摘要" in xl.sheet_names

    def test_empty_ai_report_no_crash(self, generator):
        recs = [_make_recommendation()]
        result = generator.generate_excel_file(recs, {}, ai_report={})
        xl = pd.ExcelFile(io.BytesIO(result))
        assert len(xl.sheet_names) == 2

    def test_ai_report_with_only_advisor(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        ai_report = {
            'advisor': {'mode_code': 'A', 'mode_name': '保守轉貨', 'confidence': 'low', 'reasons': [], 'warnings': []},
            'audit': None,
            'model': '',
        }
        result = generator.generate_excel_file(recs, stats, ai_report=ai_report)
        xl = pd.ExcelFile(io.BytesIO(result))
        assert "AI分析摘要" in xl.sheet_names

    def test_ai_report_with_only_auditor(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        ai_report = {
            'advisor': None,
            'audit': {'risk_level': 'low', 'summary': 'OK', 'warnings': [], 'positive_checks': []},
            'model': '',
        }
        result = generator.generate_excel_file(recs, stats, ai_report=ai_report)
        xl = pd.ExcelFile(io.BytesIO(result))
        assert "AI分析摘要" in xl.sheet_names
