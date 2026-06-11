# KiLo Reallocation — Streamlit 前端現代化重建計畫

> 目標：將既有「庫存調貨建議系統 v2.24.2」從目前的混合式（部分深色 + 多重內聯樣式）介面，
> 升級為**極簡、留白、玻璃擬態 (glassmorphism) 黑夜模式**的現代化 Dashboard，
> 同時保留所有 27 種調貨模式的既有功能。

---

## 1. 分析總結

### 1.1 目前專案結構（已實測）

| 檔案 | 行數 | 角色 |
|---|---|---|
| `app.py` | 276 | 主入口（st.set_page_config、tabs、上傳/分析流程） |
| `ui/sidebar.py` | 436 | 模式選擇 + 27 模式說明 + 進階選項 |
| `ui/display.py` | 386 | 上傳說明、KPI、調貨表格、優先級分組、統計、下載、AI 摘要 |
| `ui/tutorial.py` | 284 | 27 模式圖例教學（flow diagrams + 表格） |
| `ui/styles.py` | 10 | 載入 `static/styles.css` |
| `ui/mojibake.py` | – | 修正 utf-8 mojibake 文字 |
| `static/styles.css` | 601 | 全域 CSS（含 design tokens、按鈕、metric、tabs、expanders） |
| `.streamlit/config.toml` | 17 | `base="dark"` + 橙色主題 |

### 1.2 既有優點（保留並強化）

- ✅ 已採用 **dark base**，背景 `#0B0F19` 深色，視覺上已接近現代深色風。
- ✅ 有完整 **CSS custom properties（design tokens）**，便於統一管理。
- ✅ 引入 **Inter** 字型，提升可讀性。
- ✅ 已有 `.info-card`、`.mode-section`、`.match-container`、`.scenario-table` 等自訂 class 系統。
- ✅ 按鈕已使用 gradient + hover transform，具備動態感。
- ✅ Expander、Tabs、Alert 均有自訂配色。

### 1.3 目前 UX 痛點與缺點

| # | 問題 | 影響 |
|---|---|---|
| 1 | `app.py` header 與 footer 使用大量 `unsafe_allow_html` 內聯樣式，無法被 CSS 統一覆蓋 | 維護成本高、與 styles.css 色彩不一致（footer 用 `#00d4ff` 與全站 `#F59E0B` 衝突） |
| 2 | 側邊欄 `info-card` 使用 `rgba(255,255,255,0.02)` + 邊框 5% 透明，視覺對比過低 | 系統資訊區塊幾乎「隱形」 |
| 3 | KPI 卡片用「左邊 4px 橘色 border」，但其他資訊卡無一致規範 | 元件之間缺乏視覺韻律 |
| 4 | Tabs 切換沒有 fade/slide 動畫 | 切換感受較生硬 |
| 5 | 模式教學頁 `tutorial.py` 直接寫死 inline-style flow 節點 | 與主站風格略脫節 |
| 6 | 缺少**自動適應**表格高度／橫向滾動優化 | 大型結果表在窄螢幕體驗差 |
| 7 | Radio（模式選擇）標籤字級 14px 偏小，模式代號 (A/B/C…) 與說明層次不清 | 27 個模式快速掃視困難 |
| 8 | 進度條只有 6px 高，缺少狀態文字的「階段性高亮」 | 處理 6 階段 (0→10→25→60→70→90→100) 視覺辨識度低 |
| 9 | 缺少 dark mode toggle（雖已 dark，但無 light 主題切換） | 若需列印或簡報截圖不便 |
| 10 | FileUploader 拖放區雖然有虛線邊，但「瀏覽文件」按鈕仍是原生藍色 | 與全站橘色主題衝突 |

### 1.4 前後對比重點

| 面向 | 改版前 | 改版後 |
|---|---|---|
| 色彩一致性 | 5 種以上散落色碼 | 統一透過 `:root` design tokens 管理 |
| 間距系統 | 隨機 px | 4px 倍數基準（4/8/12/16/24/32/48/64） |
| 卡片風格 | 平面 + 1px 邊框 | 玻璃擬態（半透明 + backdrop-filter + 微光邊框） |
| 互動回饋 | 僅按鈕 hover | 按鈕、卡片、表格 row、tabs 皆有微動畫 |
| 排版層級 | h1~h3 樣式相近 | 明確字級／字重／行高對比 |
| 響應式 | 僅 `use_container_width=True` | 額外 media query 處理 ≤ 768px |
| 程式碼 | 大量 inline style | 全部移入 `static/styles.css` + 語意 class |

### 1.5 主要改善項目

