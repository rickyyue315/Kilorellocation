# 版本更新記錄

## v2.38.3 (2026-10-17)

### 針對 Streamlit Community Cloud 免費方案（約 1GB RAM）的資源防護

#### 背景（實測數據，純 Python、未含 Streamlit server 開銷）
| 輸入規模 | XLSX | DataFrame | 峰值 RSS | 配對耗時 | Excel 匯出 |
| --- | --- | --- | --- | --- | --- |
| 2 萬行 | 1.0 MB | 8.8 MB | 172 MB | 2.6 s | 1.7 s |
| 20 萬行 | 10.2 MB | 88.6 MB | 748 MB | 26 s | 17 s |

原本的上傳上限 50MB 約等於 100 萬行，遠超 1GB 容器可承受範圍，且快取無上限、列數預覽只套用主結果表。

#### 變更說明
- **雲端上傳上限**：新增 `KILO_CLOUD_MAX_UPLOAD_MB`（預設 **8MB**；本機維持 50MB），`FILE_SIZE_LIMIT_BYTES` 依環境自動套用，錯誤訊息顯示實際上限。
- **雲端列數守衛**：新增 `KILO_CLOUD_MAX_ROWS`（預設 **120,000 行**，`0` = 不限制）與 `DataProcessor.enforce_row_limit()`，在讀檔後（最便宜階段）即中止並給出可行建議，避免平台以資源限制中斷整個 App。
- **結果表預覽擴及所有大表**：新增 `_limit_rows()`（純函式）與 `_maybe_limit_rows()`，套用於調貨建議表、**優先級分組表**、**缺口分析表**（原本僅主結果表）；統計與 Excel 匯出仍為全量。
- **快取上限**：`app.py` 預處理快取與 `ui/tutorial.py` 教學快取加上 `max_entries=2`，避免多次上傳的 DataFrame 累積佔用記憶體（Cloud 常見 OOM 原因）。
- **介面提示**：上傳區新增「雲端資源設定」caption（單檔上限／列數上限／預覽列數），讓使用者事前知道限制。
- **注意**：調貨演算法、優先級分組、品質檢查、Excel 輸出與模式教學內容均無變化。

#### 修改檔案
- `config.py` — `CLOUD_MAX_UPLOAD_MB`／`CLOUD_MAX_ROWS`／`MAX_UPLOAD_MB`／`MAX_ROWS`，`VERSION` bump 至 v2.38.3
- `data_processor.py` — `enforce_row_limit()`、上傳大小訊息改用實際上限
- `ui/display.py` — `_limit_rows()`／`_maybe_limit_rows()` 與三處套用、上傳區資源提示
- `app.py`、`ui/tutorial.py` — 快取 `max_entries=2`、docstring 版本
- `tests/test_cloud_guards.py`（新增，10 項測試）
- `README.md`、`.streamlit/secrets.toml.example` — 雲端資源上限與新環境變數說明

#### 驗證
- 434 項測試全數通過（424 + 新增 10）；`AppTest` 於雲端模式（`KILO_RUNTIME=cloud`）與本機模式實跑 `app.py`：0 例外、0 錯誤、0 警告，雲端模式正確顯示「單檔上限 8MB · 雲端列數上限 120,000 行 · 雲端結果表預覽 1,000 列」。

#### 文件同步
- `README.md`／`VERSION.md`／`config.py`／`app.py` 已同步；`ui/tutorial.py`、`調貨模式詳解.txt`、`transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改）。

#### 待辦（P1，未實作）
- `use_container_width` → `width="stretch"`（20 處；目前可用但已進入棄用期，只在 console 產生提示）
- Excel 匯出改 `constant_memory` 以降低大型結果的峰值記憶體
- 讀檔 `usecols` 只載入必要欄位（需先確認來源檔欄位清單）

---

## v2.38.2 (2026-10-17)

### 套件升級：支援 Python 3.14（解決 Community Cloud 建置失敗根因）

#### 變更說明
- **根因**：Community Cloud 以 **Python 3.14.8** 建置（平台預設且部署後不可更改），而 `streamlit==1.51.0` 限制 `pyarrow<22`，`pyarrow 21.0.0` 又沒有 cp314 wheel → 建置時退回原始碼編譯 Arrow C++，容器內無 `cmake` 而失敗。
- **修法（不依賴平台選單）**：升級 `streamlit==1.52.2`（自 1.52 起移除 pyarrow 上限）並鎖定 `pyarrow==22.0.0`（提供 cp310–cp314 wheel），使 Python 3.11–3.14 全部可直接安裝 wheel。
- **altair 明確鎖版**：`altair==5.5.0`（streamlit 1.52 允許 `altair<7`，不鎖會抓到 6.x；鎖版維持原驗證版本與圖表輸出一致）。
- **CI 改為矩陣**：`.github/workflows/ci.yml` 於 **3.13（本機）與 3.14（Cloud 預設）** 雙版本執行測試；`runtime.txt`／`Dockerfile` 維持 3.13。
- **驗證**：以乾淨虛擬環境（Python 3.13.7，全新 venv 安裝 `requirements.txt`）執行 424 項測試全數通過；另以 `AppTest` 實跑 `app.py`（0 例外、0 警告，含模式教學分頁）與 Arrow 渲染煙霧測試（`st.dataframe`／`st.bar_chart`／`st.download_button`，pyarrow 22 路徑）。
- **部署操作**：既有「建置失敗」的 App **無需刪除**，push 後於 App 右上角 **Manage app → Reboot** 即重新安裝依賴。
- **注意**：調貨演算法、優先級分組、品質檢查、Excel 輸出與模式教學內容均無變化。

#### 修改檔案
- `requirements.txt` — `streamlit 1.51.0 → 1.52.2`、`pyarrow 21.0.0 → 22.0.0`、新增 `altair==5.5.0`，更新版本選擇說明
- `.github/workflows/ci.yml` — 測試矩陣 `['3.13', '3.14']`
- `README.md` — 系統需求改為 Python 3.11–3.14；部署注意事項改寫（含 `Manage app → Reboot` 指引）
- `Dockerfile` — 版本註解更新
- `config.py` — `VERSION` bump 至 v2.38.2
- `app.py` — docstring 版本更新

#### 文件同步
- `README.md`／`VERSION.md`／`config.py`／`app.py` 已同步；`ui/tutorial.py`、`調貨模式詳解.txt`、`transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改）。

---

## v2.38.1 (2026-10-17)

### 修正 Streamlit Community Cloud 建置失敗（Python 3.14 不相容）

#### 變更說明
- **問題**：首次部署 Community Cloud 時 App 使用 **Python 3.14.8** 建置，`streamlit==1.51.0` 依賴 `pyarrow<22,>=7.0`，而 `pyarrow 21.0.0` 沒有 cp314 wheel（僅 cp39–cp313），pip／uv 退回原始碼編譯 Arrow C++，容器內無 `cmake` 而失敗（`error: command 'cmake' failed: No such file or directory`）。
- **部署結論**：Community Cloud 的 Python 版本**只能在部署精靈的 Advanced settings 選擇**（`runtime.txt`／`.python-version` 不被採用），且**部署後無法更改**——必須刪除 App，再以相同 subdomain 重新部署並選 **Python 3.13（或 3.11／3.12）**。
- **版本對齊**：本機開發為 Python 3.13，故將 CI（`.github/workflows/ci.yml`）、`runtime.txt`、`Dockerfile` 一併統一為 **3.13**（原為 3.11），避免再次出現「部署／本機不一致」。
- **依賴鎖定**：`requirements.txt` 明確加入 `pyarrow==21.0.0`（由 `streamlit 1.51` 的 `<22` 上限決定），並加註 Python 3.14 不支援的原因；無需 `packages.txt`／cmake。
- **注意**：調貨演算法、優先級分組、品質檢查、Excel 輸出與模式教學內容均無變化。

#### 修改檔案
- `requirements.txt` — 新增 `pyarrow==21.0.0` 與 Python 版本支援註解
- `.github/workflows/ci.yml` — Python 3.11 → 3.13
- `runtime.txt` — python-3.11 → python-3.13
- `Dockerfile` — `python:3.11-slim` → `python:3.13-slim`
- `README.md` — 系統需求、部署步驟與注意事項（Python 版本選擇、3.14 失敗原因、刪除重建流程）
- `config.py` — `VERSION` bump 至 v2.38.1
- `app.py` — docstring 版本更新

#### 文件同步
- `README.md`／`VERSION.md`／`config.py`／`app.py` 已同步；`ui/tutorial.py`、`調貨模式詳解.txt`、`transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改）。

---

## v2.38.0 (2026-10-17)

### 部署平台遷移：Zeabur → Streamlit Community Cloud（share.streamlit.io）

#### 變更說明
- **雲端環境偵測一般化**：`config.py` 新增 `IS_CLOUD_RUNTIME`，同時偵測 Streamlit Community Cloud（`/mount/src` repo 掛載路徑、`IS_STREAMLIT_CLOUD`／`STREAMLIT_CLOUD`／`STREAMLIT_SHARING_MODE` 環境變數）與 Zeabur 舊變數；可用 `KILO_RUNTIME=cloud|local` 強制指定。原 `IS_ZEABUR_RUNTIME`／`ZEABUR_RESULT_PREVIEW_LIMIT` 保留為向後相容別名。
- **Secrets 讀取**：新增 `config.get_setting()`，讀取順序為環境變數 → `st.secrets`（Community Cloud 只提供 Secrets TOML 輸入框；根層級鍵值在 Streamlit 解析 secrets 時會同步寫入環境變數）。`app.py` 的 `KILO_LOG_LEVEL`、`KILO_FIX_MOJIBAKE` 改用此函式。
- **預覽上限設定更名**：`KILO_CLOUD_RESULT_PREVIEW_LIMIT`（舊名 `KILO_ZEABUR_RESULT_PREVIEW_LIMIT` 仍相容）；結果表提示文字「Zeabur 效能模式」改為「雲端效能模式」。
- **`.streamlit/config.toml`**：移除 `fileWatcherType = "none"`（Community Cloud 強制 `runOnSave = true`，需保留檔案監看才能自動重跑）；補註 Community Cloud 會覆寫的設定項目（`showErrorDetails`／`fastReruns`／`runOnSave`／`enableXsrfProtection`／`gatherUsageStats`）。
- **`.streamlit/secrets.toml.example`**：改為 Community Cloud Secrets 面板說明與現行可選設定（AI 相關鍵值已於 v2.37.0 移除）。
- **部署文件與檔案**：README 的「Zeabur 部署」章節改寫為「Streamlit Community Cloud 部署」（部署步驟、Python 版本須於 Advanced settings 手動選擇、依賴與設定覆寫、雲端效能模式、休眠與日誌限制）；`Dockerfile`、`Procfile` 去除 Zeabur 字樣並標註為選用（Community Cloud 不讀取這些檔案）。
- **注意**：調貨演算法、優先級分組、品質檢查、Excel 輸出與模式教學內容均無變化。

#### 修改檔案
- `config.py` — `IS_CLOUD_RUNTIME`、`get_setting()`、`CLOUD_RESULT_PREVIEW_LIMIT`、向後相容別名；`VERSION` bump 至 v2.38.0
- `app.py` — 改用 `IS_CLOUD_RUNTIME` 與 `get_setting()`、移除未使用的 `import os`、docstring 版本更新
- `ui/display.py` — 雲端效能模式文字與常數更名
- `tests/test_p2_refactoring_integration.py` — 新增 `TestCloudDeploymentCompatibility`（雲端設定匯入、`get_setting()`、雲端偵測、相容別名）
- `.streamlit/config.toml`、`.streamlit/secrets.toml.example`
- `Dockerfile`、`Procfile`、`requirements.txt`、`README.md`

#### 部署遷移步驟（一次性）
1. `share.streamlit.io` → Create app → 選擇 repo `rickyyue315/Kilorellocation`、branch `main`、main file `app.py`。
2. Advanced settings → Python version 選 `3.11`（Community Cloud 不採用 `runtime.txt`）。
3. 選用設定（Secrets）依 `.streamlit/secrets.toml.example` 內容貼上。
4. Deploy 後確認：資料上載與分析、Excel 下載、模式教學分頁、雲端效能模式提示正常。

#### 文件同步
- `README.md`／`VERSION.md`／`config.py`／`app.py` 已同步；`ui/tutorial.py`、`調貨模式詳解.txt`、`transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改）。

---

## v2.37.0 (2026-10-08)

### 移除 AI 執行摘要功能

#### 變更說明
- **移除 AI 執行摘要**：刪除「🤖 生成執行摘要」按鈕及其結果展示（`ui/display.py` 的 `render_ai_executive_summary_button()`）。
- **移除 Excel「摘要」工作表**：`excel_generator.py` 的 `generate_excel_file()` 不再接受 `ai_summary` 參數，`create_smart_summary_sheet()` 一併刪除；統計摘要、Target達成分析、缺口分析等工作表不受影響。
- **移除 AI 客戶端**：刪除 `services/ai_client.py` 及 `tests/test_ai_client.py`；`config.py` 的 AI 設定（`AI_ENABLED`、`AI_DEFAULT_MODEL`、`AI_REQUEST_TIMEOUT`）一併移除。
- **依賴變更**：`requirements.txt` 移除 `httpx`（僅 AI 客戶端使用）。
- **注意**：調貨演算法、優先級分組、品質檢查、Excel 其他輸出均無變化。部署環境中的 `OPENROUTER_API_KEY` / `AI_ENABLED` 等環境變數可以移除，移除後不再產生任何影響。

