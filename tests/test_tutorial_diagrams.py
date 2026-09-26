"""教學圖片產生器測試 — 每個模式都應產出合法 SVG。"""

import glob
import json
import re
import unittest

from ui import tutorial_diagrams as td


def _load_all_modes():
    modes = []
    for path in sorted(glob.glob("data/tutorials/*.json")):
        modes.extend(json.load(open(path, encoding="utf-8")))
    return modes


class TestTutorialDiagrams(unittest.TestCase):
    def test_all_modes_have_logic_svg(self):
        modes = _load_all_modes()
        self.assertEqual(len(modes), 30)
        for m in modes:
            svg = td.build_mode_logic_svg(m)
            self.assertTrue(svg.startswith("<svg"), f"{m.get('code')} 邏輯圖非 SVG")
            self.assertIn(str(m.get("code")), svg)
            self.assertIn("轉出", svg)
            self.assertIn("接收", svg)
            self.assertIn("配對", svg)

    def test_plain_and_collect(self):
        self.assertEqual(td._plain("<b>x</b><br>y"), "x y")
        self.assertEqual(td._plain("a &gt; b"), "a > b")
        nodes = td._collect_nodes([
            {"type": "row", "items": [
                {"type": "node", "text": "A<br>B", "color": "green"},
                {"type": "node", "text": "C", "color": "blue"},
            ]},
            {"type": "arrow", "label": "x"},
        ])
        self.assertEqual(nodes, ["A B", "C"])

    def test_scenario_svg_basic(self):
        modes = {m["code"]: m for m in _load_all_modes()}
        svg_a = td.build_mode_scenario_svg(modes["A"])
        self.assertTrue(svg_a.startswith("<svg"))
        self.assertIn("HD001", svg_a)
        # 無表格時回傳空字串而非報錯
        self.assertEqual(td.build_mode_scenario_svg({"code": "X"}), "")

    def test_scenario_svg_all_modes_no_crash(self):
        for m in _load_all_modes():
            svg = td.build_mode_scenario_svg(m)
            self.assertIsInstance(svg, str)
            if svg:
                self.assertTrue(svg.startswith("<svg"))

    def test_overview_and_decision_svg(self):
        modes = _load_all_modes()
        by_group = {}
        for m in modes:
            by_group.setdefault(m["code"], m)
        groups = [
            ("基礎調貨", [("A", "低"), ("A1", "低"), ("B", "中")], "日常補貨", "僅同OM"),
            ("B特別", [("B2", "中")], "Type分類", "僅同OM"),
        ]
        svg = td.build_overview_map_svg(groups)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("A1", svg)
        d = td.build_decision_tree_svg()
        self.assertTrue(d.startswith("<svg"))
        self.assertIn("調貨需求", d)


def _svg_height(svg: str) -> int:
    m = re.search(r'height="(\d+)"', svg)
    assert m, "SVG 缺少 height 屬性"
    return int(m.group(1))


class TestCompactLayout(unittest.TestCase):
    """版面緊湊度：圖片高度設上限，一眼望清。"""

    def test_logic_svg_height_bounded(self):
        for m in _load_all_modes():
            h = _svg_height(td.build_mode_logic_svg(m))
            self.assertLessEqual(h, 480, f"{m.get('code')} 邏輯圖太高 ({h})")

    def test_scenario_svg_height_bounded(self):
        for m in _load_all_modes():
            svg = td.build_mode_scenario_svg(m)
            if svg:
                self.assertLessEqual(_svg_height(svg), 320, f"{m.get('code')} 情境圖太高")

    def test_overview_height_bounded(self):
        groups = [("組", [(m["code"], m.get("risk", "中")) for m in _load_all_modes()[:4]], "用途", "僅同OM")]
        self.assertLessEqual(_svg_height(td.build_overview_map_svg(groups * 4)), 560)

    def test_global_and_floor_svg(self):
        import xml.etree.ElementTree as ET
        g = td.build_global_rules_svg()
        self.assertTrue(g.startswith("<svg"))
        ET.fromstring(g)
        self.assertLessEqual(_svg_height(g), 480)
        for keyword in ("ND", "雙重角色", "單件"):
            self.assertIn(keyword, g)
        f = td.build_floor_body_svg()
        self.assertTrue(f.startswith("<svg"))
        ET.fromstring(f)
        self.assertLessEqual(_svg_height(f), 520)
        for keyword in ("Safety", "Turnday", "30"):
            self.assertIn(keyword, f)


if __name__ == "__main__":
    unittest.main()
