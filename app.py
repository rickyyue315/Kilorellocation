"""
åº«å­˜調貨建議ç³»çµ± v2.4.0 - Streamlitæ‡‰ç”¨ç¨‹åº
æ”¯æŒåä¸€模式ç³»çµ±ï¼šA(ä¿å®ˆ轉貨)/B(åŠ å¼·轉貨)/B2(é™„åŠ Bç‰¹åˆ¥模式)/B3(é™„åŠ Bè·¨OMç‰¹åˆ¥模式)/C(é‡é»žè£œ0)/C2(é™„åŠ Cè·¨OMé‡é»žè£œ0)/D(æ¸…貨轉貨)/E1(å¼·åˆ¶轉å‡º)/E2(å¼·åˆ¶轉å‡ºè·¨OM)/F(ç›®æ¨™å„ªåŒ–)
æ–°å¢žï¼šé è¨­åº—èˆ–è³‡æ–™ï¼ˆOMã€Typeç­‰ï¼‰ï¼Œç•¶ç”¨æˆ¶ä¸Šå‚³çš„Excelç¼ºå°‘é€™äº›è³‡æ–™æ™‚è‡ªå‹•å¡«å……
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
import logging
from io import BytesIO
import time

# å°Žå…¥è‡ªå®šç¾©æ¨¡çµ„
from data_processor import DataProcessor
from business_logic import TransferLogic
from excel_generator import ExcelGenerator

# 資¨­ç½®æ—¥èªŒ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. é é¢é…ç½®
st.set_page_config(
    page_title="åº«å­˜調貨建議ç³»çµ± v2.4.0",
    page_icon="ðŸ“¦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# é…è‰²æ–¹æ¡ˆï¼ˆæ·ºè‰²模式ï¼‰
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

# æ‡‰ç”¨è‡ªå®šç¾©CSSæ¨£å¼
st.markdown(f"""
<style>
    /* å…¨å±€æ¨£å¼ */
    .stApp {{
        background-color: {theme['bg_primary']};
        color: {theme['text_primary']};
    }}
    
    /* å´é‚Šæ¬„ */
    section[data-testid="stSidebar"] {{
        background-color: {theme['bg_secondary']};
        border-right: 1px solid {theme['border']};
    }}
    
    /* æ¨™é¡Œå„ªåŒ– */
    h1, h2, h3 {{
        color: {theme['text_primary']};
        font-weight: 600;
        letter-spacing: -0.5px;
    }}
    
    /* ä¸»æŒ‰éˆ•æ¨£å¼ */
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
    
    /* å¡ç‰‡æ¨£å¼ */
    .info-card {{
        background: {theme['bg_secondary']};
        border: 1px solid {theme['border']};
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 2px 8px {theme['shadow']};
    }}
    
    /* ä¸Šå‚³å€åŸŸ */
    .uploadedFile {{
        background: {theme['bg_secondary']};
        border: 2px dashed {theme['border']};
        border-radius: 8px;
        padding: 20px;
    }}
    
    /* æ•¸æ“šè¡¨æ ¼ */
    .dataframe {{
        background: {theme['bg_secondary']};
        border-radius: 8px;
    }}
    
    /* Metricå¡ç‰‡ */
    div[data-testid="stMetricValue"] {{
        color: {theme['accent']};
        font-weight: 700;
    }}
    
    /* æˆåŠŸ/éŒ¯èª¤è¨Šæ¯ */
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
    
    /* ç¢ºä¿æ‰€æœ‰æ–‡å­—éƒ½æœ‰è¶³å¤ å°æ¯”åº¦ */
    p, span, div, label {{
        color: {theme['text_primary']};
    }}
    
    .stMarkdown {{
        color: {theme['text_primary']};
    }}
    
    /* ç²¾ç°¡é€²åº¦æ¢ */
    .stProgress > div > div {{
        background-color: {theme['accent']};
    }}
    
    /* ä¸‹è¼‰æŒ‰éˆ• */
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