1. **Design Token 重構**：建立 8/16/24/32 間距尺度、4 級字型、6 級陰影、3 級圓角。
2. **玻璃擬態卡片系統**：`.surface-card`、`.kpi-card`、`.info-card` 統一風格。
3. **配色微調**：保留 `#F59E0B` 主色，但把 `#00d4ff` 改為 `#22D3EE` 輔色（cyan），避免與主色撞色。
4. **微動畫系統**：`@keyframes fade-in-up`、`pulse-glow`、`shimmer`（進度條）。
5. **移除 header/footer inline style**：改用純 CSS class（`.app-header`、`.app-footer`）。
6. **響應式優化**：加入 `@media (max-width: 768px)` 區段。
7. **無障礙強化**：focus-visible 樣式、`prefers-reduced-motion` 支援、ARIA 標籤。
8. **模式教學頁同步**：把 `tutorial.py` 中的 inline 樣式收斂為 class（`flow-node` 等）。

---

## 2. 主題配置 — `.streamlit/config.toml`

```toml
[server]
# 雲端部署設定（保留既有）
fileWatcherType = "none"
headless = true
# 允許 CORS（若未來需要內嵌 iframe 預覽）
enableCORS = false
# 跨站點 WebSocket
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false
# 隱藏右上角 hamburger 漢堡按鈕（已透過 sidebar 控制）
# serverAddress = "0.0.0.0"

[theme]
# ── 基礎：黑夜模式 ──
base = "dark"

# ── 主題色（橘金，F59E0B 系列） ──
primaryColor = "#F59E0B"

# ── 背景（玻璃擬態深色階） ──
backgroundColor           = "#0B0F19"   # app 主背景（最暗）
secondaryBackgroundColor  = "#111827"   # 側邊欄 / 卡片底色

# ── 文字色（高對比白） ──
textColor                 = "#F8FAFC"

# ── 字型（Inter / 系統 sans） ──
font = "sans serif"

# ── 額外：可被 st.markdown 內 CSS 覆蓋 ──
# Streamlit 1.38 支援以下實驗性欄位（如不可用可忽略，不影響運作）
[theme.fontSizes]
#   保留預設：tiny 12px / small 14px / body 16px / large 18px / h4 20px / h3 24px / h2 32px / h1 40px

# ── 客戶端錯誤顯示（生產環境關閉） ──
[client]
# toolbarMode = "minimal"        # 收合工具列
# showErrorDetails = false      # 生產隱藏 stack trace
```

> 部署注意：`config.toml` 已隨 git tracked，Zeabur 與 streamlit.app 都會自動讀取。**無須額外建置步驟**。

---

## 3. 自訂 CSS（`static/styles.css` 重寫版）

完整 CSS 約 700 行，採「Design Tokens → Reset → Layout → 元件 → 動畫 → 響應式 → 無障礙」分層組織。
下方為可直接覆蓋的完整檔案結構（保留原檔所有功能，但用現代化變數與 class 取代散落 inline style）：

