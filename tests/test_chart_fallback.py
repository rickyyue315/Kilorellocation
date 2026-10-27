"""
圖表容錯與依賴配對測試 — 防止 Altair / Python 版本不相容再次中斷調貨流程

背景（v2.38.4）：Python 3.14 + altair 5.5.x 會在匯入圖表後端時拋
`_TypedDictMeta.__new__() got an unexpected keyword argument 'closed'`，
該錯誤發生在 STEP 3 圖表渲染，被 app.py 外層攔截後顯示為「處理文件時發生錯誤」。
"""

import os
import unittest
from unittest.mock import patch

from ui.display import _chart_error_hint, render_charts

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_STATS = {
    'article_stats': {'ART1': {'total_qty': 5}},
    'om_stats': {'OM1': {'transfer_qty': 3, 'receive_qty': 2}},
    'source_type_stats': {'R': {'qty': 4}},
    'dest_type_stats': {'N': {'qty': 6}},
}

_TYPED_DICT_ERROR = TypeError(
    "_TypedDictMeta.__new__() got an unexpected keyword argument 'closed'"
)


class TestChartErrorHint(unittest.TestCase):
    def test_typeddict_closed_error_gives_actionable_hint(self):
        hint = _chart_error_hint(_TYPED_DICT_ERROR)
        self.assertIn('altair', hint.lower())
        self.assertIn('3.14', hint)
        self.assertIn('requirements.txt', hint)

    def test_other_errors_keep_detail(self):
        hint = _chart_error_hint(ValueError('boom'))
        self.assertIn('ValueError', hint)
        self.assertIn('boom', hint)


class TestRenderChartsFallback(unittest.TestCase):
    def test_backend_failure_does_not_propagate(self):
        """圖表後端炸掉時 render_charts 必須吞掉例外，不可中斷後續流程。"""
        with patch('ui.display.st.bar_chart', side_effect=_TYPED_DICT_ERROR):
            render_charts(_STATS)  # 若拋錯，本測試即失敗

    def test_empty_statistics_returns_early(self):
        with patch('ui.display.st.bar_chart') as bar_chart:
            render_charts({})
            bar_chart.assert_not_called()


class TestRequirementsAltairPairing(unittest.TestCase):
    """altair 必須依 Python 版本分流，否則 3.14 部署會整組圖表掛掉。"""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT_DIR, 'requirements.txt'), encoding='utf-8') as fh:
            cls.requirements = fh.read()

    def test_altair_split_by_python_version(self):
        self.assertIn('altair==5.5.0; python_version < "3.14"', self.requirements)
        self.assertIn('altair==6.0.0; python_version >= "3.14"', self.requirements)

    def test_altair_not_pinned_without_marker(self):
        for line in self.requirements.splitlines():
            stripped = line.strip()
            if stripped.startswith('altair'):
                self.assertIn('python_version', stripped, f'altair 版本必須帶環境標記: {stripped}')

    def test_typing_extensions_floor(self):
        """PEP 728（TypedDict closed）支援自 typing_extensions 4.13 起。"""
        self.assertIn('typing_extensions>=4.13', self.requirements)


if __name__ == '__main__':
    unittest.main()
