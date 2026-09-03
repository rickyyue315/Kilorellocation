"""
模式選擇器測試 — 意圖分組／搜尋／推薦排序的完整性與決定性
（純函式測試，不依賴 Streamlit；UI 渲染邏輯不進測試）
"""

import unittest

from models.mode_registry import (
    MODE_DEFS,
    MODE_KEYWORDS,
    MODE_TAGLINES,
    get_intent_codes,
    get_intent_groups,
    get_mode_needs,
    get_mode_risk,
    get_mode_tagline,
    rank_candidates,
    search_modes,
)
from ui.mode_picker import _parse_code, _intent_for_code, _rich_label


class TestPickerMetadata(unittest.TestCase):
    def test_taglines_cover_all_modes(self):
        missing = [d.code for d in MODE_DEFS if d.code not in MODE_TAGLINES]
        self.assertEqual(missing, [], f"以下模式缺少短標籤: {missing}")

    def test_keywords_cover_all_modes(self):
        missing = [d.code for d in MODE_DEFS if d.code not in MODE_KEYWORDS]
        self.assertEqual(missing, [], f"以下模式缺少搜尋關鍵字: {missing}")
        for code, kws in MODE_KEYWORDS.items():
            self.assertTrue(kws, f"模式 {code} 的關鍵字為空")

    def test_risk_values_valid(self):
        for d in MODE_DEFS:
            self.assertIn(get_mode_risk(d.code), ("低", "中", "高"), d.code)

    def test_intent_groups_cover_all_modes_exactly_once(self):
        all_codes = [d.code for d in MODE_DEFS]
        grouped = [c for _k, _l, codes in get_intent_groups() for c in codes]
        self.assertEqual(len(get_intent_groups()), 6)
        self.assertEqual(sorted(grouped), sorted(all_codes))
        self.assertEqual(len(grouped), len(set(grouped)), "意圖分組內模式不可重複")

    def test_mode_needs_consistency(self):
        # E 系列需 ALL；F 系列需 Target；B 系列需 Type（含 E1b）
        for code in ("E1", "E1b", "E2"):
            self.assertIn("ALL", get_mode_needs(code), code)
        for code in ("F", "F2", "F3", "NST"):
            self.assertIn("Target", get_mode_needs(code), code)
        for code in ("B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La", "E1b"):
            self.assertIn("Type", get_mode_needs(code), code)
        self.assertEqual(get_mode_needs("A"), [])
        self.assertEqual(get_mode_needs("D"), [])


class TestSearchModes(unittest.TestCase):
    def test_empty_query_returns_all(self):
        self.assertEqual(len(search_modes("")), 30)
        self.assertEqual(len(search_modes("   ")), 30)

    def test_search_by_code(self):
        self.assertIn("F2", search_modes("F2"))
        self.assertIn("B3La", search_modes("b3la"))

    def test_search_by_keyword_target(self):
        for code in ("F", "F2", "F3", "NST"):
            self.assertIn(code, search_modes("Target"), code)

    def test_search_by_keyword_clear(self):
        for code in ("D", "D2"):
            self.assertIn(code, search_modes("清貨"), code)

    def test_search_no_match(self):
        self.assertEqual(search_modes("不存在的關鍵字zzz"), [])