```css
/* ═══════════════════════════════════════════════════════
   KiLo Reallocation — Modern Minimal Dark UI
   Version: 2026.06 — 取代舊版 i15 Dashboard Palette
   ═══════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── 1. Design Tokens (CSS Custom Properties) ── */
:root {
    /* Color — Surface (3 級) */
    --bg-canvas:        #0B0F19;
    --bg-surface:       #111827;
    --bg-elevated:      #1A2332;
    --bg-overlay:       rgba(17, 24, 39, 0.72);

    /* Color — Border */
    --border-subtle:    rgba(255, 255, 255, 0.06);
    --border-default:   #1E293B;
    --border-strong:    #334155;
    --border-accent:    rgba(245, 158, 11, 0.35);

    /* Color — Text (4 級) */
    --text-primary:     #F8FAFC;
    --text-secondary:   #CBD5E1;
    --text-muted:       #94A3B8;
    --text-disabled:    #64748B;

    /* Color — Brand & Semantic */
    --brand-orange:     #F59E0B;
    --brand-orange-2:   #FBBF24;
    --brand-orange-3:   #D97706;
    --accent-cyan:      #22D3EE;
    --accent-blue:      #60A5FA;
    --accent-violet:    #A78BFA;
    --accent-emerald:   #34D399;
    --accent-rose:      #FB7185;

    /* Semantic */
    --success:          #10B981;
    --success-bg:       rgba(16, 185, 129, 0.10);
    --warning:          #F59E0B;
    --warning-bg:       rgba(245, 158, 11, 0.10);
    --error:            #EF4444;
    --error-bg:         rgba(239, 68, 68, 0.10);
    --info:             #3B82F6;
    --info-bg:          rgba(59, 130, 246, 0.10);

    /* Spacing (4px 倍數) */
    --space-1: 4px;  --space-2: 8px;   --space-3: 12px;
    --space-4: 16px; --space-5: 24px;  --space-6: 32px;
    --space-7: 48px; --space-8: 64px;

    /* Radius */
    --radius-sm: 6px;  --radius-md: 10px;
    --radius-lg: 14px; --radius-xl: 20px;

    /* Shadow (3 級) */
    --shadow-sm:  0 1px 2px rgba(0,0,0,0.20);
    --shadow-md:  0 4px 16px rgba(0,0,0,0.30);
    --shadow-lg:  0 12px 40px rgba(0,0,0,0.45);
    --shadow-glow: 0 0 0 1px var(--border-accent), 0 8px 28px rgba(245,158,11,0.18);

    /* Motion */
    --ease-out:  cubic-bezier(0.16, 1, 0.3, 1);
    --ease-in:   cubic-bezier(0.4, 0, 1, 1);
    --dur-fast:  150ms;
    --dur-base:  250ms;
    --dur-slow:  400ms;
}

/* ── 2. Global Reset ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background-color: var(--bg-canvas) !important;
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 "Segoe UI", "Microsoft JhengHei", "PingFang TC",
                 "Noto Sans TC", sans-serif !important;
    font-feature-settings: "cv11", "ss01", "ss03";
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* 捲動軸（保持精緻） */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-canvas); }
::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 6px;
    border: 2px solid var(--bg-canvas);
}
::-webkit-scrollbar-thumb:hover { background: var(--brand-orange); }

.block-container {
    padding: var(--space-5) var(--space-6) var(--space-6) !important;
    max-width: 96% !important;
}

/* ── 3. Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border-default) !important;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
}
section[data-testid="stSidebar"] .block-container {
    padding: var(--space-5) !important;
}

/* ── 4. Typography Hierarchy ── */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.022em !important;
    line-height: 1.25 !important;
    margin: var(--space-3) 0 !important;
}
h1 { font-size: 2.25rem !important; }
h2 { font-size: 1.7rem !important; border-bottom: 1px solid var(--border-default); padding-bottom: var(--space-2); }
h3 { font-size: 1.35rem !important; }
h4 { font-size: 1.1rem !important; }

p, li { line-height: 1.65; color: var(--text-secondary); }
.stMarkdown p { color: var(--text-secondary) !important; }

/* ── 5. App Header / Footer (取代 inline style) ── */
.app-header {
    display: flex; align-items: center; gap: var(--space-5);
    margin: var(--space-2) 0 var(--space-6) 0;
    padding-bottom: var(--space-4);
    border-bottom: 1px solid var(--border-subtle);
}
.app-header__logo {
    width: 84px; height: 72px; flex-shrink: 0;
    background: var(--bg-elevated);
    border: 2px solid var(--border-accent);
    border-radius: var(--radius-lg);
    display: flex; align-items: center; justify-content: center;
    font-size: 42px;
    box-shadow: var(--shadow-glow);
    transition: transform var(--dur-base) var(--ease-out);
}
.app-header__logo:hover { transform: scale(1.05) rotate(-3deg); }
.app-header__title {
    margin: 0 !important;
    font-size: 2.1rem !important; font-weight: 900;
    background: linear-gradient(135deg, var(--brand-orange), var(--brand-orange-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}
.app-header__subtitle {
    margin: 4px 0 0 0 !important;
    color: var(--text-muted);
    font-size: 0.95rem; font-weight: 500;
    letter-spacing: 0.5px;
}

.app-footer {
    text-align: center;
    color: var(--text-muted);
    padding: var(--space-6) 0 var(--space-4) 0;
    border-top: 1px solid var(--border-subtle);
    margin-top: var(--space-7);
    font-size: 13px;
}
.app-footer strong { color: var(--accent-cyan); font-weight: 700; }

/* ── 6. Card Surfaces (玻璃擬態) ── */
.surface-card,
.info-card,
.mode-section {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: var(--space-4) var(--space-5);
    margin: var(--space-3) 0;
    box-shadow: var(--shadow-md);
    transition: border-color var(--dur-base) var(--ease-out),
                transform var(--dur-base) var(--ease-out),
                box-shadow var(--dur-base) var(--ease-out);
    backdrop-filter: blur(8px);
}
.surface-card:hover,
.info-card:hover,
.mode-section:hover {
    border-color: var(--border-accent);
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg), 0 0 0 1px var(--border-accent);
}

/* ── 7. KPI / Metric ── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-elevated) 100%);
    border: 1px solid var(--border-default);
    border-left: 3px solid var(--brand-orange);
    border-radius: var(--radius-md);
    padding: var(--space-4) var(--space-5) !important;
    box-shadow: var(--shadow-md);
    transition: all var(--dur-base) var(--ease-out);
    position: relative;
    overflow: hidden;
}
div[data-testid="stMetric"]::before {
    content: "";
    position: absolute; top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--brand-orange), transparent);
    opacity: 0.4;
}
div[data-testid="stMetric"]:hover {
    border-color: var(--border-accent);
    transform: translateY(-3px);
    box-shadow: var(--shadow-glow);
}
div[data-testid="stMetricValue"] {
    color: var(--brand-orange) !important;
    font-weight: 800 !important;
    font-size: 1.95rem !important;
    letter-spacing: -0.02em !important;
}
div[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── 8. Buttons (Primary, Secondary, Download) ── */
.stButton > button,
.stDownloadButton > button {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    padding: 12px 28px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    letter-spacing: 0.2px;
    box-shadow: var(--shadow-sm);
    transition: all var(--dur-base) var(--ease-out) !important;
    width: 100%;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--border-accent) !important;
    background: var(--bg-surface) !important;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

/* Primary variant — 橘金漸層 */
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-orange) 0%, var(--brand-orange-3) 100%) !important;
    color: #0B0F19 !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(245, 158, 11, 0.25);
    font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, var(--brand-orange-2) 0%, var(--brand-orange) 100%) !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(245, 158, 11, 0.40);
}

/* ── 9. Radio (模式選擇) ── */
div[data-testid="stRadio"] > label {
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    font-size: 0.95rem !important;
    margin-bottom: var(--space-2) !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 4px !important;
    gap: 2px !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label {
    background: transparent;
    padding: 8px 12px !important;
    border-radius: var(--radius-sm);
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    border: 1px solid transparent;
    transition: all var(--dur-fast) var(--ease-out);
    margin-bottom: 2px !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
    background: rgba(245, 158, 11, 0.06);
    color: var(--brand-orange);
}
div[data-testid="stRadio"] div[role="radiogroup"] label[data-selected="true"] {
    background: rgba(245, 158, 11, 0.12);
    border-color: var(--border-accent);
    color: var(--brand-orange) !important;
    font-weight: 700 !important;
}

/* ── 10. File Uploader ── */
section[data-testid="stFileUploadDropzone"] {
    background: var(--bg-surface) !important;
    border: 2px dashed var(--border-accent) !important;
    border-radius: var(--radius-lg) !important;
    padding: var(--space-6) !important;
    transition: all var(--dur-base) var(--ease-out);
}
section[data-testid="stFileUploadDropzone"]:hover {
    background: var(--bg-canvas) !important;
    border-color: var(--brand-orange) !important;
    box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.08);
}
section[data-testid="stFileUploadDropzone"] button {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-sm) !important;
}
section[data-testid="stFileUploadDropzone"] button:hover {
    background: var(--brand-orange) !important;
    color: var(--bg-canvas) !important;
    border-color: var(--brand-orange) !important;
}

/* ── 11. Tabs ── */
button[data-baseweb="tab"] {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    background: transparent !important;
    border: none !important;
    padding: 14px 24px !important;
    transition: color var(--dur-fast) var(--ease-out);
    border-top-left-radius: var(--radius-sm);
    border-top-right-radius: var(--radius-sm);
}
button[data-baseweb="tab"]:hover { color: var(--text-primary) !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--brand-orange) !important;
    background: rgba(245, 158, 11, 0.04) !important;
}
div[data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, var(--brand-orange), var(--brand-orange-2)) !important;
    height: 3px !important;
    border-radius: 3px 3px 0 0 !important;
}
div[data-testid="stTabs"] {
    border-bottom: 1px solid var(--border-default) !important;
    margin-bottom: var(--space-5);
}

/* ── 12. Expander ── */
div[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm);
    margin-bottom: var(--space-3) !important;
    transition: border-color var(--dur-base) var(--ease-out);
}
div[data-testid="stExpander"]:hover { border-color: var(--border-strong) !important; }
div[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    padding: 12px 18px !important;
}
div[data-testid="stExpander"] summary:hover { color: var(--brand-orange) !important; }
div[data-testid="stExpander"] summary svg { color: var(--text-muted); }

/* ── 13. Alert (Success / Info / Warning / Error) ── */
.stAlert, .stSuccess, .stInfo, .stWarning, .stError {
    border-radius: var(--radius-md) !important;
    padding: 14px 20px !important;
    box-shadow: var(--shadow-sm);
    border: 1px solid transparent !important;
    border-left-width: 4px !important;
    backdrop-filter: blur(6px);
}
.stSuccess { background: var(--success-bg) !important; color: #6EE7B7 !important; border-left-color: var(--success) !important; }
.stInfo    { background: var(--info-bg) !important;    color: #93C5FD !important; border-left-color: var(--info) !important; }
.stWarning { background: var(--warning-bg) !important; color: #FDE68A !important; border-left-color: var(--warning) !important; }
.stError   { background: var(--error-bg) !important;   color: #FCA5A5 !important; border-left-color: var(--error) !important; }
.stSuccess svg { color: var(--success) !important; }
.stInfo svg    { color: var(--info) !important; }
.stWarning svg { color: var(--warning) !important; }
.stError svg   { color: var(--error) !important; }

/* ── 14. DataFrame ── */
.stDataFrame, [data-testid="stDataFrame"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] iframe { background: var(--bg-surface) !important; }

/* ── 15. Progress Bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--brand-orange), var(--brand-orange-2)) !important;
    height: 8px !important;
    border-radius: 4px !important;
    animation: shimmer 1.6s linear infinite;
    background-size: 200% 100%;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ── 16. Number Input / Slider / Checkbox ── */
.stNumberInput input, .stTextInput input {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-primary) !important;
    border-radius: var(--radius-sm) !important;
    transition: border-color var(--dur-fast) var(--ease-out);
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: var(--brand-orange) !important;
    box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.12);
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--brand-orange) !important;
    border: 2px solid var(--bg-canvas) !important;
    box-shadow: 0 0 0 1px var(--brand-orange);
}
.stSlider [data-baseweb="slider"] > div > div {
    background: linear-gradient(90deg, var(--brand-orange), var(--brand-orange-3)) !important;
}

/* ── 17. Code / Pre ── */
code, pre, .stCode {
    font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm) !important;
    color: var(--accent-cyan) !important;
}

/* ── 18. Tutorial / Flow Elements ── */
.flow-container {
    padding: var(--space-5);
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    margin: var(--space-3) 0;
    box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.2);
}
.flow-node {
    padding: 8px 12px;
    background: rgba(15, 30, 61, 0.6);
    border: 2px solid var(--accent-blue);
    border-radius: var(--radius-sm);
    text-align: center;
    font-size: 13px;
    color: var(--text-primary);
    transition: transform var(--dur-fast) var(--ease-out);
}
.flow-node:hover { transform: scale(1.04); }
.flow-node--green  { background: rgba(5, 46, 22, 0.6);  border-color: var(--accent-emerald); }
.flow-node--red    { background: rgba(69, 10, 10, 0.6);  border-color: var(--error); }
.flow-node--yellow { background: rgba(61, 29, 6, 0.6);   border-color: var(--brand-orange-2); }
.flow-node--purple { background: rgba(37, 14, 74, 0.6);  border-color: var(--accent-violet); }
.flow-node--gray   { background: rgba(30, 30, 46, 0.6);  border-color: var(--text-muted); }
.flow-node--orange { background: rgba(67, 20, 7, 0.6);   border-color: var(--brand-orange); }
.flow-label {
    font-weight: 600; font-size: 13px;
    color: var(--text-primary);
    border-left: 3px solid var(--brand-orange);
    padding-left: var(--space-3);
    margin: var(--space-3) 0 var(--space-2) 0;
    letter-spacing: 0.3px;
}
.flow-arrow { text-align: center; color: var(--text-muted); font-size: 18px; margin: 4px 0; }
.mode-section { padding: var(--space-5) !important; }
.mode-title {
    font-size: 17px; font-weight: 700; color: var(--text-primary);
    padding-bottom: var(--space-3);
    border-bottom: 1px solid var(--border-default);
    margin: 0 0 var(--space-3) 0;
    display: flex; justify-content: space-between; align-items: center;
}
.mode-scenario { font-size: 14px; line-height: 1.6; color: var(--text-secondary); margin: var(--space-2) 0 var(--space-4) 0; }
.mode-notes {
    font-size: 13.5px; line-height: 1.6;
    color: #FDE68A;
    background: var(--warning-bg);
    border: 1px solid rgba(245, 158, 11, 0.2);
    border-radius: var(--radius-sm);
    padding: var(--space-3) var(--space-4);
    margin: var(--space-3) 0;
}
.mode-divider {
    border: none; border-top: 1px dashed var(--border-default);
    margin: var(--space-5) 0;
}
.risk-badge {
    padding: 2px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 600;
    color: #fff; background: var(--text-muted);
}
.risk-badge--low    { background: var(--success); }
.risk-badge--medium { background: var(--warning); }
.risk-badge--high   { background: var(--error); }

/* ── 19. Match Priority (教學) ── */
.match-container {
    display: flex; flex-wrap: wrap; gap: var(--space-2);
    padding: var(--space-3);
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    border: 1px solid var(--border-default);
}
.match-row {
    display: inline-flex; align-items: center; gap: var(--space-2);
    background: var(--bg-canvas);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 6px 12px;
    font-size: 12.5px;
    transition: border-color var(--dur-fast) var(--ease-out);
}
.match-row:hover { border-color: var(--border-accent); }
.match-num {
    background: var(--brand-orange); color: var(--bg-canvas);
    border-radius: 50%; width: 22px; height: 22px;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 11.5px;
}
.match-src { color: var(--accent-emerald); font-weight: 600; }
.match-dst { color: var(--accent-blue);    font-weight: 600; }
.match-arrow { color: var(--text-muted);   font-size: 14px; }

/* ── 20. Scenario Table (教學) ── */
.scenario-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    font-size: 13px; margin: var(--space-2) 0;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    overflow: hidden;
}
.scenario-table th {
    background: var(--brand-orange); color: var(--bg-canvas);
    padding: 8px 12px; text-align: center; font-weight: 700; font-size: 12.5px;
    border-bottom: 1px solid rgba(0,0,0,0.1);
}
.scenario-table td {
    padding: 7px 12px; text-align: center;
    border-bottom: 1px solid var(--border-default);
    font-size: 12.5px; color: var(--text-primary);
}
.scenario-table tr:last-child td { border-bottom: none; }
.scenario-table tr:nth-child(even) td { background: var(--bg-canvas); }
.scenario-table tr:hover td { background: rgba(245, 158, 11, 0.04); }

/* ── 21. Animations ── */
@keyframes fade-in-up {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fade-in-up var(--dur-slow) var(--ease-out) both; }
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(245,158,11,0.0); }
    50%      { box-shadow: 0 0 0 8px rgba(245,158,11,0.10); }
}
.pulse { animation: pulse-glow 2.4s var(--ease-out) infinite; }

/* ── 22. Focus Visible (無障礙) ── */
*:focus-visible {
    outline: 2px solid var(--brand-orange) !important;
    outline-offset: 2px;
    border-radius: 4px;
}

/* ── 23. Responsive (≤ 768px) ── */
@media (max-width: 768px) {
    .block-container { padding: var(--space-3) !important; max-width: 100% !important; }
    .app-header { flex-direction: column; align-items: flex-start; gap: var(--space-3); }
    .app-header__logo { width: 56px; height: 48px; font-size: 28px; }
    .app-header__title { font-size: 1.6rem !important; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    .stButton > button,
    .stDownloadButton > button { font-size: 14px !important; padding: 10px 20px !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    button[data-baseweb="tab"] { padding: 10px 14px !important; font-size: 14px !important; }
}

/* ── 24. prefers-reduced-motion (無障礙) ── */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## 4. Python 程式碼調整範例

### 4.1 `app.py` — Header / Footer 改用 CSS class

**改版前**（在 `app.py` L70-82, L267-275）：約 30 行 inline `unsafe_allow_html` 區塊。
**改版後**（直接呼叫語意 class，HTML 大幅簡化）：

```python
# app.py — 在 st.set_page_config 之後、tabs 之前
st.markdown(f"""
<div class="app-header fade-in">
    <div class="app-header__logo">📦</div>
    <div>
        <h1 class="app-header__title">庫存調貨建議系統</h1>
        <p class="app-header__subtitle">{VERSION} · Intelligent Inventory Reallocation System</p>
    </div>
</div>
""", unsafe_allow_html=True)
```

頁尾（取代 L267-275）：

```python
st.markdown(f"""
<div class="app-footer">
    <p>📦 庫存調貨建議系統 <strong>{VERSION}</strong></p>
    <p>Intelligent Inventory Reallocation System (2026) · Developed by Ricky Yue · 只限 RP Team 使用</p>
</div>
""", unsafe_allow_html=True)
```

### 4.2 `app.py` — 主流程改用 `st.container` + `columns`

```python
with tab_system:
    # Section 1: Upload
    with st.container():
        st.markdown("### 📂 資料上傳")
        render_upload_requirements(mode_code)
        uploaded_file = st.file_uploader(
            "拖放或點擊上傳 Excel 文件",
            type=["xlsx", "xls"],
            help="支援 .xlsx 和 .xls 格式",
            label_visibility="visible",
        )

    if uploaded_file:
        progress_bar = st.progress(0, text="準備開始處理文件...")
        # ... (既有驗證流程不變) ...

        # Section 2: Analysis
        with st.container():
            st.markdown("---")
            st.markdown("### 🚀 分析與建議")

            # 模式資訊卡
            st.markdown(f"""
            <div class="surface-card">
                <strong>當前模式</strong> · {transfer_mode}
            </div>
            """, unsafe_allow_html=True)

            if st.button("🎯 生成調貨建議", type="primary", use_container_width=True):
                # ... 既有邏輯不變 ...
                pass

        # Section 3: Results
        recommendations = st.session_state.get('recommendations')
        if recommendations:
            st.markdown("---")
            with st.container():
                st.markdown("### 📈 分析結果")
                render_kpi_cards(statistics)
                render_results_by_priority(recommendations, df, current_run_key, mode)
                render_statistics(statistics)
                render_ai_executive_summary_button(recommendations, statistics, mode)

            # Download
            with st.container():
                st.markdown("---")
                render_download_button(_excel_bytes, _excel_filename, current_run_key)
                progress_bar.progress(100, text="處理完畢!")
