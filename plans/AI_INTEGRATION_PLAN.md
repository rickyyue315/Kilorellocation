# AI Integration Plan — 庫存調貨建議系統

> **目標**：為 ① 模式推薦、③ 邏輯審計、④ 報表增強 三個場景引入 LLM（DeepSeek V4 Flash / Step 3.5 Flash），安全支援 Zeabur + Streamlit 部署。

---

## 一、系統架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit App (app.py)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Phase 1: 資料上傳後 (after data_processor)               │    │
│  │  ┌──────────────────────┐                                │    │
│  │  │  AI Advisor          │  ◀── ① 模式推薦               │    │
│  │  │  services/ai_        │      顯示推薦 + 原因            │    │
│  │  │  advisor.py          │      使用者仍手動選擇           │    │
│  │  └──────────────────────┘                                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Phase 2: 調貨建議生成後 (after quality_checks)            │    │
│  │  ┌──────────────────────┐                                │    │
│  │  │  AI Auditor          │  ◀── ③ 邏輯審計               │    │
│  │  │  services/ai_        │      不修改結果，僅出警示        │    │
│  │  │  auditor.py          │                                │    │
│  │  └──────────────────────┘                                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Phase 3: Excel 生成時 (during excel_generator)           │    │
│  │  ┌──────────────────────┐                                │    │
│  │  │  AI Note Enhancer    │  ◀── ④ 報表增強               │    │
│  │  │  services/ai_        │      增強 Notes + 新增 AI Sheet │    │
│  │  │  note_enhancer.py    │                                │    │
│  │  └──────────────────────┘                                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  AI Client (核心)       services/ai_client.py             │    │
│  │  - OpenRouter API 客戶端                                  │    │
│  │  - 支援多模型（DeepSeek V4 Flash / Step 3.5 Flash）       │    │
│  │  - Streamlit session_state 快取                           │    │
│  │  - 優雅降級（API 失敗 → 純文字提示）                       │    │
│  │  - 環境變數取 API Key（Zeabur Secrets）                   │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、檔案結構與模組職責

```
services/
  ├── ai_client.py           # [NEW] LLM 客戶端（OpenRouter API 封裝）
  ├── ai_advisor.py          # [NEW] 模式推薦邏輯
  ├── ai_auditor.py          # [NEW] 邏輯審計邏輯
  ├── ai_note_enhancer.py    # [NEW] 報表增強邏輯
  ├── __init__.py
  ├── matching_engine.py
  ├── notes.py
  ├── quality_checks.py
  └── ... (其他現有服務)

config.py                    # [MODIFY] 新增 AI 相關配置

app.py                       # [MODIFY] 插入 3 個 AI 調用點

ui/
  ├── sidebar.py             # [MODIFY] 新增 AI 模式推薦區塊
  └── display.py             # [MODIFY] 新增 AI 審計報告區塊

excel_generator.py           # [MODIFY] 新增 AI 增強 sheet

requirements.txt             # [MODIFY] 新增 httpx
```

---

## 三、API Key 安全方案

### Zeabur 部署

```
Zeabur Dashboard → Service → Secrets
  ┌────────────────────────────────────────┐
  │  Key                   Value           │
  ├────────────────────────────────────────┤
  │  OPENROUTER_API_KEY    sk-or-v1-xxxxx  │
  │  AI_ENABLED            true            │
  │  AI_MODEL              deepseek/       │
  │                        deepseek-v4-    │
  │                        flash           │
  └────────────────────────────────────────┘
      ↓
  Container 中 os.getenv("OPENROUTER_API_KEY") → AI Client
      ↓ TLS
  OpenRouter API → 底層模型
```

### API Key 讀取優先順序（ai_client.py）

