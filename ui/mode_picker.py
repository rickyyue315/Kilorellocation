"""
轉貨模式選擇器 — 意圖嚮導＋關鍵字搜尋＋資訊卡

設計目標（取代舊版「模式分類 selectbox → 組內 radio」兩級選單）：
1. 意圖優先：先選「調貨需求」（6 種業務意圖），再答 1–2 條跟進問題，
   即得排序後的候選清單（首位標 ⭐首選），無需先理解 B2/B2a/B2L 等技術代碼差異。
2. 搜尋直達：頂部關鍵字搜尋（代碼／名稱／短標籤／關鍵字），如 Target、清貨、跨OM。
3. 資訊即時：候選 radio 以 format_func 顯示「代碼: 名稱 — 短標籤〔需特殊欄位〕」，
   選中後即時顯示資訊卡（短標籤／風險／所需欄位／推薦理由）。
4. 進階保留：「📚 全部模式」沿用舊 8 分組瀏覽，熟悉代碼者肌肉記憶不變。
5. 記憶選擇：候選 radio 按範圍使用獨立 session key，切換意圖／分組後各範圍的
   上次選擇會被記住（舊版切組會重置為組內第一個）。

相容性：
- 回傳 (mode_code, transfer_mode_canonical)，canonical 格式維持 "CODE: name"，
  下游（app.py run_key、MODE_DESCRIPTIONS、MODE_DOCS）無需改動。
- session_state['transfer_mode'] 仍以 canonical 字串鏡像，舊讀取端不受影響；
  候選 radio 的值為純 code（經 format_func 顯示豐富標籤）。
"""

from typing import Dict, List, Optional, Tuple

import streamlit as st

from models.mode import MODE_DESCRIPTIONS, MODE_NAME_MAP
from models.mode_registry import (
    MODE_DEFS,
    get_display_groups,
    get_intent_codes,
    get_intent_groups,
    get_mode_needs,
    get_mode_risk,
    get_mode_tagline,
    rank_candidates,
    search_modes,
)
from ui.mojibake import fix_mojibake_text


_ALL_KEY = "all"
_ALL_LABEL = "📚 全部模式（我已知代碼）"

_RISK_TEXT = {"低": "風險低", "中": "風險中", "高": "風險高"}
_RISK_CLASS = {"低": "low", "中": "medium", "高": "high"}


# ── 工具函式 ──────────────────────────────────────────────────────

def _parse_code(text: str) -> Optional[str]:
    """從 "CODE: name" 或純 code 字串解析出 code；非法回傳 None。"""
    if not text or not isinstance(text, str):
        return None
    code = text.split(":", 1)[0].strip() if ":" in text else text.strip()
    return code if code in MODE_NAME_MAP else None


def _legacy_code() -> Optional[str]:
    """讀取舊版殘留／上輪鏡像的選擇，還原為 code（跨範圍連續性用）。"""
    return _parse_code(st.session_state.get("transfer_mode", ""))


def _intent_for_code(code: Optional[str]) -> str:
    """code 所屬意圖；未知回傳預設 daily。"""
    if code:
        for key, _label, codes in get_intent_groups():
            if code in codes:
                return key
    return "daily"


def _canonical(code: str) -> str:
    return fix_mojibake_text(f"{code}: {MODE_NAME_MAP[code]}")


def _rich_label(code: str, top_code: Optional[str] = None) -> str:
    """候選 radio 的顯示標籤（值仍為純 code）。"""
    label = f"{code}: {MODE_NAME_MAP[code]}"
    tag = get_mode_tagline(code)
    if tag:
        label += f" — {tag}"
    if top_code and code == top_code:
        label += " ⭐首選"
    needs = get_mode_needs(code)
    if needs:
        label += f"〔需{'、'.join(needs)}〕"
    return label