#### 修改檔案
- `app.py` — 移除 AI 摘要按鈕與 Excel 快取 key 的 AI 相依，版本號更新
- `ui/display.py` — 移除 `render_ai_executive_summary_button()`
- `excel_generator.py` — 移除 `ai_summary` 參數與「摘要」工作表
- `config.py` — 移除 AI 設定，`VERSION` 更新為 v2.37.0
- `services/ai_client.py` — 刪除
- `tests/test_ai_client.py` — 刪除
- `tests/test_excel_generator.py` — 移除 `TestSmartSummarySheet` 測試類別
- `requirements.txt` — 移除 `httpx`
- `README.md` — 移除 AI 功能說明、環境變數與專案結構中的 AI 項目

## v2.36.0 (2026-10-08)

### 調貨缺口分析與 Target達成一致性修正（含模式邏輯變更）

#### 變更說明
- **F 模式 Target達成 vs 缺口分析矛盾修正**：`compute_target_fulfillment_stats` 新增 `target_dest_types` 過濾；「Target達成分析」只計使用者設定 Target 的接收點（F模式目標接收／F指定模式目標接收／NST模式目標接收），系統自動補0的「重點補0」目標（目標 = max(Safety×0.5,3)、缺口基準為目標−現有庫存）改以「調貨缺口分析」為準。修正前同一店會在 Target 表顯示「未達成」、缺口表顯示「已滿足」。
  - 注意：配對與分配邏輯不變，自動補0目標店仍會如常收貨，僅報表統計口徑改變；實收為 0 的自動補0店（原本只在 Target 表以「未達成」呈現）請改看「調貨缺口分析」的未滿足列。
- **來源可轉量上限保護（A1/ND4 模式邏輯）**：後處理「消除餘 1 件」的 +1 增益改為受來源可轉量限制（與匹配階段 `_adjust_a1_remainder` 一致），餘量不足時不增益。修正前可令店舖轉出超過可轉量、跌破安全庫存，且報表無法察覺（剩餘被截成 0、來源轉出率可超過 100%）。
- **品質檢查新增第 8 項**：來源店累計轉出不得超過配對前可轉出量（`perform_quality_checks` 傳入 pre-match 快照）。
- **缺口分析超量轉出可見化**：來源列新增 `after_transfer_stock`（轉後店內庫存）與 `over_transferred_qty`（超過可轉量）；超量時狀態顯示「已超出可轉量(N件)」，KPI 新增「超量轉出件數」，UI 顯示警告列。
- **E 模式（強制調撥）顯示修正**：目的地缺口值改為 None（不適用），不再顯示 0／達成率 100% 的假象；目的地總數為 0 時「目的地滿足率」顯示「不適用」而非 0.0%。
- **缺口分析 KPI 與欄位語義**：KPI 改名「未滿足店×SKU／剩餘店×SKU」（原「店數」實為店×SKU 組數）；新增「件數滿足率」（Σ實收 ÷ Σ需求）；來源「剩餘」欄更名「未轉出可轉量」並補充說明（可轉量為政策上限，非店內實體庫存），來源轉出率標示「(可轉量)」；「轉出率」ProgressColumn 上限改為 100 顯示，超量另以警告欄呈現。
- **D 模式缺口語義確認**：D 模式目的地的真實未滿足需求（如 RF 缺貨）維持如實顯示；`test_d_mode_no_dest_gap` 正名為 `test_d_mode_dest_partially_fulfilled` 並補上缺口 > 0 斷言。
- **測試新增**：`tests/test_gap_report_flow.py`（F 模式 Target/缺口一致性、A1 後處理上限防護、E 模式不適用顯示、D 模式部分滿足）；`tests/test_gap_report.py` 補超量轉出、件數滿足率、E 模式 None 值案例。

#### 修改檔案
- `services/statistics.py` — `TARGET_DEST_TYPES`、`compute_target_fulfillment_stats(target_dest_types=)`、缺口報表超量／件數滿足率／E 模式 None
- `services/post_processing.py` — `_source_remaining_capacity`／`_cap_group_boosts_remaining`，A1/ND4 後處理 +1 加上上限防護
- `services/quality_checks.py` — 新增來源累計轉出 ≤ 可轉量檢查（可選傳入 pre-match 快照）
- `business_logic.py` — `perform_quality_checks` 傳入快照
- `ui/display.py` — 缺口 KPI 改名與新增、超量警告、欄位語義（未轉出可轉量／轉後店內庫存／超過可轉量／缺口%）
- `excel_generator.py` — Target 表只計使用者目標、缺口表新欄位與 KPI、E 模式留空
- `tests/test_gap_report.py`、`tests/test_gap_report_flow.py`（新增）
- `config.py` — VERSION bump 至 v2.36.0
- `app.py` — docstring 版本更新
- `README.md`、`調貨模式詳解.txt`、`transfer_logic_ai_brief.md`、`data/tutorials/basic.json`、`data/tutorials/f.json` — 同步修正說明

#### 文件同步
- `README.md` / `VERSION.md` / `config.py` / `app.py` / `調貨模式詳解.txt` / `transfer_logic_ai_brief.md` / `data/tutorials/basic.json` / `data/tutorials/f.json` 已同步；模式邏輯變更屬 A1/ND4 後處理上限（影響總覽配對優先級陳述）與 F 模式報表界定，教學內容已於相關模式卡補註。

---

## v2.35.0 (2026-09-26)

### 全介面優化（無模式邏輯變更）

#### 變更說明
- **側邊欄三步化**：保底主體→選擇轉貨模式→模式參數編號分區，只顯示目前模式可用參數（無參數時提示直達上傳）；模式 radio 維持 30 選項平面列表（不分類），長選單啟用內部捲動；新增必填欄位即時提示與「目前選擇」總結卡（模式／保底／欄位）。
- **主流程步驟條**：調貨系統頂部新增 4 步進度（上傳→生成→檢視→下載，依上傳／結果／Excel 狀態自動推進）；上傳區 MTD 日期與提示並排，未上傳顯示 3 步空狀態指引；當前配置條新增參數摘要；結果／匯出區加 STEP 標題與數量 caption。
- **結果展示**：資料查覽新增 ND/RF 行數第 4 指標、表格固定高度＋隱藏索引；調貨建議新增 Article/店舖關鍵字篩選（顯示層過濾，不影響統計與 Excel，快取 key 含關鍵字防舊快取）；缺口分析三篩選改為並排＋顯示列數；圖表固定高度；統計表隱藏索引。
- **教學分頁**：8 組圖片版教學新增「全部展開」開關（註：遠端 main 已先行合併圖片版教學重構——總覽圖／速覽表／模式直達／場景篩選，本次 rebase 保留該結構，僅疊加展開開關）。
- **視覺**：新增 steps / section-title / current-config-banner / empty-state / side-step / side-summary / toolbar-card 樣式；長 radio 選單 `:has(> label:nth-child(10))` 內部捲動（短選單不受影響）。

#### 修改檔案
- `ui/sidebar.py` — 三步分區、必填欄位提示、參數條件顯示、目前選擇總結
- `app.py` — 步驟條、空狀態、並排日期、配置條參數摘要、STEP 標題、docstring 版本
- `ui/display.py` — ND/RF 指標、關鍵字篩選、缺口篩選並排、表格高度與隱藏索引、圖表高度
- `ui/tutorial.py` — 8 組圖片版教學新增「全部展開」開關（疊加於遠端圖片版重構之上）
- `static/styles.css` — 新增介面元件樣式
- `config.py` — VERSION bump 至 v2.35.0
- `README.md` — 介面操作流程更新

#### 文件同步
- `README.md` / `VERSION.md` / `config.py` / `app.py` 已同步；`ui/tutorial.py` 僅疊加展開開關於遠端圖片版教學結構之上（教學內容不變）、`調貨模式詳解.txt` 與 `transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改）。

---

## v2.34.0 (2026-09-03)

### 模式選擇器簡化（無模式邏輯變更）

#### 變更說明
- **模式選擇 UX**：「模式分類（8 組）→ 組內模式」兩級選擇改回 30 個選項平面 radio，全部模式一次列出、不分類（依照使用者反饋）。
- 側邊欄「選擇轉貨模式」改為 `get_ui_options()` 直接顯示全部 30 個模式，操作指引同步更新。
- 移除 `models/mode_registry.py` 的 `_DISPLAY_GROUPS` / `get_display_groups()` / `get_ui_options_for_codes()`（不再使用）；`get_ui_options()` 原樣保留。
- `tests/test_ui_helpers.py` 更新：顯示分組測試改為 `get_ui_options()` 覆蓋全部 30 模式且不重複、格式維持 `"CODE: name"`。

#### 修改檔案
- `ui/sidebar.py` — 兩級選擇器改回平面 radio、操作指引更新
- `models/mode_registry.py` — 移除分組輔助函式（get_ui_options 保留）
- `tests/test_ui_helpers.py` — 測試改為選項完整性與格式
- `config.py` — VERSION bump 至 v2.34.0
- `app.py` — docstring 版本更新
- `README.md` — 介面操作流程版本對齊

#### 文件同步
- `README.md` / `VERSION.md` / `config.py` / `app.py` 已同步；`ui/tutorial.py`（教學分頁分組屬教學展示，維持不變）、`調貨模式詳解.txt` 與 `transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改，僅 UI 層重組）。

---

## v2.33.0 (2026-08-16)

### UI/UX 改進（無模式邏輯變更）

#### 變更說明
- **Bug 修復**：
  - 優先級統計列改為彩色色塊統計條（🔴🟡🟢 顏色原本已定義但從未套用）
  - 側邊欄操作指引 markdown 縮排修正（次層列表不再破版）
  - 調貨缺口分析欄位改為數值型（缺口／剩餘可排序），達成率／轉出率以 ProgressColumn 進度條呈現（0–100%）
  - 缺口分析篩選狀態按 run 隔離，切換設定後自動重置（與結果表快取行為一致）
  - 教學 SVG 圖（Turnday 公式／對比圖）配色由舊青色主題改為現行橙色深色主題
  - 移除 `config.py` 未使用的 THEME 死代碼
- **圖表概覽**：結果區新增「📈 圖表概覽」— 轉出／接收類型分佈、按 OM 轉出 vs 接收量、Top 10 商品轉出量長條圖（Streamlit 內建圖表，零新依賴）
- **表格強化**：結果表與統計表整數欄位套用 column_config 數字格式（千分位）
- **模式選擇 UX**：30 個選項平面 radio 改為「模式分類（8 組，與教學分頁一致）→ 組內模式」兩級選擇；側邊欄「詳細模式說明」240 行全量文檔改為只顯示目前模式詳解（重構為 MODE_DOCS 字典，重複的 NST 段落自動消除）＋獨立「通用規則」區塊
- **流程優化**：
  - Excel 改為按下「📤 準備 Excel 報表」才生成（原本結果一出來即自動生成）
  - 上傳進度條於預處理完成後收起；分析階段改用 st.status 狀態面板逐步顯示（演算法 → 品質檢查 → 統計與缺口分析）
  - 錯誤追蹤改為常駐 expander（原本藏在 checkbox 後面）
  - 教學 JSON 加入 @st.cache_data，rerun 不再重讀 8 個 JSON 檔

#### 修改檔案
- `ui/display.py` — 優先級彩色統計條、render_charts 圖表概覽、column_config、缺口分析數值化＋run 隔離
- `ui/sidebar.py` — 兩級模式選擇器、MODE_DOCS 重構、操作指引縮排修復（538 → 323 行）
- `ui/mode_docs.py` — 新增（30 模式詳解字典＋通用規則）
- `ui/tutorial.py` — _load_group 加 @st.cache_data
- `app.py` — render_charts 接線、惰性 Excel、st.status、進度條收起、錯誤 expander、docstring 版本
- `models/mode_registry.py` — 新增 get_display_groups() / get_ui_options_for_codes()（get_ui_options 原樣保留）
- `config.py` — VERSION bump 至 v2.33.0、移除 THEME
- `static/tutorials/turnday_formula.svg` / `turnday_compare.svg` — 配色更新為現行主題
- `tests/test_ui_helpers.py` — 新增（顯示分組覆蓋全部 30 模式、MODE_DOCS 完整性）
- `README.md` — 標題版本對齊、介面操作流程更新

#### 文件同步
- `README.md` / `VERSION.md` / `config.py` / `app.py` 已同步；`調貨模式詳解.txt` 與 `transfer_logic_ai_brief.md` 無需變更（無模式新增／移除／邏輯修改，僅 UI 層重組）

---

## v2.32.0 (2026-08-16)

### 新增保底主體（Safety / Turnday）× 模式矩陣

#### 變更說明
- **保底主體二選一**（側邊欄），與全部 30 個調貨模式任意組合（2 主體 × 30 模式 = 60 種組合，零代碼分叉）：
  - `Safety Stock（現行版本）`（預設）：沿用上載檔 Safety Stock，行為與 v2.31 完全一致（現有 392 個測試全數不改一行通過）。
  - `Turnday（日銷速×日數）`：以 Turnday 保底值取代 Safety Stock 欄位值，全部 Safety 觸點自動切換（轉出保底、緊急/潛在缺貨目標、補0目標 S×0.5→T×0.5、接收上限 S×2→T×2、精簡SKU Cap Max(S×2,銷×2)→Max(T×2,銷×2)）。
- **Turnday 公式**：`保底 = ceil(日銷速 × 自選日數 N)`（3–60 日，預設 14）；`日銷速 = Effective Sold Qty ÷ 覆蓋日數`；`覆蓋日數 = 上月日數 + MTD數據日期日號`（例：8/15 = 7月31日 + 15日 = 46日）。零銷量 SKU 保底 = 0（可全數轉出）。
- **上載區新增 MTD 數據日期輸入**（`st.date_input`，預設昨日 T-1），Turnday 主體顯示覆蓋日數核對 caption。
- **透明度**：Turnday 套用後原值備份至 `Original Safety Stock`、新增 `Daily Sold Rate` 欄；結果標題標明「當前模式 | 保底主體」；Excel 統計摘要新增「保底主體」列（主體、日數、數據日期）供輸出追溯。
- **不受影響**：C1（淨存>2）、F3/NST（保留2件/75%）、ND3/ND4（保留3件）等非 Safety 固定保底維持原狀；Safety 主體路徑零改動（`business_logic.py` / `strategies/` 不變）。

