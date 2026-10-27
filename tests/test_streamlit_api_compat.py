"""
Streamlit API 相容性測試 — 防止已棄用參數回流

背景（v2.38.5）：Streamlit 1.52 起 `use_container_width` 進入棄用期
（官方公告 2025-12-31 後移除），每次 rerun、每個元件都會各印一條警告，
Community Cloud 日誌會被灌爆。專案全面改用 `width="stretch"`。
"""

import os
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _scanned_files():
    """掃描入口檔與 ui/ 下所有模組（新增模組自動納入）。"""
    files = [os.path.join(ROOT_DIR, 'app.py')]
    ui_dir = os.path.join(ROOT_DIR, 'ui')
    files += [
        os.path.join(ui_dir, name)
        for name in sorted(os.listdir(ui_dir))
        if name.endswith('.py')
    ]
    return files


class TestNoDeprecatedContainerWidth(unittest.TestCase):
    def test_no_use_container_width(self):
        offenders = []
        for path in _scanned_files():
            with open(path, encoding='utf-8') as fh:
                for lineno, line in enumerate(fh, 1):
                    if 'use_container_width' in line:
                        rel = os.path.relpath(path, ROOT_DIR)
                        offenders.append(f'{rel}:{lineno}: {line.strip()}')
        self.assertEqual(
            offenders,
            [],
            '偵測到已棄用的 use_container_width，請改用 width="stretch"：\n' + '\n'.join(offenders),
        )

    def test_width_stretch_is_used(self):
        """確認新寫法確實存在（避免整批被誤刪成無寬度設定）。"""
        found = 0
        for path in _scanned_files():
            with open(path, encoding='utf-8') as fh:
                found += fh.read().count('width="stretch"')
        self.assertGreater(found, 0)


if __name__ == '__main__':
    unittest.main()