def _ensure_radio(label: str, candidates: List[str], scope_key: str,
                  top_code: Optional[str] = None, help: Optional[str] = None) -> Optional[str]:
    """建立 code 值 radio，保證 session 值合法（跨範圍記憶＋舊值遷移）。

    不傳 index 參數以避開「index 與既有 widget state 衝突」問題；
    改為在建立前把 session_state[scope_key] 預設為合法值。
    """
    valid = [c for c in candidates if c in MODE_NAME_MAP]
    if not valid:
        st.warning("此範圍目前沒有候選模式，請調整上方問題或搜尋字。")
        return None
    current = st.session_state.get(scope_key)
    if current not in valid:
        # 範圍內記憶：current 仍在 valid 內則保持（用戶剛選的）；首次進入此範圍
        # 則沿用跨範圍舊選擇（legacy），否則落到首選。舊版切組會重置為組內第一個，
        # 此處刻意改為「記住選擇」以減少重選成本。
        legacy = _legacy_code()
        if legacy in valid:
            pick = legacy
        else:
            pick = top_code if top_code in valid else valid[0]
        st.session_state[scope_key] = pick
    st.radio(label, options=valid, key=scope_key,
             format_func=lambda c: _rich_label(c, top_code), help=help)
    selected = st.session_state.get(scope_key)
    return selected if selected in valid else valid[0]


