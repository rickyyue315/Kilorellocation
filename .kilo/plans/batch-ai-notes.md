# Plan: 方案 B — 批次 AI Notes（並行執行）

## 目標

在保留現有模板 Notes 不變的前提下，新增可選的 AI 批次分析功能。按 Article 分組，每組並行呼叫一次 OpenRouter API，為每條調貨建議附加 AI 生成的分析說明與風險標記。

---

## 1. 架構概覽

```
現有流程（不變）:
  generate_transfer_recommendations()
    → 匹配引擎 → build_recommendation(notes=模板Notes)
    → _optimize_single_piece_transfers()
    → assign_priority()
    → return recommendations

新增（可選，末尾追加）:
  → enrich_notes_with_ai(recommendations, mode)   ← 新增的獨立函數
      → 按 Article 分組
      → ThreadPoolExecutor 並行呼叫 chat_completion()
      → 解析 JSON 回傳 → 附加到 rec['Notes'] += AI 補充
```

**核心原則：加法架構，不修改任何現有代碼。**

---

## 2. 新增檔案

### 2.1 `services/ai_batch_notes.py`（核心模組，~150 行）

```python
# 主要結構
BATCH_SYSTEM_PROMPT = """..."""   # 系統 prompt

def _build_batch_context(article, recs) -> dict
def _parse_ai_response(response, recs) -> dict
def _process_one_article(article, recs, model, timeout) -> dict
def enrich_notes_with_ai(recommendations, mode) -> None
```

#### 函數職責

| 函數 | 職責 | 行數估計 |
|------|------|---------|
| `_build_batch_context()` | 將一個 Article 的所有建議聚合為 AI 輸入 JSON | ~30 行 |
| `_parse_ai_response()` | 解析 AI 回傳的 JSON，對應回每條 rec 的 index | ~25 行 |
| `_process_one_article()` | 單一 Article 的完整流程（構建上下文→呼叫API→解析） | ~30 行 |
| `enrich_notes_with_ai()` | 主入口：分組→ThreadPoolExecutor 並行→回寫 Notes | ~40 行 |

#### System Prompt 設計

```
你是零售庫存調撥系統的分析助手。你會收到一個商品（Article）下所有調撥建議的摘要數據。

對每條建議，請：
1. 用簡潔繁體中文（30-50字）解釋「為何這樣配對」
2. 標記風險等級：高(🔴)/中(🟡)/低(🟢)
3. 如有需要人工審核的特殊情況，在 note 中說明

風險評估考量因素：
- 轉出後剩餘庫存是否低於安全庫存
- 接收店是否有銷售記錄支持
- 跨OM轉移是否有更近的同OM替代
- 單筆大量轉移是否合理
- 零銷量店舖是否應該接收

嚴格以 JSON 陣列回傳，每個元素對應一條建議（按 id 順序）：
[{"id": 0, "ai_note": "...", "risk": "🟢", "needs_review": false}]
```

#### 並行設計

```python
def enrich_notes_with_ai(recommendations, mode):
    if not AI_BATCH_NOTES_ENABLED or not is_ai_enabled():
        return

    # 分組
    article_groups = defaultdict(list)
    for rec in recommendations:
        article_groups[rec['Article']].append(rec)

    # 並行處理
    with ThreadPoolExecutor(max_workers=AI_BATCH_MAX_WORKERS) as executor:
        futures = {
            executor.submit(_process_one_article, article, recs, ...): (article, recs)
            for article, recs in article_groups.items()
        }
        for future in as_completed(futures):
            article, recs = futures[future]
            try:
                results = future.result()
                for idx, ai_data in results.items():
                    rec = recs[idx]
                    rec['Notes'] += f" | 【AI分析: {ai_data['ai_note']}】 | 【AI風險: {ai_data['risk']}】"
                    if ai_data.get('needs_review'):
                        rec['Notes'] += " | 【AI標記: 建議人工審核】"
                    rec['AI Risk'] = ai_data['risk']
                    rec['AI Needs Review'] = ai_data.get('needs_review', False)
            except Exception:
                logger.warning("AI batch notes failed for %s", article)
```

---

### 2.2 `tests/test_ai_batch_notes.py`（測試，~120 行）

測試案例：

