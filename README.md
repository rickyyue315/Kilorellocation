# KiLo 庫存調貨建議系統 v2.38.0

## 系統概述

KiLo 是基於 Streamlit 的庫存調貨建議系統，依據庫存、在途、銷量與安全庫存（或 Turnday 保底）自動產生跨店鋪調貨建議。`MOQ` 雖列為必需欄位，但目前不參與任何模式計算（不會按 MOQ 取整或補貨）。

系統目前為 **三十模式**：

- A：保守轉貨
- **A1：保守轉貨(轉出店舖不餘存貨1件)**
- B：加強轉貨
- B2：附加 B 特別模式
- B2a：附加 B2a（T 遊客鋪不出貨）
- B2L：附加 B2L（Type=L 低銷量保留 2 件）
- B2La：附加 B2La（Type=L 低銷量保留 2 件 + T 遊客鋪不出貨）
- B3：附加 B 跨 OM 特別模式
- B3a：附加 B3a（跨 OM + T 遊客鋪不出貨）
- B3L：附加 B3L（跨 OM + Type=L 低銷量保留 2 件）
- B3La：附加 B3La（跨 OM + Type=L 低銷量保留 2 件 + T 遊客鋪不出貨）
- C：重點補 0（每店轉出件數上限可調）
- C1：重點補 0（只補 0/1，可自訂門檻及每店轉出件數上限）
- C2：附加 C 跨 OM 重點補 0
- D：清貨轉貨
- **D2：清貨轉貨（ND 限定）**
- E1：強制轉出（僅同 OM）
- E1b：強制轉出（僅同 OM，優先類型接收）
- E2：強制轉出（可跨 OM）
- F：目標優化
- F2：F指定模式（僅 Target 店舖接收，可設定 HD 轉出選項；Windy 目標店優先從同 OM 無 Target 店提取）
- **F3：目標性補0（F2 + RF轉出保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級）**
- **NST：New Shop Target調貨（僅 Target 店舖接收，RF轉出保留≥2件 + 75%上限 + 庫存<3不轉出，可設定同一SKU轉出店數上限）**
- **ND1：ND 同 OM 轉貨（ND 店舖互轉，限同 OM）**
- **ND2：ND 混合 OM 轉貨（ND 店舖互轉，允許跨 OM）**
- **ND3：ND 限同 OM 轉貨（補 0）（ND 同 OM 轉貨，轉出保留 3 件，只補零庫存 ND 店）**
- **ND4：ND 限同 OM 轉貨（補 0 及有銷售記錄）（ND 同 OM 轉貨，無銷量來源店不保留全數轉出，有銷量來源店保留 3 件，只補有銷售記錄的零庫存 ND 店）**
- **精簡SKU（限同OM）：超出 Cap 轉出，僅同 OM；可選擇剩餘庫存退回 D001 或留在店舖**
- **精簡SKU（跨OM）：超出 Cap 轉出，允許跨 OM**
- **精簡SKU（退D001）：RF 超出 Cap 全數回退 D001，ND 全數回退 D001，不配對接收**

## 核心規則