```python
import os
import streamlit as st

def _get_api_key() -> str:
    """安全取得 API Key：st.secrets → os.environ → 錯誤提示"""
    try:
        if 'OPENROUTER_API_KEY' in st.secrets:
            return st.secrets['OPENROUTER_API_KEY']
    except Exception:
        pass
    key = os.getenv('OPENROUTER_API_KEY', '')
    if key:
        return key
    st.error("⚠️ 未設定 OPENROUTER_API_KEY")
    return ''
```

**安全原則**：
- 不寫 API Key 到 log
- 不暴露到前端 HTML/JS
- 原始數據不上傳 LLM — 只傳統計摘要

---

## 四、AI Client 核心設計（services/ai_client.py）

```python
"""
AI Client — OpenRouter API 封裝
支援多模型、session_state 快取、優雅降級
"""
import os, json, hashlib, logging
from typing import Optional
import streamlit as st
import httpx

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
REQUEST_TIMEOUT = 30

def _get_api_key() -> str:
    try:
        if 'OPENROUTER_API_KEY' in st.secrets:
            return st.secrets['OPENROUTER_API_KEY']
    except Exception:
        pass
    return os.getenv('OPENROUTER_API_KEY', '')

def _get_model() -> str:
    try:
        if 'AI_MODEL' in st.secrets:
            return st.secrets['AI_MODEL']
    except Exception:
        pass
    return os.getenv('AI_MODEL', DEFAULT_MODEL)

def is_ai_enabled() -> bool:
    val = os.getenv('AI_ENABLED', 'true').lower()
    try:
        if 'AI_ENABLED' in st.secrets:
            val = str(st.secrets['AI_ENABLED']).lower()
    except Exception:
        pass
    return val in ('true', '1', 'yes')

def chat_completion(messages: list, model: Optional[str] = None,
                    temperature: float = 0.1, max_tokens: int = 1024) -> str:
    """呼叫 OpenRouter API。session_state 快取，失敗返回空字串。"""
    if not is_ai_enabled():
        return ""
    model = model or _get_model()
    api_key = _get_api_key()
    if not api_key:
        return ""
    # 快取
    raw = json.dumps({"messages": messages, "model": model}, ensure_ascii=False)
    ck = hashlib.md5(raw.encode()).hexdigest()
    cache = st.session_state.setdefault('_ai_cache', {})
    if ck in cache:
        return cache[ck]
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            cache[ck] = result
            return result
    except Exception as e:
        logger.error(f"AI API 錯誤: {e}")
        return ""
```

---

## 五、三個場景的詳細設計

### ① 模式推薦（services/ai_advisor.py）

**觸發**：上傳資料後 → `app.py` line 157 後

**輸入**：DataFrame 統計摘要（不傳原始資料）

```python
def build_df_summary(df) -> dict:
    return {
        'total_rows': len(df),
        'unique_articles': df['Article'].nunique(),
        'unique_oms': df['OM'].nunique(),
        'unique_sites': df['Site'].nunique(),
        'nd_ratio': (df['RP Type'] == 'ND').mean(),
        'zero_stock_count': int((df['SaSa Net Stock'] == 0).sum()),
        'has_type_column': 'Type' in df.columns,
        'has_target_column': 'Target' in df.columns,
        'has_all_column': 'ALL' in df.columns,
        'cross_om_article_count': df.groupby('Article')['OM'].nunique().gt(1).sum(),
        'om_distribution': df['OM'].value_counts().to_dict(),
    }
```

**提示詞**：要求以 JSON 回覆推薦的模式代碼、名稱、原因

**UI** ：`ui/sidebar.py` 中 radio 按鈕上方插入 AI 建議區塊

### ③ 邏輯審計（services/ai_auditor.py）

**觸發**：quality_checks 後 → `app.py` line 200

**不修改結果**，僅出警示

檢查方向：商品集中度、來源集中度、反向流動、數據異常

**UI** ：`ui/display.py` 中原 quality 訊息下方插入審計報告

### ④ 報表增強（services/ai_note_enhancer.py）

**觸發**：Excel 生成時