#### 修改檔案
- `config.py` — 版本號 bump 至 v2.32.0；新增 FLOOR_BODY_SAFETY / FLOOR_BODY_TURNDAY / TURNDAY_DEFAULT_DAYS / TURNDAY_MIN_DAYS / TURNDAY_MAX_DAYS
- `services/turnday.py` — 新增（compute_coverage_days / describe_coverage / apply_turnday_floor）
- `ui/sidebar.py` — 新增保底主體 radio + Turnday 日數輸入，回傳 dict 增 floor_body / floor_body_option / turnday_days
- `app.py` — 上載區 MTD 數據日期輸入 + 覆蓋日數核對；Turnday 套用（df.copy 後欄位取代）；current_run_key 加入主體設定；結果卡片標明主體；Excel 傳遞 floor_body_label；docstring 版本更新
- `excel_generator.py` — generate_excel_file / create_summary_dashboard_sheet 新增 floor_body_label 參數，統計摘要寫入「保底主體」列
- `tests/test_turnday.py` — 新增 20 個測試（覆蓋日數月邊界/ceil/零銷量/欄位取代/原 df 不變動/Safety×Turnday×A模式整合/印章流轉）
- `README.md` — 核心規則、功能重點、系統衍生欄位、介面操作流程更新
- `調貨模式詳解.txt` — 新增「保底主體（Safety / Turnday）」章節
- `ui/tutorial.py` — 新增 `_render_floor_body_guide()` 保底主體教學段（概念流程圖 + SVG 圖解 + 公式 + 模式受影響對照 + 風險提示），模式教學區頂部加入 Safety→Turnday 替換說明
- `static/tutorials/turnday_formula.svg` — 新增 Turnday 三步計算流程圖解（覆蓋日數 → 日銷速 → 保底，深色主題）
- `static/tutorials/turnday_compare.svg` — 新增 Safety vs Turnday 保底對比圖（快銷/慢銷/零銷量店舖情境條形圖，深色主題）
- `transfer_logic_ai_brief.md` — Safety Stock 語義更新（dual floor body）

#### 文件同步
- `README.md` / `VERSION.md` / `config.py` / `app.py` / `ui/tutorial.py` / `調貨模式詳解.txt` / `transfer_logic_ai_brief.md` 已全部同步

---

## v2.31.0 (2026-08-14)

### Excel 輸出新欄位順序 + 新增 Type 欄位

#### 變更說明
- 調貨建議工作表（調貨建議 (Transfer Recommendations)）欄位順序統一調整為 **21 欄**（全模式適用）：
  `Brand;Article;Product Desc;Transfer OM;Transfer Site;Transfer Site Type;Transfer Site Last Month Sold Qty;Transfer Site MTD Sold Qty;Transfer Original Stock;Transfer Safety Stock;Transfer After Transfer Stock;Receive OM;Receive Site;Receive Site Type;Receive Site Last Month Sold Qty;Receive Site MTD Sold Qty;Receive Original Stock;Receive Site Safety Stock;Transfer Qty;Remark;Notes`
- **新增 `Transfer Site Type` / `Receive Site Type`**：輸出該店舖於輸入檔 `Type` 欄位的值（T/M/L/R）；非 B 系模式如無 Type 資料則為空白。
- `精簡SKU(退D001)` 模式維持在最後追加 `D001 Receive Qty` 欄。
- App 內結果預覽表：B 系模式（B2/B2a/B2L/B2La/B3/B3a/B3L/B3La）改為與新 Excel 欄位一致；其餘模式預覽維持不變。

#### 修改檔案
- `config.py` — 版本號 bump 至 v2.31.0
- `services/recommendation_factory.py` — `build_recommendation()` 新增 `Transfer Site Type` / `Receive Site Type`
- `excel_generator.py` — 新 21 欄順序（EXCEL_COLUMN_ORDER）、索引式列寬/格式套用
- `ui/display.py` — B 系模式預覽表與新 Excel 欄位一致
- `tests/test_excel_generator.py` — 新增欄位順序/Type 值/D001 欄測試
- `tests/test_recommendation_factory.py` — 新增 build_recommendation Type 傳遞測試
- `app.py` — docstring 版本更新（v2.31.0）
- `README.md` — Excel 輸出新欄位說明
- `調貨模式詳解.txt` — Excel輸出資料結構更新
- `ui/tutorial.py` — B 系模式輸出 Type 欄說明

---

## v2.30.0 (2026-07-22)

### 新增 A1 模式：保守轉貨(轉出店舖不餘存貨1件)

#### 模式說明
- **A1**：基於 A（保守轉貨）規則，但**避免轉出店舖剛好剩 1 件存貨**
- 繼承 A 模式全部規則：RF 過剩轉出（20% 庫存上限、最低 2 件）、安全庫存保護
- **核心差異**：轉出配對時若源店會剩 1 件，自動執行以下調整：
  1. **接收方 +1 件**：在接收店 target_qty 上限 +1 的範圍內，增量 1 件以避免餘 1
  2. **源店保留 2 件**：若 +1 會超出接收上限，則源店保留 2 件（不強制至 0）
- **ND Shop 不強制出清**：不要求 ND Shop 必須轉至 0 件，僅消除「餘 1 件」情況
- 適合 ND Shop 轉出且不希望存貨餘 1 件的場景

#### 修改檔案
- `config.py` — 版本號 bump 至 v2.30.0
- `models/mode_registry.py` — MODE_DEFS 新增 A1 ModeDef（30 模式）
- `business_logic.py` — _compute_rf_transferable 加入 mode_a1 路由；generate 加入 A1 後處理
- `services/matching_engine.py` — 新增 _adjust_a1_remainder()；compute_transfer_qty 雙向調用
- `services/post_processing.py` — 新增 optimize_a1_avoid_one_remainder()
- `ui/sidebar.py` — A1 模式描述、功能清單、操作指引
- `ui/tutorial.py` — 教學內容更新（30 模式、基礎組標題）
- `data/tutorials/basic.json` — 新增 A1 教學 JSON 資料（含 flow、情境、對比表）
- `app.py` — docstring 版本更新（v2.30.0，30 模式）
- `tests/test_mode_registry.py` — 更新模式計數（29→30）
- `tests/test_all_modes_comprehensive.py` — 新增 TestModeA1（6 個測試案例）

#### 文件同步
- `README.md` — 模式列表新增 A1、模式對照表、功能亮點、介面流程更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.30.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — 教學內容更新
- `調貨模式詳解.txt` — 新增 A1 模式說明
- `transfer_logic_ai_brief.md` — 更新模式列表與限制

---

## v2.29.0 (2026-07-15)

### 新增 ND4 模式：ND 限同 OM 轉貨（補 0 及有銷售記錄）

#### 模式說明
- **ND4**：基於 ND3（ND限同OM轉貨補0），但對接收店舖增加銷售記錄限制
- **轉出端優化**（與 ND3 不同）：無銷量來源店（Last Month+MTD=0）不保留 3 件，全數可轉出；有銷量來源店保留 3 件（與 ND3 相同）
- **接收端差異**：僅 Last Month Sold Qty + MTD Sold Qty > 0（有銷售記錄）的零庫存 ND 店舖才可接收
- 無銷售記錄的零庫存 ND 店舖不會收到任何貨品
- 同 OM 配對（不跨 OM）
- 可設定同一 SKU 下單一出貨店舖配對接收店舖：優先 1 間 / 最多 2 間 / 不限

#### 修改檔案
- `config.py` — 版本號 bump 至 v2.29.0
- `models/mode_registry.py` — MODE_DEFS 新增 ND4 ModeDef
- `strategies/nd_mode.py` — 新增 identify_sources_nd4_mode、identify_destinations_nd4_mode、NDModeStrategy 路由
- `business_logic.py` — dest_method 路由更新、docstring 版本更新
- `services/notes.py` — 新增 ND4 轉出/接收分析 note
- `ui/sidebar.py` — ND4 模式描述、功能清單、操作指引
- `ui/tutorial.py` — 教學內容更新（決策指南、全局規則、群組標題）
- `data/tutorials/nd_sku.json` — 新增 ND4 教學 JSON 資料
- `app.py` — docstring 版本更新（v2.29.0，29 模式）

#### 文件同步
- `README.md` — 模式列表、模式對照表、功能亮點、介面流程更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.29.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — ND4 教學內容
- `data/tutorials/nd_sku.json` — ND4 教學資料
- `調貨模式詳解.txt` — 新增 ND4 詳細規則
- `transfer_logic_ai_brief.md` — 新增 ND4 條目

---

## v2.28.0 (2026-07-13)

### 同步 stores-template.csv 店舖資料更新（88 → 90 間店舖）

#### 變更說明
- **HB97（新旺角文華）**：Class 2 由 A2 修正為 A1
- **HBA7（AIRSIDE）**：新增店舖（HK, C, C2, XS, Hippo, M）
- **HC71（荃錦中心）**：新增店舖（HK, C, C1, L, Eva, L）
- **HD20（澳門銀河2）**：Class 1 由 B 修正為 A，Class 2 由 B1 修正為 A3，Size 由 S 修正為 M

#### 修改檔案
- `stores-template.csv` — 原始資料更新（本次來源）
- `data/stores.json` — 同步 4 筆變更（HB97 修正、新增 HBA7/HC71、HD20 修正）
- `config.py` — 版本號 bump 至 v2.28.0
- `app.py` — docstring 版本更新
- `VERSION.md` — 本版本記錄

---

## v2.27.0 (2026-06-16)

### D/D2 模式 Excel 報表新增「ND清貨完成分析」頁

#### 變更說明
- D 系列（`清貨轉貨`、`清貨轉貨(ND限定)`）Excel 報表新增第三張工作表 `ND清貨完成分析`
- 仿照 F 系列 `Target達成分析` 頁面，彙整 ND 清貨來源的完成狀態
- 提供每 SKU 的未完成剩餘件數與未完成店舖數彙總
- 提供 per-store 明細（Original Stock / Total Transferred / After Transfer Stock / Status）
- 若來源 ND 店舖完全未配對到接收店，仍會出現在統計中（需提供原始 df）

#### 新增檔案
- （無）

#### 修改檔案
- `services/statistics.py` — 新增 `compute_nd_clearance_stats()` 函式
- `excel_generator.py` — 新增 `create_nd_clearance_sheet()` 方法；`generate_excel_file()` D/D2 分支
- `config.py` — 版本號 bump 至 v2.27.0
- `app.py` — docstring 版本更新
- `VERSION.md` — 本版本記錄

#### 文件同步
- `README.md` — 輸出內容補充（D/D2 報表含 ND清貨完成分析頁）
- `ui/tutorial.py` — D/D2 教學補充輸出結構說明
- `調貨模式詳解.txt` — D/D2 輸出內容補充
- `transfer_logic_ai_brief.md` — D/D2 輸出格式補充

---

## v2.26.0 (2026-06-15)

### D2 模式新增「限制2間店舖接收（原有設定）」選項（3選1）

#### 變更說明
- D2 模式接收策略從 2 選 1 擴展為 3 選 1：
  1. **「不限店舖數量（原有設定）」**：每間 ND 源可配對任意數量 RF 接收店，target_qty 為正常值
  2. **「限制2間店舖接收（原有設定）」**（新增）：每間 ND 源最多配對 2 間 RF 接收店，target_qty 為正常值
  3. **「限制2間店舖接收（優化版）」**：每間 ND 源最多配對 2 間 RF 接收店，target_qty 放大至 200%
- 遷移 `d2_enable_2site_limit`（bool）→ `d2_site_limit_mode`（str），支援 3 種狀態

#### 修改檔案
- `ui/sidebar.py` — 新增第 3 個 radio 選項及對應註解；D2 詳細模式說明更新
- `config.py` — 版本號 bump 至 v2.26.0
- `app.py` — `d2_enable_2site_limit` 改為 `d2_site_limit_mode`；docstring 版本更新
- `business_logic.py` — `d2_site_limit_mode` 參數（預設 "unlimited"）；dest/matching 三路路由
- `services/notes.py` — 三種模式的 note suffix 邏輯

#### 文件同步
- `README.md` — D2 模式描述、核心規則、功能亮點、模式對照表更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.26.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — D2 教學內容更新（3 選 1 說明）
- `data/tutorials/d.json` — D2 extra_notes 更新
- `調貨模式詳解.txt` — D2 新增「原有設定」優化版說明
- `transfer_logic_ai_brief.md` — D2 模式說明更新

---

## v2.25.0 (2026-06-11)

### 新增 NST 模式：New Shop Target調貨（第28個模式）

#### 模式說明
- **NST（New Shop Target調貨）**：基於 F2 架構（僅 Target > 0 店舖接收），RF 轉出有更嚴格的限制
- **核心差異**：
  - RF 轉出後保留 ≥2 件（轉出量 = min(net_stock × 0.75, net_stock - 2)）
  - RF 轉出上限為庫存的 75%
  - RF 庫存 < 3 件不轉出
  - 可設定同一 SKU 轉出店舖數量上限（10 間 / 20 間 / 不限制）
  - 因 RF 轉出限制，目標可能未達 100%，此為預期行為
- ND 店舖全數轉出（與 F2 相同）
- 繼承 F2 的 HD 轉出選項、Windy 目標優先、優先滿足小型目標、配對後缺口填補

#### 新增檔案
- `strategies/nst_mode.py` — NewShopTargetStrategy 策略類別（轉出/接收識別 + 匹配邏輯）

