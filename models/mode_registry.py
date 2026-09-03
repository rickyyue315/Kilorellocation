from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set


@dataclass(frozen=True)
class ModeDef:
    code: str
    name: str
    description: str
    attr_name: str
    families: FrozenSet[str] = frozenset()
    cross_om_grouping: bool = False
    cross_om_matching: bool = False
    source_filter: bool = True
    strategy_key: Optional[str] = None
    receive_site_limit: bool = False
    extra_ui_options: FrozenSet[str] = frozenset()
    required_columns: FrozenSet[str] = frozenset()
    source_method: Optional[str] = None
    dest_method: Optional[str] = None


MODE_DEFS: List[ModeDef] = [
    ModeDef("A", "保守轉貨", "轉出後保留安全庫存，單件自動上調至2件",
            attr_name="mode_a", source_filter=False),
    ModeDef("A1", "保守轉貨(轉出店舖不餘存貨1件)", "基於保守轉貨規則，避免轉出店剩1件，接收方可+1件",
            attr_name="mode_a1", source_filter=False),
    ModeDef("B", "加強轉貨", "積極處理滯銷品",
            attr_name="mode_b", source_filter=False),
    ModeDef("B2", "附加B(特別模式)", "B模式 + Type=L全轉出 + Mix高銷量保護",
            attr_name="mode_b_special",
            families=frozenset({'b_special'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2a", "附加B2a(特別模式-T遊客鋪不出貨)", "B2 + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b_special_a",
            families=frozenset({'b_special', 'b_tourist_no_source'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2L", "附加B2L(特別模式-Type=L保留2件)", "B2L模式 + Type=L低銷量保留2件 + Mix高銷量保護",
            attr_name="mode_b2l",
            families=frozenset({'b_special', 'b_l_retain'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2La", "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)", "B2L + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b2la",
            families=frozenset({'b_special', 'b_tourist_no_source', 'b_l_retain'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3", "附加B3(跨OM特別模式)", "B2 + 跨OM配對 + Mix高銷量保護",
            attr_name="mode_b3",
            families=frozenset({'b_special', 'b3_family'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3a", "附加B3a(跨OM特別模式-T遊客鋪不出貨)", "B3 + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b3a",
            families=frozenset({'b_special', 'b3_family', 'b_tourist_no_source'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3L", "附加B3L(跨OM特別模式-Type=L保留2件)", "B3L模式 + 跨OM配對 + Type=L低銷量保留2件 + Mix高銷量保護",
            attr_name="mode_b3l",
            families=frozenset({'b_special', 'b3_family', 'b_l_retain'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3La", "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)", "B3L + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b3la",
            families=frozenset({'b_special', 'b3_family', 'b_tourist_no_source', 'b_l_retain'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("C", "重點補0", "補充庫存≤1的店舖",
            attr_name="mode_c", source_filter=False,
            extra_ui_options=frozenset({'c1_ceiling'})),
    ModeDef("C1", "重點補0-只補0/1 (或自選數量)", "僅補total_available≤N（N可自訂），不回落一般缺貨",
            attr_name="mode_c1",
            dest_method='_dests_c1_mode', source_filter=False,
            extra_ui_options=frozenset({'c1_threshold', 'c1_ceiling'})),
    ModeDef("C2", "附加C2(跨OM重點補0)", "C模式 + 跨OM配對",
            attr_name="mode_c2",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='c2_mode',
            extra_ui_options=frozenset({'c1_ceiling'})),
    ModeDef("D", "清貨轉貨", "清理無銷售ND店舖",
            attr_name="mode_d",
            families=frozenset({'d_family'}),
            dest_method='_dests_d_mode', source_filter=False),
    ModeDef("D2", "清貨轉貨(ND限定)", "僅ND清貨轉出，RF不轉出",
            attr_name="mode_d2",
            families=frozenset({'d_family'}),
            dest_method='_dests_d_mode', source_filter=False,
            extra_ui_options=frozenset({'d2_enable_2site_limit'})),
    ModeDef("E1", "強制轉出", "標記商品強制轉出(僅同OM)",
            attr_name="mode_e1",
            source_filter=True, strategy_key='e1_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("E1b", "強制轉出(優先類型接收)", "標記商品強制轉出(僅同OM，接收端優先Type=T/M)",
            attr_name="mode_e1b",
            source_filter=True, strategy_key='e1_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("E2", "強制轉出(跨OM)", "標記商品強制轉出(可跨OM)",
            attr_name="mode_e2",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='e2_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("F", "目標優化", "依Target目標分配",
            attr_name="mode_f",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f_fulfill_small_first'})),
    ModeDef("F2", "F指定模式", "僅Target店舖可接收，集中調貨，可設定HD轉出選項；Windy目標店優先從同OM無Target店提取",
            attr_name="mode_f_target_only",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first'})),
    ModeDef("F3", "目標性補0", "F2 + RF轉出後保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級",
            attr_name="mode_f3",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first'})),
    ModeDef("ND1", "ND同OM轉貨", "ND店舖互轉(同OM)，按銷量排序",
            attr_name="mode_nd1",
            families=frozenset({'nd_transfer'}), source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd_mode', dest_method='_dests_nd_mode'),
    ModeDef("ND2", "ND混合OM轉貨", "ND店舖互轉(跨OM)，Windy只轉Windy",
            attr_name="mode_nd2",
            families=frozenset({'nd_transfer'}),
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd_mode', dest_method='_dests_nd_mode'),
    ModeDef("ND3", "ND限同OM轉貨(補0)", "ND同OM轉貨，轉出保留3件，只補零庫存ND店",
            attr_name="mode_nd3",
            families=frozenset({'nd_transfer'}), source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd3_mode', dest_method='_dests_nd3_mode'),
    ModeDef("ND4", "ND限同OM轉貨(補0及有銷售記錄)", "ND4 同OM補0 + 僅限有銷售記錄Shop接收,轉出保留3件",
            attr_name="mode_nd4",
            families=frozenset({'nd_transfer'}), source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd4_mode', dest_method='_dests_nd4_mode'),
    ModeDef("精簡SKU(限同OM)", "精簡SKU(限同OM)", "精簡SKU同OM轉貨",
            attr_name="mode_simplified_sku_same",
            families=frozenset({'simplified_sku'}), source_filter=True,
            strategy_key='simplified_sku',
            source_method='_sources_simplified_sku', dest_method='_dests_simplified_sku'),
    ModeDef("精簡SKU(跨OM)", "精簡SKU(跨OM)", "精簡SKU跨OM轉貨",
            attr_name="mode_simplified_sku_cross",
            families=frozenset({'simplified_sku'}),
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='simplified_sku',
            source_method='_sources_simplified_sku', dest_method='_dests_simplified_sku'),
    ModeDef("精簡SKU(退D001)", "精簡SKU(退D001)", "精簡SKU全數退回D001",
            attr_name="mode_simplified_sku_return_d001",
            families=frozenset({'simplified_sku'}),
            source_filter=True,
            cross_om_grouping=True,
            cross_om_matching=True,
            strategy_key='simplified_sku_return_d001',
            source_method='_sources_simplified_sku'),
    ModeDef("NST", "New Shop Target調貨",
            "僅Target門市可接收，RF轉出保留≥2件且上限75%庫存，庫存<3不轉出，可設定HD轉出選項及同一SKU轉出店數上限；目標可能未達100%",
            attr_name="mode_nst",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='nst_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first', 'nst_shop_limit'})),
]


def _build_indices() -> Dict[str, ModeDef]:
    by_name = {}
    for d in MODE_DEFS:
        by_name[d.name] = d
    return by_name


REGISTRY: Dict[str, ModeDef] = _build_indices()

_BY_CODE: Dict[str, ModeDef] = {d.code: d for d in MODE_DEFS}
_BY_ATTR: Dict[str, ModeDef] = {d.attr_name: d for d in MODE_DEFS}


def get_mode_def(mode_name: str) -> Optional[ModeDef]:
    return REGISTRY.get(mode_name)


def get_mode_def_by_code(code: str) -> Optional[ModeDef]:
    return _BY_CODE.get(code)


def get_all_mode_names() -> Set[str]:
    return {d.name for d in MODE_DEFS}


def get_mode_families() -> Dict[str, Set[str]]:
    families: Dict[str, Set[str]] = {}
    for d in MODE_DEFS:
        for f in d.families:
            families.setdefault(f, set()).add(d.name)
    return families


def get_ui_options() -> List[str]:
    return [f"{d.code}: {d.name}" for d in MODE_DEFS]


# 側邊欄兩級選擇器的顯示分組（分組與「📖 模式教學」分頁一致）
_DISPLAY_GROUPS: List[tuple] = [
    ("基礎調貨模式（A / A1 / B）", ["A", "A1", "B"]),
    ("B特別模式（B2 / B2a / B2L / B2La）", ["B2", "B2a", "B2L", "B2La"]),
    ("B跨OM特別模式（B3 / B3a / B3L / B3La）", ["B3", "B3a", "B3L", "B3La"]),
    ("重點補0系列（C / C1 / C2）", ["C", "C1", "C2"]),
    ("清貨模式（D / D2）", ["D", "D2"]),
    ("強制轉出系列（E1 / E1b / E2）", ["E1", "E1b", "E2"]),
    ("目標優化系列（F / F2 / F3 / NST）", ["F", "F2", "F3", "NST"]),
    ("ND/SKU專項（ND1~ND4 / 精簡SKU）", ["ND1", "ND2", "ND3", "ND4",
                                            "精簡SKU(限同OM)", "精簡SKU(跨OM)", "精簡SKU(退D001)"]),
]


def get_display_groups() -> List[tuple]:
    """回傳 (組名, [模式code]) 有序清單，8 組恰好覆蓋全部 30 個模式。"""
    return list(_DISPLAY_GROUPS)


# ── 模式選擇器（意圖嚮導）用的輕量元數據 ──────────────────────────
# 與 ModeDef 解耦：純展示層（短標籤／搜尋關鍵字／意圖分組），不影響配對邏輯。
# 新增模式時只需在此補一筆 TAGLINE + KEYWORDS + 歸入一個 INTENT 群組。

MODE_TAGLINES: Dict[str, str] = {
    "A": "保守互調・保Safety",
    "A1": "保守互調・不剩1件",
    "B": "加強清滯銷・可下探",
    "B2": "Type調撥・L全清（同OM）",
    "B2a": "Type調撥・L全清・T不出（同OM）",
    "B2L": "Type調撥・L留2件（同OM）",
    "B2La": "Type調撥・L留2件・T不出（同OM）",
    "B3": "Type調撥・L全清（跨OM）",
    "B3a": "Type調撥・L全清・T不出（跨OM）",
    "B3L": "Type調撥・L留2件（跨OM）",
    "B3La": "Type調撥・L留2件・T不出（跨OM）",
    "C": "重點補低庫存・順帶補缺貨",
    "C1": "只補0/1精準・不補一般缺貨",
    "C2": "重點補低庫存（跨OM）",
    "D": "清ND死貨・RF也可轉",
    "D2": "清ND死貨・RF只接收",
    "E1": "強制清指定貨（同OM）",
    "E1b": "強制清指定貨・T/M優先收（同OM）",
    "E2": "強制清指定貨（跨OM）",
    "F": "按Target分配＋順帶補0",
    "F2": "只補Target店",
    "F3": "只補Target・RF留2件",
    "NST": "新店Target・RF嚴控75%",
    "ND1": "ND互調（同OM）",
    "ND2": "ND互調（跨OM）",
    "ND3": "ND補零庫存・留3件（同OM）",
    "ND4": "ND補零・僅有銷量可收（同OM）",
    "精簡SKU(限同OM)": "SKU超標轉出（同OM）",
    "精簡SKU(跨OM)": "SKU超標轉出（跨OM）",
    "精簡SKU(退D001)": "超標全退D001",
}

MODE_KEYWORDS: Dict[str, List[str]] = {
    "A": ["保守", "安全庫存", "safety", "日常", "互調"],
    "A1": ["保守", "不剩1件", "餘1", "safety", "日常"],
    "B": ["加強", "滯銷", "下探", "積極", "日常"],
    "B2": ["type", "遊客", "混合", "local", "全清", "同om"],
    "B2a": ["type", "遊客不出", "t不出", "全清", "同om"],
    "B2L": ["type", "保留2件", "留2件", "同om"],
    "B2La": ["type", "保留2件", "遊客不出", "同om"],
    "B3": ["type", "跨om", "全清"],
    "B3a": ["type", "跨om", "遊客不出", "全清"],
    "B3L": ["type", "跨om", "保留2件"],
    "B3La": ["type", "跨om", "保留2件", "遊客不出"],
    "C": ["補0", "低庫存", "缺貨", "重點"],
    "C1": ["補0", "精準", "自選門檻", "只補0"],
    "C2": ["補0", "跨om", "重點"],
    "D": ["清貨", "nd", "死貨", "無銷售"],
    "D2": ["清貨", "nd限定", "rf只接收"],
    "E1": ["強制", "all", "標記", "下架", "同om"],
    "E1b": ["強制", "all", "t/m優先", "遊客優先", "同om"],
    "E2": ["強制", "all", "跨om"],
    "F": ["target", "目標", "分配", "補0"],
    "F2": ["target", "指定", "集中", "新店"],
    "F3": ["target", "保留2件", "指定"],
    "NST": ["target", "新店", "new shop", "75%", "嚴控"],
    "ND1": ["nd互轉", "nd", "同om"],
    "ND2": ["nd互轉", "nd", "跨om", "混合om"],
    "ND3": ["nd", "補0", "保留3件", "零庫存"],
    "ND4": ["nd", "補0", "有銷售記錄", "保留3件"],
    "精簡SKU(限同OM)": ["sku", "精簡", "cap", "退d001", "同om"],
    "精簡SKU(跨OM)": ["sku", "精簡", "cap", "跨om", "退d001"],
    "精簡SKU(退D001)": ["sku", "退倉", "d001", "全退"],
}

# 意圖分組（嚮導第一步）：6 意圖＋全部瀏覽，恰好覆蓋 30 模式且無重複
_INTENT_GROUPS: List[tuple] = [
    ("daily", "📦 日常補貨・缺貨互調", ["A", "A1", "B", "C", "C1", "C2"]),
    ("type", "🏷️ Type分類調撥", ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"]),
    ("clear", "🧹 ND清貨", ["D", "D2"]),
    ("forced", "📌 強制轉出", ["E1", "E1b", "E2"]),
    ("target", "🎯 Target指定分配", ["F", "F2", "F3", "NST"]),
    ("nd_sku", "🔄 ND互轉／SKU精簡", ["ND1", "ND2", "ND3", "ND4",
                                      "精簡SKU(限同OM)", "精簡SKU(跨OM)", "精簡SKU(退D001)"]),
]


def get_intent_groups() -> List[tuple]:
    """回傳 (intent_key, 標籤, [模式code])，6 意圖恰好覆蓋全部 30 模式。"""
    return list(_INTENT_GROUPS)


def get_intent_codes(intent_key: str) -> List[str]:
    for key, _label, codes in _INTENT_GROUPS:
        if key == intent_key:
            return list(codes)
    return []


def get_mode_tagline(code: str) -> str:
    """回傳模式短標籤（選擇器顯示用）；未知 code 回傳空字串。"""
    return MODE_TAGLINES.get(code, "")


# 風險等級（與「📖 模式教學」分頁各 JSON 的 risk 欄一致，供選擇器資訊卡使用）
MODE_RISKS: Dict[str, str] = {
    "A": "低", "A1": "低", "B": "中",
    "B2": "中", "B2a": "中", "B2L": "中", "B2La": "中",
    "B3": "中", "B3a": "中", "B3L": "中", "B3La": "中",
    "C": "中", "C1": "低", "C2": "中",
    "D": "中", "D2": "低",
    "E1": "高", "E1b": "高", "E2": "高",
    "F": "中", "F2": "中", "F3": "中", "NST": "中",
    "ND1": "中", "ND2": "中", "ND3": "中", "ND4": "中",
    "精簡SKU(限同OM)": "中", "精簡SKU(跨OM)": "中", "精簡SKU(退D001)": "低",
}

# 特殊欄位需求（選擇器資訊卡提示用；與 display.py / app.py 的欄位檢查一致）
_MODE_NEEDS_TYPE = frozenset({"B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La", "E1b"})
_MODE_NEEDS_ALL = frozenset({"E1", "E1b", "E2"})
_MODE_NEEDS_TARGET = frozenset({"F", "F2", "F3", "NST"})


def get_mode_risk(code: str) -> str:
    """回傳模式風險等級（低/中/高）；未知 code 回傳空字串。"""
    return MODE_RISKS.get(code, "")


def get_mode_needs(code: str) -> List[str]:
    """回傳模式所需的特殊欄位提示，如 ["Type", "Target"]；無特殊需求回傳 []。"""
    needs: List[str] = []
    if code in _MODE_NEEDS_TYPE:
        needs.append("Type")
    if code in _MODE_NEEDS_ALL:
        needs.append("ALL")
    if code in _MODE_NEEDS_TARGET:
        needs.append("Target")
    return needs


def _normalize_query(text: str) -> str:
    return (text or "").strip().lower()


def search_modes(query: str) -> List[str]:
    """依 code／名稱／短標籤／關鍵字做子字串搜尋，回傳符合的 code 清單（保持 MODE_DEFS 順序）。

    空查詢回傳全部 30 個 code。
    """
    q = _normalize_query(query)
    if not q:
        return [d.code for d in MODE_DEFS]
    matched: List[str] = []
    for d in MODE_DEFS:
        haystack = " ".join([
            d.code.lower(),
            d.name.lower(),
            MODE_TAGLINES.get(d.code, "").lower(),
            d.description.lower(),
            " ".join(MODE_KEYWORDS.get(d.code, [])).lower(),
        ])
        if q in haystack.replace(" ", "") or q in haystack:
            matched.append(d.code)
    return matched


def rank_candidates(intent_key: str, answers: Dict[str, str]) -> List[str]:
    """依意圖＋細化答案回傳推薦排序（首位為最推薦）。純函式，可單元測試。

    answers 的 key 按意圖而定（見 ui/mode_picker.py 的問卷定義）；
    未知意圖或缺答案時回傳該意圖的預設順序。
    """
    base = get_intent_codes(intent_key)
    if not base:
        return [d.code for d in MODE_DEFS]
    get = (answers or {}).get

    if intent_key == "daily":
        need = get("daily_need", "")
        if need == "只補0/極低庫存":
            cross = get("daily_cross", "同OM")
            scope = get("daily_c_scope", "補0＋順便補缺貨")
            if cross == "可跨OM":
                return ["C2", "C1", "C"]
            return ["C1", "C"] if scope == "只補0不補缺貨" else ["C", "C1"]
        risk = get("daily_risk", "保守")
        if risk == "加強":
            return ["B", "A", "A1"]
        no_one = get("daily_no_one", False)
        return ["A1", "A", "B"] if no_one else ["A", "A1", "B"]

    if intent_key == "type":
        cross = get("type_range", "同OM") == "可跨OM"
        t_no = get("type_t", "可出貨") == "T不出貨"
        l_keep = get("type_l", "全清") == "留2件"
        if not cross:
            if not t_no and not l_keep:
                top = "B2"
            elif t_no and not l_keep:
                top = "B2a"
            elif not t_no and l_keep:
                top = "B2L"
            else:
                top = "B2La"
            rest = [c for c in ["B2", "B2a", "B2L", "B2La"] if c != top]
        else:
            if not t_no and not l_keep:
                top = "B3"
            elif t_no and not l_keep:
                top = "B3a"
            elif not t_no and l_keep:
                top = "B3L"
            else:
                top = "B3La"
            rest = [c for c in ["B3", "B3a", "B3L", "B3La"] if c != top]
        return [top] + rest

    if intent_key == "clear":
        return ["D2", "D"] if get("clear_rf", "") == "僅ND轉出" else ["D", "D2"]

    if intent_key == "forced":
        if get("forced_range", "僅同OM") == "可跨OM":
            return ["E2", "E1", "E1b"]
        return ["E1b", "E1", "E2"] if get("forced_recv", "") == "優先T/M接收" else ["E1", "E1b", "E2"]

    if intent_key == "target":
        if get("target_scope", "") == "Target＋順帶補0":
            return ["F", "F2", "F3", "NST"]
        rf = get("target_rf", "RF可全轉")
        if rf == "RF保留2件":
            return ["F3", "F2", "NST", "F"]
        if rf == "RF嚴控(留2件＋75%上限)":
            return ["NST", "F3", "F2", "F"]
        return ["F2", "F3", "NST", "F"]

    if intent_key == "nd_sku":
        goal = get("nd_goal", "ND店互調")
        if goal == "SKU精簡／退倉":
            sku = get("sku_range", "限同OM")
            if sku == "全退D001不配對":
                return ["精簡SKU(退D001)", "精簡SKU(限同OM)", "精簡SKU(跨OM)"]
            if sku == "可跨OM":
                return ["精簡SKU(跨OM)", "精簡SKU(限同OM)", "精簡SKU(退D001)"]
            return ["精簡SKU(限同OM)", "精簡SKU(跨OM)", "精簡SKU(退D001)"]
        nd_range = get("nd_range", "同OM互調")
        if nd_range == "跨OM互調":
            return ["ND2", "ND1", "ND3", "ND4"]
        if nd_range == "只補ND零庫存":
            if get("nd_recv", "") == "僅有銷售記錄可收":
                return ["ND4", "ND3", "ND1", "ND2"]
            return ["ND3", "ND4", "ND1", "ND2"]
        return ["ND1", "ND2", "ND3", "ND4"]

    return base


def get_ui_options_for_codes(codes) -> List[str]:
    """依 code 清單產生 "CODE: name" 選項字串（與 get_ui_options 同格式）。"""
    return [f"{_BY_CODE[c].code}: {_BY_CODE[c].name}" for c in codes if c in _BY_CODE]


def get_receive_limit_codes() -> List[str]:
    return [d.code for d in MODE_DEFS if d.receive_site_limit]


def get_extra_ui_flags() -> Dict[str, Set[str]]:
    flags: Dict[str, Set[str]] = {}
    for d in MODE_DEFS:
        for flag in d.extra_ui_options:
            flags.setdefault(flag, set()).add(d.code)
    return flags


def get_cross_om_grouping_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.cross_om_grouping}


def get_cross_om_matching_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.cross_om_matching}


def get_source_filter_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.source_filter}


def get_codes_needing_column(col: str) -> Set[str]:
    return {d.name for d in MODE_DEFS if col in d.required_columns}
