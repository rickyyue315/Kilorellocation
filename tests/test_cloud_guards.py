"""雲端資源防護測試（v2.38.3 P0）：上傳上限、行數守衛、結果表列數限制。

Community Cloud 免費方案約 1GB RAM；這些機制避免大型輸入把容器撐爆。
"""

import pandas as pd
import pytest

import config
import data_processor
from data_processor import DataProcessor
from ui import display
from ui.display import _limit_rows


class _FakeUpload:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


class TestCloudAwareLimits:
    """config 依執行環境（本機／雲端）套用不同的上傳與行數上限。"""

    def test_upload_limit_follows_runtime(self):
        expected = config.CLOUD_MAX_UPLOAD_MB if config.IS_CLOUD_RUNTIME else config.LOCAL_MAX_UPLOAD_MB
        assert config.MAX_UPLOAD_MB == expected
        assert config.FILE_SIZE_LIMIT_BYTES == expected * 1024 * 1024

    def test_row_limit_follows_runtime(self):
        expected = config.CLOUD_MAX_ROWS if config.IS_CLOUD_RUNTIME else 0
        assert config.MAX_ROWS == expected

    def test_local_environment_is_unrestricted(self):
        if config.IS_CLOUD_RUNTIME:
            pytest.skip("此測試預期在本機（非雲端）環境執行")
        assert config.MAX_UPLOAD_MB == 50
        assert config.MAX_ROWS == 0

    def test_file_size_message_uses_configured_limit(self):
        too_big = _FakeUpload("stock.xlsx", config.FILE_SIZE_LIMIT_BYTES + 1)
        ok, msg = DataProcessor().validate_file_format(too_big)
        assert ok is False
        assert f"{config.MAX_UPLOAD_MB}MB" in msg

    def test_small_file_passes_format_check(self):
        ok, msg = DataProcessor().validate_file_format(_FakeUpload("stock.xlsx", 1024))
        assert ok is True
        assert msg == ""


class TestRowGuard:
    """enforce_row_limit：雲端行數守衛（本機 MAX_ROWS=0 時不限制）。"""

    @staticmethod
    def _df(rows: int) -> pd.DataFrame:
        return pd.DataFrame({"Article": [f"{i:012d}" for i in range(rows)], "Site": ["HA1"] * rows})

    def test_raises_when_over_limit(self, monkeypatch):
        monkeypatch.setattr(data_processor, "MAX_ROWS", 5)
        with pytest.raises(ValueError) as exc:
            DataProcessor().enforce_row_limit(self._df(6))
        assert "6 行" in str(exc.value)
        assert "5 行" in str(exc.value)

    def test_passes_when_at_limit(self, monkeypatch):
        monkeypatch.setattr(data_processor, "MAX_ROWS", 5)
        DataProcessor().enforce_row_limit(self._df(5))

    def test_disabled_when_zero(self, monkeypatch):
        monkeypatch.setattr(data_processor, "MAX_ROWS", 0)
        DataProcessor().enforce_row_limit(self._df(5000))


class TestResultPreviewLimit:
    """_limit_rows / _maybe_limit_rows：雲端只渲染前 N 列，不影響匯出資料。"""

    def test_limit_rows_truncates_only_when_needed(self):
        df = pd.DataFrame({"a": range(10)})
        assert len(_limit_rows(df, 3)) == 3
        assert len(_limit_rows(df, 10)) == 10
        assert len(_limit_rows(df, 100)) == 10
        assert len(_limit_rows(df, 0)) == 10

    def test_no_limit_outside_cloud(self):
        df = pd.DataFrame({"a": range(10)})
        if display.IS_CLOUD_RUNTIME:
            pytest.skip("此測試預期在本機（非雲端）環境執行")
        assert len(display._maybe_limit_rows(df, "測試表", "k")) == 10
