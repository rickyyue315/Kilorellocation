import io
import os
import sys

import pandas as pd
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data_processor import DataProcessor


def _make_minimal_df(rows=None, **overrides):
    defaults = {
        "Article": "12345",
        "OM": "Ivy",
        "RP Type": "RF",
        "Site": "HA02",
        "SaSa Net Stock": 10,
        "Pending Received": 0,
        "Safety Stock": 3,
        "Last Month Sold Qty": 2,
        "MTD Sold Qty": 1,
        "MOQ": 1,
    }
    if rows is None:
        defaults.update(overrides)
        return pd.DataFrame([defaults])
    result = []
    for r in rows:
        d = dict(defaults)
        d.update(r)
        result.append(d)
    return pd.DataFrame(result)


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def processor():
    return DataProcessor()


class TestReadExcelFile:
    def test_article_zero_padding(self, processor):
        df = _make_minimal_df(Article="456")
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert result["Article"].iloc[0] == "000000000456"

    def test_article_truncation(self, processor):
        df = _make_minimal_df(Article="1234567890123")
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert len(result["Article"].iloc[0]) == 12
        assert result["Article"].iloc[0] == "234567890123"

    def test_column_case_insensitive_all(self, processor):
        df = _make_minimal_df()
        df = df.rename(columns={"RP Type": "RP Type"})
        df["all"] = "X"
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert "ALL" in result.columns
        assert result["ALL"].iloc[0] == "X"

    def test_column_case_insensitive_target(self, processor):
        df = _make_minimal_df()
        df = df.rename(columns={"RP Type": "RP Type"})
        df["target"] = "5"
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert "Target" in result.columns

    def test_column_case_insensitive_type(self, processor):
        df = _make_minimal_df()
        df["type"] = "R"
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert "Type" in result.columns

    def test_missing_article_description_fallback_to_long_text(self, processor):
        df = _make_minimal_df()
        df = df.drop(columns=["Article Description"], errors="ignore")
        df["Article Long Text (60 Chars)"] = "Long desc"
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert result["Article Description"].iloc[0] == "Long desc"

    def test_missing_article_description_no_long_text(self, processor):
        df = _make_minimal_df()
        df = df.drop(columns=["Article Description"], errors="ignore")
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert result["Article Description"].iloc[0] == "N/A"

    def test_missing_optional_columns_created(self, processor):
        df = _make_minimal_df()
        buf = _df_to_excel_bytes(df)
        result = processor.read_excel_file(io.BytesIO(buf))
        assert "ALL" in result.columns
        assert "Target" in result.columns
        assert "Type" in result.columns


class TestValidateColumns:
    def test_validate_columns_pass(self, processor):
        df = _make_minimal_df()
        assert processor.validate_columns(df) is True

    def test_validate_columns_fail_missing_article(self, processor):
        df = _make_minimal_df().drop(columns=["Article"])
        assert processor.validate_columns(df) is False


class TestValidateFileFormat:
    def _mock_file(self, name, size=100):
        class MockFile:
            pass
        f = MockFile()
        f.name = name
        f.size = size
        return f

    def test_valid_xlsx(self, processor):
        f = self._mock_file("test.xlsx")
        ok, msg = processor.validate_file_format(f)
        assert ok is True
        assert msg == ""

    def test_valid_xls(self, processor):
        f = self._mock_file("test.xls")
        ok, msg = processor.validate_file_format(f)
        assert ok is True

    def test_wrong_extension(self, processor):
        f = self._mock_file("test.csv")
        ok, msg = processor.validate_file_format(f)
        assert ok is False
        assert "xlsx" in msg or "xls" in msg

    def test_oversized_file(self, processor):
        f = self._mock_file("test.xlsx", size=60 * 1024 * 1024)
        ok, msg = processor.validate_file_format(f)
        assert ok is False
        assert "50" in msg or "大小" in msg