def _render_info_card(code: str, reason: str = "") -> None:
    name = MODE_NAME_MAP.get(code, "")
    tag = get_mode_tagline(code)
    risk = get_mode_risk(code)
    needs = get_mode_needs(code)
    desc = MODE_DESCRIPTIONS.get(f"{code}: {name}", "")
    risk_cls = _RISK_CLASS.get(risk, "medium")
    risk_txt = _RISK_TEXT.get(risk, "")
    if needs:
        needs_line = f"⚠️ 需要 Excel 含「{'、'.join(needs)}」欄，否則此模式無作用"
    else:
        needs_line = "✅ 無需特殊欄位（基本欄位即可）"
    reason_html = f"<div class='mode-pick-reason'>💡 {reason}</div>" if reason else ""
    st.markdown(
        f"<div class='mode-pick-card'>"
        f"<div class='mode-pick-card__head'>"
        f"<span class='mode-pick-card__code'>{code}</span>"
        f"<span class='mode-pick-card__name'>{name}</span>"
        f"<span class='risk-badge risk-badge--{risk_cls}'>{risk_txt}</span>"
        f"</div>"
        f"<div class='mode-pick-card__tag'>{tag}</div>"
        f"<div class='mode-pick-card__desc'>{desc}</div>"
        f"<div class='mode-pick-card__needs'>{needs_line}</div>"
        f"{reason_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── 各意圖的跟進問題（widget key 固定為 mq_*，選項靜態不變） ───────

def _ask_daily() -> Dict:
    answers: Dict = {}
    need = st.radio(
        "補貨情境？",
        ["一般缺貨互調", "只補0/極低庫存"],
        key="mq_daily_need",
        help="一般缺貨互調：A/A1/B；只補極低庫存店：C/C1/C2",
    )
    answers["daily_need"] = need
    if need == "只補0/極低庫存":
        cross = st.radio("配對範圍？", ["同OM", "可跨OM"], key="mq_daily_cross")
        answers["daily_cross"] = cross
        if cross == "同OM":
            scope = st.radio(
                "補貨範圍？",
                ["補0＋順便補缺貨", "只補0不補缺貨"],
                key="mq_daily_c_scope",
                help="順便補缺貨→C；只補0不回落一般缺貨→C1",
            )
            answers["daily_c_scope"] = scope
    else:
        risk = st.radio(
            "轉出積極度？",
            ["保守", "加強"],
            key="mq_daily_risk",
            help="保守：轉出後保Safety（上限20%）；加強：可下探Safety（上限50%）",
        )
        answers["daily_risk"] = risk
        if risk == "保守":
            no_one = st.checkbox(
                "避免轉出後剩1件",
                key="mq_daily_no_one",
                help="勾選→推薦A1（接收方可+1件或源店保留2件）",
            )
            answers["daily_no_one"] = no_one
    return answers


def _ask_type() -> Dict:
    answers: Dict = {}
    answers["type_range"] = st.radio("配對範圍？", ["同OM", "可跨OM"], key="mq_type_range",
                                     help="跨OM→B3系列（含HD/Windy限制）")
    answers["type_t"] = st.radio("遊客鋪(T)可否出貨？", ["可出貨", "T不出貨"], key="mq_type_t")
    answers["type_l"] = st.radio(
        "Type=L低銷量店？", ["全清", "留2件"], key="mq_type_l",
        help="全清：銷量≤2全轉出；留2件：保留2件後轉出",
    )
    return answers


def _ask_clear() -> Dict:
    answers: Dict = {}
    answers["clear_rf"] = st.radio(
        "RF店舖是否參與轉出？",
        ["RF也可轉出", "僅ND轉出"],
        key="mq_clear_rf",
        help="RF也可轉出→D；僅ND轉出（RF只接收）→D2",
    )
    return answers


def _ask_forced() -> Dict:
    answers: Dict = {}
    answers["forced_range"] = st.radio("配對範圍？", ["僅同OM", "可跨OM"], key="mq_forced_range",
                                       help="可跨OM→E2")
    if answers["forced_range"] == "僅同OM":
        answers["forced_recv"] = st.radio(
            "接收排序？", ["標準接收", "優先T/M接收"], key="mq_forced_recv",
            help="優先T/M（遊客區/混合型優先）→E1b",
        )
    return answers


def _ask_target() -> Dict:
    answers: Dict = {}
    answers["target_scope"] = st.radio(
        "接收範圍？",
        ["只補Target店", "Target＋順帶補0"],
        key="mq_target_scope",
        help="順帶補0→F；只補Target店→F2/F3/NST",
    )
    if answers["target_scope"] == "只補Target店":
        answers["target_rf"] = st.radio(
            "RF轉出限制？",
            ["RF可全轉", "RF保留2件", "RF嚴控(留2件＋75%上限)"],
            key="mq_target_rf",
            help="保留2件→F3；嚴控（新店專用，目標可能未達100%）→NST",
        )
    return answers


def _ask_nd_sku() -> Dict:
    answers: Dict = {}
    answers["nd_goal"] = st.radio("你的目標？", ["ND店互調", "SKU精簡／退倉"], key="mq_nd_goal")
    if answers["nd_goal"] == "SKU精簡／退倉":
        answers["sku_range"] = st.radio(
            "退倉範圍？", ["限同OM", "可跨OM", "全退D001不配對"], key="mq_sku_range",
            help="全退D001不配對→精簡SKU(退D001)",
        )
    else:
        answers["nd_range"] = st.radio(
            "ND配對範圍？", ["同OM互調", "跨OM互調", "只補ND零庫存"], key="mq_nd_range",
        )
        if answers["nd_range"] == "只補ND零庫存":
            answers["nd_recv"] = st.radio(
                "哪些ND可接收？", ["都可接收", "僅有銷售記錄可收"], key="mq_nd_recv",
                help="僅有銷售記錄→ND4；都可→ND3",
            )
    return answers


_ASKERS = {
    "daily": _ask_daily,
    "type": _ask_type,
    "clear": _ask_clear,
    "forced": _ask_forced,
    "target": _ask_target,
    "nd_sku": _ask_nd_sku,
}


def _recommend_reason(intent_key: str, answers: Dict, top: str) -> str:
    bits: List[str] = []
    get = answers.get
    if intent_key == "daily":
        if get("daily_need") == "只補0/極低庫存":
            bits = [get("daily_need", ""), get("daily_cross", "同OM")]
            if get("daily_c_scope"):
                bits.append(get("daily_c_scope"))
        else:
            bits = ["一般缺貨互調", get("daily_risk", "保守")]
            if get("daily_no_one"):
                bits.append("不剩1件")
    elif intent_key == "type":
        bits = [get("type_range", "同OM"), get("type_t", "可出貨"), f"L{get('type_l', '全清')}"]
    elif intent_key == "clear":
        bits = [get("clear_rf", "")]
    elif intent_key == "forced":
        bits = [get("forced_range", "僅同OM")]
        if get("forced_recv"):
            bits.append(get("forced_recv"))
    elif intent_key == "target":
        bits = [get("target_scope", "")]
        if get("target_rf"):
            bits.append(get("target_rf"))
    elif intent_key == "nd_sku":
        bits = [get("nd_goal", "")]
        bits.append(get("sku_range", "") or get("nd_range", ""))
        if get("nd_recv"):
            bits.append(get("nd_recv"))
    return f"符合「{'・'.join(b for b in bits if b)}」→ 首選 {top}" if bits else f"首選 {top}"


# ── 主入口 ────────────────────────────────────────────────────────

def render_mode_picker() -> Tuple[str, str]:
    """渲染新版模式選擇器，回傳 (mode_code, transfer_mode_canonical)。"""
    # 0. 搜尋框（有輸入時優先，覆蓋意圖嚮導）
    st.text_input(
        "🔍 搜尋模式",
        key="mode_search",
        placeholder="輸入代碼或關鍵字，如：Target、清貨、ND、跨OM…",
        help="按代碼、名稱、短標籤、關鍵字篩選全部 30 個模式；清空則回到需求嚮導",
    )
    query = (st.session_state.get("mode_search") or "").strip()

    if query:
        candidates = search_modes(query)
        st.caption(f"🔍 找到 {len(candidates)} 個符合「{query}」的模式")
        if not candidates:
            st.warning("找不到符合的模式，換個關鍵字或清除搜尋框回到需求嚮導。")
            fallback = _legacy_code() or "A"
            st.session_state["transfer_mode"] = _canonical(fallback)
            return fallback, st.session_state["transfer_mode"]
        selected = _ensure_radio(
            "選擇轉貨模式", candidates, "mode_pick__search",
            help="搜尋結果依代碼順序排列",
        )
        code = selected or candidates[0]
        _render_info_card(code)
        st.session_state["transfer_mode"] = _canonical(code)
        return code, st.session_state["transfer_mode"]

    # 1. 意圖選擇（預設落在舊選擇所屬意圖，老用戶不迷路）
    intent_options = [(key, label) for key, label, _codes in get_intent_groups()]
    intent_options.append((_ALL_KEY, _ALL_LABEL))
    intent_keys = [k for k, _l in intent_options]
    intent_labels = {k: l for k, l in intent_options}
    current_intent = st.session_state.get("mode_intent")
    if current_intent not in intent_keys:
        st.session_state["mode_intent"] = _intent_for_code(_legacy_code())
    st.selectbox(
        "① 你的調貨需求是？",
        options=intent_keys,
        key="mode_intent",
        format_func=lambda k: intent_labels[k],
        help="先選需求，再答 1–2 條問題即得推薦；已知代碼可選「📚 全部模式」",
    )
    intent_key = st.session_state.get("mode_intent", "daily")

    # 2. 全部模式（進階）：沿用舊 8 分組
    if intent_key == _ALL_KEY:
        display_groups = get_display_groups()
        group_labels = [label for label, _codes in display_groups]
        cur_group = st.session_state.get("mode_group")
        if cur_group not in group_labels:
            legacy = _legacy_code()
            fallback_idx = next(
                (i for i, (_l, codes) in enumerate(display_groups) if legacy in codes),
                0,
            )
            st.session_state["mode_group"] = group_labels[fallback_idx]
        st.selectbox("模式分組", options=group_labels, key="mode_group",
                     help="與「📖 模式教學」分頁的 8 組一致")
        group = st.session_state.get("mode_group", group_labels[0])
        group_codes = next(codes for label, codes in display_groups if label == group)
        selected = _ensure_radio(
            "選擇轉貨模式", group_codes, f"mode_pick__all::{group}",
            help="同一分組的上次選擇會被記住",
        )
        code = selected or group_codes[0]
        _render_info_card(code)
        st.session_state["transfer_mode"] = _canonical(code)
        return code, st.session_state["transfer_mode"]

    # 3. 意圖嚮導：跟進問題 → 排序候選 → radio
    asker = _ASKERS.get(intent_key)
    answers = asker() if asker else {}
    candidates = rank_candidates(intent_key, answers)
    # 保險：候選必須非空且合法，否則退回該意圖全集
    candidates = [c for c in candidates if c in MODE_NAME_MAP] or get_intent_codes(intent_key)
    top = candidates[0]
    st.markdown(f"**② 選擇模式**（{len(candidates)} 個候選）")
    selected = _ensure_radio(
        "選擇轉貨模式", candidates, f"mode_pick__{intent_key}", top_code=top,
        help="⭐為依上方答案推薦的首選；仍可自由改選同列其他模式",
    )
    code = selected or top
    _render_info_card(code, _recommend_reason(intent_key, answers, top))
    st.session_state["transfer_mode"] = _canonical(code)
    return code, st.session_state["transfer_mode"]