#### 修改檔案
- `config.py` — 新增 `NST_RF_RETAIN_STOCK`、`NST_RF_TRANSFER_CAP`、`NST_RF_MIN_STOCK_TO_SOURCE` 常數；版本號 bump 至 v2.25.0
- `models/mode_registry.py` — MODE_DEFS 新增 NST ModeDef，含 `nst_shop_limit` extra_ui_options
- `business_logic.py` — 新增 `nst_max_source_shops` 參數、NST 策略路由、target_stores 保護、skip_nd_check
- `ui/sidebar.py` — 新增 NST 專屬 UI（同一SKU轉出店數上限 radio）、NST加入HD轉出及優先滿足小型目標選項
- `app.py` — 提取 `nst_max_source_shops`、傳入 TransferLogic、更新 run_key 及 docstring

#### 文件同步
- `README.md` — 模式列表、核心規則、模式對照表、功能亮點、介面流程、教學分組更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.25.0
- `app.py` — docstring 版本更新、模式數更新為 28
- `ui/tutorial.py` — 目標優化系列新增 NST 教學內容
- `data/tutorials/f.json` — 新增 NST 教學 JSON 資料
- `調貨模式詳解.txt` — 新增 NST 詳細規則
- `transfer_logic_ai_brief.md` — 新增 NST 模式說明

---

## v2.24.2 (2026-06-11)

### C/C1/C2 模式新增每店轉出件數上限滑塊（原僅 C1 可用）

#### 變更說明
- 將 C1 模式的「每店轉出件數上限」滑塊（c1_ceiling, 3~10, 預設 3）擴展至 C 和 C2 模式
- C 和 C2 模式原先使用硬編碼常數 `C_MODE_ABS_CAP = 3`，現改為可調
- C/C1/C2 三模式共用同一側邊欄滑塊，預設值 3 完整向後兼容
- C1 模式的補0門檻（c1_threshold）仍為 C1 獨有

#### 修改檔案
- `business_logic.py` — `_compute_rf_transferable` 中 abs_cap 條件從 `mode == self.mode_c1` 擴展為 `mode in (self.mode_c, self.mode_c1, self.mode_c2)`
- `models/mode_registry.py` — C 和 C2 ModeDef 的 `extra_ui_options` 新增 `c1_ceiling`
- `ui/sidebar.py` — 將 ceiling 滑塊從 `if mode_code == "C1"` 移至 `if mode_code in ("C", "C1", "C2")`；threshold number_input 保持 C1 獨有；UI 標籤改為「每店轉出件數上限」
- `config.py` — 版本號 bump 至 v2.24.2
- `app.py` — docstring 版本更新

#### 文件同步
- `README.md` — 模式列表、功能亮點、模式對照表更新
- `VERSION.md` — 本版本記錄
- `data/tutorials/c.json` — C/C2 教學內容更新（流程圖文字、extra_notes、diff_table）
- `調貨模式詳解.txt` — C/C2 轉出規則更新
- `transfer_logic_ai_brief.md` — C/C2 模式說明更新

---

## v2.24.1 (2026-06-10)

### Bug fixes & Zeabur deployment hardening

#### 變更說明
- 修復 `safe_get_last2m` NaN crash：`services/source_dest_factory.py` 中 `int()` 遇到 NaN 會拋出 `ValueError`，現加入 `pd.notna()` 保護
- 修復 `notes.py` 不可能條件：`transfer_qty==2` 與 `original_stock==1` 不可能同時成立，移除無效的 dead code
- 修復 article_site_index 字串比對容錯性：`Site` 與 `Transfer Site` 欄位進行 `.strip().upper()` 正規化，避免靜默查詢失敗
- 鎖定 Zeabur Python 版本（新增 `runtime.txt` → python-3.12）
- 鎖定 Streamlit 版本為 `1.38.0`（避免容器環境 breaking changes）
- 新增 `.streamlit/secrets.toml.example` 範本，API Key 改由 Zeabur Dashboard Secrets 管理
- 新增 `pytest>=8.0.0` 以相容 Python 3.13

## v2.24.0 (2026-06-10)

### C1 模式新增每店轉出件數上限滑塊（3~10 件，自選）

#### 變更說明
- C1 模式新增 UI 滑塊：可在側邊欄設定每間 RF 源店的轉出件數上限（`c1_ceiling`，範圍 3~10，預設 3）
- 原本轉出上限固定為 3 件（30% total_available 比例上限不變），現改為可調
- 提高每店轉出上限可直接減少調出店舖總數量（source 越少，拆單越集中）
- 預設值 3 完整向後兼容原有行為

#### 修改檔案
- `config.py` — 新增 `C1_MODE_DEFAULT_CEILING = 3`；版本號 bump 至 v2.24.0
- `models/mode_registry.py` — C1 ModeDef extra_ui_options 新增 `c1_ceiling`
- `ui/sidebar.py` — 新增 C1 件數上限滑塊（st.slider, 3~10, 預設 3），更新 C1 描述文字、return dict
- `app.py` — 提取 `c1_ceiling` 選項、傳入 `TransferLogic` 建構子、加入 run_key
- `business_logic.py` — 新增 `c1_ceiling` 參數（預設 3），`_compute_rf_transferable` 中 C1 模式 `C_MODE_ABS_CAP` 改為 `self.c1_ceiling`

#### 文件同步
- `README.md` — 模式列表、功能亮點、模式對照表更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.24.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — C1 教學內容更新（流程圖文字、extra_notes、diff_table）
- `調貨模式詳解.txt` — C1 轉出規則更新、關鍵差異對比表更新
- `transfer_logic_ai_brief.md` — C1 模式說明更新

---

## v2.23.0 (2026-06-09)

### F/F2/F3 模式 Target 達成改善（優先滿足小型目標 + 配對後缺口填補 + Target達成分析）

#### 變更說明
- **「優先滿足小型目標」checkbox**（F/F2/F3 側邊欄）：勾選後 Priority-1 目標店按 needed_qty 升序排序（小型目標優先），最大化達成目標數量
- **配對後缺口填補**：主要配對完成後，若有剩餘來源庫存，自動分配給尚未滿足的目標店
- **Target達成分析 Excel 工作表**：新增獨立工作表，顯示每組 (Article, Site) 的 Target Qty 與 Actual Received 對比、Gap、Status（達成/部分達成/未達成），以及彙總 KPI（總目標數、達成數、達成率、總差距）

#### 修改檔案
- `business_logic.py` — 新增 `f_fulfill_small_first` 參數、`_f_mode_gap_fill()` 方法、`_generate_target_fulfillment_analysis()` 方法；Priority-1 目標排序邏輯
- `models/mode_registry.py` — F/F2/F3 ModeDef 新增 `extra_ui_options=frozenset({'f_fulfill_small_first'})`
- `ui/sidebar.py` — 新增 F/F2/F3「優先滿足小型目標」checkbox
- `app.py` — 提取 `f_fulfill_small_first` 選項並傳入 `TransferLogic`
- `excel_generator.py` — 新增 `create_target_fulfillment_analysis_sheet()` 方法；F/F2/F3 模式下生成 Target達成分析工作表

#### 文件同步
- `README.md` — 模式對照表、功能亮點、輸出內容更新
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.23.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — F/F2/F3 教學內容更新（新增 Target fulfillment 說明）
- `調貨模式詳解.txt` — F/F2/F3 模式新增描述
- `transfer_logic_ai_brief.md` — F/F2/F3 模式更新

## v2.22.0 (2026-06-08)

### C1 模式新增可調節補0門檻（UI 選擇鍵）

#### 變更說明
- C1 模式新增 UI 選擇鍵：可在側邊欄設定補0門檻（`c1_threshold`，預設 N=1），調整 C1 模式處理的 total_available 上限
- 原本固定 `total_available > 1` 跳過，現改為 `total_available > self.c1_threshold`（可設定）
- 預設值 `1` 完整向後兼容原有行為
- 輸入範圍：0-100（0 = 不補任何店舖，100 = 補幾乎所有 RF 店舖）

#### 修改檔案
- `config.py` — 新增 `C1_MODE_DEFAULT_THRESHOLD = 1`；版本號 bump 至 v2.22.0
- `models/mode_registry.py` — C1 ModeDef 新增 `extra_ui_options=frozenset({'c1_threshold'})`
- `ui/sidebar.py` — 新增 C1 門檻數字輸入（st.number_input），更新 C1 描述文字
- `app.py` — 提取 `c1_threshold` 選項、傳入 `TransferLogic` 建構子、加入 run_key
- `business_logic.py` — 新增 `c1_threshold` 參數（預設 1），`_dests_c1_mode` 條件改為 `total_available > self.c1_threshold`

## v2.21.0 (2026-06-05)

### D2 優化：新增 UI 選擇鍵 + 限制接收店舖數量 + 放寬數量

#### 變更說明
- D2 模式新增 UI 選擇鍵：可在側邊欄切換「不限店舖數量（原有設定）」與「限制2間店舖接收（優化版）」
- 優化版限制每間 ND 轉出源最多配對 2 間 RF 接收店（`max_receive_sites_per_source=2`），避免轉出店需為大量不同店舖打包
- 優化版將接收量放大至 200%（`D2_NEEDED_QTY_MULTIPLIER=2`），補償接收店數量減少的影響

#### 新增檔案
- `.kilo/plans/1780626584804-quiet-garden.md` — 實作計劃文件

#### 修改檔案
- `config.py` — 新增 `D2_MAX_RECEIVE_SITES_PER_SOURCE`、`D2_NEEDED_QTY_MULTIPLIER` 常數；版本號 bump 至 v2.21.0
- `models/mode_registry.py` — D2 ModeDef 新增 `extra_ui_options=frozenset({'d2_enable_2site_limit'})`
- `ui/sidebar.py` — 新增 D2 模式選擇鍵（st.radio）
- `app.py` — 提取 `d2_enable_2site_limit` 選項並傳入 `TransferLogic`
- `business_logic.py` — 新增 `_dests_d2_mode()` 方法（target_qty ×2）、`d2_enable_2site_limit` 參數、條件路由（identify_destinations/match_transfers）
- `services/matching_engine.py` — 新增 `match_d2_mode()` 函式，每回合傳入 `max_receive_sites_per_source=2`
- `services/notes.py` — D2 優化版 note 增加「限制接收店≤2間，接收量放大至200%」標示

## v2.20.0 (2026-06-01)

### 方案三：優先級分組 + 可選 AI 執行摘要

#### 變更說明
- 移除原有的 AI 模式建議（Advisor）、AI 邏輯審計（Auditor）功能
- 取而代之的是**確定性優先級分組**（🔴🟡🟢）—— 100% 基於規則、零 API 依賴、永遠可用
- AI 僅保留為可選的「執行摘要」按鈕（聚合統計資料 → LLM → 短文摘要）
- Excel 不再包含 AI 分析摘要 sheet

#### 新增檔案
- `services/prioritizer.py` — 優先級指派引擎（純函式、確定性規則）

#### 修改檔案
- `business_logic.py` — 在 `generate_transfer_recommendations()` 中為每條建議賦予優先級，按優先級排序
- `ui/display.py` — 新增 `render_results_by_priority()`（三層 expander 分組）與 `render_ai_executive_summary_button()`（可選 AI）
- `app.py` — 移除 AI 審計按鈕與下載含 AI 摘要的 Excel 按鈕，改為優先級分組展示
- `config.py` — 精簡 AI 配置區（13 行 → 3 行）、版本號 bump 至 v2.20.0
- `excel_generator.py` — 移除 `ai_report` 參數與 `create_ai_analysis_sheet()` 方法

#### 刪除檔案
- `services/ai_advisor.py`
- `services/ai_auditor.py`
- `tests/test_ai_advisor.py`
- `tests/test_ai_auditor.py`
- `tests/test_ai_note_simulation.py`

#### 新增測試
- `tests/test_prioritizer.py` — 22 個測試案例覆蓋所有優先級規則

#### 文件同步
- `README.md` — 更新 AI 章節
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.20.0
- `app.py` — docstring 版本更新，移除 AI advisory/audit 提及

## v2.19.0 (2026-06-01)

### 新增 ND3 模式：ND 限同 OM 轉貨（補 0）

#### 模式說明
- **ND3**：ND 同 OM 轉貨，轉出保留 3 件庫存，僅針對零庫存 ND 店舖補貨
- 參考 C1 模式：僅處理目標需求，不回落一般缺貨
- 同 OM 配對（不跨 OM）

#### 轉出規則（`_sources_nd3_mode`）
- 僅 ND 店舖，`SaSa Net Stock > 3` 才可轉出
- 轉出量 = `SaSa Net Stock - 3`（保留 3 件）
- 最高銷量 ND 店舖受保護
- 按銷量由低到高排序（零銷量優先）

#### 接收規則（`_dests_nd3_mode`）
- 僅 ND 店舖，`SaSa Net Stock == 0` 才可接收
- 目標數量 = `max(Safety Stock × 0.5, 3)`（同 C1）
- 需求數量 = 目標數量 - 總可用庫存
- 按銷量由高到低排序
- 接收類型：`ND3補0接收`

#### 配對策略
- 使用 `nd_mode` 策略（同 ND1/ND2）
- 可配置接收店數限制
- 同 OM 配對（groupby Article + OM）

#### 程式碼新增/修改
- `config.py` — 新增 `ND3_KEEP_STOCK = 3` 常量，版本號 bump 至 v2.19.0
- `models/mode_registry.py` — 新增 ND3 ModeDef
- `business_logic.py` — 新增 `_sources_nd3_mode()`、`_dests_nd3_mode()`，更新 import 與 docstring
- `services/notes.py` — 新增 ND3 轉出/接收分析 note
- `app.py` — docstring 版本更新（v2.19.0，27 模式）