```

### 4.3 `ui/sidebar.py` — 改用 `st.tabs` 整理說明區

```python
def render_sidebar() -> Dict:
    with st.sidebar:
        # 系統資訊卡（不再 inline）
        st.markdown("### 📦 系統資訊")
        st.markdown(f"""
        <div class="surface-card" style="margin-top: -8px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="color:var(--text-muted);font-size:13px;">系統版本</span>
                <span style="color:var(--accent-cyan);font-size:13px;font-weight:700;font-family:'JetBrains Mono',monospace;">{VERSION}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="color:var(--text-muted);font-size:13px;">開發者</span>
                <span style="color:var(--text-primary);font-size:13px;font-weight:600;">Ricky Yue</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 三段說明收進 tabs
        with st.expander("📖 完整功能與操作指引", expanded=False):
            tab_features, tab_howto, tab_modes = st.tabs(["核心功能", "操作流程", "模式說明"])
            with tab_features:
                st.markdown("...現有『核心功能』內容...")  # 保持文字不變
            with tab_howto:
                st.markdown("...現有『操作指引』內容...")
            with tab_modes:
                st.markdown("...現有『詳細模式說明』內容...")

        st.markdown("---")

        # 模式選擇（既有邏輯不變，僅 class 由新 CSS 接管）
        st.markdown("### ⚙️ 選擇轉貨模式")
        transfer_mode = st.radio(
            "選擇轉貨模式",
            _MODE_OPTIONS,
            key='transfer_mode',
            label_visibility="collapsed",
        )
        # ... 其餘 6 個條件式控件不變 ...

        st.caption(MODE_DESCRIPTIONS.get(transfer_mode, ""))
        st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        _render_perf_panel()

    return { ... }
```

### 4.4 `ui/display.py` — KPI 卡片加重點高亮

```python
def render_kpi_cards(statistics: dict):
    cols = st.columns(4)
    metrics = [
        ("調貨建議",   f"{statistics.get('total_recommendations', 0):,}", "📦"),
        ("調貨件數",   f"{statistics.get('total_transfer_qty', 0):,}",   "🔢"),
        ("產品數量",   f"{statistics.get('unique_articles', 0):,}",      "🏷️"),
        ("OM 數量",    f"{statistics.get('unique_oms', 0):,}",           "🗺️"),
    ]
    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.metric(label=f"{icon} {label}", value=value)
```

### 4.5 `ui/tutorial.py` — 流程節點改用 class

把 `_flow_node()` 內 inline 顏色全部換成 class：

```python
def _flow_node(text, color="blue", width="auto"):
    color_class = f"flow-node--{color}"  # e.g. "flow-node--green"
    w = f"width:{width};" if width != "auto" else ""
    return (
        f'<div class="flow-node {color_class}" style="{w}">'
        f'{text}</div>'
    )

def _risk_badge(level):
    return (
        f'<span class="risk-badge risk-badge--'
        f'{"low" if level == "低" else "medium" if level == "中" else "high"}">'
        f'風險：{level}</span>'
    )
```

### 4.6 套用新 CSS 的入口（`app.py` 不變，僅 `ui/styles.py` 維持現狀）

`ui/styles.py` 已正確載入 `static/styles.css`，**不需要改動**。
未來若要熱切換主題，只需在 `load_css()` 中加上 `?v=20260611` query string。

---

## 5. 實施步驟（部署指引）

### 5.1 檔案替換清單

| 動作 | 檔案 |
|---|---|
| 修改 | `.streamlit/config.toml`（貼上 §2 內容） |
| **完全覆蓋** | `static/styles.css`（貼上 §3 內容，**先備份**） |
| 修改 | `app.py`（套用 §4.1, §4.2） |
| 修改 | `ui/sidebar.py`（套用 §4.3） |
| 修改 | `ui/display.py`（套用 §4.4） |
| 修改 | `ui/tutorial.py`（套用 §4.5） |

### 5.2 本地驗證

```bash
# 1. 啟動開發伺服器
streamlit run app.py

# 2. 檢查項目
#    - 側邊欄模式選擇視覺是否清晰
#    - 上傳檔案、生成建議流程正常
#    - 切換到「模式教學」分頁時 fade-in 動畫流暢
#    - DevTools → Lighthouse → Accessibility ≥ 90
#    - 視窗縮窄到 375px（手機寬）是否仍可讀

# 3. 清除快取
streamlit cache clear
```

### 5.3 Zeabur 部署

1. **無須額外步驟**：`.streamlit/config.toml` 隨 git tracked，Zeabur 啟動時自動讀取。
2. 確認 `requirements.txt` 沒新增依賴（本次改版**純 CSS + 既有 Streamlit API**）。
3. 若日後新增 `streamlit-shadcn-ui` 或 `streamlit-extras`，記得：
   ```bash
   pip freeze | grep -E "streamlit-shadcn|streamlit-extras" >> requirements.txt
   git add requirements.txt
   git commit -m "deps: 新增 UI 元件庫"
   ```
4. 觸發 Zeabur 重新部署：
   ```bash
   git push origin main
   ```
   或手動 `Redeploy` 在 Zeabur Dashboard。

### 5.4 streamlit.app（Streamlit Community Cloud）部署

1. 把 repo 推到 GitHub。
2. 在 https://share.streamlit.io 連結 → 選擇 `app.py` 為入口。
3. Secrets 從 `.streamlit/secrets.toml` 自動載入（OpenAI API key 等）。
4. Community Cloud 預設 `base="light"`，但我們的 `config.toml` 強制 `base="dark"`，無需擔心。
5. 若日後要 hot-reload CSS，可加 query string：`static/styles.css?v=20260611`。

### 5.5 靜態檔案處理

- **字型（Inter / JetBrains Mono）**：採用 Google Fonts CDN（CSS 內 `@import`），無需打包。
- **本地離線部署**：若需離線，請下載字型 `.woff2` 放到 `static/fonts/` 並改用 `@font-face`。
- **無 favicon**：`page_icon="📦"` 為 emoji 內嵌，**無需** `static/favicon.png`。

### 5.6 驗證清單（Deploy Acceptance）

- [ ] 切換 27 種模式，sidebar 不閃爍、無 console error
- [ ] 上傳範例 Excel，正常生成 KPI / 表格 / 下載
- [ ] 模式教學頁 27 個 flow diagram 顯示正常
- [ ] 切換到窄螢幕 (≤ 768px) 排版不破
- [ ] DevTools Lighthouse Accessibility ≥ 90
- [ ] `prefers-reduced-motion: reduce` 動畫被關閉
- [ ] GitHub Pages / 截圖列印時仍可讀

---

## 6. 額外建議

### 6.1 是否引入 `streamlit-shadcn-ui` 或 `streamlit-extras`？

| 套件 | 優點 | 風險 | 建議 |
|---|---|---|---|
| `streamlit-shadcn-ui` | shadcn/ui 風格（極簡黑白 + 大量留白） | 第三方，版本可能與 Streamlit 1.38 衝突；客製難度高 | **謹慎** — 若團隊有時間，先在分支試用 |
| `streamlit-extras` | 提供 `st.metric_with_delta`、`st.dataframe_explorer` 等增強元件 | 體積小，相容性好 | **推薦** — 可逐步替換現有 KPI 為 `metric_with_delta` 顯示漲跌 |
| `streamlit-aggrid` | 高階表格（可排序、篩選、群組） | 體積大（~10MB），Zeabur 冷啟動變慢 | **不推薦** — 既有 `st.dataframe` 已足夠 |
| `streamlit-elements` | Material UI / React 元件 | 需熟悉 React，學習成本高 | **不推薦** |

**最終建議**：先以**純 CSS 強化**完成本次改版，**不引入新依賴**。
若日後需 KPI 漲跌顯示，再評估 `streamlit-extras` 即可。

### 6.2 性能優化

1. **`@st.cache_data` 包裹**：
   - `load_css()` → 改為 `@st.cache_data` 避免每次 rerun 重讀檔案
   - `_cached_preprocess` 既有（保留）
2. **CSS 體積**：本次 CSS 約 700 行 / 25 KB，未壓縮；Zeabur 容器 4 MB 限制內毫無壓力。
3. **DataFrame 大表**：
   - 既有 `ZEABUR_RESULT_PREVIEW_LIMIT` 機制（預設 1000 列）保留
   - 可額外加入 `st.dataframe(df, height=500)` 限制高度

### 6.3 無障礙優化（A11Y）

| 項目 | 實作 |
|---|---|
| 鍵盤導引 | `*:focus-visible` 已加橘色 outline |
| 螢幕閱讀器 | 既有 `st.file_uploader` / `st.button` 自帶 ARIA |
| 對比度 | `--text-primary: #F8FAFC` 對 `--bg-canvas: #0B0F19` 對比度 = **17.4:1**（WCAG AAA） |
| 動畫 | `@media (prefers-reduced-motion: reduce)` 自動停用 |
| 色彩盲 | 主色橘 + 輔色青，色相差距大；避免純紅綠傳達 |

### 6.4 後續可考慮項目（Out of Scope，本次不實施）

- 暗 / 亮主題切換 toggle（Streamlit 1.38 暫不支援 runtime 切換）
- 多語系 i18n（簡體中文 / 英文）
- 將 README 截圖更新為新版介面
- 將 `config.py` 的 `THEME` dict 與 CSS tokens 同步（避免兩處配色）

---

## 7. 風險與回滾計畫

| 風險 | 機率 | 緩解 |
|---|---|---|
| CSS 覆蓋 Streamlit 內部 class 失敗（版本更新） | 中 | 每次升級 Streamlit 後跑 smoke test；保留 `git tag v2.24.2-pre-ui-redesign` |
| 第三方元件庫衝突 | 低 | 本次不新增依賴 |
| 使用者已習慣舊版配色 | 中 | 在 README 與教學頁公告「介面升級」訊息 |
| 動畫降低性能（老舊設備） | 低 | `prefers-reduced-motion` 自動保護 |

**回滾方式**：
```bash
git revert HEAD~3..HEAD   # 撤銷最近三次提交
git push origin main       # 觸發 Zeabur 自動重部署
```

---

## 8. 開放問題（待用戶確認）

1. 是否同意本次改版**不新增第三方依賴**（純 CSS + 既有 Streamlit API）？
2. 是否同意保留 `static/styles.css` 路徑不變（向下相容 `ui/styles.py` 既有呼叫）？
3. 是否需要同步把 `config.py` 的 `THEME` dict 標記為 deprecated（避免雙軌維護）？
4. 是否同意「介面升級」公告文案統一放在 README 與 `tutorial.py` 開頭？

> 若以上 4 項均同意，請回覆「**Finalize and save the plan**」；
> 若有任一項需調整，請回覆「**Continue refining**」並指明修改方向。