- **保底主體（Safety / Turnday，v2.32.0 新增）**：側邊欄二選一，與全部 30 個模式任意組合（2 主體 × 30 模式）。
  - `Safety Stock（現行版本）`：沿用上載檔案的 Safety Stock 做保底（預設，行為與以往完全一致）。
  - `Turnday（日均銷量×日數）`：保底 = ceil(日均銷量 × 自選日數 N，3–60 日，預設 14）；日均銷量 = Effective Sold Qty ÷ 覆蓋日數；覆蓋日數 = 上月日數 + MTD 數據日期日號（數據日期於上載區輸入，通常 T-1，例：8月15日 = 7月31日 + 15日 = 46日）。所有 Safety 觸點（轉出保底、緊急/潛在缺貨目標、補0目標 Safety×0.5、接收上限 Safety×2、精簡SKU Cap）自動切換至 Turnday 基準；零銷量 SKU 保底為 0（可全數轉出）；原 Safety 值備份於 `Original Safety Stock`。
  - 不受主體影響的固定保底：C1（淨存>2）、F3/NST（保留2件、75%上限）、ND3/ND4（保留3件）維持原狀；Turnday 只改變各模式中讀取 Safety Stock 的公式。
- ND 店舖預設只可轉出、不可接收；例外：**ND1/ND2/ND3/ND4**（ND 互轉）、**F/F2/F3/NST**（有 Target 的 ND 店可接收）。ND 來源在所有模式均為「淨庫存全轉」，不受 A/B/C 的百分比上限限制。
- RF 最高有效銷量店舖受保護，不會被選為轉出方。
- 同一 SKU 下，轉出店舖不可同時為接收店舖。
- D 模式會調整轉移量，避免轉出後剛好剩 1 件。D 對所有 ND（不論有無銷量）都會全數轉出，只有 D2 限定「無銷量 ND」。
- **D2 模式新增 UI 選擇鍵（3 選 1）**：可切換「不限店舖數量（原有設定）」、「限制2間店舖接收（原有設定）」、「限制2間店舖接收（優化版）」。優化版限制每間 ND 轉出源最多配對 2 間 RF 接收店，並將接收量放大至 200%；原有設定版限制店數但 target_qty 為正常值。
- **單件後處理（D/D2 除外）**：避免單筆調貨數量為 1 件（例外：若出貨店舖該 SKU 可調總量本身只有 1 件則保留）。D 家族刻意保留 1 件線，以維持「清空或剩 ≥2」的餘貨邏輯。
- E1/E1b/E2 僅處理 `ALL` 欄位有標記的行（只檢查非空，填 `0` 亦會觸發；要保留請留空）。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La：若出貨店為 Type=M（Mix）且其總銷量高於目標店，該配對會被取消（`總銷量 = Last Month Sold Qty + MTD Sold Qty`）。
- B3/C2/E2/F/精簡SKU(跨OM) 的跨 OM 規則：
  - HD 來源不可轉到 HA/HB/HC。
  - Windy 來源僅可轉到 Windy。
- F2/F3/NST 跨 OM 規則：
  - 預設 HD 來源不可轉到 HA/HB/HC；可切換為「HD 可轉出（最後優先）」，此時 HD 來源排在最低優先級，僅在其他來源不足時才使用。
  - Windy 來源僅可轉到 Windy。
  - **Windy 目標店（有 Target）優先從其他無 Target 的 Windy 店舖提取**；若 Windy 來源不足，才回落至非 Windy 來源。
- F3 額外規則：
  - RF 轉出後保留 2 件（net_stock > 2 才可轉出，轉出量 = net_stock - 2）
  - RF 按最高庫存優先轉出（同優先級內銷量最低優先）
  - RF 跨 OM 不降級（同 OM / 跨 OM 同等優先）
- **NST 額外規則**：
  - RF 轉出後保留 ≥2 件（net_stock - 2）
  - RF 轉出上限為庫存的 75%（轉出量 = min(net_stock × 0.75, net_stock - 2)）
  - RF 庫存 < 3 件不轉出
  - 可設定同一 SKU 轉出店舖數量上限（10 間 / 20 間 / 不限制）
  - 因 RF 轉出限制，目標可能未達 100%，此為預期行為
- **F/F2/F3/NST 模式 Target 接收**：Target 數量是「追加接收量」，不是「補至量」（現有 2、Target 6 → 再收 6，最終 8）；不考慮現有庫存與在途，Target 店舖不論 ND/RF 均可接收。
- **F2/F3/NST 全域 Target 保護**：只要某店在任何 Article 有 Target>0，該店全部 SKU 都不可作來源（F 只按同一 Article 的 Target 行跳過，沒有全域保護）。
- **F/F2/F3/NST 模式新增「優先滿足小型目標」選項**：勾選後 Priority-1 目標店按 needed_qty 升序排序（小型目標優先），最大化達成目標數量。
- **F/F2/F3/NST 模式配對後缺口填補**：主要配對完成後，若有剩餘來源庫存，自動分配給尚未滿足的目標店。
- **F/F2/F3 模式新增「Target達成分析」Excel 工作表**：顯示每組 (Article, Site) 的目標量、實際接收量、差距、達成狀態，以及整體 KPI（總目標數、達成數、達成率、總差距）。
  - v2.36.0 修正：只計**使用者設定 Target** 的接收點；系統自動補0的「重點補0」接收點不列入本表，其缺口以「調貨缺口分析」為準（避免同一店在兩表出現「已滿足 vs 未達成」的矛盾）。

## 功能重點

- 三十模式調貨策略。
- **保底主體 × 模式矩陣（v2.32.0）**：Safety Stock（現行版本）或 Turnday（日均銷量×自選日數）兩種保底主體，可與全部 30 個調貨模式任意組合；Turnday 主體下上載區需輸入 MTD 數據日期（通常 T-1）以計算日均銷量，並顯示覆蓋日數核對。
- **模式教學分頁**：嵌入「30 模式邏輯審查」完整文件（流程圖、可重跑範例、不能處理的情景、審查發現），涵蓋全部 30 種模式。
- **C/C1/C2 模式新增 UI 選擇鍵**：可在側邊欄設定每店轉出件數上限（3~10件，預設 3），調整 C/C1/C2 模式的源店分散程度。提高每店轉出上限可減少調出店舖總數量。
- **D2 模式新增 UI 選擇鍵（3 選 1）**：可在側邊欄切換「不限店舖數量（原有設定）」、「限制2間店舖接收（原有設定）」或「限制2間店舖接收（優化版）」。其中限制版限制同一 SKU 各 ND 轉出源最多配對 2 間 RF 接收店；優化版另將接收量放大至 200%，原有設定版維持正常接收量。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La 可在介面設定「單一出貨店舖最多配對接收店舖數」：`優先 1 間` / `最多 2 間` / `不限制`。
- B2/B2a/B2L/B2La/B3/B3a/B3L/B3La Mix 高銷量保護：避免高銷售 Mix 店舖被轉去較低銷售店舖。
- **單筆1件調貨後處理（D/D2 除外）**：所有其他模式輸出後統一消除單件調貨，優先重新平衡（Rebalance），次選合併至高銷量目標店（Merge）。
- **精簡SKU模式**：RF 超出 Cap（Max(Safety×2, 過去2個月銷量×2)）部分轉出，ND 全轉出，剩餘退回 D001。
- **精簡SKU(限同OM) 剩餘庫存選項**：側邊欄可選「退回 D001（預設）」或「不退 D001（留在店舖）」。選「不退 D001」時只輸出店與店之間的調貨建議，配對後的剩餘庫存留在來源店舖，不產生退回 D001 的建議；跨 OM 及退D001 模式不受此選項影響。
- **精簡SKU(退D001)特殊規則**：完全不配對，所有可轉量直接退 D001；只剩 1 件時不退（RF 與 ND 相同），`Supply source` 為 1 或 4 亦不退。
- **F/F2/F3/NST Target 改善**：Target 數量作為追加接收量，不論 ND/RF 均可接收，不考慮在途；F2/F3/NST 另有 Target 店全 SKU 全域保護。新增「優先滿足小型目標」選項、配對後缺口填補、Target達成分析工作表。
- 自動資料預處理（型別轉換、缺值補齊、異常校正）。
- 內建店舖預設資料（缺少 OM/Type 時自動補值）。
- 輸出 Excel（調貨建議 + 統計摘要）。
- **優先級分組**：所有調貨建議按 🔴高優先 / 🟡中優先 / 🟢低優先 自動分組，優先處理高件數、強制轉出、退 D001 等重要建議。

## 系統需求

- Python 3.11–3.14（Community Cloud 目前預設 3.14，可直接部署；本機與 CI 驗證於 3.13／3.14）
- 依賴（版本見 `requirements.txt`）：`pandas`、`numpy`、`openpyxl`、`python-calamine`、`streamlit`、`pyarrow`、`altair`、`xlsxwriter`、`ftfy`
- ⚠️ **altair 必須與 Python 版本配對**：`altair` 5.5.x 在 Python 3.14 匯入即失敗
  （`_TypedDictMeta.__new__() got an unexpected keyword argument 'closed'`，圖表步驟會整個掛掉）。
  `requirements.txt` 已用環境標記分流（`<3.14` → 5.5.0、`>=3.14` → 6.0.0），
  請一律用 `pip install -r requirements.txt` 安裝，不要手動指定 altair 版本。

## 安裝與執行

### Windows

1. 雙擊 `run_system.bat`（使用專案內 `.venv\Scripts\python.exe` 啟動，port 8501）。
1. 若 `.venv` 不存在或依賴缺漏，先依下方「手動安裝」建立環境。

### Linux / macOS

1. 在專案根目錄執行：

```bash
chmod +x run.sh
./run.sh
```

1. 系統會建立虛擬環境並安裝依賴。
1. 自動啟動 Streamlit。

### 手動安裝

1. 建立並啟用虛擬環境（`run_system.bat` 讀的是 `.venv`，名稱請保持一致）：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

1. 安裝依賴：

```bash
pip install -r requirements.txt
```

1. 啟動應用：

```bash
streamlit run app.py
```

預設網址：`http://localhost:8501`

## Streamlit Community Cloud 部署（share.streamlit.io）

本專案為標準 Streamlit 應用，**不需要 Docker**：Community Cloud 直接讀取 `requirements.txt`（安裝依賴）、`.streamlit/config.toml`（介面與伺服器設定）與 `app.py`（進入點）。

### 部署步驟

1. 登入 <https://share.streamlit.io>，於右上角點 **Create app** → 「Yup, I have an app」。
2. 填入 Repository（`rickyyue315/Kilorellocation`）、Branch（`main`）、Main file path（`app.py`）。
3. 點 **Advanced settings**：
   - **Python version**：維持平台預設即可（本專案支援 3.11–3.14，含 Community Cloud 預設的 3.14）；想與本機一致可選 3.13。
   - **Secrets**（選用）：可直接貼上 `.streamlit/secrets.toml.example` 的內容。
4. 點 **Deploy!**；之後每次 push 到 `main` 分支都會自動重新部署（依賴變更需數分鐘重新安裝）。

### 部署注意事項

1. **Python 版本**：本專案鎖定的套件在 **3.11–3.14** 都有預編譯 wheel，直接使用 Community Cloud 預設版本即可。
   - 歷史坑（v2.38.1 已修正）：`streamlit 1.51` 以前限制 `pyarrow<22`，而 `pyarrow 21` 沒有 cp314 wheel，在 Python 3.14 上會退回原始碼編譯 Arrow C++ 而失敗（`error: command 'cmake' failed`）。現已升級至 `streamlit==1.52.2`（移除 pyarrow 上限）並鎖定 `pyarrow==22.0.0`（cp310–cp314 wheel）。
   - 註：Community Cloud **不會**採用 `runtime.txt` 或 `.python-version`，Python 版本只能在部署精靈的 Advanced settings 選擇，且部署後無法更改（需刪除 App 後以相同 subdomain 重新部署）。
   - 若 App 已是「建置失敗」狀態，**不需要刪除 App**：push 修正後於 App 右上角 **Manage app → Reboot** 即會重新安裝依賴。
2. **依賴安裝**：`requirements.txt` 版本已鎖定並通過測試（`streamlit==1.52.2`、`pyarrow==22.0.0`、`altair==5.5.0`）；無需 `packages.txt`（全部套件皆有 Linux wheel，無需 apt 套件、無需 cmake）。
3. **設定覆寫**：Community Cloud 會強制覆寫 `showErrorDetails`、`fastReruns`、`runOnSave`、`enableXsrfProtection`、`gatherUsageStats`；其餘 `.streamlit/config.toml` 設定（主題、`maxUploadSize = 50`）照常生效。
4. **上載大小**：`maxUploadSize` 已對齊應用層 50MB 上限，避免大型暫存造成容器記憶體壓力。
5. **雲端效能模式**：偵測到雲端環境（`/mount/src` 掛載路徑、`STREAMLIT_CLOUD` 或 Zeabur 舊環境變數）時，**所有大型表格**（調貨建議表、優先級分組表、缺口分析表）預設只渲染前 1,000 列並提供「載入完整…」勾選項；統計與 Excel 匯出仍使用全量資料。
6. **雲端資源防護（免費方案約 1GB RAM、共享 CPU）**：

   | 機制 | 雲端預設 | 本機 | 說明 |
   | --- | --- | --- | --- |
   | 單檔上載上限 | **8MB** | 50MB | 讀檔前即擋下；由 `KILO_CLOUD_MAX_UPLOAD_MB` 調整 |
   | 列數上限 | **120,000 行** | 無限制 | 讀檔後立即檢查並顯示明確訊息；由 `KILO_CLOUD_MAX_ROWS` 調整（`0` = 不限制） |
   | 結果表預覽 | 1,000 列 | 全量 | 由 `KILO_CLOUD_RESULT_PREVIEW_LIMIT` 調整 |
   | 快取上限 | `max_entries=2` | 同 | 避免多次上載的 DataFrame 累積佔用記憶體 |

   實測參考（純 Python、未含 Streamlit server 開銷）：2 萬行 ≈ 172MB 峰值、20 萬行 ≈ 748MB 峰值。實務上「1MB 以下／2 萬行內」的檔案在雲端非常安全；超過 12 萬行建議先縮小匯出範圍或改用本機執行。
7. **環境變數 / Secrets**（全部選用）：

   | 變數 | 預設 | 說明 |
   | --- | --- | --- |
   | `KILO_LOG_LEVEL` | `WARNING`（雲端）/ `INFO`（本機） | 日誌層級 |
   | `KILO_CLOUD_MAX_UPLOAD_MB` | `8` | 雲端單檔上載上限（MB） |
   | `KILO_CLOUD_MAX_ROWS` | `120000` | 雲端列數上限（`0` = 不限制，風險自負） |
   | `KILO_CLOUD_RESULT_PREVIEW_LIMIT` | `1000` | 雲端結果表預覽行數上限（`0` = 不限制；舊名 `KILO_ZEABUR_RESULT_PREVIEW_LIMIT` 仍相容） |
   | `KILO_FIX_MOJIBAKE` | `0` | 啟用亂碼修補（Windows 上載亂碼時用；Linux 雲端環境不需要） |
   | `KILO_PERF_TIMING` | `0` | 啟用效能計時面板 |
   | `KILO_RUNTIME` | 自動偵測 | 強制指定 `cloud` / `local` |

   設定方式：`share.streamlit.io` → App → **Settings → Secrets**（TOML 格式；根層級鍵值會同步成為環境變數，`config.get_setting()` 會依序讀取環境變數與 Secrets）。
8. **檔案系統為臨時性**：容器重啟後會回到 Git 版本；本系統只做記憶體內處理與下載輸出，不會寫入檔案，資料不會遺失。
9. **閒置休眠**：免費方案閒置一段時間後會休眠，下次開啟需數十秒喚醒，屬正常現象。
10. **查看日誌**：App 頁面右側的 Cloud logs 僅對具備 repo 寫入權限的成員可見。

### 其他平台（Docker，選用）

`Dockerfile`、`Procfile` 與 `.dockerignore` 保留作為自架或其他容器主機的備援；**Streamlit Community Cloud 不會讀取這些檔案**。

## 輸入資料欄位

### 必需欄位

- `Article`（12 位字串，系統會自動補零）
- `Article Description` 或 `Article Long Text (60 Chars)`
- `OM`
- `RP Type`
- `Site`
- `SaSa Net Stock`
- `Pending Received`
- `Safety Stock`
- `Last Month Sold Qty`
- `MTD Sold Qty`
- `MOQ`

### 模式專用欄位

- `ALL`：E1 / E1b / E2
- `Type`：B2 / B2a / B2L / B2La / B3 / B3a / B3L / B3La / E1b
- `Target`：F / F2 / F3 / NST

### 系統衍生欄位

- `Effective Sold Qty = Last Month Sold Qty + MTD Sold Qty`
- `Total Available = SaSa Net Stock + Pending Received`
- Turnday 主體額外衍生：`Original Safety Stock`（上載檔案原值備份）、`Daily Sold Rate`（日均銷量，Effective Sold Qty ÷ 覆蓋日數）；`Safety Stock` 欄位值此時為 Turnday 保底 ceil(日均銷量 × N)

## 模式對照

| 模式 | 名稱 | 重點 |
| --- | --- | --- |
| A | 保守轉貨 | RF 20% 上限；ND 淨庫存全轉；單件上調可能令來源低於 Safety 1 件 |
| B | 加強轉貨 | RF 50% 上限；ND 淨庫存全轉；「RF加強轉出」只在有 Pending Received 時出現，純淨庫存仍保留 Safety |
| B2 | 附加 B 特別模式 | Type=L 低銷量可全轉出，接收上限 Safety × 2，Mix 高銷量保護；只配對接收優先級 1–2（T/M 且有銷量），P3–4 目前不會被配對 |
| B2a | 附加 B2a | 參照 B2，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B2L | 附加 B2L 特別模式 | 參照 B2，但 Type=L 低銷量改為保留 2 件後轉出（僅新 L 系列） |
| B2La | 附加 B2La 特別模式 | 參照 B2L，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B3 | 附加 B 跨 OM 特別模式 | 參照 B2，允許跨 OM，含 HD/Windy 限制與 Mix 高銷量保護 |
| B3a | 附加 B3a 跨 OM 特別模式 | 參照 B3，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| B3L | 附加 B3L 跨 OM 特別模式 | 參照 B3，但 Type=L 低銷量改為保留 2 件後轉出（僅新 L 系列） |
| B3La | 附加 B3La 跨 OM 特別模式 | 參照 B3L，且 Type=T 不可作為來源（含 Mix 高銷量保護） |
| C | 重點補 0 | 30% 上限、每店最多 3~10 件（可調）；補 0 目標 max(Safety×0.5, 3)；仍會回落一般缺貨 |
| C1 | 重點補 0（只補 0/1，可自訂門檻及轉出上限） | 參照 C，僅補 total_available ≤ N（N 可於側邊欄設定），不回落一般缺貨；每店轉出件數上限可調（3~10件） |
| C2 | 附加 C 跨 OM 重點補 0 | 參照 C，每店轉出上限可調，允許跨 OM，含 HD/Windy 限制 |
| D | 清貨轉貨 | ND 全轉（有銷量亦以「ND轉出」全轉）；RF 按 B 規則（50%）；避免剩 1 件 |
| D2 | 清貨轉貨（ND 限定） | 僅 ND 清貨轉出，RF 不轉出只接收 |
| E1 | 強制轉出 | 僅同 OM，僅處理 `ALL` 標記 |
| E1b | 強制轉出優先類型接收 | 僅同 OM，接收優先 Type=T/M |
| E2 | 強制轉出跨 OM | 優先同 OM，可跨 OM，僅處理 `ALL` 標記 |
| F | 目標優化 | `Target` 優先接收（ND/RF 均可），Target 為追加量，其餘按補 0 |
| F2 | F指定模式 | 僅 `Target` 店舖可接收（ND/RF 均可），Target 為追加量；可設定 HD 轉出選項；Windy 目標店優先從同 OM 無 Target 店提取；Target 店全 SKU 全域保護 |
| F3 | 目標性補0 | 繼承 F2 + RF轉出保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級。新增「優先滿足小型目標」選項、配對後缺口填補、Target達成分析。Target 店全 SKU 全域保護 |
| NST | New Shop Target調貨 | 僅Target店接收，RF轉出保留≥2件 + 75%上限 + 庫存<3不轉出，可設定同一SKU轉出店數上限(10/20/不限)；目標可能未達100%；Target 店全 SKU 全域保護 |
| ND1 | ND 同 OM 轉貨 | ND 店舖可互轉（同 OM），按銷量排序，接收上限 2×過去2個月銷量，可限制單一出貨店配對接收店數 |
| ND2 | ND 混合 OM 轉貨 | ND 店舖可互轉（跨 OM），Windy 只轉 Windy，接收上限 2×過去2個月銷量，可限制單一出貨店配對接收店數 |
| ND3 | ND 限同OM轉貨(補0) | ND 同 OM 轉貨，轉出保留 3 件，只補零庫存 ND 店（參考C1），按銷量排序，可限制單一出貨店配對接收店數 |
| ND4 | ND 限同OM轉貨(補0及有銷售記錄) | ND 同 OM 轉貨，無銷量來源店不保留全數轉出，有銷量來源店保留 3 件，只補有銷售記錄的零庫存 ND 店，按銷量排序，可限制單一出貨店配對接收店數 |
| 精簡SKU(限同OM) | 精簡SKU 調貨 | RF 超出 Cap（Max(Safety×2, 過去2個月銷量×2)）部分轉出，ND 全轉出，僅同 OM；剩餘庫存可選退回 D001（預設）或留在店舖 |
| 精簡SKU(跨OM) | 精簡SKU 跨 OM 調貨 | 同精簡SKU(限同OM)，允許跨 OM，含 Windy/HD 限制 |
| 精簡SKU(退D001) | 精簡SKU 全數退回 D001 | 不配對；RF 超出 Cap 部分及 ND 全部退 D001；只剩 1 件不退（ND 亦同） |

> B2/B2a/B2L/B2La/B3/B3a/B3L/B3La 全家族只配對接收優先級 1–2（Type=T/M 且有銷量）；優先級 3–4（零銷量、Type=L、其他 Type）目前不會被配對，即使庫存為 0。

## 介面操作流程

1. 上載 Excel（上載區可一併設定 MTD 數據日期，通常 T-1；僅 Turnday 主體用於計算日均銷量；未上載時顯示 3 步空狀態指引）。
2. 選擇保底主體（步驟 1：Safety Stock / Turnday＋日數），再於「步驟 2 選擇轉貨模式」一次選取全部 30 個調貨模式（不分類；長選單內部捲動；側邊欄即時顯示必填欄位提示、目前選擇總結與目前模式詳解）。
3. 若為 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3/ND4，可於「步驟 3 模式參數」設定接收店數限制。若為 NST，可設定 HD 轉出選項及同一 SKU 轉出店數上限。若為 精簡SKU(限同OM)，可設定剩餘庫存「退回 D001（預設）」或「不退 D001（留在店舖）」。
4. 點擊「生成調貨建議」（頂部 4 步進度條：上載→生成→檢視→下載；分析進度以狀態面板逐步顯示：演算法 → 品質檢查 → 統計與缺口分析；當前配置條顯示模式＋保底＋參數摘要）。
5. 檢視 KPI（新增 ND/RF 行數）、「📈 圖表概覽」（類型分佈／OM 對比／Top 10 商品）、調貨建議（關鍵字篩選 Article/店舖，不影響匯出）與統計（「📊 調貨缺口分析」：達成率／轉出率以進度條呈現，模式／角色／狀態三篩選並排，可排序；KPI 改以店×SKU 計數並新增件數滿足率，來源附「未轉出可轉量」「轉後店內庫存」，超量轉出會顯示警告）。
6. 點擊「📤 準備 Excel 報表」生成文件後，再點擊下載按鈕取得報表。

### 模式教學分頁

系統頂部提供「📖 模式教學」分頁，直接顯示 **30 模式邏輯審查**：

- 嵌入 `docs/KiLo_30模式邏輯審查.html`，內容包括全局管線、保底主體（三步計算圖＋Safety／Turnday 對比圖＋受影響模式表）、6 分支決策圖、10 個營運情境對照、9 個家族共 30 張模式卡（四段流程圖＋可重跑範例＋不能處理的情景）、15 條審查發現與附錄（公式／參數／欄位矩陣）。
- 分頁內提供「下載完整 HTML」按鈕；需要全螢幕或列印（A4 橫向）時，下載後以瀏覽器開啟。
- HTML 與 `audit/` 腳本同步：`python audit/scenarios.py` 可重跑全部範例，`python audit/build_doc.py` 可重建文件。
- 嵌入時收起文件內置目錄，避免與頁面標題及 Streamlit 側邊欄重複；下載版仍保留完整目錄。
- 舊版「圖卡教學」已移除，其內容（全局規則、Safety／Turnday 保底、模式卡、決策指引）已整合進審查文件。

審查文件同時釐清了舊教學中與程式不符的描述（例如 D 會清有銷量 ND、C 的補 0 目標是 max(Safety×0.5, 3)、MOQ 不參與計算、精簡SKU(退D001) 完全不做配對）。

## 輸出內容

- 工作表 1：`調貨建議 (Transfer Recommendations)`
- 調貨明細、來源/接收分類、庫存變化、備註
- 欄位順序（21 欄，全模式適用）：`Brand;Article;Product Desc;Transfer OM;Transfer Site;Transfer Site Type;Transfer Site Last Month Sold Qty;Transfer Site MTD Sold Qty;Transfer Original Stock;Transfer Safety Stock;Transfer After Transfer Stock;Receive OM;Receive Site;Receive Site Type;Receive Site Last Month Sold Qty;Receive Site MTD Sold Qty;Receive Original Stock;Receive Site Safety Stock;Transfer Qty;Remark;Notes`
- `Transfer Site Type` / `Receive Site Type` 顯示該店舖於輸入檔 `Type` 欄位的值（T=遊客區/M=混合型/L/R）；非 B 系模式如無 Type 資料則為空白
- 工作表 2：`統計摘要 (Summary Dashboard)`
- KPI、按 Article/OM 統計、來源/接收類型分佈
- 工作表 3（F/F2/F3/NST 模式）：`Target達成分析` — 每組 (Article, Site) 目標量與實際接收量對比、達成狀態、總達成率與總差距（只計使用者設定 Target 的接收點；自動補0目標見調貨缺口分析）
- 工作表（全模式）：`調貨缺口分析` — 目的地（需求/實收/缺口）與來源（可轉量/實轉/未轉出可轉量/轉後店內庫存）逐店×SKU 明細；KPI 含未滿足店×SKU、缺口件數、剩餘店×SKU、剩餘件數、目的地滿足率（店×SKU）、件數滿足率、來源轉出率（可轉量）與超量轉出件數；E 模式（強制調撥）目的地以「不適用」顯示

## 測試

建議先跑與本次模式改動最相關的測試：

```bash
python -m pytest tests/test_b2_b3_source_receive_site_limit.py tests/test_b2_priority.py tests/test_b2_fix.py tests/test_b2a_b3a_t_no_source.py tests/test_modes_simple.py -q
```

## 專案結構

- `app.py`：Streamlit 介面與操作流程（含雙分頁：調貨系統 / 模式教學）
- `business_logic.py`：來源/接收識別與配對規則
- `services/matching_engine.py`：核心配對引擎（轉移量計算、前置過濾、多回合匹配）
- `services/prioritizer.py`：優先級分組引擎（確定性規則）
- `data_processor.py`：Excel 讀取、驗證、欄位標準化、預設資料補齊
- `excel_generator.py`：報表匯出
- `ui/tutorial.py`：模式教學分頁（嵌入 `docs/KiLo_30模式邏輯審查.html`，提供 HTML 下載）
- `docs/KiLo_30模式邏輯審查.html`：30 模式邏輯審查主文件（模式教學分頁的內容來源）
- `audit/`：文件產生與範例重跑腳本（`scenarios.py`、`mode_spec.py`、`build_doc.py`）
- `config.py`：版本、環境偵測（雲端／本機）、Secrets 讀取、Magic Numbers
- `.streamlit/config.toml`：Streamlit 介面與伺服器設定（本機與 Community Cloud 共用）
- `.streamlit/secrets.toml.example`：Secrets 設定範本（Community Cloud Secrets 面板／本機 secrets.toml）
- `調貨模式詳解.txt`：中文規則細節
- `VERSION.md`：版本紀錄

## 常見問題

### 為什麼沒有產生建議？

- 檢查是否同時存在可轉出來源與可接收需求。
- 檢查 `RP Type`、`Type`、`ALL`、`Target` 是否符合所選模式。
- 確認資料中沒有把所有 RF 店舖都變成受保護狀態。

### 哪些模式可以使用接收店數限制？

- 在側欄選擇 B2/B2a/B2L/B2La/B3/B3a/B3L/B3La/E1/E1b/E2/ND1/ND2/ND3/ND4 後，會出現「出貨店舖接收店數限制」。
- 選 `優先 1 間`：同一 SKU 下，每個來源店最多配對 1 個接收店（最集中）。
- 選 `最多 2 間`：同一 SKU 下，每個來源店最多配對 2 個接收店。
- 選 `不限制`：不套用該限制。

### E 模式沒有作用？

- E1/E1b/E2 僅處理 `ALL` 欄位有標記的資料行。
- 請確認 `ALL` 欄位存在，且要轉出的行不是空白；填 `0` 也會被視為標記（系統只檢查非空），要保留請留空。

## 版本

- 目前版本：`v2.38.0`
- 詳細異動請見 `VERSION.md`
