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


class TestSmartSummarySheet:
    def test_no_ai_summary_two_sheets(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats)
        xl = pd.ExcelFile(io.BytesIO(result))
        assert len(xl.sheet_names) == 2
        assert '智能摘要' not in xl.sheet_names

    def test_with_ai_summary_adds_sheet(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats, ai_summary='這是一段測試摘要')
        xl = pd.ExcelFile(io.BytesIO(result))
        assert '智能摘要' in xl.sheet_names
        assert len(xl.sheet_names) == 3

    def test_empty_string_no_sheet(self, generator):
        recs = [_make_recommendation()]
        stats = _make_statistics()
        result = generator.generate_excel_file(recs, stats, ai_summary='')
        xl = pd.ExcelFile(io.BytesIO(result))
        assert '智能摘要' not in xl.sheet_names
