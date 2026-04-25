"""
庫存調貨建議系統 v2.9.0 - Streamlit應用程序
支持二十一模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)
新增:預設店舖資料(OM、Type等),當用戶上傳的Excel缺少這些資料時自動填充
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import os
import base64
import unicodedata

try:
    from streamlit.delta_generator import DeltaGenerator
except Exception:
    DeltaGenerator = None

try:
    import ftfy
except Exception:
    ftfy = None

# 導入自定義模組
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator


@st.cache_data(show_spinner=False)
def _cached_preprocess(file_bytes: bytes) -> tuple:
    """
    快取數據預處理結果，相同文件內容只處理一次，
    避免 Streamlit 重新渲染時重複執行高代價的 Excel 解析。
    """
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        processor = DataProcessor()
        df, stats = processor.preprocess_data(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return df, stats

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _fix_mojibake_text(value):
    if not isinstance(value, str) or not value:
        return value
    if ftfy is None:
        return value
    try:
        return ftfy.fix_text(value)
    except Exception:
        return value


def _fix_mojibake_value(value):
    if isinstance(value, str):
        return _fix_mojibake_text(value)
    if isinstance(value, list):
        return [_fix_mojibake_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_fix_mojibake_value(item) for item in value)
    return value


def _patch_streamlit_text_rendering():
    if DeltaGenerator is None or ftfy is None:
        return

    patch_rules = {
        'markdown': {'arg_indexes': [0], 'kw_keys': []},
        'title': {'arg_indexes': [0], 'kw_keys': []},
        'header': {'arg_indexes': [0], 'kw_keys': []},
        'subheader': {'arg_indexes': [0], 'kw_keys': []},
        'text': {'arg_indexes': [0], 'kw_keys': []},
        'caption': {'arg_indexes': [0], 'kw_keys': []},
        'code': {'arg_indexes': [0], 'kw_keys': []},
        'info': {'arg_indexes': [0], 'kw_keys': []},
        'warning': {'arg_indexes': [0], 'kw_keys': []},
        'error': {'arg_indexes': [0], 'kw_keys': []},
        'success': {'arg_indexes': [0], 'kw_keys': []},
        'button': {'arg_indexes': [0], 'kw_keys': []},
        'download_button': {'arg_indexes': [0], 'kw_keys': []},
        'file_uploader': {'arg_indexes': [0], 'kw_keys': []},
        'checkbox': {'arg_indexes': [0], 'kw_keys': []},
        'radio': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'selectbox': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'multiselect': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'tabs': {'arg_indexes': [0], 'kw_keys': []},
        'expander': {'arg_indexes': [0], 'kw_keys': []},
        'metric': {'arg_indexes': [0, 2], 'kw_keys': ['label', 'delta']}
    }

    def make_wrapper(method_name, original, arg_indexes, kw_keys):
        def wrapper(self, *args, **kwargs):
            args = list(args)

            if method_name == 'write':
                args = [_fix_mojibake_value(arg) for arg in args]
            else:
                for index in arg_indexes:
                    if index < len(args):
                        args[index] = _fix_mojibake_value(args[index])

            for key in kw_keys:
                if key in kwargs:
                    kwargs[key] = _fix_mojibake_value(kwargs[key])

            return original(self, *args, **kwargs)

        wrapper._kilo_mojibake_patched = True
        return wrapper

    write_original = getattr(DeltaGenerator, 'write', None)
    if write_original is not None and not getattr(write_original, '_kilo_mojibake_patched', False):
        setattr(DeltaGenerator, 'write', make_wrapper('write', write_original, [], []))

    for method_name, rule in patch_rules.items():
        original = getattr(DeltaGenerator, method_name, None)
        if original is None or getattr(original, '_kilo_mojibake_patched', False):
            continue
        wrapped = make_wrapper(method_name, original, rule['arg_indexes'], rule['kw_keys'])
        setattr(DeltaGenerator, method_name, wrapped)


def _parse_target_for_ui(value):
    """將 Target 欄位轉為可比較數值，支援全形數字與千分位逗號。"""
    if pd.isna(value):
        return float('nan')

    text = str(value).strip()
    if text == "":
        return float('nan')

    text = unicodedata.normalize('NFKC', text).replace(',', '')
    return pd.to_numeric(text, errors='coerce')


def _find_f_mode_nd_target_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """找出 F/F2 模式下 ND 且 Target>0 的店舖資料。"""
    if 'RP Type' not in df.columns or 'Target' not in df.columns:
        return pd.DataFrame()

    target_numeric = df['Target'].map(_parse_target_for_ui)
    nd_mask = df['RP Type'].astype(str).str.strip().str.upper() == 'ND'
    target_mask = pd.Series(target_numeric, index=df.index).fillna(0) > 0
    conflicts = df[nd_mask & target_mask].copy()
    if conflicts.empty:
        return conflicts

    conflicts['Target Numeric'] = target_numeric[conflicts.index]
    return conflicts


# 僅在明確需要修復亂碼時啟用（本機 Windows 環境可設 KILO_FIX_MOJIBAKE=1）
# Zeabur/streamlit.io 等 Linux 容器無需啟用，避免每次渲染的額外 CPU 開銷
if os.getenv("KILO_FIX_MOJIBAKE", "0") == "1":
    _patch_streamlit_text_rendering()

# 1. 頁面配置
st.set_page_config(
    page_title=_fix_mojibake_text("庫存調貨建議系統 v2.8.0"),
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配色方案(淺色模式）
theme = {
    'bg_primary': '#FFFFFF',
    'bg_secondary': '#F8F9FA',
    'text_primary': '#212529',
    'text_secondary': '#6C757D',
    'accent': '#4A90E2',
    'accent_hover': '#357ABD',
    'success': '#28A745',
    'success_bg': '#D4EDDA',
    'success_text': '#155724',
    'info': '#17A2B8',
    'info_bg': '#D1ECF1',
    'info_text': '#0C5460',
    'warning': '#FFC107',
    'warning_bg': '#FFF3CD',
    'warning_text': '#856404',
    'error_bg': '#F8D7DA',
    'error_text': '#721C24',
    'border': '#DEE2E6',
    'shadow': 'rgba(0,0,0,0.05)'
}

# 應用自定義CSS樣式
st.markdown(f"""
<style>
    /* 全局樣式 */
    .stApp {{
        background-color: {theme['bg_primary']};
        color: {theme['text_primary']};
    }}
    
    /* 側邊欄 */
    section[data-testid="stSidebar"] {{
        background-color: {theme['bg_secondary']};
        border-right: 1px solid {theme['border']};
    }}
    
    /* 標題優化 */
    h1, h2, h3 {{
        color: {theme['text_primary']};
        font-weight: 600;
        letter-spacing: -0.5px;
    }}
    
    /* 主按鈕樣式 */
    .stButton > button {{
        background: linear-gradient(135deg, {theme['accent']} 0%, {theme['accent_hover']} 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 12px {theme['shadow']};
        transition: all 0.3s ease;
        width: 100%;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px {theme['shadow']};
    }}
    
    /* 卡片樣式 */
    .info-card {{
        background: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 2px 8px {theme['shadow']};
    }}
    
    /* 上傳區域 */
    .uploadedFile {{
        background: {theme['bg_secondary']};
        border: 2px dashed {theme['border']};
        border-radius: 8px;
        padding: 20px;
    }}
    
    /* 數據表格 */
    .dataframe {{
        background: {theme['bg_secondary']};
        border-radius: 8px;
    }}
    
    /* Metric卡片 */
    div[data-testid="stMetricValue"] {{
        color: {theme['accent']};
        font-weight: 700;
    }}
    
    /* 成功/錯誤訊息 */
    .stSuccess {{
        background-color: {theme['success_bg']} !important;
        color: {theme['success_text']} !important;
        border-left: 4px solid {theme['success']};
        border-radius: 6px;
        padding: 12px 16px;
    }}
    
    .stSuccess svg {{
        color: {theme['success']} !important;
    }}
    
    .stInfo {{
        background-color: {theme['info_bg']} !important;
        color: {theme['info_text']} !important;
        border-left: 4px solid {theme['info']};
        border-radius: 6px;
        padding: 12px 16px;
    }}
    
    .stInfo svg {{
        color: {theme['info']} !important;
    }}
    
    .stWarning {{
        background-color: {theme['warning_bg']} !important;
        color: {theme['warning_text']} !important;
        border-left: 4px solid {theme['warning']};
        border-radius: 6px;
        padding: 12px 16px;
    }}
    
    .stWarning svg {{
        color: {theme['warning']} !important;
    }}
    
    .stError {{
        background-color: {theme['error_bg']} !important;
        color: {theme['error_text']} !important;
        border-left: 4px solid #DC3545;
        border-radius: 6px;
        padding: 12px 16px;
    }}
    
    .stError svg {{
        color: #DC3545 !important;
    }}
    
    /* 確保所有文字都有足夠對比度 */
    p, span, div, label {{
        color: {theme['text_primary']};
    }}
    
    .stMarkdown {{
        color: {theme['text_primary']};
    }}
    
    /* 精簡進度條 */
    .stProgress > div > div {{
        background-color: {theme['accent']};
    }}
    
    /* 下載按鈕 */
    .stDownloadButton > button {{
        background: {theme['success']};
        color: white;
        border-radius: 8px;
        padding: 12px 28px;
        font-weight: 600;
        box-shadow: 0 4px 12px {theme['shadow']};
    }}
</style>
""", unsafe_allow_html=True)

# 2. 側邊欄設計
with st.sidebar:
    st.markdown("### 📦 系統資訊")
    st.markdown("""
    <div class="info-card">
    <b>版本</b>: v2.9.0<br>
    <b>開發者</b>: Ricky
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💡 核心功能", expanded=False):
        st.markdown("""
        **二十一模式智能調貨系統:**
        - ✅ A模式(保守轉貨) / B模式(加強轉貨)
        - ✅ B2模式(附加B特別模式) / B2a模式(B2+T遊客鋪不出貨)
        - ✅ B2L模式(附加B2L:Type=L保留2件) / B2La模式(B2L+T遊客鋪不出貨)
        - ✅ B3模式(附加B跨OM特別模式) / B3a模式(B3+T遊客鋪不出貨)
        - ✅ B3L模式(附加B3L跨OM:Type=L保留2件) / B3La模式(B3L+T遊客鋪不出貨)
        - ✅ C模式(重點補0) / C2模式(附加C跨OM重點補0)
        - ✅ D模式(清貨轉貨) / D2模式(清貨轉貨ND限定)
        - ✅ E1模式(強制轉出) / E1b模式(強制轉出優先類型接收) / E2模式(強制轉出跨OM) / F模式(目標優化) / F2模式(F指定模式)
        - ✅ ND1模式(ND同OM轉貨) / ND2模式(ND混合OM轉貨)
        
        **智能識別與匹配:**
        - ✅ ND/RF類型智慧識別
        - ✅ 優先順序調貨匹配
        - ✅ RF轉出限制控制
        - ✅ 跨OM配對支援(B3/C2/E/F/F2模式）
        
        **特殊功能:**
        - ✅ D模式：避免1件餘貨
        - ✅ E1模式：標記商品強制轉出(僅同OM)
        - ✅ E1b模式：標記商品強制轉出(僅同OM，優先Type=T/M接收)
        - ✅ E2模式：標記商品強制轉出(跨OM)
        - ✅ F模式：Target目標接收優先
        - ✅ F2模式：僅Target店舖可接收，集中優先補貨
        - ✅ B2/B2a模式：接收端依遊客區/混合型店舖優先排序
        - ✅ B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式：Mix店舖若總銷量高於目標店，禁止出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - ✅ B2a/B2La/B3a/B3La模式：T遊客鋪不作為出貨來源
        - ✅ B3/B3a/B3L/B3La/C2模式：跨OM配對規則(HD不能轉到HA/HB/HC；Windy轉出只能到Windy)
        - ✅ 所有模式：後處理避免單筆1件調貨（優先Rebalance，其次合並至高銷量目標店）
        **自動化功能:**
        - ✅ 預設店舖資料自動填充(OM、Type)
        - ✅ 統計分析和圖表
        - ✅ Excel格式匯出
        """)
    
    st.markdown("---")
    
    with st.expander("🎯 操作指引", expanded=False):
        st.markdown("""
        **完整操作流程:**
        
        1. **上傳 Excel 文件**
           - 點擊瀏覽文件或拖放文件到上傳區域
           - 確保包含所有必需欄位
        
        2. **選擇轉貨模式**
              - 在側邊欄選擇適合的轉貨模式（A/B/B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/C/C2/D/D2/E1/E1b/E2/F/F2/ND1/ND2)
           - 查看模式說明了解各模式特點
                  - 若選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2，可設定「同一SKU下單一出貨店舖配對接收店舖」：優先1間 / 最多2間 / 不限
        
        3. **啟動分析**
           - 點擊「生成調貨建議」按鈕開始處理
           - 系統會自動進行數據驗證和分析
        
        4. **查看結果**
           - 在主頁面查看KPI、調貨建議和統計圖表
           - 展開詳細統計了解更多信息
        
        5. **下載報告**
           - 點擊下載按鈕獲取 Excel 報告
           - 報告包含完整的調貨建議和統計信息
        """)
    
    st.markdown("---")
    
    # 模式選擇
    st.markdown("### ⚙️ 模式選擇")
    transfer_mode = st.radio(
        "選擇轉貨模式",
        [
            "A: 保守轉貨", "B: 加強轉貨", "B2: 附加B(特別模式)", "B2a: 附加B2a(特別模式-T遊客鋪不出貨)",
            "B2L: 附加B2L(特別模式-Type=L保留2件)", "B2La: 附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
            "B3: 附加B(跨OM特別模式)", "B3a: 附加B3a(跨OM特別模式-T遊客鋪不出貨)",
            "B3L: 附加B3L(跨OM特別模式-Type=L保留2件)", "B3La: 附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
            "C: 重點補0", "C2: 附加C(跨OM重點補0)", "D: 清貨轉貨", "D2: 清貨轉貨(ND限定)", "E1: 強制轉出", "E1b: 強制轉出(優先類型接收)", "E2: 強制轉出(跨OM)", "F: 目標優化", "F2: F指定模式",
            "ND1: ND同OM轉貨", "ND2: ND混合OM轉貨"
        ],
        key='transfer_mode',
        help="選擇適合的調貨模式"
    )
    transfer_mode = _fix_mojibake_text(transfer_mode)
    mode_code = transfer_mode.split(":", 1)[0].strip() if ":" in transfer_mode else transfer_mode.strip()

    receive_site_limit_mode_codes = ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La", "E1", "E1b", "E2", "ND1", "ND2"]

    b_special_receive_site_limit_option = "最多 2 間"
    b_special_max_receive_sites_per_source = None
    if mode_code in receive_site_limit_mode_codes:
        b_special_receive_site_limit_option = st.radio(
            "出貨店舖配對接收店數限制",
            ["優先 1 間", "最多 2 間", "不限制"],
            index=1,
            key='b_special_receive_site_limit_option',
            help="控制同一SKU下，每個出貨店舖最多可分配到多少個接收店舖（優先1間：盡量只配1間；最多2間；不限制）"
        )
        if b_special_receive_site_limit_option == "優先 1 間":
            b_special_max_receive_sites_per_source = 1
        elif b_special_receive_site_limit_option == "最多 2 間":
            b_special_max_receive_sites_per_source = 2
    
    # 精簡模式說明
    mode_descriptions = {
        "A: 保守轉貨": "轉出後保留安全庫存",
        "B: 加強轉貨": "積極處理滯銷品",
        "B2: 附加B(特別模式)": "B模式 + Type=L全轉出 + Mix高銷量保護",
        "B2a: 附加B2a(特別模式-T遊客鋪不出貨)": "B2 + Type=T遊客鋪不出貨 + Mix高銷量保護",
        "B2L: 附加B2L(特別模式-Type=L保留2件)": "B2L模式 + Type=L低銷量保留2件 + Mix高銷量保護",
        "B2La: 附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)": "B2L + Type=T遊客鋪不出貨 + Mix高銷量保護",
        "B3: 附加B(跨OM特別模式)": "B2 + 跨OM配對 + Mix高銷量保護",
        "B3a: 附加B3a(跨OM特別模式-T遊客鋪不出貨)": "B3 + Type=T遊客鋪不出貨 + Mix高銷量保護",
        "B3L: 附加B3L(跨OM特別模式-Type=L保留2件)": "B3L模式 + 跨OM配對 + Type=L低銷量保留2件 + Mix高銷量保護",
        "B3La: 附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)": "B3L + Type=T遊客鋪不出貨 + Mix高銷量保護",
        "C: 重點補0": "補充庫存≤1的店舖",
        "C2: 附加C(跨OM重點補0)": "C模式 + 跨OM配對",
        "D: 清貨轉貨": "清理無銷售ND店舖",
        "D2: 清貨轉貨(ND限定)": "僅ND清貨轉出，RF不轉出",
        "E1: 強制轉出": "標記商品強制轉出(僅同OM)",
        "E1b: 強制轉出(優先類型接收)": "標記商品強制轉出(僅同OM，接收端優先Type=T/M)",
        "E2: 強制轉出(跨OM)": "標記商品強制轉出(可跨OM)",
        "F: 目標優化": "依Target目標分配",
        "F2: F指定模式": "僅Target店舖可接收，集中調貨",
        "ND1: ND同OM轉貨": "ND店舖互轉(同OM)，按銷量智能排序",
        "ND2: ND混合OM轉貨": "ND店舖互轉(跨OM)，Windy只轉Windy"
    }
    
    st.caption(mode_descriptions[transfer_mode])
    
    with st.expander("📋 詳細模式說明", expanded=False):
        st.markdown("""
        ### 轉貨模式詳解
        
        **A模式(保守轉貨)**
        - 轉出後剩餘庫存不低於安全庫存
        - 轉出類型為RF過剩轉出
        - 適合保守型調貨策略
        
        **B模式(加強轉貨)**
        - 轉出後剩餘庫存可能低於安全庫存
        - 轉出類型為RF加強轉出
        - 更積極地處理滯銷品
        
        **B2模式(附加B特別模式)**
        - ND店舖全轉出
        - Type=L在銷量≤2時全轉出(含RF),若銷量>2則回到B模式
        - 其餘RF依B模式規則
        - Mix店舖若總銷量高於目標店則不可出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - 接收端依遊客區/混合型店舖優先級排序
        - 接收上限為Safety Stock的2倍
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **B2L模式(附加B2L特別模式)**
        - 參照B2模式,差異僅在 Type=L 特例
        - Type=L在銷量≤2時不再全轉出,改為保留2件（可轉出=max(淨庫存-2,0)）
        - 若 Type=L 淨庫存≤2，則不轉出
        - Mix店舖若總銷量高於目標店則不可出貨（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
        
        **B3模式(附加B跨OM特別模式)**
        - 參照B2,但允許跨OM配對
        - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - HD不能轉到HA/HB/HC
        - Windy轉出只能到Windy,Windy可接收其他OM
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **B2a模式(附加B2a特別模式)**
        - 參照B2模式
        - 新增限制：Type=T(遊客鋪)不可出貨
        - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **B3a模式(附加B3a跨OM特別模式)**
        - 參照B3模式
        - 新增限制：Type=T(遊客鋪)不可出貨
        - 同樣套用Mix店舖總銷量保護規則（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **B2La模式(附加B2La特別模式)**
        - 參照B2L模式
        - 新增限制：Type=T(遊客鋪)不可出貨
        - Type=L低銷量維持保留2件規則

        **B3L模式(附加B3L跨OM特別模式)**
        - 參照B3模式,差異僅在 Type=L 特例
        - Type=L在銷量≤2時保留2件（可轉出=max(淨庫存-2,0)）
        - 保留B3跨OM規則（HD限制、Windy限制）

        **B3La模式(附加B3La跨OM特別模式)**
        - 參照B3L模式
        - 新增限制：Type=T(遊客鋪)不可出貨
        
        **C模式(重點補0)**
        - 主要針對接收店舖
        - 當(SaSa Net Stock+Pending Received)≤1時
        - 補充至該店舖的Safety或MOQ+1的數量(取最低值)
        
        **C2模式(附加C跨OM重點補0)**
        - 參照C模式的轉出/接收邏輯
        - 允許跨OM配對
        - HD不能轉到HA/HB/HC
        - Windy轉出只能到Windy,Windy可接收其他OM
        
        **D模式(清貨轉貨)**
        - 針對ND類型且無銷售記錄的店舖進行清貨
        - 避免1件餘貨,確保轉出後剩餘庫存為0件或≥2件
        - 轉出類型為ND清貨轉出
        - RF店舖亦可作為過剩轉出源(沿用A模式規則)
        
        **D2模式(清貨轉貨ND限定)**
        - 按照D模式邏輯,但**僅ND Shop轉出，RF Shop只做接收不做轉出**
        - 僅針對無銷售記錄(Last Month=0且MTD=0)的ND店舖清貨轉出
        - 有銷售記錄的ND店舖不做轉出
        - RF店舖只作為接收方(緊急缺貨/潛在缺貨)
        - 仍限制同一組OM內配對
        - 避免1件餘貨邏輯同D模式
        
        **E1模式(強制轉出)**
        - 針對標記為*ALL*的商品行,全數強制轉出
        - 接收店舖為RF,上限為Safety Stock的2倍
        - **僅同OM配對**,HD不能轉到HA/HB/HC
        - 轉出類型為E模式強制轉出
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **E1b模式(強制轉出優先類型接收)**
        - 使用E1模式轉出邏輯:標記為*ALL*的商品行全數強制轉出
        - **僅同OM配對**,HD不能轉到HA/HB/HC
        - 接收店舖為RF,上限為Safety Stock的2倍
        - 接收優先級參照B2:Type=T(遊客區)優先,其次Type=M(混合型)
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
        
        **E2模式(強制轉出跨OM)**
        - 針對標記為*ALL*的商品行,全數強制轉出
        - 接收店舖為RF,上限為Safety Stock的2倍
        - 優先同OM配對,**可跨OM**,HD不能轉到HA/HB/HC
        - 轉出類型為E模式強制轉出
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
        
        **F模式(目標優化)**
        - Target欄位填數字作為優先接收目標
        - 其他店舖按C模式補0需求計算
        - 允許跨OM配對,HD不能轉到HA/HB/HC

        **F2模式(F指定模式)**
        - Target欄位填數字作為唯一接收目標
        - 僅Target店舖可接收，非Target RF店舖不參與接收
        - 允許跨OM配對,HD不能轉到HA/HB/HC

        **ND1模式(ND同OM轉貨)**
        - 打破「ND不可接收」全局限制，ND店舖可互相調貨
        - **限制同OM**：轉出與接收店舖須屬同一OM組別
        - 轉出排序：兩月銷量=0(Last Month + MTD)優先轉出 → 銷量最低次選 → 最高銷量保護不轉
        - 接收優先級1：RF緊急缺貨(零庫存但有銷售記錄)
        - 接收優先級2：ND潛在缺貨(按兩月銷量降序，高銷量優先接收)
        - 接收上限：2×(Last Month Sold Qty + MTD Sold Qty)
        - 兩月銷量=0的ND店舖不可接收
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限

        **ND2模式(ND混合OM轉貨)**
        - 同ND1模式規則，但允許**跨OM**配對
        - Windy(澳門)轉出只能到Windy店舖
        - HD不能轉到HA/HB/HC
        - 可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
        
        ---
        
        ### 轉出類型判斷
        
        - **RF過剩轉出**:轉出後剩餘庫存不會低於Safety Stock
        - **RF加強轉出**:轉出後剩餘庫存會低於Safety Stock
        - **ND清貨轉出**:D/D2模式特殊，ND店舖無銷售記錄時
        - **E模式強制轉出**:E1/E1b/E2模式特殊，標記商品強制轉出
        
        ### 接收條件說明
        
        **一般條件:**
        - SaSa Net Stock + Pending Received < Safety Stock 時需要調撥接收
        
        **特殊條件:**
        - C/C2模式：當(SaSa Net Stock+Pending Received)≤1時,補充至Safety或MOQ+1(取最低值)
        - D/D2模式：避免1件餘貨規則(D2僅ND清貨轉出，RF不轉出)
        - E1模式：所有RF店舖可接收,上限為Safety Stock的2倍(僅同OM)
        - E1b模式：所有RF店舖可接收,上限為Safety Stock的2倍(僅同OM，優先Type=T/M)
        - E2模式：所有RF店舖可接收,上限為Safety Stock的2倍(可跨OM)
        - B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式：接收上限為Safety Stock的2倍,並累計追蹤接收量
        - ND1/ND2模式：可設定同一SKU下單一出貨店舖配對接收店舖：優先1間 / 最多2間 / 不限
        - 接收優先級(B2/B2a/B2L/B2La/B3/B3a/B3L/B3La):遊客區店舖高銷量 → 混合型店舖高銷量 → 遊客區店舖高Safety → 混合型店舖高Safety
        """)
    
    st.markdown("---")
    st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 3. 頁面頭部
st.title("📦 庫存調貨建議系統")
st.caption("v2.9.0 | Intelligent Inventory Reallocation System")
st.markdown("---")

# 4. 主要區塊
# 4.1. 資料上傳區塊
st.markdown("### 📂 資料上傳")

# 根據模式顯示詳細欄位說明
if mode_code in ["A", "B", "C", "C2", "D", "D2"]:
    with st.expander("📋 必需欄位說明", expanded=False):
        st.markdown("""
        **基本欄位:**
        - Article, Article Description, OM, RP Type, Site
        
        **庫存欄位:**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **銷量欄位:**
        - Last Month Sold Qty, MTD Sold Qty
        """)
elif mode_code in ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"]:
    with st.expander("📋 必需欄位說明", expanded=False):
        st.markdown("""
        **基本欄位:**
        - Article, Article Description, OM, RP Type, Site, **Type**
        
        **庫存欄位:**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **銷量欄位:**
        - Last Month Sold Qty, MTD Sold Qty
        
        **⚠️ 特殊要求:**
        - **Type 欄位**:B2/B2a/B3/B3a 的 Type=L 且銷量≤2 店舖將全轉出(即使是RF)
        - **Type 欄位**:B2L/B2La/B3L/B3La 的 Type=L 且銷量≤2 店舖保留2件後轉出
        - **Type 說明**:Type=T 為遊客區店舖、Type=M 為混合型店舖;B2/B2a/B2L/B2La/B3/B3a/B3L/B3La接收優先級以此排序
        - **Mix 保護規則**:若出貨店舖 Type=M 且總銷量 > 目標店總銷量，該配對會被跳過（總銷量=Last Month Sold Qty+MTD Sold Qty）
        - **B2a/B2La/B3a/B3La 限制**:Type=T(遊客鋪)不可出貨
        """)
elif mode_code in ["E1", "E1b", "E2"]:
    with st.expander("📋 必需欄位說明", expanded=False):
        st.markdown("""
        **基本欄位:**
        - Article, Article Description, OM, RP Type, Site, **ALL**(標記商品), Type
        
        **庫存欄位:**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **銷量欄位:**
        - Last Month Sold Qty, MTD Sold Qty
        
        **⚠️ 特殊要求:**
        - **ALL 欄位**:請在要強制轉出的商品行填寫任意非空值(例如:*、Y、ALL 等)
        - E1/E1b/E2 模式只會處理標記的商品
        - E1/E1b 模式僅同OM配對,E2 模式可跨OM配對
        - E1b 接收優先級參照B2:Type=T(遊客區)優先,其次Type=M(混合型)
        """)
elif mode_code in ["ND1", "ND2"]:
    with st.expander("📋 必需欄位說明", expanded=False):
        st.markdown("""
        **基本欄位:**
        - Article, Article Description, OM, RP Type, Site

        **庫存欄位:**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ

        **銷量欄位:**
        - Last Month Sold Qty, MTD Sold Qty

        **⚠️ 特殊要求:**
        - ND1 模式僅同OM配對；ND2 模式允許跨OM配對
        - ND 店舖在 ND1/ND2 模式可作為接收方，但兩月銷量=0 的 ND 店舖不可接收
        - 同一SKU下可設定單一出貨店舖最多配對接收店舖數：優先1間 / 最多2間 / 不限
        """)
else:  # F / F2
    with st.expander("📋 必需欄位說明", expanded=False):
        st.markdown("""
        **基本欄位:**
        - Article, Article Description, OM, RP Type, Site, **Target**(目標接收數量)
        
        **庫存欄位:**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **銷量欄位:**
        - Last Month Sold Qty, MTD Sold Qty
        
        **⚠️ 特殊要求:**
        - **Target 欄位**:填數字代表該店舖的優先接收目標數量
        - F模式:未填Target的店舖會按C模式補0需求計算
        - F2模式:未填Target的店舖不會接收
        """)

uploaded_file = st.file_uploader(
    "拖放或點擊上傳 Excel 文件",
    type=["xlsx", "xls"],
    help="支援 .xlsx 和 .xls 格式"
)

if uploaded_file is not None:
    progress_bar = st.progress(0, text="準備開始處理文件...")
    try:
        # 文件上傳驗證
        progress_bar.progress(10, text="正在驗證文件格式...")
        
        # 數據預處理
        progress_bar.progress(25, text="文件讀取成功!正在進行數據預處理...")
        processor = DataProcessor()
        
        # 驗證文件格式
        file_valid, error_msg = processor.validate_file_format(uploaded_file)
        if not file_valid:
            st.error(f"文件格式驗證失敗: {error_msg}")
            st.stop()
        
        try:
            # 使用快取函數，相同文件重複分析不需重新解析 Excel
            # 臨時文件的建立與清理由 _cached_preprocess 內部負責
            df, processing_stats = _cached_preprocess(uploaded_file.getvalue())
            progress_bar.progress(60, text="數據預處理完成!")
        except ValueError as e:
            st.error(f"❌ {str(e)}")
            st.stop()

        # B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式：必須有Type欄位(不分大小寫)
        if mode_code in ["B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La"]:
            original_columns = processing_stats['original_stats'].get('columns', [])
            has_type_column = any(col.upper() == 'TYPE' for col in original_columns)
            if not has_type_column:
                st.error("❌ B2/B2a/B2L/B2La/B3/B3a/B3L/B3La模式必須包含Type欄位(不分大小寫)。請確認Excel欄位後再上傳。")
                st.stop()
        
        st.success("檔案上傳與數據預處理成功!")
        
        # 若有無效 RP Type，於界面顯示警告讓使用者知情
        invalid_rp_count = processing_stats['processed_stats'].get('invalid_rp_type_count', 0)
        if invalid_rp_count > 0:
            invalid_rp_vals = processing_stats['processed_stats'].get('invalid_rp_types', [])
            st.warning(
                f"⚠️ 資料品質提示：發現 {invalid_rp_count} 行 RP Type 欄位值不是 ND 或 RF "
                f"（{', '.join(str(v) for v in invalid_rp_vals)}），已自動修正為 RF。請確認原始數據是否正確。"
            )

        # F/F2 模式前置警示：ND + Target>0 不會接收
        if mode_code in ["F", "F2"]:
            f_mode_conflicts = _find_f_mode_nd_target_conflicts(df)
            if not f_mode_conflicts.empty:
                affected_sites = sorted(
                    set(f_mode_conflicts['Site'].astype(str).str.strip().str.upper())
                )
                site_text = "、".join(affected_sites[:8])
                if len(affected_sites) > 8:
                    site_text += f" 等{len(affected_sites)}間店"

                st.warning(
                    f"⚠️ {mode_code}模式提示：偵測到 {len(f_mode_conflicts)} 行資料為 ND 且 Target>0。"
                    f"此店因 ND 規則不會接收。"
                    f"受影響店舖：{site_text}"
                )

                preview_cols = [c for c in ['Article', 'OM', 'Site', 'RP Type', 'Target', 'SaSa Net Stock', 'Pending Received'] if c in f_mode_conflicts.columns]
                with st.expander("檢視 ND + Target>0 明細", expanded=False):
                    st.dataframe(
                        f_mode_conflicts[preview_cols].head(50),
                        use_container_width=True
                    )
        
        # 4.2. 資料查覽模塊
        st.markdown("### 📊 資料查覽")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總行數", processing_stats['processed_stats']['total_rows'])
        with col2:
            st.metric("商品數", df['Article'].nunique())
        with col3:
            st.metric("店鋪數", df['Site'].nunique())
        
        st.markdown("**資料樣本（前 10 行)**")
        st.dataframe(df.head(10), use_container_width=True)
        
        # 4.3. 分析按鈕區塊
        st.markdown("---")
        st.markdown("### 🚀 分析與建議")
        
        st.info(f"當前模式:**{transfer_mode}**")
        
        # 當模式或檔案改變時，清除舊的分析結果
        current_run_key = f"{mode_code}_{b_special_receive_site_limit_option}_{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get('_run_key') != current_run_key:
            for k in ['recommendations', 'statistics', 'quality_passed', 'quality_errors', 'excel_data', 'excel_filename', 'excel_run_key']:
                st.session_state.pop(k, None)
            st.session_state['_run_key'] = current_run_key
        
        if st.button("🎯 生成調貨建議", type="primary", use_container_width=True):
            progress_bar.progress(70, text="正在分析數據並生成建議...")
            with st.spinner("演算法運行中,請稍候..."):
                # 轉換模式名稱
                mode_name_map = {
                    "A": "保守轉貨",
                    "B": "加強轉貨",
                    "B2": "附加B(特別模式)",
                    "B2a": "附加B2a(特別模式-T遊客鋪不出貨)",
                    "B2L": "附加B2L(特別模式-Type=L保留2件)",
                    "B2La": "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
                    "B3": "附加B3(跨OM特別模式)",
                    "B3a": "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
                    "B3L": "附加B3L(跨OM特別模式-Type=L保留2件)",
                    "B3La": "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
                    "C": "重點補0",
                    "C2": "附加C2(跨OM重點補0)",
                    "D": "清貨轉貨",
                    "D2": "清貨轉貨(ND限定)",
                    "E1": "強制轉出",
                    "E1b": "強制轉出(優先類型接收)",
                    "E2": "強制轉出(跨OM)",
                    "F": "目標優化",
                    "F2": "F指定模式",
                    "ND1": "ND同OM轉貨",
                    "ND2": "ND混合OM轉貨"
                }
                mode_name = mode_name_map.get(mode_code, "目標優化")
                
                # 創建業務邏輯對象
                transfer_logic = TransferLogic(
                    b_special_max_receive_sites_per_source=b_special_max_receive_sites_per_source
                )
                
                # 生成調貨建議
                recommendations = transfer_logic.generate_transfer_recommendations(df, mode_name)
                
                # 執行質量檢查（傳入模式名稱，ND1/ND2模式允許ND接收）
                quality_passed = transfer_logic.perform_quality_checks(df, mode_name)
                
                # 獲取統計信息
                statistics = transfer_logic.get_transfer_statistics()
                
                # 將結果存入 session_state，確保重新渲染時結果不消失
                st.session_state['recommendations'] = recommendations
                st.session_state['statistics'] = statistics
                st.session_state['quality_passed'] = quality_passed
                st.session_state['quality_errors'] = transfer_logic.quality_errors
                
            progress_bar.progress(90, text="分析完成!正在準備結果展示...")
        
        # 從 session_state 讀取結果（按鈕觸發後或重新渲染均可顯示）
        recommendations = st.session_state.get('recommendations')
        statistics = st.session_state.get('statistics', {})
        quality_passed = st.session_state.get('quality_passed')
        
        if quality_passed is not None:
            if quality_passed:
                st.success("質量檢查通過!")
            else:
                st.error("質量檢查失敗,請查看錯誤信息")
                
                # 顯示錯誤信息
                with st.expander("質量檢查錯誤詳情"):
                    for error in st.session_state.get('quality_errors', []):
                        st.error(error)
            
        if recommendations:
            # 4.4. 結果展示區塊
            st.markdown("---")
            st.markdown("### 📈 分析結果")
            
            # KPI 指標卡
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("調貨建議", f"{statistics.get('total_recommendations', 0):,}")
            col2.metric("調貨件數", f"{statistics.get('total_transfer_qty', 0):,}")
            col3.metric("產品數量", f"{statistics.get('unique_articles', 0):,}")
            col4.metric("OM數量", f"{statistics.get('unique_oms', 0):,}")
            
            st.markdown("")
            
            # 調貨建議表格
            st.markdown("### 📋 調貨建議清單")
            
            # 預先建立 (Article, Site) → 庫存數據的字典（向量化操作，避免 iterrows 逐行 Python 迴圈）
            _stock_lookup = (
                df[['Article', 'Site', 'SaSa Net Stock', 'Safety Stock', 'MOQ']]
                .set_index(['Article', 'Site'])
                .rename(columns={'SaSa Net Stock': 'stock', 'Safety Stock': 'safety', 'MOQ': 'moq'})
                .to_dict('index')
            )
            
            # 準備顯示數據
            display_data = []
            
            # 創建一個字典來跟蹤每個店幫的累計轉出量
            cumulative_transfers = {}
            
            for rec in recommendations:
                # 透過預建字典查詢，O(1) 取得轉出/接收店幫數據
                src_key = (rec['Article'], rec['Transfer Site'])
                src_info = _stock_lookup.get(src_key, {})
                source_stock = src_info.get('stock', 0)
                source_safety = src_info.get('safety', 0)
                source_moq = src_info.get('moq', 0)
                
                dst_key = (rec['Article'], rec['Receive Site'])
                dst_info = _stock_lookup.get(dst_key, {})
                dest_stock = dst_info.get('stock', 0)
                dest_safety = dst_info.get('safety', 0)
                dest_moq = dst_info.get('moq', 0)
                
                # 計算接收後的總貨量
                dest_total_after = dest_stock + rec['Transfer Qty']
                
                # 創建店幫的唯一標識符
                source_key = f"{rec['Article']}_{rec['Transfer Site']}"
                
                # 如果是第一次轉出,初始化累計轉出量
                if source_key not in cumulative_transfers:
                    cumulative_transfers[source_key] = 0
                
                # 更新累計轉出量
                cumulative_transfers[source_key] += rec['Transfer Qty']
                
                # 計算累減後的庫存
                source_after_transfer_stock = source_stock - cumulative_transfers[source_key]
                
                display_data.append({
                    'Article': rec['Article'],
                    'Product Desc': rec['Product Desc'],
                    'Transfer OM': rec['Transfer OM'],
                    'Transfer Site': rec['Transfer Site'],
                    'Transfer Qty': rec['Transfer Qty'],
                    'Source Original Stock': source_stock,
                    'Source After Transfer Stock': source_after_transfer_stock,
                    'Source Safety Stock': source_safety,
                    'Source MOQ': source_moq,
                    'Receive OM': rec['Receive OM'],
                    'Receive Site': rec['Receive Site'],
                    'Receive Original Stock': dest_stock,
                    'Receive Total After': dest_total_after,
                    'Receive Safety Stock': dest_safety,
                    'Receive MOQ': dest_moq,
                    'Source Type': rec.get('Source Type', ''),
                    'Destination Type': rec.get('Destination Type', '')
                })
            
            # 創建DataFrame並顯示
            rec_df = pd.DataFrame(display_data)
            st.dataframe(rec_df, use_container_width=True)
            
            # 統計圖表
            with st.expander("📊 詳細統計", expanded=False):
            
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**按產品統計**")
                    article_stats = statistics.get('article_stats', {})
                    if article_stats:
                        article_df = pd.DataFrame([
                            {
                                'Article': article,
                                'Total Qty': stats['total_qty'],
                                'Count': stats['count'],
                                'OM Count': stats['om_count']
                            }
                            for article, stats in article_stats.items()
                        ])
                        st.dataframe(article_df, use_container_width=True)
                    
                    st.markdown("**轉出類型分佈**")
                    source_type_stats = statistics.get('source_type_stats', {})
                    if source_type_stats:
                        source_df = pd.DataFrame([
                            {
                                'Source Type': source_type,
                                'Count': stats['count'],
                                'Qty': stats['qty']
                            }
                            for source_type, stats in source_type_stats.items()
                        ])
                        st.dataframe(source_df, use_container_width=True)
                
                with col2:
                    st.markdown("**按 OM 統計**")
                    om_stats = statistics.get('om_stats', {})
                    if om_stats:
                        om_df = pd.DataFrame([
                            {
                                'OM': om,
                                'Transfer Qty': stats.get('transfer_qty', stats.get('total_qty', 0)),
                                'Receive Qty': stats.get('receive_qty', 0),
                                'Count': stats['count'],
                                'Article Count': stats['article_count']
                            }
                            for om, stats in om_stats.items()
                        ])
                        st.dataframe(om_df, use_container_width=True)
                    
                    st.markdown("**接收類型分佈**")
                    dest_type_stats = statistics.get('dest_type_stats', {})
                    if dest_type_stats:
                        dest_df = pd.DataFrame([
                            {
                                'Destination Type': dest_type,
                                'Count': stats['count'],
                                'Qty': stats['qty']
                            }
                            for dest_type, stats in dest_type_stats.items()
                        ])
                        st.dataframe(dest_df, use_container_width=True)
            
            st.markdown("---")
            st.success("✅ 分析完成!")
            
            # 生成Excel文件（BytesIO記憶體模式，無磁碟暫存安全問題）
            # 只在本次分析結果首次展示時生成，避免重渲染/下載按鈕觸發時重算
            if st.session_state.get('excel_run_key') != current_run_key or 'excel_data' not in st.session_state:
                with st.spinner("生成 Excel 文件..."):
                    excel_generator = ExcelGenerator()
                    st.session_state['excel_data'] = excel_generator.generate_excel_file(recommendations, statistics)
                    st.session_state['excel_filename'] = excel_generator.output_filename
                    st.session_state['excel_run_key'] = current_run_key
            
            _excel_bytes = st.session_state.get('excel_data', b'')
            _excel_filename = st.session_state.get('excel_filename', '調貨建議.xlsx')
            _b64 = base64.b64encode(_excel_bytes).decode('utf-8')
            _mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            st.markdown(
                f'<a href="data:{_mime};base64,{_b64}" download="{_excel_filename}" '
                f'style="display:block;padding:0.5em 1em;background:#ff4b4b;color:white;'
                f'text-decoration:none;border-radius:0.3em;text-align:center;'
                f'font-weight:bold;font-size:1rem;">📥 下載 Excel 報表</a>',
                unsafe_allow_html=True
            )
            
            progress_bar.progress(100, text="處理完畢!")
        else:
            st.info("根據當前規則，沒有生成任何調貨建議。")
            progress_bar.progress(100, text="處理完畢!")
    
    except Exception as e:
        st.error(f"處理文件時發生錯誤: {e}")
        if st.checkbox("顯示詳細錯誤追蹤"):
            st.exception(e)
        if 'progress_bar' in locals():
            progress_bar.progress(100, text="處理失敗!")

# 系統頁腳
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6C757D; padding: 30px 0;">
    <p style="margin: 0; font-size: 12px;">庫存調貨建議系統 v2.8.0</p>
    <p style="margin: 5px 0 0 0; font-size: 11px;">Inventory Reallocation System (2026) | Developed by Ricky Yue</p>
</div>
""", unsafe_allow_html=True)