#### 文件同步
- `README.md` — 新增 ND3 模式描述、模式對照、接收店數限制列表、教學分頁
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.19.0
- `app.py` — docstring 版本更新
- `ui/tutorial.py` — 新增 ND3 教學內容
- `調貨模式詳解.txt` — 新增 ND3 詳細規則
- `transfer_logic_ai_brief.md` — 新增 ND3 條目

### 新增 AI 顧問／審計／報表摘要（可選功能）

#### AI 功能說明
- **AI 模式建議（Advisor）**：上傳資料後，基於 aggregate summary 推薦合適的調貨模式；不自動切換使用者選擇。
- **AI 邏輯審計（Auditor）**：產生調貨建議後，基於 capped payload 提供風險提示與正面檢查；不修改建議結果。
- **Excel AI 分析摘要**：在有 AI report 時，Excel 新增 `AI分析摘要` sheet（顧問建議、審計結果、風險等級、驗證檢查）。
- 所有 AI 功能預設**關閉**（`AI_ENABLED=false`），不影響既有調貨流程。
- 使用 OpenRouter API，模型可透過環境變數／Zeabur secrets 配置。

#### 程式碼新增
- `services/ai_client.py` — OpenRouter REST API 封裝、session cache、錯誤降級
- `services/ai_advisor.py` — 模式推薦（build_df_summary、build_mode_options、parse_advisor_response）
- `services/ai_auditor.py` — 邏輯審計（build_audit_payload、parse_audit_response）
- `ui/display.py` — `render_ai_status_badge`、`render_ai_advisor_card`、`render_ai_audit_report`
- `config.py` — AI config 常數（AI_ENABLED、AI_DEFAULT_MODEL 等）+ `_get_env_bool` helper
- `requirements.txt` — 新增 `httpx>=0.27.0`

#### Excel 更新
- `excel_generator.py` — `generate_excel_file()` 新增 `ai_report` 參數；`create_ai_analysis_sheet()` 條件式建立 AI 分析摘要 sheet

#### 測試新增
- `tests/test_ai_client.py` — 8 項 AI client 測試
- `tests/test_ai_advisor.py` — 15 項 advisor 測試
- `tests/test_ai_auditor.py` — 10 項 auditor 測試
- `tests/test_excel_generator.py` — 新增 6 項 AI sheet 測試

#### Zeabur Secrets 設定
```text
OPENROUTER_API_KEY=sk-or-v1-xxxxx
AI_ENABLED=true
AI_MODEL=deepseek/deepseek-v4-flash
AI_MODEL_ADVISOR=deepseek/deepseek-v4-flash
AI_MODEL_AUDITOR=deepseek/deepseek-v4-flash
AI_REQUEST_TIMEOUT=30
OPENROUTER_SITE_URL=https://<your-zeabur-domain>
OPENROUTER_APP_TITLE=KiLo Reallocation
```

#### 文件同步
- `README.md` — AI 功能說明、環境變數、Zeabur secrets、disclaimer
- `VERSION.md` — 本版本記錄
- `config.py` — 版本號 bump 至 v2.18.0
- `app.py` — docstring 版本更新、AI 功能描述

#### 核心原則
- AI 不修改 `business_logic.py` 的 deterministic 調貨結果
- AI disabled / no key / API failure / JSON parse failure 時核心流程完全可用
- 不上傳全量 DataFrame，只傳 aggregate summary / capped samples
- 不記錄 API key、不在 UI 或 log 暴露 prompt 全量內容

---

## v2.17.0 (2026-06-01)

### 新增 F3 模式（目標性補0）

#### 功能說明
- 新增第 26 種模式：`F3: 目標性補0`
- 基於 F2 架構（僅 Target > 0 店舖接收、HD 轉出選項、Windy 目標優先）
- **核心差異**：
  - RF 轉出後保留 2 件（net_stock > 2 才可轉出，轉出量 = net_stock - 2）
  - RF 按最高庫存優先轉出（同優先級內銷量低優先）
  - RF 跨 OM 不降級（同 OM / 跨 OM 同等 tier）

#### 程式碼更新
- [`models/mode_registry.py`](models/mode_registry.py) — MODE_DEFS 新增 F3 記錄
- [`business_logic.py`](business_logic.py) — `_sources_f_mode` F3 RF 邏輯、模式路由、質量檢查、target_stores 保護
- [`strategies/f_mode.py`](strategies/f_mode.py) — `_sort_key` F3 tier / HD / Windy 懲罰邏輯
- [`ui/sidebar.py`](ui/sidebar.py) — F3 HD 轉出選項、模式描述、功能清單、操作指引
- [`app.py`](app.py) — docstring 更新為 26 模式、F3 ND+Target 衝突檢查
- [`config.py`](config.py) — 版本號 bump 至 v2.17.0

#### 文件同步
- [`README.md`](README.md) — 模式列表、跨 OM 規則、功能亮點、模式對照表、教學分組
- [`VERSION.md`](VERSION.md) — 本版本記錄
- [`ui/tutorial.py`](ui/tutorial.py) — 目標優化系列新增 F3 教學內容
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — 模式列表、關鍵差異對比表、F3 詳解
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — F3 模式說明

#### 測試新增
- [`tests/test_f3_mode.py`](tests/test_f3_mode.py) — F3 專屬測試（保留2件、最高庫存排序、跨OM不降級等）

---

## v2.16.0 (2026-05-26)

### 新增精簡SKU(退D001)模式

#### 功能說明
- 新增第 25 種模式：`精簡SKU(退D001)`
- 與精簡SKU(限同OM/跨OM)共用相同的來源識別邏輯（ND 全轉出、RF 超出 Cap 轉出）
- **核心差異**：所有轉出數量一律直接回退 D001，不進行 RF 接收配對
- RF僅1件不回退D001（避免浪費人力），ND不受此限
- 報告新增「D001 Receive Qty」欄位（僅此模式顯示）

#### 程式碼更新
- [`strategies/simplified_sku_return_d001.py`](strategies/simplified_sku_return_d001.py)（新增）— SimplifiedSKUReturnD001Strategy 匹配策略
- [`models/mode_registry.py`](models/mode_registry.py) — MODE_DEFS 新增精簡SKU(退D001) 記錄
- [`business_logic.py`](business_logic.py) — 策略路由、mode_info 快取、docstring 更新
- [`excel_generator.py`](excel_generator.py) — D001 Receive Qty 欄位條件顯示、docstring 更新
- [`ui/tutorial.py`](ui/tutorial.py) — ND/SKU 專項組新增精簡SKU(退D001) 教學內容，決策指南更新

#### 文件同步
- [`README.md`](README.md) — 模式對照表新增精簡SKU(退D001)、版本號更新
- [`VERSION.md`](VERSION.md) — 本版本記錄
- [`config.py`](config.py) — 版本號 bump 至 v2.16.0
- [`app.py`](app.py) — docstring 更新
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — 模式25 精簡SKU(退D001) 說明
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — 模式概覽更新為 25 模式、新增完整模式說明

## v2.15.0 (2026-05-21)

### 匹配引擎去重與代碼品質優化

#### matching_engine.py 去重
- 提取 `_clamp_target_qty()` 輔助函數，統一 b_special / 重點補0 / d_family 三向 target_qty 限制邏輯（原重複 2 次）
- 提取 `_adjust_d_family_remainder()` 輔助函數，統一 D 系列「避免剩餘1件」調整邏輯（原重複 2 次）
- 提取 `_mark_dest_saturated()` 輔助函數，統一飽和度檢查（原分散於 match_by_priority）
- `compute_transfer_qty` 從 72 行縮減至 ~40 行，消除重複代碼塊

#### can_transfer 冗餘修正
- 修正 B3 模式下跨 OM 檢查重複執行的問題（通用跨 OM 檢查 + B3 專屬檢查 → 改為 if/elif 互斥）

#### prep_temp_lists 統一
- 提取 `prep_temp_lists()` 共用函數至 matching_engine.py
- 消除 8 個策略檔案中重複的 temp_sources/temp_destinations 初始化樣板（b_special、f_mode、e1_mode、e2_mode、nd_mode、c2_mode、simplified_sku、matching_engine）

#### mode_info 快取
- `business_logic.py` 的 `_create_recommendation_note` 每次調用時不再重新建立 mode_info 字典
- 改為在 `__init__` 中預先快取所有 24 種模式的 mode_info（`_mode_info_cache`），查表取代 9 次 `_is_*_mode` 調用

#### 影響範圍
- 純內部重構，無外部 API 變更
- 所有 265 項測試全部通過
- 不影響 Zeabur 或 Streamlit Community Cloud 部署

## v2.14.0 (2026-05-21)

### 模式參數化表 + 效能架構準備

#### 模式註冊表（Mode Registry）
- `models/mode_registry.py`：新增 `ModeDef` dataclass + 24 筆 `MODE_DEFS` + 衍生查詢函式（`get_mode_def`、`get_mode_families`、`get_ui_options`、`get_receive_limit_codes` 等）
- `models/mode.py`：改為從 `mode_registry.py` 衍生（`MODE_NAME_MAP`、`MODE_DESCRIPTIONS`、`RECEIVE_SITE_LIMIT_MODE_CODES`），保持向後兼容匯出
- `ui/sidebar.py`：`_MODE_OPTIONS` 改為 `get_ui_options()` 自動生成，`RECEIVE_SITE_LIMIT_MODE_CODES` 改為 `get_receive_limit_codes()`
- `business_logic.py`：`__init__` 中 24 個 `self.mode_*` 常數改為從 registry 自動 `setattr`；`MODE_FAMILIES`、`_ALL_MODES`、`_CROSS_OM_*`、`_SOURCE_FILTER_MODES` 改為從 registry 衍生
- `business_logic.py`：`identify_sources/destinations` 路由改為 registry 查表；`generate_transfer_recommendations` 策略路由改為 `strategy_key` 查表

#### 效能架構準備
- `services/perf_timer.py`：新增可選計時 decorator，預設關閉（`KILO_PERF_TIMING=1` 才啟用）
- `services/matching_engine.py`：新增架構文檔 docstring（平行化準備說明）
- `business_logic.py`：`generate_transfer_recommendations` 加上 `@perf_timer` 裝飾

#### 測試新增
- `tests/test_mode_registry.py`：25 項測試涵蓋 registry 資料完整性、衍生查詢函式、向後兼容匯出

#### 影響範圍
- 純內部重構，無外部 API 變更
- 所有 268 項測試全部通過（243 既有 + 25 新增）
- 不影響 Zeabur 或 Streamlit Community Cloud 部署
- 新增第 25 種模式時，只需在 `MODE_DEFS` 加 1 筆記錄（+ 新策略類別如需要）

## v2.13.0 (2026-05-21)

### 程式碼重構與測試強化

#### 模組拆分
- `services/target_utils.py`：Target 解析、正規化、ND 衝突偵測等共用函式（從 `app.py` 及 `business_logic.py` 抽出）
- `services/matching_engine.py`：核心配對邏輯（`match_by_priority`、`can_transfer`、`compute_transfer_qty`、`match_general_mode`）從 `business_logic.py` 抽出
- `services/post_processing.py`：後處理邏輯（`optimize_single_piece_transfers`、`refresh_recommendation_fields`、銷量計算）從 `business_logic.py` 抽出
- `business_logic.py` 保留 `TransferLogic` 類別作為 facade，以薄委派（thin delegation）方式呼叫新模組，所有公開 API 不變

#### 測試新增
- `tests/test_data_processor.py`：31 項測試涵蓋 `read_excel_file`、`validate_columns`、`validate_file_format`、`convert_data_types`、`fill_default_store_data`、`handle_missing_values`、`correct_outliers`、`calculate_effective_sold_qty`、`preprocess_data`
- `tests/test_excel_generator.py`：10 項測試涵蓋 `generate_filename`、`_generate_remark`、`generate_excel_file`（回傳格式、雙工作表、空建議、欄位驗證等）

#### 影響範圍
- 純內部重構，無外部 API 變更
- 243 項既有 + 新增測試全部通過
- 不影響 Zeabur 或 Streamlit Community Cloud 部署

## v2.12.0 (2026-05-19)

### 新增模式教學分頁

#### 功能說明
- 新增「模式教學」分頁（`st.tabs`），位於系統頂部「調貨系統」旁邊
- 繁體中文圖例化教學，涵蓋全部 24 種調貨模式
- 無需額外套件，使用 HTML + inline CSS 繪製流程圖

#### 教學內容
- **全局規則**：ND 限制、最高動銷店保護、避免雙重角色、單件後處理（HTML 流程圖）
- **8 組模式教學**（延遲載入，expander 展開時才生成）：
  1. 基礎調貨（A / B）
  2. B 特別模式（B2 / B2a / B2L / B2La）
  3. B 跨 OM 特別模式（B3 / B3a / B3L / B3La）
  4. 重點補 0 系列（C / C1 / C2）
  5. 清貨模式（D / D2）
  6. 強制轉出系列（E1 / E1b / E2）
  7. 目標優化系列（F / F2）
  8. ND/SKU 專項（ND1 / ND2 / 精簡SKU(限同OM) / 精簡SKU(跨OM)）
- 每個模式包含：適用場景、風險等級（低/中/高）、轉出篩選流程圖、接收篩選流程圖、配對優先級、數字情境範例表格、模式對比
- **模式選擇決策指南**：決策流程圖 + 進一步區分表格，幫助使用者根據業務需求選擇模式

#### 效能設計
- 延遲載入（lazy evaluation）：8 組教學內容以函數引用傳入 `st.expander`，僅在展開時才生成 HTML
- 全靜態內容，無數據處理，適合 Zeabur 部署
- 不影響現有調貨系統功能

#### 相關檔案
- [`ui/tutorial.py`](ui/tutorial.py)（新增）— 教學分頁渲染模組
- [`app.py`](app.py) — 新增 `st.tabs(["調貨系統", "模式教學"])` 雙分頁結構
- [`static/styles.css`](static/styles.css) — 新增教學頁面專用 CSS
- [`README.md`](README.md) — 功能重點、介面操作流程、專案結構更新