**策略**：只對 Transfer Qty ≥ 10 的重要條目使用 AI（控制 Token）

```python
def enhance_notes(recommendations: list, mode: str, min_qty: int = 10) -> list:
    enhanced = []
    for rec in recommendations:
        if rec.get('Transfer Qty', 0) >= min_qty:
            ai_note = _single_note(rec, mode)
            if ai_note:
                rec = {**rec, 'Notes': rec.get('Notes', '') + '\n📋 ' + ai_note}
        enhanced.append(rec)
    return enhanced
```

---

## 六、config.py 新增配置

```python
# ── AI 功能配置 ──
DEFAULT_AI_MODEL = "deepseek/deepseek-v4-flash"
AI_MODEL_ADVISOR = os.getenv('AI_MODEL_ADVISOR', DEFAULT_AI_MODEL)
AI_MODEL_AUDITOR = os.getenv('AI_MODEL_AUDITOR', DEFAULT_AI_MODEL)
AI_MODEL_ENHANCER = os.getenv('AI_MODEL_ENHANCER', DEFAULT_AI_MODEL)
AI_ENABLED = os.getenv('AI_ENABLED', 'true').lower() in ('true', '1', 'yes')
AI_MAX_TOKENS_ADVISOR = 512
AI_MAX_TOKENS_AUDITOR = 1024
AI_MAX_TOKENS_ENHANCER = 256
AI_ENHANCE_MIN_QTY = 10
AI_REQUEST_TIMEOUT = 30
```

---

## 七、requirements.txt 新增

```
httpx>=0.27.0
```

> 僅需 `httpx`。直接使用 OpenRouter REST API，不需要 `openai` 套件。

---

## 八、Zeabur 部署

| 事項 | 說明 |
|:----|:------|
| Secrets | Zeabur Dashboard → Service → Secrets → `OPENROUTER_API_KEY` |
| 無狀態 | AI 呼叫等冪，不依賴 Server 狀態 |
| 快取 | `st.session_state` — 相同輸入不重複呼叫 |
| 降級 | API 中斷 → 跳過 AI，不影響調貨功能 |
| Timeout | 30 秒，可環境變數調整 |
| 日誌 | 不記錄 API Key、原始數據 |
| 開關 | `AI_ENABLED=false` 完全關閉 |

---

## 九、實施路線圖

```
Week 1: 基礎建設
  ai_client.py + config.py + requirements.txt + Zeabur 驗證

Week 2: Phase 1 — 模式推薦 (①)
  ai_advisor.py + sidebar.py 整合 + 測試

Week 3: Phase 2 — 邏輯審計 (③)
  ai_auditor.py + display.py 整合 + 測試

Week 4: Phase 3 — 報表增強 (④)
  ai_note_enhancer.py + excel_generator.py 整合 + 端到端測試
```

---

## 十、成本估算（每月 500 次）

| 場景 | Token | Step 3.5 Flash | DeepSeek V4 Flash |
|:----|:-----:|:--------------:|:-----------------:|
| ① 模式推薦 | ~700 | $0.000105 | $0.000088 |
| ③ 邏輯審計 | ~3,300 | $0.000465 | $0.000403 |
| ④ 報表增強 | ~1,500 | $0.000240 | $0.000197 |
| **單次** | ~5,500 | **$0.00081** | **$0.00069** |
| **月成本** | ~2.75M | **$0.41** | **$0.34** |

---

## 十一、總結

| 面向 | 結論 |
|:----|:------|
| **模型** | DeepSeek V4 Flash（主力）/ Step 3.5 Flash（備選）|
| **API 安全** | 環境變數 + st.secrets + TLS 加密 |
| **Zeabur** | ✅ 完全相容 |
| **依賴** | 僅新增 `httpx` |
| **核心影響** | ❌ 零 — 失敗不影響調貨邏輯 |
| **月成本** | ~$0.34 (DeepSeek) 或 ~$0.41 (Step 3.5 Flash) |