class TestRankCandidates(unittest.TestCase):
    def test_daily_default(self):
        self.assertEqual(rank_candidates("daily", {})[:3], ["A", "A1", "B"])

    def test_daily_no_one_prefers_a1(self):
        ranked = rank_candidates("daily", {"daily_need": "一般缺貨互調",
                                           "daily_risk": "保守", "daily_no_one": True})
        self.assertEqual(ranked[0], "A1")

    def test_daily_aggressive_prefers_b(self):
        ranked = rank_candidates("daily", {"daily_need": "一般缺貨互調", "daily_risk": "加強"})
        self.assertEqual(ranked[0], "B")

    def test_daily_c_scope(self):
        only_zero = rank_candidates("daily", {"daily_need": "只補0/極低庫存",
                                              "daily_cross": "同OM",
                                              "daily_c_scope": "只補0不補缺貨"})
        self.assertEqual(only_zero[0], "C1")
        with_backfill = rank_candidates("daily", {"daily_need": "只補0/極低庫存",
                                                  "daily_cross": "同OM",
                                                  "daily_c_scope": "補0＋順便補缺貨"})
        self.assertEqual(with_backfill[0], "C")
        cross = rank_candidates("daily", {"daily_need": "只補0/極低庫存", "daily_cross": "可跨OM"})
        self.assertEqual(cross[0], "C2")

    def test_type_matrix(self):
        self.assertEqual(rank_candidates(
            "type", {"type_range": "同OM", "type_t": "可出貨", "type_l": "全清"})[0], "B2")
        self.assertEqual(rank_candidates(
            "type", {"type_range": "同OM", "type_t": "T不出貨", "type_l": "全清"})[0], "B2a")
        self.assertEqual(rank_candidates(
            "type", {"type_range": "同OM", "type_t": "可出貨", "type_l": "留2件"})[0], "B2L")
        self.assertEqual(rank_candidates(
            "type", {"type_range": "同OM", "type_t": "T不出貨", "type_l": "留2件"})[0], "B2La")
        self.assertEqual(rank_candidates(
            "type", {"type_range": "可跨OM", "type_t": "T不出貨", "type_l": "留2件"})[0], "B3La")

    def test_clear(self):
        self.assertEqual(rank_candidates("clear", {"clear_rf": "僅ND轉出"})[0], "D2")
        self.assertEqual(rank_candidates("clear", {"clear_rf": "RF也可轉出"})[0], "D")

    def test_forced(self):
        self.assertEqual(rank_candidates("forced", {"forced_range": "僅同OM",
                                                    "forced_recv": "標準接收"})[0], "E1")
        self.assertEqual(rank_candidates("forced", {"forced_range": "僅同OM",
                                                    "forced_recv": "優先T/M接收"})[0], "E1b")
        self.assertEqual(rank_candidates("forced", {"forced_range": "可跨OM"})[0], "E2")

    def test_target(self):
        self.assertEqual(rank_candidates("target", {"target_scope": "Target＋順帶補0"})[0], "F")
        self.assertEqual(rank_candidates("target", {"target_scope": "只補Target店",
                                                    "target_rf": "RF可全轉"})[0], "F2")
        self.assertEqual(rank_candidates("target", {"target_scope": "只補Target店",
                                                    "target_rf": "RF保留2件"})[0], "F3")
        self.assertEqual(rank_candidates("target", {"target_scope": "只補Target店",
                                                    "target_rf": "RF嚴控(留2件＋75%上限)"})[0], "NST")

    def test_nd_sku(self):
        self.assertEqual(rank_candidates("nd_sku", {"nd_goal": "ND店互調",
                                                    "nd_range": "同OM互調"})[0], "ND1")
        self.assertEqual(rank_candidates("nd_sku", {"nd_goal": "ND店互調",
                                                    "nd_range": "跨OM互調"})[0], "ND2")
        self.assertEqual(rank_candidates("nd_sku", {"nd_goal": "ND店互調",
                                                    "nd_range": "只補ND零庫存",
                                                    "nd_recv": "都可接收"})[0], "ND3")
        self.assertEqual(rank_candidates("nd_sku", {"nd_goal": "ND店互調",
                                                    "nd_range": "只補ND零庫存",
                                                    "nd_recv": "僅有銷售記錄可收"})[0], "ND4")
        self.assertEqual(rank_candidates("nd_sku", {"nd_goal": "SKU精簡／退倉",
                                                    "sku_range": "全退D001不配對"})[0],
                         "精簡SKU(退D001)")

    def test_unknown_intent_returns_all(self):
        self.assertEqual(len(rank_candidates("unknown", {})), 30)

    def test_rank_is_deterministic(self):
        answers = {"type_range": "同OM", "type_t": "可出貨", "type_l": "全清"}
        self.assertEqual(rank_candidates("type", answers), rank_candidates("type", answers))


class TestPickerHelpers(unittest.TestCase):
    def test_parse_code(self):
        self.assertEqual(_parse_code("A: 保守轉貨"), "A")
        self.assertEqual(_parse_code("精簡SKU(退D001): 精簡SKU(退D001)"), "精簡SKU(退D001)")
        self.assertEqual(_parse_code("F2"), "F2")
        self.assertIsNone(_parse_code("不存在: xxx"))
        self.assertIsNone(_parse_code(""))
        self.assertIsNone(_parse_code(None))

    def test_intent_for_code(self):
        self.assertEqual(_intent_for_code("A"), "daily")
        self.assertEqual(_intent_for_code("B2a"), "type")
        self.assertEqual(_intent_for_code("D2"), "clear")
        self.assertEqual(_intent_for_code("E1b"), "forced")
        self.assertEqual(_intent_for_code("NST"), "target")
        self.assertEqual(_intent_for_code("ND4"), "nd_sku")
        self.assertEqual(_intent_for_code(None), "daily")
        self.assertEqual(_intent_for_code("不存在"), "daily")

    def test_rich_label_contains_tag_and_needs(self):
        label = _rich_label("F2", top_code="F2")
        self.assertIn("F2", label)
        self.assertIn(get_mode_tagline("F2"), label)
        self.assertIn("⭐首選", label)
        self.assertIn("Target", label)
        plain = _rich_label("A")
        self.assertNotIn("⭐首選", plain)
        self.assertNotIn("〔需", plain)


if __name__ == "__main__":
    unittest.main()