---

## v2.11.3 (2026-05-19)

### 匹配優先次序優化（P0/P1/P2）

#### 問題描述
經全面分析24種模式的匹配優先次序後，發現以下三個需優化的優先級問題：

##### P0 — C模式重點補0回合過晚（高嚴重性）
C模式的重點補0（零庫存店鋪補充）原本放在第7回合（最後），ND/RF庫存已被前6回合的緊急/潛在缺貨消耗殆盡，導致零庫存店得不到補貨。

##### P1 — B Special Local全轉出優先於RF過剩（中高嚴重性）
B2/B2a/B3/B3a模式中，`Local店舖全轉出`（Type=L低銷量店強制清空）排在第3-4回合，優先於`RF過剩轉出`（第5-6回合），導致激進的全轉出先於保守的RF過剩被執行。

##### P2 — C1模式回合未明確分離（中嚴重性）
C1模式依賴「沒有緊急/潛在缺貨目的地」的巧合來讓RF來源正確匹配重點補0，程式碼意圖不明確，依賴隱式行為。

#### 修改內容

**P0：C模式重點補0提前**（`business_logic.py` `match_transfers()`）
- 新增回合 `0a`：ND轉出 → 重點補0（C模式限定）
- 新增回合 `4a`：RF過剩轉出 → 重點補0（C模式限定）
- 新增回合 `6a`：RF加強轉出 → 重點補0（C模式限定）
- 每個來源層級（ND/RF過剩/RF加強）都先做重點補0，再做緊急缺貨/潛在缺貨
- 刪除舊的第7回合（RF轉出 → 重點補0，無來源類型區分）

**P1：B Special Local全轉出移後**（`strategies/b_special.py`）
- 回合順序變更：`RF過剩轉出` → `Local店舖全轉出` → `RF加強轉出`
- 確保保守的RF過剩先於激進的Local全轉出被使用

**P2：C1模式回合分離**（`business_logic.py` `match_transfers()`）
- 新增回合 `2a`：RF過剩轉出 → 重點補0（C1模式限定，附 `dest_type_filter='重點補0'`）
- 新增回合 `4b`：RF加強轉出 → 重點補0（C1模式限定，附 `dest_type_filter='重點補0'`）
- 確保RF過剩先於RF加強被選中，且未來修改標準回合時C1不受影響

#### 相關檔案
- [`business_logic.py`](business_logic.py) — 匹配回合重組
- [`strategies/b_special.py`](strategies/b_special.py) — Local全轉出移後
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — 匹配優先級順序更新
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — 匹配流程更新
- [`README.md`](README.md) — 版本號更新
- [`VERSION.md`](VERSION.md) — 本版本記錄

#### 測試結果
- 137 項測試全部通過（0 失敗）
- 涵蓋所有24個模式的：dual-role防護、接收上限、單件優化、B Special Mix保護等

---

## v2.11.2 (2026-05-19)

### F2 模式 — Windy 目標店優先從同 OM 無 Target 店提取

#### 功能說明
- F2 模式下，當 Windy 目標店（有 Target > 0）需要接收時，優先從其他無 Target 的 Windy 店舖提取
- 僅在 Windy 來源不足時，才回落至非 Windy 來源（Ivy/Eva 等 OM）

#### 程式碼更新
- [`strategies/f_mode.py`](strategies/f_mode.py)
  - `_sort_key` 新增 `windy_penalty=5`：當目的地為 Windy 且來源非 Windy 時加 5，確保 Windy 來源排序於非 Windy 來源之前
- [`tests/test_f2_windy_priority.py`](tests/test_f2_windy_priority.py) (新增)
  - `test_f2_windy_source_prioritized_over_non_windy`：Windy 來源足夠時不使用非 Windy 來源
  - `test_f2_windy_falls_back_to_non_windy_when_insufficient`：Windy 來源不足時回落非 Windy 來源
  - `test_f2_windy_nd_source_prioritized_over_non_windy_nd`：Windy ND 來源優先於非 Windy ND 來源

#### 文件同步
- [`README.md`](README.md) — 模式列表、跨 OM 規則、模式對照表更新
- [`調貨模式詳解.txt`](調貨模式詳解.txt) — F2 核心特徵與轉出規則更新
- [`ui/sidebar.py`](ui/sidebar.py) — 特殊功能列表與 F2 模式說明更新
- [`models/mode.py`](models/mode.py) — F2 模式描述更新
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md) — F2 Extra constraints 新增 Windy source priority
- [`VERSION.md`](VERSION.md) — 本版本記錄

## v2.11.1-hotfix (2026-05-12)

### 系統架構重構（Phase 1-5）

#### 核心改動
本日進行了大規模系統架構重構，共計 12 個 commit，涵蓋以下範圍：

**Phase 1 — 清理**
- 刪除 `debug/` 目錄（30+ 除錯腳本）
- 刪除根目錄重複腳本（60+ 檔案）
- 刪除 `Geminiapp.py` 替代版本
- 將臨時測試腳本遷移至 `tests/legacy/`

**Phase 2 — 模組抽取**
- 新增 `config.py`：集中所有魔術數字與配置常數
- 新增 `models/mode.py`：MODE_NAME_MAP、MODE_DESCRIPTIONS、RECEIVE_SITE_LIMIT_MODE_CODES
- 新增 `ui/` 目錄：sidebar.py、display.py、styles.py、mojibake.py
- `app.py` 從 1201 行精簡至 266 行

**Phase 3 — 工廠模式**
- 新增 `services/recommendation_factory.py`：`build_recommendation()` + `apply_transfer()` 統一建構
- 新增 `_make_source()` / `_make_dest()` 工廠函式
- 抽取 `_compute_transfer_qty()` 方法
- 抽取 `_note_source_analysis()` / `_note_dest_analysis()` 方法

**Phase 4 — 策略模式抽取**
- 新增 `strategies/base.py`：BaseMatchStrategy 抽象基類
- 新增 `strategies/predicates.py`：`is_hd_to_hk_restricted()` 共用判斷
- 新增 `strategies/simplified_sku.py`：SimplifiedSKUStrategy
- 新增 `strategies/c2_mode.py`：C2ModeStrategy
- 新增 `strategies/f_mode.py`：FModeStrategy
- 新增 `strategies/e1_mode.py`：E1ModeStrategy（E1/E1b）
- 新增 `strategies/nd_mode.py`：NDModeStrategy（ND1/ND2）
- 新增 `strategies/b_special.py`：BSpecialStrategy（委派至 `_match_by_priority`）

**Phase 5 — 程式碼清理**
- 刪除 6 個已抽取的死方法
- `business_logic.py` 從 3400+ 行精簡至 2144 行
- 統一所有模式使用 `build_recommendation()` + `apply_transfer()`

#### Bug 修復
- **ND 模式 NaN 崩潰**：`_make_dest()` 中 `int(row['Safety Stock'])` 在 NaN 時崩潰，新增 `pd.notna()` 防禦
- **Streamlit Cloud import 錯誤**：保留 `_parse_target_for_ui` 和 `_find_f_mode_nd_target_conflicts` 在 app.py 中的本地副本

#### 版本號修正
- `business_logic.py` class docstring：v2.11.0 → v2.11.1
- `data_processor.py` docstring：v2.10.0 → v2.11.1
- `excel_generator.py` docstring：v2.10.0 → v2.11.1
- `DEBUG_CHECKLIST.md` 版本：v2.10.0 → v2.11.1

#### 測試結果
- 全部 175 個測試通過（0 失敗）
- 涵蓋所有 24 個模式的：dual-role 防護、HD 限制、Windy 限制、Mix 銷量保護、接收上限、單件優化、ND 模式等

#### 已知限制（待後續處理）
1. `_parse_target_for_ui()` 和 `_find_f_mode_nd_target_conflicts()` 重複定義於 app.py 和 business_logic.py，待合併至共用模組
2. E2 模式匹配邏輯仍留在 business_logic.py 中（`_match_transfers_e_mode` + `_e_mode_phase3_c_fallback`），待抽取至 `strategies/e2_mode.py`
3. SimplifiedSKUStrategy 和 C2ModeStrategy 的 Notes 使用簡化格式，與其他策略的詳細格式不完全一致
4. 無 data_processor.py 和 excel_generator.py 的單元測試

---

## v2.11.1 (2026-05-11)

### 模式A單件調貨上調優化

#### 核心改動
- 模式A（保守轉貨）來源識別階段，當 `actual_transferable` 計算為 1 件且 `remaining_stock >= 3`（轉出 1 件後淨庫存餘 3 件以上）時，自動上調至 2 件轉出
- 上調後以 `Safety Stock - 1` 作為放寬安全線（數學等價於原始安全檢查，不降低實際安全水準）
- 避免來源店被限制只能轉出 1 件的低效調撥情況

#### 條件總結
1. `actual_transferable == 1`（由 `base_transferable = total_available - safety_stock` 限制所致）
2. `remaining_stock >= 3`（SaSa Net Stock ≥ 4，確保上調至 2 件後來源仍餘 ≥ 2 件）
3. `2 <= upper_limit`（20% 上限允許，因 floor=2 故本條件永遠成立）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.11.1
  - `identify_sources()` 模式 A 區塊新增上調邏輯（第 500-507 行）
  - 放寬安全線由數學等價性隱式保證，無需額外顯式檢查

#### 文件同步
- [`README.md`](README.md)
  - 版本號更新至 v2.11.1
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 模式A說明新增單件上調規則
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 模式A說明新增上調規則

---

## v2.11.0 (2026-05-11)

### F2模式新增HD轉出選項

#### 核心功能
- F2模式新增「HD 店舖轉出設定」選項，提供兩種選擇：
  - **HD 不能轉出（預設）**：維持原有行為，HD 店舖不可轉貨到 HA/HB/HC 店舖
  - **HD 可轉出（最後優先）**：允許 HD 店舖轉貨到 HA/HB/HC，但排在最低優先級，僅在其他來源（ND、同OM RF、跨OM RF）都不足時才使用

#### 使用場景
- 當 HA/HB/HC 店舖不夠貨，且 HD 店舖有庫存可轉出時，可啟用此選項
- HD 轉出會被排在配對排序的最後，確保優先使用非 HD 來源

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.11.0
  - `TransferLogic.__init__` 新增 `f2_allow_hd_transfer: bool = False` 參數
  - `_match_transfers_f_mode`：`_f_source_sort_key` 新增 `dest_site` 參數與 HD 懲罰項（`hd_penalty=10`）
  - `_match_transfers_f_mode`：HD 限制檢查改為條件式，F2 + `f2_allow_hd_transfer=True` 時不跳過
- [`app.py`](app.py)
  - 新增 F2 模式「HD 店舖轉出設定」radio button（僅 F2 模式下顯示）
  - 將 `f2_allow_hd_transfer` 傳入 `TransferLogic` 建構子
  - 更新模式描述、詳細模式說明、欄位說明

## v2.10.0 (2026-04-30)

### 新增精簡SKU模式（限同OM / 跨OM）+ F/F2模式改善

#### 精簡SKU模式核心規則
- 新增兩個精簡SKU模式：`精簡SKU(限同OM)`、`精簡SKU(跨OM)`
- 針對 SKU 精簡場景設計，將超出上限的庫存轉出至有需求的 RF 店舖
- RF 店舖存貨上限 Cap = `Max(Safety Stock × 2, Last 2 Month Sold Qty × 2)`
- ND 店舖全數可轉出
- 轉給 RF 店舖最少 2 件起轉（參考 C1 模式）
- 剩餘無法配對的數量一律退回 D001（無數量限制）
- 精簡SKU(跨OM) 額外規則：Windy 只轉 Windy，HD 不能轉到 HA/HB/HC

#### F/F2 模式改善
- **Target 接收店舖不論 ND 或 RF 均可接收**（打破 ND 不可接收的全局限制）
- **Target 數量直接作為接收量**（`needed_qty = Target Qty`，不考慮現有庫存與在途數量）
- 現行邏輯：`needed_qty = Target - (SaSa Net Stock + Pending Received)`，僅 RF 可接收
- 改善後：`needed_qty = Target`，ND/RF 均可接收
- 非 Target 店舖邏輯不變（F 模式：RF 補0；F2 模式：不接收）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 版本升級至 v2.10.0（二十四模式系統）
  - 新增 `mode_simplified_sku_same`、`mode_simplified_sku_cross` 常數
  - 新增 `_is_simplified_sku_mode()` 家族判斷
  - `identify_sources`：新增精簡SKU模式 ND 全轉出 + RF 超出 Cap 轉出邏輯
  - `identify_destinations`：新增精簡SKU模式 RF 接收上限邏輯
  - 新增 `_match_transfers_simplified_sku()` 專用匹配方法（Phase 1: RF-to-RF 配對，Phase 2: 剩餘退回 D001）
  - `generate_transfer_recommendations`：新增精簡SKU模式到驗證白名單與跨OM分組
  - `_create_recommendation_note`：新增精簡SKU模式 Notes 文案
- [`app.py`](app.py)
  - 版本升級至 v2.10.0（二十四模式系統）
  - 側欄模式選單新增 `精簡SKU(限同OM)`、`精簡SKU(跨OM)`
  - `mode_name_map`、模式說明、欄位要求同步更新
  - 核心功能說明新增精簡SKU模式
- [`excel_generator.py`](excel_generator.py)
  - 更新 docstring：二十四模式系統