class TestConvertDataTypes:
    def test_integer_coercion(self, processor):
        df = _make_minimal_df(**{"SaSa Net Stock": "abc"})
        result = processor.convert_data_types(df)
        assert result["SaSa Net Stock"].iloc[0] == 0

    def test_string_trim(self, processor):
        df = _make_minimal_df(OM="  Ivy  ")
        result = processor.convert_data_types(df)
        assert result["OM"].iloc[0] == "Ivy"

    def test_invalid_rp_type_auto_corrected(self, processor):
        df = _make_minimal_df(**{"RP Type": "XX"})
        result = processor.convert_data_types(df)
        assert result["RP Type"].iloc[0] == "RF"
        assert processor._invalid_rp_type_count == 1

    def test_valid_rp_type_unchanged(self, processor):
        df = _make_minimal_df(**{"RP Type": "ND"})
        result = processor.convert_data_types(df)
        assert result["RP Type"].iloc[0] == "ND"


class TestFillDefaultStoreData:
    def test_fill_om_for_known_site(self, processor):
        df = _make_minimal_df(**{"OM": ""}, Site="HA02")
        result = processor.fill_default_store_data(df)
        assert result["OM"].iloc[0] != ""

    def test_no_overwrite_existing_om(self, processor):
        df = _make_minimal_df(OM="Ivy", Site="HA02")
        result = processor.fill_default_store_data(df)
        assert result["OM"].iloc[0] == "Ivy"

    def test_unknown_site_recorded(self, processor):
        df = _make_minimal_df(**{"OM": ""}, Site="UNKNOWN_SITE_XYZ")
        processor.fill_default_store_data(df)
        assert "UNKNOWN_SITE_XYZ" in processor.fill_stats["sites_not_found"]


class TestHandleMissingValues:
    def test_nan_safety_stock_filled(self, processor):
        df = _make_minimal_df()
        df["Safety Stock"] = df["Safety Stock"].astype(float)
        df.loc[0, "Safety Stock"] = float("nan")
        result = processor.handle_missing_values(df)
        assert result["Safety Stock"].iloc[0] == 0

    def test_nan_moq_filled(self, processor):
        df = _make_minimal_df()
        df["MOQ"] = df["MOQ"].astype(float)
        df.loc[0, "MOQ"] = float("nan")
        result = processor.handle_missing_values(df)
        assert result["MOQ"].iloc[0] == 0


class TestCorrectOutliers:
    def test_negative_sales_clamped(self, processor):
        df = _make_minimal_df(**{"Last Month Sold Qty": -5})
        result = processor.correct_outliers(df)
        assert result["Last Month Sold Qty"].iloc[0] == 0

    def test_outlier_sales_capped(self, processor):
        df = _make_minimal_df(**{"Last Month Sold Qty": 200000})
        result = processor.correct_outliers(df)
        assert result["Last Month Sold Qty"].iloc[0] == 100000

    def test_negative_safety_stock_clamped(self, processor):
        df = _make_minimal_df(**{"Safety Stock": -3})
        df["Safety Stock"] = df["Safety Stock"].astype(int)
        result = processor.correct_outliers(df)
        assert result["Safety Stock"].iloc[0] == 0


class TestCalculateEffectiveSoldQty:
    def test_basic_calculation(self, processor):
        df = _make_minimal_df(**{"Last Month Sold Qty": 3, "MTD Sold Qty": 2})
        result = processor.calculate_effective_sold_qty(df)
        assert result["Effective Sold Qty"].iloc[0] == 5


class TestPreprocessData:
    def test_full_pipeline(self, processor):
        df = _make_minimal_df()
        buf = _df_to_excel_bytes(df)
        result_df, stats = processor.preprocess_data(io.BytesIO(buf))
        assert len(result_df) == 1
        assert "Effective Sold Qty" in result_df.columns
        assert "original_stats" in stats
        assert "processed_stats" in stats

    def test_missing_columns_raises_value_error(self, processor):
        df = pd.DataFrame({"Article": ["123"]})
        buf = _df_to_excel_bytes(df)
        with pytest.raises(ValueError, match="缺少必需欄位"):
            processor.preprocess_data(io.BytesIO(buf))

    def test_stats_contain_fill_stats(self, processor):
        df = _make_minimal_df()
        buf = _df_to_excel_bytes(df)
        _, stats = processor.preprocess_data(io.BytesIO(buf))
        assert "fill_stats" in stats["processed_stats"]

    def test_stats_contain_invalid_rp_types(self, processor):
        df = _make_minimal_df()
        buf = _df_to_excel_bytes(df)
        _, stats = processor.preprocess_data(io.BytesIO(buf))
        assert "invalid_rp_types" in stats["processed_stats"]
        assert "invalid_rp_type_count" in stats["processed_stats"]