# 2. å´é‚Šæ¬„è¨­è¨ˆ
with st.sidebar:
    st.markdown("### ðŸ“¦ ç³»çµ±è³‡è¨Š")
    st.markdown("""
    <div class="info-card">
    <b>ç‰ˆæœ¬</b>: v2.4.0<br>
    <b>é–‹ç™¼è€…</b>: Ricky
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("ðŸ’¡ æ ¸å¿ƒåŠŸèƒ½", expanded=False):
        st.markdown("""
        **ä¹模式æ™ºèƒ½調貨ç³»çµ±ï¼š**
        - âœ… A模式(ä¿å®ˆ轉貨) / B模式(åŠ å¼·轉貨)
        - âœ… B2模式(é™„åŠ Bç‰¹åˆ¥模式) / B3模式(é™„åŠ Bè·¨OMç‰¹åˆ¥模式)
        - âœ… C模式(é‡é»žè£œ0) / C2模式(é™„åŠ Cè·¨OMé‡é»žè£œ0)
        - âœ… D模式(æ¸…貨轉貨) / E1模式(å¼·åˆ¶轉å‡º) / E2模式(å¼·åˆ¶轉å‡ºè·¨OM) / F模式(ç›®æ¨™å„ªåŒ–)
        
        **æ™ºèƒ½è­˜åˆ¥èˆ‡åŒ¹é…ï¼š**
        - âœ… ND/RFé¡žåž‹æ™ºæ…§è­˜åˆ¥
        - âœ… å„ªå…ˆé †åº調貨åŒ¹é…
        - âœ… RF轉å‡ºé™åˆ¶æŽ§åˆ¶
        - âœ… è·¨OMé…å°æ”¯æ´ï¼ˆB3/C2/E/F模式ï¼‰
        
        **ç‰¹æ®ŠåŠŸèƒ½ï¼š**
        - âœ… D模式ï¼šé¿å…1ä»¶é¤˜貨
        - âœ… E1模式ï¼šæ¨™è¨˜å•†å“å¼·åˆ¶轉å‡ºï¼ˆåƒ…åŒOMï¼‰
        - âœ… E2模式ï¼šæ¨™è¨˜å•†å“å¼·åˆ¶轉å‡ºï¼ˆè·¨OMï¼‰
        - âœ… F模式ï¼šTargetç›®æ¨™æŽ¥æ”¶å„ªå…ˆ
        - âœ… B2模式ï¼šæŽ¥æ”¶ç«¯ä¾éŠå®¢å€/æ··åˆåž‹åº—èˆ–å„ªå…ˆæŽ’åº
        - âœ… B3/C2模式ï¼šè·¨OMé…å°è¦å‰‡ï¼ˆHDä¸èƒ½轉åˆ°HA/HB/HCï¼›Windy轉å‡ºåªèƒ½åˆ°Windyï¼‰
        
        **è‡ªå‹•åŒ–åŠŸèƒ½ï¼š**
        - âœ… é è¨­åº—èˆ–è³‡æ–™è‡ªå‹•å¡«å……ï¼ˆOMã€Typeï¼‰
        - âœ… çµ±è¨ˆåˆ†æžå’Œåœ–è¡¨
        - âœ… Excelæ ¼å¼åŒ¯å‡º
        """)
    
    st.markdown("---")
    
    with st.expander("ðŸŽ¯ æ“ä½œæŒ‡å¼•", expanded=False):
        st.markdown("""
        **å®Œæ•´æ“ä½œæµç¨‹ï¼š**
        
        1. **ä¸Šå‚³ Excel æ–‡ä»¶**
           - é»žæ“Šç€è¦½æ–‡ä»¶æˆ–æ‹–æ”¾æ–‡ä»¶åˆ°ä¸Šå‚³å€åŸŸ
           - ç¢ºä¿åŒ…å«æ‰€æœ‰å¿…éœ€æ¬„ä½
        
        2. **é¸æ“‡轉貨模式**
           - åœ¨å´é‚Šæ¬„é¸æ“‡é©åˆçš„轉貨模式ï¼ˆA/B/B2/B3/C/C2/D/E/Fï¼‰
           - æŸ¥çœ‹模式èªªæ˜Žäº†è§£å„模式ç‰¹é»ž
        
        3. **å•Ÿå‹•åˆ†æž**
           - é»žæ“Šã€Œç”Ÿæˆ調貨建議ã€æŒ‰éˆ•é–‹å§‹è™•ç†
           - ç³»çµ±æœƒè‡ªå‹•é€²è¡Œæ•¸æ“šé©—è­‰å’Œåˆ†æž
        
        4. **æŸ¥çœ‹çµæžœ**
           - åœ¨ä¸»é é¢æŸ¥çœ‹KPIã€調貨建議å’Œçµ±è¨ˆåœ–è¡¨
           - å±•é–‹è©³ç´°çµ±è¨ˆäº†è§£æ›´å¤šä¿¡æ¯
        
        5. **ä¸‹è¼‰å ±å‘Š**
           - é»žæ“Šä¸‹è¼‰æŒ‰éˆ•ç²å– Excel å ±å‘Š
           - å ±å‘ŠåŒ…å«å®Œæ•´çš„調貨建議å’Œçµ±è¨ˆä¿¡æ¯
        """)
    
    st.markdown("---")
    
    # 模式é¸æ“‡
    st.markdown("### âš™ï¸ 模式é¸æ“‡")
    transfer_mode = st.radio(
        "é¸æ“‡轉貨模式",
        ["A: ä¿å®ˆ轉貨", "B: åŠ å¼·轉貨", "B2: é™„åŠ B(ç‰¹åˆ¥模式)", "B3: é™„åŠ B(è·¨OMç‰¹åˆ¥模式)", 
         "C: é‡é»žè£œ0", "C2: é™„åŠ C(è·¨OMé‡é»žè£œ0)", "D: æ¸…貨轉貨", "E1: å¼·åˆ¶轉å‡º", "E2: å¼·åˆ¶轉å‡º(è·¨OM)", "F: ç›®æ¨™å„ªåŒ–"],
        key='transfer_mode',
        help="é¸æ“‡é©åˆçš„調貨模式"
    )
    
    # ç²¾ç°¡模式èªªæ˜Ž
    mode_descriptions = {
        "A: ä¿å®ˆ轉貨": "轉å‡ºå¾Œä¿ç•™å®‰å…¨åº«å­˜",
        "B: åŠ å¼·轉貨": "ç©æ¥µè™•ç†æ»¯éŠ·å“",
        "B2: é™„åŠ B(ç‰¹åˆ¥模式)": "B模式 + Type=Lå…¨轉å‡º",
        "B3: é™„åŠ B(è·¨OMç‰¹åˆ¥模式)": "B2 + è·¨OMé…å°",
        "C: é‡é»žè£œ0": "è£œå……åº«å­˜â‰¤1çš„åº—幫",
        "C2: é™„åŠ C(è·¨OMé‡é»žè£œ0)": "C模式 + è·¨OMé…å°",
        "D: æ¸…貨轉貨": "æ¸…ç†ç„¡éŠ·å”®NDåº—幫",
        "E1: å¼·åˆ¶轉å‡º": "æ¨™è¨˜å•†å“å¼·åˆ¶轉å‡ºï¼ˆåƒ…åŒOMï¼‰",
        "E2: å¼·åˆ¶轉å‡º(è·¨OM)": "æ¨™è¨˜å•†å“å¼·åˆ¶轉å‡ºï¼ˆå¯è·¨OMï¼‰",
        "F: ç›®æ¨™å„ªåŒ–": "ä¾Targetç›®æ¨™åˆ†é…"
    }
    
    st.caption(mode_descriptions[transfer_mode])
    
    with st.expander("ðŸ“‹ è©³ç´°模式èªªæ˜Ž", expanded=False):
        st.markdown("""
        ### 轉貨模式è©³è§£
        
        **A模式(ä¿å®ˆ轉貨)**
        - 轉å‡ºå¾Œå‰©é¤˜åº«å­˜ä¸ä½Žæ–¼å®‰å…¨åº«å­˜
        - 轉å‡ºé¡žåž‹ç‚ºRFéŽå‰©轉å‡º
        - é©åˆä¿å®ˆåž‹調貨ç­–ç•¥
        
        **B模式(åŠ å¼·轉貨)**
        - 轉å‡ºå¾Œå‰©é¤˜åº«å­˜å¯èƒ½ä½Žæ–¼å®‰å…¨åº«å­˜
        - 轉å‡ºé¡žåž‹ç‚ºRFåŠ å¼·轉å‡º
        - æ›´ç©æ¥µåœ°è™•ç†æ»¯éŠ·å“
        
        **B2模式(é™„åŠ Bç‰¹åˆ¥模式)**
        - NDåº—幫å…¨轉å‡º
        - Type=Låœ¨éŠ·é‡â‰¤2æ™‚å…¨轉å‡º(å«RF)ï¼Œè‹¥éŠ·é‡>2å‰‡å›žåˆ°B模式
        - å…¶é¤˜RFä¾B模式è¦å‰‡
        - æŽ¥æ”¶ç«¯ä¾éŠå®¢å€/æ··åˆåž‹åº—èˆ–å„ªå…ˆç´šæŽ’åº
        - æŽ¥æ”¶ä¸Šé™ç‚ºSafety Stockçš„2å€
        
        **B3模式(é™„åŠ Bè·¨OMç‰¹åˆ¥模式)**
        - åƒç…§B2ï¼Œä½†å…è¨±è·¨OMé…å°
        - HDä¸èƒ½轉åˆ°HA/HB/HC
        - Windy轉å‡ºåªèƒ½åˆ°Windyï¼ŒWindyå¯æŽ¥æ”¶å…¶ä»–OM
        
        **C模式(é‡é»žè£œ0)**
        - ä¸»è¦é‡å°æŽ¥æ”¶åº—幫
        - ç•¶(SaSa Net Stock+Pending Received)â‰¤1æ™‚
        - è£œå……è‡³è©²åº—幫çš„Safetyæˆ–MOQ+1çš„æ•¸é‡(å–æœ€ä½Žå€¼)
        
        **C2模式(é™„åŠ Cè·¨OMé‡é»žè£œ0)**
        - åƒç…§C模式çš„轉å‡º/æŽ¥æ”¶é‚è¼¯
        - å…è¨±è·¨OMé…å°
        - HDä¸èƒ½轉åˆ°HA/HB/HC
        - Windy轉å‡ºåªèƒ½åˆ°Windyï¼ŒWindyå¯æŽ¥æ”¶å…¶ä»–OM
        
        **D模式(æ¸…貨轉貨)**
        - é‡å°NDé¡žåž‹ä¸”ç„¡éŠ·å”®è¨˜éŒ„çš„åº—幫é€²è¡Œæ¸…貨
        - é¿å…1ä»¶é¤˜貨ï¼Œç¢ºä¿轉å‡ºå¾Œå‰©é¤˜åº«å­˜ç‚º0ä»¶æˆ–â‰¥2ä»¶
        - 轉å‡ºé¡žåž‹ç‚ºNDæ¸…貨轉å‡º
        
        **E1模式(å¼·åˆ¶轉å‡º)**
        - é‡å°æ¨™è¨˜ç‚º*ALL*çš„å•†å“è¡Œï¼Œå…¨æ•¸å¼·åˆ¶轉å‡º
        - æŽ¥æ”¶åº—幫ç‚ºRFï¼Œä¸Šé™ç‚ºSafety Stockçš„2å€
        - **åƒ…åŒOMé…å°**ï¼ŒHDä¸èƒ½轉åˆ°HA/HB/HC
        - 轉å‡ºé¡žåž‹ç‚ºE模式å¼·åˆ¶轉å‡º
        
        **E2模式(å¼·åˆ¶轉å‡ºè·¨OM)**
        - é‡å°æ¨™è¨˜ç‚º*ALL*çš„å•†å“è¡Œï¼Œå…¨æ•¸å¼·åˆ¶轉å‡º
        - æŽ¥æ”¶åº—幫ç‚ºRFï¼Œä¸Šé™ç‚ºSafety Stockçš„2å€
        - å„ªå…ˆåŒOMé…å°ï¼Œ**å¯è·¨OM**ï¼ŒHDä¸èƒ½轉åˆ°HA/HB/HC
        - 轉å‡ºé¡žåž‹ç‚ºE模式å¼·åˆ¶轉å‡º
        
        **F模式(ç›®æ¨™å„ªåŒ–)**
        - Targetæ¬„ä½å¡«æ•¸å­—ä½œç‚ºå„ªå…ˆæŽ¥æ”¶ç›®æ¨™
        - å…¶ä»–åº—幫æŒ‰C模式è£œ0éœ€æ±‚è¨ˆ算
        - å…è¨±è·¨OMé…å°ï¼ŒHDä¸èƒ½轉åˆ°HA/HB/HC
        
        ---
        
        ### 轉å‡ºé¡žåž‹åˆ¤æ–·
        
        - **RFéŽå‰©轉å‡º**ï¼š轉å‡ºå¾Œå‰©é¤˜åº«å­˜ä¸æœƒä½Žæ–¼Safety Stock
        - **RFåŠ å¼·轉å‡º**ï¼š轉å‡ºå¾Œå‰©é¤˜åº«å­˜æœƒä½Žæ–¼Safety Stock
        - **NDæ¸…貨轉å‡º**ï¼šD模式ç‰¹æ®Šï¼ŒNDåº—幫ç„¡éŠ·å”®è¨˜éŒ„æ™‚
        - **E模式å¼·åˆ¶轉å‡º**ï¼šE1/E2模式ç‰¹æ®Šï¼Œæ¨™è¨˜å•†å“å¼·åˆ¶轉å‡º
        
        ### æŽ¥æ”¶æ¢ä»¶èªªæ˜Ž
        
        **ä¸€èˆ¬æ¢ä»¶ï¼š**
        - SaSa Net Stock + Pending Received < Safety Stock æ™‚éœ€è¦調æ’¥æŽ¥æ”¶
        
        **ç‰¹æ®Šæ¢ä»¶ï¼š**
        - C/C2模式ï¼šç•¶(SaSa Net Stock+Pending Received)â‰¤1æ™‚ï¼Œè£œå……è‡³Safetyæˆ–MOQ+1(å–æœ€ä½Žå€¼)
        - D模式ï¼šé¿å…1ä»¶é¤˜貨è¦å‰‡
        - E1模式ï¼šæ‰€æœ‰RFåº—幫å¯æŽ¥æ”¶ï¼Œä¸Šé™ç‚ºSafety Stockçš„2å€ï¼ˆåƒ…åŒOMï¼‰
        - E2模式ï¼šæ‰€æœ‰RFåº—幫å¯æŽ¥æ”¶ï¼Œä¸Šé™ç‚ºSafety Stockçš„2å€ï¼ˆå¯è·¨OMï¼‰
        - B2/B3模式ï¼šæŽ¥æ”¶ä¸Šé™ç‚ºSafety Stockçš„2å€ï¼Œä¸¦ç´¯è¨ˆè¿½è¹¤æŽ¥æ”¶é‡
        - æŽ¥æ”¶å„ªå…ˆç´šï¼ˆB2/B3ï¼‰ï¼šéŠå®¢å€åº—èˆ–é«˜éŠ·é‡ â†’ æ··åˆåž‹åº—èˆ–é«˜éŠ·é‡ â†’ éŠå®¢å€åº—èˆ–é«˜Safety â†’ æ··åˆåž‹åº—èˆ–é«˜Safety
        """)
    
    st.markdown("---")
    st.caption(f"æ›´æ–°æ™‚é–“: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 3. é é¢é ­éƒ¨
st.title("ðŸ“¦ åº«å­˜調貨建議ç³»çµ±")
st.caption("v2.4.0 | Intelligent Inventory Reallocation System")
st.markdown("---")

# 4. ä¸»è¦å€å¡Š
# 4.1. è³‡æ–™ä¸Šå‚³å€å¡Š
st.markdown("### ðŸ“‚ è³‡æ–™ä¸Šå‚³")

# æ ¹æ“š模式é¡¯ç¤ºè©³ç´°æ¬„ä½èªªæ˜Ž
if transfer_mode in ["A: ä¿å®ˆ轉貨", "B: åŠ å¼·轉貨", "C: é‡é»žè£œ0", "C2: é™„åŠ C(è·¨OMé‡é»žè£œ0)", "D: æ¸…貨轉貨"]:
    with st.expander("ðŸ“‹ å¿…éœ€æ¬„ä½èªªæ˜Ž", expanded=False):
        st.markdown("""
        **åŸºæœ¬æ¬„ä½ï¼š**
        - Article, Article Description, OM, RP Type, Site
        
        **åº«å­˜æ¬„ä½ï¼š**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **éŠ·é‡æ¬„ä½ï¼š**
        - Last Month Sold Qty, MTD Sold Qty
        """)
elif transfer_mode in ["B2: é™„åŠ B(ç‰¹åˆ¥模式)", "B3: é™„åŠ B(è·¨OMç‰¹åˆ¥模式)"]:
    with st.expander("ðŸ“‹ å¿…éœ€æ¬„ä½èªªæ˜Ž", expanded=False):
        st.markdown("""
        **åŸºæœ¬æ¬„ä½ï¼š**
        - Article, Article Description, OM, RP Type, Site, **Type**
        
        **åº«å­˜æ¬„ä½ï¼š**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **éŠ·é‡æ¬„ä½ï¼š**
        - Last Month Sold Qty, MTD Sold Qty
        
        **âš ï¸ ç‰¹æ®Šè¦æ±‚ï¼š**
        - **Type æ¬„ä½**ï¼šType=L ä¸”éŠ·é‡â‰¤2 çš„åº—幫å°‡è¢«å…¨轉å‡ºï¼ˆå³ä½¿æ˜¯RFï¼‰ï¼›è‹¥éŠ·é‡>2 å‰‡æŒ‰B模式è™•ç†
        - **Type èªªæ˜Ž**ï¼šType=T ç‚ºéŠå®¢å€åº—èˆ–ã€Type=M ç‚ºæ··åˆåž‹åº—èˆ–ï¼›B2/B3æŽ¥æ”¶å„ªå…ˆç´šä»¥æ­¤æŽ’åº
        """)
elif transfer_mode in ["E1: å¼·åˆ¶轉å‡º", "E2: å¼·åˆ¶轉å‡º(è·¨OM)"]:
    with st.expander("ðŸ“‹ å¿…éœ€æ¬„ä½èªªæ˜Ž", expanded=False):
        st.markdown("""
        **åŸºæœ¬æ¬„ä½ï¼š**
        - Article, Article Description, OM, RP Type, Site, **ALL**ï¼ˆæ¨™è¨˜å•†å“ï¼‰
        
        **åº«å­˜æ¬„ä½ï¼š**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **éŠ·é‡æ¬„ä½ï¼š**
        - Last Month Sold Qty, MTD Sold Qty
        
        **âš ï¸ ç‰¹æ®Šè¦æ±‚ï¼š**
        - **ALL æ¬„ä½**ï¼šè«‹åœ¨è¦å¼·åˆ¶轉å‡ºçš„å•†å“è¡Œå¡«å¯«ä»»æ„éžç©ºå€¼ï¼ˆä¾‹å¦‚ï¼š*ã€Yã€ALL ç­‰ï¼‰
        - E1/E2 模式åªæœƒè™•ç†æ¨™è¨˜çš„å•†å“
        - E1 模式åƒ…åŒOMé…å°ï¼ŒE2 模式å¯è·¨OMé…å°
        """)
else:  # F: ç›®æ¨™å„ªåŒ–
    with st.expander("ðŸ“‹ å¿…éœ€æ¬„ä½èªªæ˜Ž", expanded=False):
        st.markdown("""
        **åŸºæœ¬æ¬„ä½ï¼š**
        - Article, Article Description, OM, RP Type, Site, **Target**ï¼ˆç›®æ¨™æŽ¥æ”¶æ•¸é‡ï¼‰
        
        **åº«å­˜æ¬„ä½ï¼š**
        - SaSa Net Stock, Pending Received, Safety Stock, MOQ
        
        **éŠ·é‡æ¬„ä½ï¼š**
        - Last Month Sold Qty, MTD Sold Qty
        
        **âš ï¸ ç‰¹æ®Šè¦æ±‚ï¼š**
        - **Target æ¬„ä½**ï¼šå¡«æ•¸å­—ä»£è¡¨è©²åº—幫çš„å„ªå…ˆæŽ¥æ”¶ç›®æ¨™æ•¸é‡
        - æœªå¡«Targetçš„åº—幫æœƒæŒ‰C模式è£œ0éœ€æ±‚è¨ˆ算
        """)

uploaded_file = st.file_uploader(
    "æ‹–æ”¾æˆ–é»žæ“Šä¸Šå‚³ Excel æ–‡ä»¶",
    type=["xlsx", "xls"],
    help="æ”¯æ´ .xlsx å’Œ .xls æ ¼å¼"
)

if uploaded_file is not None:
    progress_bar = st.progress(0, text="æº–å‚™é–‹å§‹è™•ç†æ–‡ä»¶...")
    try:
        # æ–‡ä»¶ä¸Šå‚³é©—è­‰
        progress_bar.progress(10, text="æ­£åœ¨é©—è­‰æ–‡ä»¶æ ¼å¼...")
        
        # å‰µå»ºè‡¨æ™‚æ–‡ä»¶
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # æ•¸æ“šé è™•ç†
        progress_bar.progress(25, text="æ–‡ä»¶è®€å–æˆåŠŸï¼æ­£åœ¨é€²è¡Œæ•¸æ“šé è™•ç†...")
        processor = DataProcessor()
        
        # é©—è­‰æ–‡ä»¶æ ¼å¼
        file_valid, error_msg = processor.validate_file_format(uploaded_file)
        if not file_valid:
            st.error(f"æ–‡ä»¶æ ¼å¼é©—è­‰å¤±æ•—: {error_msg}")
            os.unlink(tmp_file_path)
            st.stop()
        
        try:
            df, processing_stats = processor.preprocess_data(tmp_file_path)
            progress_bar.progress(60, text="æ•¸æ“šé è™•ç†å®Œæˆï¼")
        except ValueError as e:
            st.error(f"âŒ {str(e)}")
            os.unlink(tmp_file_path)
            st.stop()

        # B2/B3模式ï¼šå¿…é ˆæœ‰Typeæ¬„ä½ï¼ˆä¸åˆ†å¤§å°å¯«ï¼‰
        if transfer_mode in ["B2: é™„åŠ B(ç‰¹åˆ¥模式)", "B3: é™„åŠ B(è·¨OMç‰¹åˆ¥模式)"]:
            original_columns = processing_stats['original_stats'].get('columns', [])
            has_type_column = any(col.upper() == 'TYPE' for col in original_columns)
            if not has_type_column:
                st.error("âŒ B2/B3模式å¿…é ˆåŒ…å«Typeæ¬„ä½ï¼ˆä¸åˆ†å¤§å°å¯«ï¼‰ã€‚è«‹ç¢ºèªExcelæ¬„ä½å¾Œå†ä¸Šå‚³ã€‚")
                os.unlink(tmp_file_path)
                st.stop()
        
        # 清†è‡¨æ™‚æ–‡ä»¶
        os.unlink(tmp_file_path)
        
        st.success("檔案上傳èˆ‡æ•¸æ“šé è™•ç†æˆåŠŸï¼")
        
        # 4.2. 資料查覽模塊
        st.markdown("### 📊 資料查覽")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總行數", processing_stats['processed_stats']['total_rows'])
        with col2:
            st.metric("商品數", df['Article'].nunique())
        with col3:
            st.metric("店鋪數", df['Site'].nunique())
        
        st.markdown("**資料樣本ï¼ˆå‰ 10 è¡Œï¼‰**")
        st.dataframe(df.head(10), use_container_width=True)
        
        # 4.3. åˆ†æžæŒ‰éˆ•å€å¡Š
        st.markdown("---")
        st.markdown("### 🚀 åˆ†æžèˆ‡建議")
        
        st.info(f"當前模式ï¼š**{transfer_mode}**")
        
        if st.button("ðŸŽ¯ ç”Ÿæˆ調貨建議", type="primary", use_container_width=True):
            progress_bar.progress(70, text="æ­£åœ¨åˆ†æžæ•¸æ“šä¸¦ç”Ÿæˆ建議...")
            with st.spinner("æ¼”算æ³•é‹è¡Œä¸­ï¼Œè«‹ç¨å€™..."):
                # 轉æ›模式åç¨±
                if transfer_mode == "A: ä¿å®ˆ轉貨":
                    mode_name = "ä¿å®ˆ轉貨"
                elif transfer_mode == "B: åŠ å¼·轉貨":
                    mode_name = "åŠ å¼·轉貨"
                elif transfer_mode == "B2: é™„åŠ B(ç‰¹åˆ¥模式)":
                    mode_name = "é™„åŠ B(ç‰¹åˆ¥模式)"
                elif transfer_mode == "B3: é™„åŠ B(è·¨OMç‰¹åˆ¥模式)":
                    mode_name = "é™„åŠ B3(è·¨OMç‰¹åˆ¥模式)"
                elif transfer_mode == "C: é‡é»žè£œ0":
                    mode_name = "é‡é»žè£œ0"
                elif transfer_mode == "C2: é™„åŠ C(è·¨OMé‡é»žè£œ0)":
                    mode_name = "é™„åŠ C2(è·¨OMé‡é»žè£œ0)"
                elif transfer_mode == "D: æ¸…貨轉貨":
                    mode_name = "æ¸…貨轉貨"
                elif transfer_mode == "E1: å¼·åˆ¶轉å‡º":
                    mode_name = "å¼·åˆ¶轉å‡º"
                elif transfer_mode == "E2: å¼·åˆ¶轉å‡º(è·¨OM)":
                    mode_name = "å¼·åˆ¶轉å‡º(è·¨OM)"
                else:  # F: ç›®æ¨™å„ªåŒ–
                    mode_name = "ç›®æ¨™å„ªåŒ–"
                
                # å‰µå»ºæ¥­å‹™é‚è¼¯å°è±¡
                transfer_logic = TransferLogic()
                
                # ç”Ÿæˆ調貨建議
                recommendations = transfer_logic.generate_transfer_recommendations(df, mode_name)
                
                # åŸ·è¡Œè³ªé‡æª¢æŸ¥
                quality_passed = transfer_logic.perform_quality_checks(df)
                
                # ç²å–çµ±è¨ˆä¿¡æ¯
                statistics = transfer_logic.get_transfer_statistics()
                
                time.sleep(1)  # æ¨¡æ“¬è€—æ™‚æ“ä½œ
                
            progress_bar.progress(90, text="åˆ†æžå®Œæˆï¼æ­£åœ¨æº–å‚™çµæžœå±•ç¤º...")
            
            if quality_passed:
                st.success("è³ªé‡æª¢æŸ¥é€šéŽï¼")
            else:
                st.error("è³ªé‡æª¢æŸ¥å¤±æ•—ï¼Œè«‹æŸ¥çœ‹éŒ¯èª¤ä¿¡æ¯")
                
                # é¡¯ç¤ºéŒ¯èª¤ä¿¡æ¯
                with st.expander("è³ªé‡æª¢æŸ¥éŒ¯èª¤è©³æƒ…"):
                    for error in transfer_logic.quality_errors:
                        st.error(error)
            
            if recommendations:
                # 4.4. çµæžœå±•ç¤ºå€å¡Š
                st.markdown("---")
                st.markdown("### ðŸ“ˆ åˆ†æžçµæžœ")
                
                # KPI æŒ‡æ¨™å¡
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("調貨建議", f"{statistics.get('total_recommendations', 0):,}")
                col2.metric("調貨ä»¶æ•¸", f"{statistics.get('total_transfer_qty', 0):,}")
                col3.metric("ç”¢å“æ•¸é‡", f"{statistics.get('unique_articles', 0):,}")
                col4.metric("OMæ•¸é‡", f"{statistics.get('unique_oms', 0):,}")
                
                st.markdown("")
                
                # 調貨建議è¡¨æ ¼
                st.markdown("### 📋 調貨建議清單")
                
                # æº–å‚™é¡¯示數æ"š
                display_data = []
                
                # å‰µå»ºä¸€å€‹å­—å…¸ä¾†è·Ÿè¹¤æ¯å€‹åº—幫çš„ç´¯è¨ˆ轉å‡ºé‡
                cumulative_transfers = {}
                
                for rec in recommendations:
                        # ç²å–轉å‡ºåº—幫çš„åŽŸå§‹æ•¸æ“š
                        source_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Transfer Site'])]
                        source_stock = source_data['SaSa Net Stock'].iloc[0] if not source_data.empty else 0
                        source_safety = source_data['Safety Stock'].iloc[0] if not source_data.empty else 0
                        source_moq = source_data['MOQ'].iloc[0] if not source_data.empty else 0
                        
                        # ç²å–æŽ¥æ”¶åº—幫çš„åŽŸå§‹æ•¸æ“š
                        dest_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Receive Site'])]
                        dest_stock = dest_data['SaSa Net Stock'].iloc[0] if not dest_data.empty else 0
                        dest_safety = dest_data['Safety Stock'].iloc[0] if not dest_data.empty else 0
                        dest_moq = dest_data['MOQ'].iloc[0] if not dest_data.empty else 0
                        
                        # 資¨ˆ算æŽ¥æ”¶å¾Œçš„ç¸½貨é‡
                        dest_total_after = dest_stock + rec['Transfer Qty']
                        
                        # å‰µå»ºåº—幫çš„å”¯ä¸€æ¨™è­˜ç¬¦
                        source_key = f"{rec['Article']}_{rec['Transfer Site']}"
                        
                        # å¦‚æžœæ˜¯ç¬¬ä¸€æ¬¡轉å‡ºï¼Œåˆå§‹åŒ–ç´¯è¨ˆ轉å‡ºé‡
                        if source_key not in cumulative_transfers:
                            cumulative_transfers[source_key] = 0
                        
                        # æ›´æ–°ç´¯è¨ˆ轉å‡ºé‡
                        cumulative_transfers[source_key] += rec['Transfer Qty']
                        
                        # 資¨ˆ算ç´¯æ¸›å¾Œçš„åº«å­˜
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
                    
                # å‰µå»ºDataFrameä¸¦é¡¯ç¤º
                rec_df = pd.DataFrame(display_data)
                st.dataframe(rec_df, use_container_width=True)
                
                # çµ±è¨ˆåœ–è¡¨
                with st.expander("ðŸ“Š è©³ç´°çµ±è¨ˆ", expanded=False):
                
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**æŒ‰ç”¢å“çµ±è¨ˆ**")
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
                        
                        st.markdown("**轉å‡ºé¡žåž‹åˆ†ä½ˆ**")
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
                        st.markdown("**æŒ‰ OM çµ±è¨ˆ**")
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
                        
                        st.markdown("**æŽ¥æ”¶é¡žåž‹åˆ†ä½ˆ**")
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
                st.success("âœ… åˆ†æžå®Œæˆï¼")
                
                # ç”ŸæˆExcelæ–‡ä»¶
                with st.spinner("ç”Ÿæˆ Excel æ–‡ä»¶..."):
                    excel_generator = ExcelGenerator()
                    excel_path = excel_generator.generate_excel_file(recommendations, statistics)
                
                # 資®€å–Excelæ–‡ä»¶
                with open(excel_path, "rb") as file:
                    excel_data = file.read()
                
                # 清†æš«å­˜Excelæ–‡ä»¶
                try:
                    os.unlink(excel_path)
                except OSError:
                    pass
                
                st.download_button(
                    label="ðŸ“¥ ä¸‹è¼‰ Excel å ±è¡¨",
                    data=excel_data,
                    file_name=excel_generator.output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                progress_bar.progress(100, text="è™•ç†å®Œç•¢ï¼")
            else:
                st.info("æ ¹æ“š當前è¦å‰‡ï¼Œæ²’æœ‰ç”Ÿæˆä»»ä½•調貨建議ã€‚")
                progress_bar.progress(100, text="è™•ç†å®Œç•¢ï¼")
    
    except Exception as e:
        st.error(f"è™•ç†æ–‡ä»¶æ™‚ç™¼ç”ŸéŒ¯èª¤: {e}")
        if st.checkbox("é¡¯ç¤ºè©³ç´°éŒ¯èª¤è¿½è¹¤"):
            st.exception(e)
        if 'progress_bar' in locals():
            progress_bar.progress(100, text="è™•ç†å¤±æ•—ï¼")
        
        # 清†è‡¨æ™‚æ–‡ä»¶
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

# ç³»çµ±é è…³
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6C757D; padding: 30px 0;">
    <p style="margin: 0; font-size: 12px;">åº«å­˜調貨建議ç³»çµ± v2.4.0</p>
    <p style="margin: 5px 0 0 0; font-size: 11px;">Inventory Reallocation System (2026) | Developed by Ricky Yue</p>
</div>
""", unsafe_allow_html=True)