#### 文件同步
- [`README.md`](README.md)
  - 系統概述改為二十四模式
  - 模式對照表新增精簡SKU(限同OM)、精簡SKU(跨OM) 行
  - F/F2 模式描述更新
  - 補回 D2 模式描述
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 標題改為「二十四種調貨模式詳解」
  - 新增精簡SKU(限同OM)、精簡SKU(跨OM) 完整說明段落
  - F/F2 模式接收規則更新（ND/RF 均可接收、Target 直接作為接收量）
  - 關鍵差異對比表新增精簡SKU 列
  - 應用場景建議新增精簡SKU 說明
  - 轉出/接收分類類型新增精簡SKU
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 新增精簡SKU(限同OM)、精簡SKU(跨OM) 模式說明
  - 更新 Mode F / Mode F2 的 Destination rules

---

## v2.9.1 (2026-04-27)

### 正式加入 C1 模式（重點補0-只補0/1）

#### C1 模式核心規則
- 參照 C 模式，但**僅處理 total_available ≤ 1 的店舖**（重點補0）
- **不回落**到一般缺貨補貨（緊急缺貨、潛在缺貨）分支
- 轉出門檻提高：`SaSa Net Stock > 2` 才可轉出（C 模式僅要求 total_available > Safety Stock）
- 轉出量下限提高：至少 2 件才參與配對（C 模式最少 1 件），避免低效的單件來源
- 來源排序：優先使用可轉量較大的來源（按 transferable_qty 降序），減少拆單

#### 與 C 模式的差異
| 項目 | C 模式 | C1 模式 |
|------|--------|---------|
| 接收類型 | 重點補0 + 緊急缺貨 + 潛在缺貨 | **僅** 重點補0 |
| 轉出門檻 | total_available > Safety Stock | SaSa Net Stock > 2 |
| 轉出量下限 | 至少 1 件 | 至少 2 件 |
| 來源排序 | 標準排序 | 優先可轉量較大者 |
| 適用場景 | 全面補低庫存 | 精準只補零庫存/1件 |

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - C1 模式常數與邏輯早已存在於代碼中（`mode_c1`），本次僅更新 docstring
  - 更新模組 docstring：二十一模式 → 二十二模式系統
- [`app.py`](app.py)
  - 側欄模式選單新增 `C1: 重點補0(只補0/1)`
  - `mode_name_map` 新增 C1 對應
  - `mode_descriptions` 新增 C1 說明
  - 欄位提示群組新增 C1（與 C/C2/D/D2 共用基本欄位）
  - 更新 docstring：二十一模式 → 二十二模式系統
- [`excel_generator.py`](excel_generator.py)
  - 更新 docstring：十八模式 → 二十二模式系統（含 C1）

#### 文件同步
- [`README.md`](README.md)
  - 系統概述改為二十二模式
  - 功能重點更新
  - 模式對照表新增 C1 行
  - 介面操作流程更新
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
  - 標題改為「二十二種調貨模式詳解」
  - 新增 C1 模式完整說明段落
  - 關鍵差異對比表新增 C1 列
  - 應用場景建議新增 C1 說明
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)
  - 模式總覽新增 C1
  - 新增 C1 模式說明段落

---

## v2.9.0 (2026-04-24)

### 新增 B2L/B2La/B3L/B3La（Type=L 低銷量保留2件）

#### 新模式核心規則
- 新增四個 B-special L 系列模式：`B2L`、`B2La`、`B3L`、`B3La`
- **僅新 L 系列**套用 Type=L 低銷量保留2件：
  - 條件：`Type=L` 且 `max(Last Month Sold Qty, MTD Sold Qty) <= 2`
  - 轉出量：`max(SaSa Net Stock - 2, 0)`
  - 當淨庫存 `<= 2` 時不轉出
- 舊模式 `B2/B2a/B3/B3a` 維持原行為（Type=L 低銷量全轉出）
- `B2La/B3La` 延續 a 系列限制：`Type=T` 不可作為出貨來源
- `B3L/B3La` 延續跨 OM 家族限制：HD/Windy 規則不變

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增四個模式常數與家族判斷
  - Type=L 低銷量特例新增「保留2件」分支（僅 L 系列）
  - 模式白名單、跨 OM 分組/分支與備註文案同步
- [`app.py`](app.py)
  - 側欄模式選單新增 B2L/B2La/B3L/B3La
  - 接收店數限制適用模式清單、模式描述、欄位要求與 Type 欄位驗證同步
  - `mode_name_map` 新增四模式對應
- 文件同步
  - [`README.md`](README.md)
  - [`調貨模式詳解.txt`](調貨模式詳解.txt)

#### 測試同步
- [`tests/test_b_special_mix_sales_guard.py`](tests/test_b_special_mix_sales_guard.py)
  - Mix 高銷量保護測試納入四新模式
- [`tests/test_b2a_b3a_t_no_source.py`](tests/test_b2a_b3a_t_no_source.py)
  - 新增 B2La/B3La Type=T 不可 source 測試
- [`tests/test_b2_b3_source_receive_site_limit.py`](tests/test_b2_b3_source_receive_site_limit.py)
  - 新增 B2L/B2La/B3L/B3La 接收店數上限測試
- [`tests/test_all_modes_comprehensive.py`](tests/test_all_modes_comprehensive.py)
  - 新增 B-L 系列整合測試（保留2件、邊界庫存、跨OM、a系列限制）

---

## v2.8.0 (2026-04-08)

### 新增 D2 模式（清貨轉貨ND限定）

#### D2 模式核心規則
- 按照 D 模式邏輯，但**僅 ND Shop 轉出，RF Shop 只做接收不做轉出**
- 僅針對無銷售記錄（Last Month Sold Qty = 0 且 MTD Sold Qty = 0）的 ND 店舖清貨轉出
- 有銷售記錄的 ND 店舖在 D2 模式下也不轉出（與 D 模式不同）
- RF 店舖完全不進入轉出候選，只作為接收方
- 仍限制同一 OM 內配對
- 繼承 D 模式的避免 1 件餘貨邏輯

#### 與 D 模式的差異
| 項目 | D 模式 | D2 模式 |
|------|--------|---------|
| ND 清貨轉出（無銷售） | ✅ | ✅ |
| ND 轉出（有銷售） | ✅ | ❌ |
| RF 過剩轉出 | ✅ (A模式規則) | ❌ |
| RF 接收 | ✅ | ✅ |

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增 `mode_d2 = "清貨轉貨(ND限定)"`
  - 新增 `_is_d_family_mode()` 共用 D/D2 邏輯判斷
  - `identify_sources`：D2 模式跳過所有 RF 轉出源，ND 僅清貨轉出
  - `identify_destinations`：D/D2 共用放寬接收條件
  - `_match_by_priority`：D/D2 共用避免 1 件餘貨邏輯
  - `_create_recommendation_note`：D2 使用 D2 標籤
  - `generate_transfer_recommendations`：新增 mode_d2 到驗證白名單
- [`app.py`](app.py)
  - 側邊欄新增 `D2: 清貨轉貨(ND限定)`
  - `mode_name_map`、模式說明同步更新
- 測試：D2 已納入 `test_all_modes_comprehensive.py`、`test_modes_simple.py`、`test_all_modes_no_dual_role.py` 模式清單

#### 文件同步
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)

---

## v2.7.0 (2026-03-30)

### 新增 F2 模式（F指定模式）

#### F2 模式核心規則
- 僅 `Target > 0` 的 RF 店舖可以接收
- 非 Target RF 店舖不再走補 0 接收流程
- 保留 F 模式的跨 OM 配對能力與 HD 限制（HD 不可轉到 HA/HB/HC）
- 轉出邏輯沿用 F 模式（ND 可全轉出；RF 保護最高銷量店）

#### 程式碼更新
- [`business_logic.py`](business_logic.py)
  - 新增 `mode_f_target_only = "F指定模式"`
  - `identify_sources` / `identify_destinations` / `match_transfers` / `generate_transfer_recommendations` 納入 F2 分支
  - F2 接收類型新增 `F指定模式目標接收`
- [`app.py`](app.py)
  - 側邊欄新增 `F2: F指定模式`
  - `mode_name_map`、模式說明、欄位要求與前置警示同步更新
- [`tests/test_all_modes_comprehensive.py`](tests/test_all_modes_comprehensive.py)
  - 新增 F2 僅 Target 接收測試
- [`tests/test_modes_simple.py`](tests/test_modes_simple.py)、[`tests/test_all_modes_no_dual_role.py`](tests/test_all_modes_no_dual_role.py)
  - 將 F2 納入模式清單

#### 文件同步
- [`README.md`](README.md)
- [`調貨模式詳解.txt`](調貨模式詳解.txt)
- [`transfer_logic_ai_brief.md`](transfer_logic_ai_brief.md)

---

## v2.6.0 (2026-03-20)

### 新增 ND1/ND2 模式（ND 調貨）

#### ND1 模式（ND 同 OM 轉貨）
- ND 店舖可互相調貨，限同一 OM 組別及同一 Article
- 打破「ND 不可接收」全局規則（ND1/ND2 模式例外）
- 轉出排序：過去2個月銷量=0 優先 → 最低銷量次選 → 最高銷量保護
- 接收優先級 1：RF 緊急缺貨（零庫存有銷售記錄）
- 接收優先級 2：ND 潛在缺貨（按過去2個月銷量降序）
- 接收上限：2 × (Last Month Sold Qty + MTD Sold Qty)；銷量=0 不可接收

#### ND2 模式（ND 混合 OM 轉貨）
- 繼承 ND1 所有算法邏輯，但允許跨 OM
- Windy（澳門）轉出只能到 Windy；HD 不能轉到 HA/HB/HC

#### 技術架構
- [`business_logic.py`](business_logic.py)：`mode_nd1`/`mode_nd2` 常數、`_is_nd_transfer_mode()`、`_match_transfers_nd_mode(cross_om)` 共用核心
- [`perform_quality_checks(mode)`](business_logic.py) 新增 `mode` 參數，ND 模式豁免 ND 接收檢查
- [`app.py`](app.py)：新增兩個模式選項、說明、`mode_name_map`
- [`tests/test_nd_modes.py`](tests/test_nd_modes.py)：14 個單元測試，全部通過

---

## v2.5.0 (2026-03-11)

### 新增功能：所有模式後處理 — 避免單筆1件調貨

**核心改動：** 在 `generate_transfer_recommendations` 最後一步，加入通用後處理，對所有 13 個模式的輸出結果統一執行「避免單筆1件調貨」優化。

#### 規則說明
- **目標**：所有模式輸出中，同一出貨店舖（Transfer Site）同一 SKU（Article）的每筆調貨數量，不應出現 `Transfer Qty = 1`。
- **例外**：若該出貨店舖對該 SKU 的可調總量本身就只有 1 件，則允許保留（無法再重新分配）。
- **不影響** D 模式餘貨邏輯（D 模式處理的是「轉出後剩餘庫存」，本後處理處理的是「每筆調貨數量」，兩者互補）。

#### 兩種優化策略（依序嘗試）
1. **Rebalance（重新平衡）**：若同群組內有其他目標店數量 ≥ 3，從中取 1 件給單件店舖，使其變為 2 件，施方維持總量不變。
2. **Merge（合併）**：若無法 Rebalance（例如僅有 2+1 的情況），將 1 件合併至「接收店舖總銷量（Last Month + MTD）最高」的目標店，並移除原單件行。

#### 新增方法（`business_logic.py`）
| 方法名稱 | 用途 |
|----------|------|
| `_get_record_sales_total(rec, prefix)` | 計算某紀錄的 Last Month + MTD 總銷量 |
| `_refresh_recommendation_fields(recommendations, mode)` | 調整數量後重新計算 After Transfer Stock、Cumulative Received Qty、Notes 欄位 |
| `_optimize_single_piece_transfers(recommendations, mode)` | 主後處理函式：偵測並消除單件調貨記錄 |

#### 新增測試（`tests/test_single_qty_optimization.py`）
- `test_optimize_single_qty_rebalance_to_avoid_one_piece`：驗證 11+1 → 10+2 的 Rebalance 情境
- `test_optimize_single_qty_merge_to_higher_sales_destination`：驗證 2+1 → 3（合併至高銷量目標店）情境

#### 實際效果驗證
- `100008801001 / HA42`：(HA32:11, HA44:1) → (HA32:10, HA44:2) ✅
- `100314808024 / HC62`：(HC49:2, HC61:1) → (HC49:3) ✅

---

## v2.4.1 (2026-02-25)

### B 特別模式規則更新（2026-02-25）
- 新增 B2/B2a/B3/B3a 的 **Mix 店舖高銷量保護**：
  - 若出貨店舖為 Type=M（Mix），且其總銷量高於目標店舖總銷量，取消該配對。
  - 總銷量口徑統一為：**Last Month Sold Qty + MTD Sold Qty**。
- 已將上述規則同步至 App 介面與說明文件，確保系統行為與文件描述一致：
  - `app.py`（模式說明、欄位提示、核心功能文案）
  - `README.md`
  - `調貨模式詳解.txt`
  - `transfer_logic_ai_brief.md`

### 程式碼審查與清理
- 進行全面的程式碼審查
- 建立 .gitignore 檔案以排除不必要的檔案
- 從版本控制中移除大型 Excel 檔案
- 修正版本號不一致問題

### 專案結構優化
- 計劃重構 business_logic.py 為較小的模組
- 建立適當的目錄結構（tests/, debug/, legacy/）

---

## v2.3.0 (2026-02-10)

### 新增功能
- **新增 C2 模式（附加C跨OM重點補0）**：
  - 參照 C 模式的轉出/接收邏輯（重點補0）
  - 允許跨 OM 配對（分組僅按 Article，不按 OM）
  - **HD 限制**：HD 店鋪不能轉到 HA/HB/HC
  - **Windy 限制**：Windy 轉出只能到 Windy 的店鋪（Windy 可接收其他 OM）
  - 升級系統為九模式系統：A/B/B2/B3/C/C2/D/E/F

