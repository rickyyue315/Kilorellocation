# KiLo Reallocation — Frontend Polish Plan

## Goal
在不影響任何功能與使用流程的前提下，全面強化 Streamlit 前端的視覺、引導與微互動體驗。維持深色主題、純 CSS + `st.dataframe` 路線，不引入新依賴。

## Constraints
- 不改業務邏輯（`business_logic.py` / `strategies/` / `models/`）
- 不改資料處理（`data_processor.py` / `excel_generator.py`）
- 純 CSS（`static/styles.css`）+ Streamlit 原生元件 + 必要的小段 HTML/Markdown
- 不新增 Python 依賴、不做淺色主題切換
- 不可影響既有操作流程（檔案上傳 → 模式選擇 → 產生建議 → 下載）

## Affected Files
- `static/styles.css` — 主要設計 token 與組件樣式（~70% 工作量）
- `app.py` — Hero、空狀態、進度條分階段、Footer 細修
- `ui/sidebar.py` — 模式卡片化、系統資訊卡重構、版本時間排版
- `ui/display.py` — KPI、資料預覽、結果表格、統計區、缺口分析
- `ui/tutorial.py` — 模式教學頁面排版優化
- `.streamlit/config.toml` — 主題細部設定（確認與 token 對齊）

---

## Phase 1 — Design Tokens & Global Polish（基礎層）
**檔案**：`static/styles.css`、`.streamlit/config.toml`

1. 統一設計 token：在 `:root` 新增 `--radius-pill`、`--gradient-hero`、`--gradient-orange`、`--gradient-cool`、`--ring-focus`、`--surface-glass` 等變數；移除散落各處的硬編碼值。
2. 補強 `prefers-reduced-motion` 段落：除動畫外，連 hover 動效也一併降速。
3. `config.toml`：將 `font = "sans serif"` 改為 `"sans serif"` 並加入 `font = "Inter, sans-serif"` 註解（若 Streamlit 支援），不影響主題色。
4. 加入 `::selection` 樣式（橘色高亮文字選取），微質感提升。
5. 統一滾動條 hover/active 狀態、加深細節。

## Phase 2 — Header / Hero / Footer
**檔案**：`app.py`、`static/styles.css`

6. `app-header` 增強：左側 logo 改用漸層背景 + 細光暈；右側加入「目前模式 + 版本」chip；標題副標改為更清楚的雙語排版。
7. 新增 `.app-hero` 區塊（無檔案時顯示）：
   - 大標題 + 一句話副標
   - 4 格「使用步驟」卡片（上傳 → 選模式 → 產生 → 下載）
   - 步驟數字用漸層圓形
8. Footer 增強：左側版本資訊、右側「回到頂部」錨點連結、最底下版權列用更細的字級與分隔線。

## Phase 3 — Sidebar Redesign
**檔案**：`ui/sidebar.py`、`static/styles.css`

9. 系統資訊卡改為兩欄網格（版本 / 開發者 / 環境 / 更新時間），用 icon chip 區分。
10. 模式選擇區：在 `st.radio` 上方加一段「選擇模式」標題 + 副標；radio 容器改用更明顯的「選項卡式」分組。
11. 模式說明文字（`st.caption(MODE_DESCRIPTIONS...)`）改為 `.mode-tooltip` 卡片，加左側橘色色條、icon、摺疊效果。
12. 模式相關的條件式控件（B 特別限制、F2 HD、C1 門檻、D2 限制…）統一包成 `.control-card`，邊框 + 標題列，視覺分組。
13. 詳細模式說明 expander：標題列改用橘色漸層底，內文加大行距、章節用小標分隔、列表加上勾選圖示。
14. 效能面板（`⏱`）改為 `.perf-card`，等寬字體 + 漸層色條顯示耗時比例。
15. 操作指引 expander：步驟改為 1~5 編號圓圈 + 簡述，視覺上像 onboarding checklist。

## Phase 4 — Empty State & Upload Zone
**檔案**：`app.py`、`static/styles.css`

16. 未上傳檔時，主區顯示 `.hero-empty`：
    - 大圖示 + 「開始你的第一次調貨分析」
    - 3 張「使用提示」卡（資料格式 / 模式選擇 / 結果解讀）
    - 一行 demo 連結：可下載 `stores-template.csv` 模板（已存在，直接連結）
17. `st.file_uploader` 拖放區：hover 時加橘色光暈環 + 上傳箭頭動畫；拖入中狀態加 `dashed-orange-glow`。
18. 上傳成功後：成功狀態卡（取代裸 `st.success`），顯示檔名、大小、行數、OM 數、模式名。
19. 進度條分階段（取代單一 `st.progress`）：用 4 步驟進度器（讀取 → 驗證 → 預處理 → 產生建議），每步完成時該步驟卡片打勾並高亮。

## Phase 5 — Loading & Progress
**檔案**：`app.py`、`ui/display.py`、`static/styles.css`