| 測試名稱 | 驗證內容 |
|---------|---------|
| `test_enrich_disabled` | 開關關閉時不修改 Notes |
| `test_enrich_no_api_key` | 無 API key 時不修改 Notes |
| `test_build_batch_context` | 上下文結構正確，含所有必要欄位 |
| `test_parse_valid_json` | 正確解析 JSON 回傳並對應到 rec |
| `test_parse_invalid_json` | 解析失敗時不崩潰，回傳空結果 |
| `test_parse_partial_json` | 部分 id 缺失時不影響已有項 |
| `test_notes_appended_not_replaced` | AI Notes 附加在模板 Notes 後面，原始 Notes 完整保留 |
| `test_ai_risk_field_added` | rec 新增 'AI Risk' 和 'AI Needs Review' 欄位 |
| `test_parallel_processing` | 多個 Article 分組確實並行執行 |
| `test_single_article_group` | 只有 1 個 Article 時正常運作 |
| `test_empty_recommendations` | 空 recommendations 不報錯 |
| `test_api_failure_graceful` | API 呼叫失敗時不影響任何 rec |

---

## 3. 修改現有檔案

### 3.1 `config.py`（+4 行）

在 AI 整合區塊後新增：

```python
AI_BATCH_NOTES_ENABLED = _get_env_bool('AI_BATCH_NOTES_ENABLED', False)
AI_BATCH_MAX_WORKERS = _get_env_int('AI_BATCH_MAX_WORKERS', 10)
AI_BATCH_NOTES_TIMEOUT = _get_env_int('AI_BATCH_NOTES_TIMEOUT', 60)
AI_BATCH_NOTES_MAX_TOKENS_PER_REC = 150
```

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `AI_BATCH_NOTES_ENABLED` | `False` | 總開關，預設關閉 |
| `AI_BATCH_MAX_WORKERS` | `10` | 並行線程數（付費 model 無 rate limit） |
| `AI_BATCH_NOTES_TIMEOUT` | `60` | 整體批次超時（秒） |
| `AI_BATCH_NOTES_MAX_TOKENS_PER_REC` | `150` | 每條建議的 max_tokens 估算基數 |

### 3.2 `business_logic.py`（+2 行）

在 `generate_transfer_recommendations()` 末尾、`return` 之前新增：

```python
# 在 all_recommendations.sort(...) 之後
from services.ai_batch_notes import enrich_notes_with_ai
enrich_notes_with_ai(all_recommendations, mode)

return all_recommendations
```

### 3.3 `ui/display.py`（+5 行）

在 `render_ai_executive_summary_button()` 中，增加 AI 批次 Notes 的狀態顯示：

```python
from services.ai_client import is_ai_enabled
from config import AI_BATCH_NOTES_ENABLED

# 在 AI 執行摘要按鈕旁邊顯示 AI Notes 狀態
if is_ai_enabled() and AI_BATCH_NOTES_ENABLED:
    ai_notes_count = sum(1 for r in recommendations if 'AI Risk' in r)
    if ai_notes_count > 0:
        st.caption(f"🤖 AI Notes 已為 {ai_notes_count} 條建議生成分析")
```

### 3.4 `excel_generator.py`（不改）

Notes 欄位原樣輸出 `rec.get('Notes', '')`，已包含 AI 附加內容，無需修改。

### 3.5 `services/notes.py`（不改）

模板 Notes 完全不動。

### 3.6 `services/ai_client.py`（不改）

`chat_completion()` 已有完整的快取、錯誤處理、timeout 機制，直接複用。

### 3.7 `app.py`（不改）

AI 批次 Notes 在 `business_logic.py` 內部完成，`app.py` 不需要改動。

---

## 4. 聚合上下文格式（發送給 AI 的 JSON）

```json
{
  "article": "900123456789",
  "product_desc": "SK-II Facial Treatment Essence 230ml",
  "mode": "B2(附加B特別模式)",
  "recommendations": [
    {
      "id": 0,
      "from_site": "HA12",
      "from_om": "Ivy",
      "to_site": "HA45",
      "to_om": "Ivy",
      "qty": 5,
      "source_type": "ND轉出",
      "dest_type": "遊客區店舖 高銷量優先",
      "from_original_stock": 8,
      "from_remaining": 3,
      "from_last_month_sold": 0,
      "from_mtd_sold": 0,
      "to_original_stock": 0,
      "to_cumulative_received": 5,
      "to_safety_stock": 3,
      "to_last_month_sold": 4,
      "to_mtd_sold": 2,
      "is_cross_om": false
    }
  ],
  "summary": {
    "total_out_qty": 5,
    "total_sources": 1,
    "total_destinations": 1,
    "has_cross_om": false
  }
}
```

