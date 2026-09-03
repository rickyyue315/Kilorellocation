"""
UI 輔助結構測試 — 模式選項與文檔的完整性（防止新增模式時漏配）
"""

import unittest

from models.mode_registry import (
    MODE_DEFS,
    get_ui_options,
)
from ui.mode_docs import MODE_DOCS, GENERAL_DOCS


class TestUiOptions(unittest.TestCase):
    def test_ui_options_cover_all_modes_exactly_once(self):
        """get_ui_options() 應恰好覆蓋全部 30 個模式，且無重複。"""
        all_codes = [d.code for d in MODE_DEFS]
        option_codes = [o.split(":", 1)[0].strip() for o in get_ui_options()]

        self.assertEqual(len(all_codes), 30)
        self.assertEqual(sorted(option_codes), sorted(all_codes))
        self.assertEqual(len(option_codes), len(set(option_codes)), "選項不可重複")

    def test_ui_options_format(self):
        """選項字串須維持 "CODE: name" 格式（app.py 以 split(":", 1) 解析）。"""
        options = get_ui_options()
        self.assertEqual(len(options), len(MODE_DEFS), "選項數量不符")
        for option in options:
            self.assertIn(":", option)
            code, _name = option.split(":", 1)
            self.assertIn(code.strip(), [d.code for d in MODE_DEFS])


class TestModeDocs(unittest.TestCase):
    def test_every_mode_has_docs(self):
        """每個模式 code 都必須有詳細說明（防新增模式時漏寫文檔）。"""
        missing = [d.code for d in MODE_DEFS if d.code not in MODE_DOCS]
        self.assertEqual(missing, [], f"以下模式缺少 MODE_DOCS 條目: {missing}")

    def test_docs_content_nonempty(self):
        for code, doc in MODE_DOCS.items():
            self.assertTrue(doc.strip(), f"模式 {code} 的文檔為空")

    def test_general_docs_nonempty(self):
        self.assertTrue(GENERAL_DOCS.strip())
        self.assertIn("轉出類型判斷", GENERAL_DOCS)
        self.assertIn("接收條件說明", GENERAL_DOCS)


if __name__ == "__main__":
    unittest.main()