20. `with st.spinner("演算法運行中,請稍候...")` 改為自訂 `.loading-state` 區塊，顯示旋轉圖示 + 「演算法運行中」 + 已完成步驟列表（動態新增）。
21. 大檔案（>10MB）處理時加 `.skeleton-bar` 骨架屏（表格區先以漸層條佔位）。
22. 步驟式進度器：4 格 stepper，CSS 變數控制 active / done / pending 三態。

## Phase 6 — Results Display
**檔案**：`ui/display.py`、`static/styles.css`

23. KPI 卡片：每張卡片加上 icon（在數值上方）、小標籤；4 欄改成「重點指標（2 大卡）+ 次要指標（4 小卡）」布局；底色用左側色條區分。
24. 結果表格（`render_results_by_priority`）：
    - 每個優先級分組的 expander 標題列加上數量徽章（例如 `P1 — 緊急 (42)`）
    - 表頭 sticky 樣式
    - 表格行 hover 高亮 + zebra 條紋
    - 轉出類型欄位加上顏色 chip（RF 過剩 / RF 加強 / ND 清貨 / E 強制 / NST）
25. 統計區（`render_statistics`）：加入 `st.bar_chart` 顯示按 OM / 接收類型的長條圖；圖表卡片化。
26. 缺口分析（`render_gap_report`）：
    - 4 個小 metric 改為漸層色卡（依指標類型配色：綠=已達標 / 橘=部分達標 / 紅=未達標）
    - 篩選器區獨立卡片化
27. AI 執行摘要（`render_ai_executive_summary_button`）：按鈕點擊後以 `.ai-card` 顯示摘要（漸層背景 + 機器人 icon + 「AI 摘要」徽章），取代裸 `st.markdown`。
28. 下載按鈕：放在固定底部的 `.download-bar` 浮動區塊，下載按鈕更大、含檔名預覽、加上「重新整理快取」小按鈕（不影響邏輯，只是視覺）。

## Phase 7 — Tutorial Page
**檔案**：`ui/tutorial.py`、`static/styles.css`

29. 教學頁 hero：每個模式大卡片改用三欄 grid（情境描述 / 風險徽章 / 模式代碼 chip）。
30. 流程圖（flow-node / flow-arrow）：節點圓角加大、加陰影；箭頭改用真正的 ↓ 圖示 + 連接線 CSS。
31. Match Priority 區：match-row 加左側漸層色條、號碼徽章放大；hover 時整列輕微抬升。
32. Scenario Table：表頭改用橘色漸層底、表格行高加大、加上 zebra。
33. Mode Notes（黃色提示）：改為 `.note-card` 含 icon 與摺角效果。
34. 模式教學頁頂部加目錄（28 個模式 → 錨點跳轉），可摺疊。

## Phase 8 — Microinteractions & Accessibility
**檔案**：`static/styles.css`

35. 全部可點擊元素（按鈕、radio label、tab、expander、card）加入 `:focus-visible` 橘色 outline + 偏移，鍵盤導航更明顯。
36. 按鈕 active 狀態（`:active`）：加入下沉 + 內陰影模擬。
37. Radio / tab 切換時加入 200ms 淡入動畫。
38. Sidebar 摺疊時加入滑入動畫。
39. 表格加 `prefers-reduced-motion` 兼容：動畫停用時直接顯示最終狀態。
40. 對比度檢查：確保正文 (`--text-secondary`) 在背景上 ≥ 4.5:1；按鈕文字確認。
41. 為互動元素加 `aria-label` 提示（透過 Streamlit `help` 參數，不需改 CSS）。

## Phase 9 — Validation & Final Pass
**檔案**：所有受影響檔案

42. 啟動 app，逐頁檢查：
    - 三種瀏覽器寬度（手機 375px / 平板 768px / 桌面 1440px）
    - 28 種模式的可見性與可讀性
    - 上傳 → 產生 → 下載全流程未受影響
43. 執行既有測試（`pytest`），確認無迴歸。
44. 截圖比對（before/after），歸檔到 `plans/` 或 `archive/`。

---

## Estimated Risk
- **低**：純 CSS 變更 + 小段 HTML/Markdown，不動邏輯
- **中**：Streamlit 版本更新時 `data-testid` / `[data-baseweb=...]` selector 可能失效 → 需在 phase 9 驗證
- **零資料風險**：不更動任何 cache key 或 rerun 觸發邏輯

## Validation Plan
1. `pytest -q` 全綠
2. 手動測 28 種模式的上傳 → 產生 → 下載流程
3. 用 Chrome DevTools 模擬三種 viewport 確認無破版
4. 開啟 Chrome Lighthouse → Accessibility 分數 ≥ 90
5. 開啟 `prefers-reduced-motion` 後所有頁面仍可正常使用

## Out of Scope
- 淺色主題 / 主題切換
- 新圖表庫（plotly / altair / echarts）
- 業務邏輯 / 演算法變更
- 國際化（i18n）
- 後端 API 改動