---

## 5. AI 回傳格式

```json
[
  {
    "id": 0,
    "ai_note": "ND零銷量店清貨至零庫存遊客區高銷量店，配對合理，轉出後仍餘3件安全",
    "risk": "🟢",
    "needs_review": false
  }
]
```

回寫後的 Notes 範例：

```
【轉出分類: ND轉出】 | 【接收分類: 遊客區店舖 高銷量優先】 | ... | 【AI分析: ND零銷量店清貨至零庫存遊客區高銷量店，配對合理，轉出後仍餘3件安全】 | 【AI風險: 🟢】
```

---

## 6. 性能估算

### 並行延遲

假設 50 個 Article 分組，`max_workers=10`，每次 API 呼叫 ~3s：

| 指標 | 估算值 |
|------|--------|
| 並行批次數 | ceil(50/10) = 5 批 |
| 每批延遲 | ~3s |
| **AI 總延遲** | **~15s** |
| 100 個 Article | ceil(100/10) = 10 批 → **~30s** |

### 成本（DeepSeek V4 Flash）

| 指標 | 每組估算 | 50 組總計 |
|------|---------|----------|
| Input tokens | ~1,200 | ~60,000 |
| Output tokens | ~300 | ~15,000 |
| 成本 | ~$0.00006 | **~$0.003** |

---

## 7. 還原方案

| 步驟 | 動作 | 時間 |
|------|------|------|
| 1 | `config.py`: `AI_BATCH_NOTES_ENABLED = False` | 10s |
| 2 | 或刪除 `business_logic.py` 中 2 行呼叫 | 30s |
| 3 | 或刪除 `services/ai_batch_notes.py` 整個檔案 | 10s |
| **總計** | | **< 1 分鐘** |

---

## 8. 文件同步（按 AGENTS.md 要求）

| 檔案 | 更新內容 |
|------|---------|
| `README.md` | 新增 AI 批次 Notes 功能說明、環境變數 |
| `VERSION.md` | 新版本記錄 |
| `config.py` | 版本號 bump |
| `app.py` | docstring 版本更新 |
| `ui/tutorial.py` | 不需要（非模式變更） |
| `調貨模式詳解.txt` | 不需要（非模式變更） |
| `transfer_logic_ai_brief.md` | 不需要（匹配邏輯不變） |

版本號：v2.21.0 → **v2.22.0**

---

## 9. 實施順序

1. **Phase 1: 配置** — 修改 `config.py`（新增 4 個常數 + 版本號 bump）
2. **Phase 2: 核心模組** — 新建 `services/ai_batch_notes.py`
3. **Phase 3: 整合** — 修改 `business_logic.py`（2 行）
4. **Phase 4: UI** — 修改 `ui/display.py`（狀態顯示）
5. **Phase 5: 測試** — 新建 `tests/test_ai_batch_notes.py`
6. **Phase 6: 驗證** — 執行全部測試，確認現有測試不受影響
7. **Phase 7: 文件** — 更新 `README.md`、`VERSION.md`、`app.py` docstring
8. **Phase 8: 提交** — commit

---

## 10. 環境變數清單

```text
# .streamlit/secrets.toml 或 Zeabur Secrets
AI_BATCH_NOTES_ENABLED = true          # 啟用 AI 批次 Notes
AI_BATCH_MAX_WORKERS = 10              # 並行線程數
AI_BATCH_NOTES_TIMEOUT = 60            # 整體超時（秒）
OPENROUTER_API_KEY = sk-or-v1-xxxxx    # 已有的 API key
AI_ENABLED = true                       # 已有的總開關
AI_MODEL = deepseek/deepseek-v4-flash  # 已有的 model
```

---

## 11. 風險與緩解

| 風險 | 緩解措施 |
|------|---------|
| API 回傳非 JSON | `_parse_ai_response()` 用 try/except 包裹，失敗時跳過 |
| 部分分組超時 | 每個 future 有獨立 timeout，不影響其他分組 |
| AI 生成不準確的描述 | AI Notes 是附加資訊，不影響模板 Notes；用戶可關閉開關 |
| 並行數過高導致 OpenRouter 限流 | `AI_BATCH_MAX_WORKERS` 可配置，付費用戶通常無限制 |
| Notes 欄位過長 | AI note 限制 30-50 字，每條附加 ~80 字元 |
| Streamlit Cloud 記憶體 | 快取機制複用 `ai_client.py` 現有的 SHA-256 快取 |