### 業務邏輯更新
- **C2 模式（附加C跨OM重點補0）**：
  - 轉出條件：完全沿用 C 模式（30% 上限 / 3 件上限 / 至少 1 件）
  - 接收條件：完全沿用 C 模式（total_available <= 1 的重點補0）
  - 目標數量：min(Safety Stock, MOQ + 1)
  - 跨 OM 配對：分組僅按 Article，不按 OM
  - HD 限制：HD 店鋪不能轉到 HA/HB/HC
  - Windy 限制：Windy 轉出只能到 Windy，但 Windy 可接收其他 OM

### 技術更新
- 更新 `business_logic.py` (v2.3.0)：
  - 新增 `mode_c2 = "附加C2(跨OM重點補0)"` 常量
  - 修改 `identify_sources` 方法：C2 模式使用 C 模式的轉出邏輯
  - 修改 `identify_destinations` 方法：C2 模式使用 C 模式的接收邏輯
  - 新增 `_match_transfers_c2_mode` 專用匹配方法，實現跨 OM 配對邏輯
  - 更新 `generate_transfer_recommendations`：將 C2 加入跨 OM 模式列表和驗證
  - 更新文檔字串為九模式系統

- 更新 `app.py` (v2.3.0)：
  - 更新頁面標題為 "庫存調貨建議系統 v2.3.0"
  - 增加 C2 模式選項與說明
  - 更新模式名稱轉換邏輯，支持 C2 模式
  - 更新系統資訊，添加 C2 模式特殊功能說明

- 更新 `excel_generator.py` (v2.3.0)：
  - 更新文檔字串為九模式系統

- 更新 `README.md`：
  - 系統概述改為九模式系統
  - 功能特點新增 C2 描述
  - 模式對比表新增 C2 列
  - 使用說明新增 C2 模式行
  - 業務邏輯詳解新增 C2 模式完整說明

### 與 C 模式的差異
| 項目 | C 模式 | C2 模式 |
|------|--------|---------|
| 轉出邏輯 | 30% 上限 / 3 件上限 | 同 C 模式 |
| 接收邏輯 | total_available <= 1 | 同 C 模式 |
| 分組方式 | Article + OM | 僅 Article |
| 跨 OM 配對 | ❌ 不允許 | ✅ 允許 |
| HD 限制 | N/A | ✅ HD 不能轉到 HA/HB/HC |
| Windy 限制 | N/A | ✅ Windy 轉出只能到 Windy |

### 重要說明
- C2 模式的轉出/接收邏輯完全沿用 C 模式，差異僅在於允許跨 OM 配對
- HD/Windy 限制規則與 B3/E/F 模式一致
- C2 模式適用於需要跨 OM 重點補0的場景

---

## v2.2.2 (2026-02-10)

### 新增功能
- **新增 B3 模式（附加B跨OM特別模式）**：
  - 參照 B2 規則（Type=L 全轉出、接收上限 2 倍安全庫存、接收優先排序）
  - 允許跨 OM 配對
  - **HD 限制**：HD 店鋪不能轉到 HA/HB/HC
  - **Windy 限制**：Windy 轉出只能到 Windy（Windy 可接收其他 OM）

### 技術更新
- 更新 `business_logic.py`：
  - 新增 `mode_b3` 並支援跨 OM 分組
  - 在匹配階段加入 Windy/HD 限制
  - B2/B3 共用接收上限與優先排序
- 更新 `app.py`：
  - 增加 B3 模式選項與說明
  - B2/B3 共用 Type 欄位檢查
- 更新 `README.md`：
  - 補充 B3 模式規則與使用說明

---

## v2.2.1 (2026-02-10)

### 業務邏輯更新
- **B2 接收優先級**：
  - 依 Type T (遊客區店舖) / Type M (混合型店舖) 分層排序
  - 先比合計銷量 (MTD + Last Month)，再比 Safety Stock

### 輸出說明更新
- **Excel 接收類型文字**：
  - Type T → 遊客區店舖
  - Type M → 混合型店舖

### 測試
- 新增 `test_b2_priority.py`，驗證 B2 接收優先排序

---

## v2.2.0 (2026-02-09)

### 新增功能
  - 將 stores-template.csv 的 85 間店舖資料直接寫入程式內
  - 當用戶上傳的 Excel 缺少 OM 或 Type 資料時，系統會根據 Site 自動填充預設值
  - 如果用戶有自己的資料，系統會優先使用，不會覆蓋

### 業務邏輯更新
- **預設店舖資料**：
  - 包含 85 間店舖的預設資料（HA02-HD20）
  - 資料欄位：Site、Shop、Regional、Class 1、Class 2、Size、OM、Type
  - HK 區域：77 間店舖
  - MO 區域：8 間店舖
  - OM 分佈：Ivy、Violet、Queenie、Candy、Hippo、Eva、Windy

### 技術更新
- 更新 `data_processor.py`：
  - 新增 `DEFAULT_STORE_DATA` 常量，包含 85 間店舖的預設資料
  - 新增 `get_store_default_info(site)` 方法，根據店舖編號查詢預設資料
  - 新增 `fill_default_store_data(df)` 方法，批量填充缺失的 OM 和 Type
  - 修改 `preprocess_data()` 方法，在數據類型轉換後調用填充方法
  - 新增 `fill_stats` 統計，記錄填充的筆數和找不到的店舖

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v2.2.0"
  - 更新系統資訊，添加「預設店舖資料自動填充」功能說明

### 使用場景
1. **用戶上傳的 Excel 有完整的 OM 和 Type 資料**：系統使用用戶提供的資料，不進行覆蓋
2. **用戶上傳的 Excel 缺少 OM 或 Type 資料**：系統根據 Site 欄位自動從預設資料中填充
3. **用戶上傳的 Excel 有部分 OM 或 Type 資料**：系統只填充缺失的欄位，已有資料不被覆蓋

### 重要說明
- 預設資料應定期更新以反映店舖資訊變更
- 如果需要更新預設資料，需要修改程式碼並重新部署
- 系統會記錄哪些資料是從預設值填充的（可在日誌中查看）

---

## v2.1.1 (2026-01-30)

### 新增功能
- **新增F模式：目標優化**
  - 針對Target欄位填數字作為優先接收目標
  - 其他店鋪按C模式補0需求計算
  - 支持跨OM配對，HD不能轉到HA/HB/HC
  - 更新系統為六模式系統：A/B/C/D/E/F

### 業務邏輯更新
- **F模式(目標優化)**：
  - 轉出條件：
    - ND類型：全數轉出
    - RF類型：可忽視最小庫存要求，但保護最高銷量店鋪
  - 轉出類型：F模式ND轉出 / F模式RF轉出
  - 接收條件：
    - Target數字：優先接收目標
    - 未標Target的店鋪：按C模式重點補0
  - 優先級邏輯：
    - Target數字優先接收
    - 其他店鋪按C模式補0需求計算
  - HD限制：
    - HD店鋪的轉出絕對不能到HA/HB/HC店鋪

### 技術更新
- 更新 `data_processor.py`：
  - 在 optional_columns 中添加 'Target' 欄位
  - 修改 `read_excel_file` 方法，能夠讀取並標準化 *Target* 欄位
  - 自動創建空 Target 欄位（若上傳文件中不存在）
  - 添加日誌記錄 *Target* 欄位的識別狀態

- 更新 `business_logic.py`：
  - 添加 `self.mode_f = "目標優化"`
  - 修改 `identify_sources` 方法，添加F模式的轉出識別邏輯
  - 修改 `identify_destinations` 方法，添加F模式的接收邏輯（Target優先+C模式補0）
  - 修改 `match_transfers` 方法，增加F模式路由到專用匹配方法
  - 新增 `_match_transfers_f_mode` 方法，實現F模式的Target優先和跨OM限制邏輯
  - 更新 `generate_transfer_recommendations` 方法的模式驗證，支持F模式
  - 更新所有相關方法的文檔字符串

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v2.1.1"
  - 更新模式選擇，添加 "F: 目標優化" 選項
  - 更新模式說明，添加F模式的詳細說明
  - 更新模式名稱轉換邏輯，支持F模式

### 重要說明
- *Target* 欄位識別不分大小寫，系統會自動標準化為 'Target'
- F模式上傳的Excel文件需要包含 *Target*、Target 或其他大小寫組合的欄位
- F模式下，Target數字優先接收，未標Target的店鋪會按C模式補0需求計算
- HD和其他OM的限制規則遵循客戶的業務規則：HD不能轉到同一OM集群的其他OM

---

## v1.9.9 (2026-01-29)

### 新增功能
- **新增E模式：強制轉出**
  - 針對標記為 *ALL* 的商品行進行全數強制轉出
  - 只有被標記為 *ALL* 的行才會成為轉出源
  - 接收店鋪限制為RF類型，接收上限為Safety Stock的2倍
  - 優先同OM配對，當該OM無法接收時放寬跨OM配對
  - HD店鋪絕對不能轉到HA/HB/HC的店鋪
  - 更新系統為五模式系統：A/B/C/D/E

### 業務邏輯更新
- **E模式(強制轉出)**：
  - 轉出條件：該行在 *ALL* 欄位中有任何非空白文字
  - 轉出數量：全數轉出（不考慮安全庫存）
  - 轉出類型：E模式強制轉出
  - 接收條件：
    - 只接收RF店鋪
    - 當前庫存(SaSa Net Stock + Pending Received) < Safety Stock × 2
    - 接收上限 = Safety Stock × 2
  - 優先級邏輯：
    - Phase 1：優先配對同OM的接收店鋪
    - Phase 2：當同OM無法接收時，放寬跨OM配對（但受HD限制）
    - **Phase 3：C模式回退** - 當其他OM未有店舖涉及強制轉出時，可按照C模式照常做重點補0
  - HD限制：
    - HD店鋪的轉出絕對不能到HA/HB/HC店鋪

### 技術更新
- 更新 `data_processor.py`：
  - 在 optional_columns 中添加 'ALL' 欄位
  - 修改 `read_excel_file` 方法，能夠讀取並標準化 *ALL* 欄位（不分大小寫）
  - 自動創建空 ALL 欄位（若上傳文件中不存在）
  - 添加日誌記錄 *ALL* 欄位的識別狀態

- 更新 `business_logic.py`：
  - 添加 `self.mode_e = "強制轉出"`
  - 修改 `identify_sources` 方法，添加E模式的強制轉出識別邏輯
  - 修改 `identify_destinations` 方法，添加E模式的接收邏輯（RF限制+上限為2倍Safety Stock）
  - 修改 `match_transfers` 方法，增加E模式路由到專用匹配方法
  - 新增 `_match_transfers_e_mode` 方法，實現E模式的優先級和跨OM限制邏輯
  - 更新 `generate_transfer_recommendations` 方法的模式驗證，支持E模式
  - 更新所有相關方法的文檔字符串

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v1.9.9"
  - 更新模式選擇，添加 "E: 強制轉出" 選項
  - 更新模式說明，添加E模式的詳細說明
  - 更新模式名稱轉換邏輯，支持E模式

### 重要說明
- *ALL* 欄位識別不分大小寫，系統會自動標準化為 'ALL'
- E模式上傳的Excel文件需要包含 *ALL*、ALL 或其他大小寫組合的欄位
- E模式下，只有被標記的行才會進行轉出，其他行被忽略
- HD和其他OM的限制規則遵循客戶的業務規則：HD不能轉到同一OM集群的其他OM

---

## v1.9.8 (2026-01-26)

### 新增功能
- **新增D模式：清貨轉貨**
  - 針對ND類型且無銷售記錄的店鋪進行清貨處理
  - 實現避免1件餘貨的特殊邏輯
  - 更新系統為四模式系統：A/B/C/D

### 業務邏輯更新
- **D模式(清貨轉貨)**：
  - 轉出條件：ND類型且 Last Month Sold Qty = 0 且 MTD Sold Qty = 0
  - 轉出類型：ND清貨轉出
  - 特殊規則：避免1件餘貨
    - 如果轉出後會剩餘1件，則嘗試多轉1件（使剩餘為0）
    - 若無法多轉，則少轉1件（使剩餘為2）
    - 確保轉出後剩餘庫存為0件或≥2件
  - 接收規則：遵循A模式(保守轉貨)的接收規則

### 技術更新
- 更新 `business_logic.py`：
  - 添加 `self.mode_d = "清貨轉貨"`
  - 修改 `identify_sources` 方法，添加D模式的ND清貨轉出識別
  - 修改 `_match_by_priority` 方法，添加避免1件餘貨的特殊處理
  - 修改 `_create_recommendation_note` 方法，添加ND清貨轉出的說明
  - 更新模式驗證邏輯，支持D模式
  - 更新所有相關方法的文檔字符串
  - 更新版本號至 v1.9.8

- 更新 `app.py`：
  - 更新頁面標題為 "庫存調貨建議系統 v1.9.8"
  - 更新模式選擇，添加 "D: 清貨轉貨" 選項
  - 更新模式說明，添加D模式的詳細說明
  - 更新模式名稱轉換邏輯，支持D模式
  - 更新操作指引，添加D模式的說明
  - 更新系統資訊，更新版本號和核心功能描述
  - 更新圖表顯示邏輯，支持D模式的ND清貨轉出類型

- 更新 `README.md`：
  - 更新系統概述，改為四模式系統
  - 更新功能特點，添加D模式特殊功能說明
  - 更新使用說明，添加D模式的說明
  - 更新業務邏輯詳解，添加D模式的完整說明
  - 更新更新日誌，添加v1.9.8的版本記錄

- 新增 `test_mode_d.py`：
  - 創建D模式專用測試腳本
  - 驗證ND清貨轉出邏輯的正確性
  - 驗證避免1件餘貨功能的有效性
  - 提供詳細的測試結果和統計分析

---

**開發者：Ricky**
**最後更新：2026-02-10**
