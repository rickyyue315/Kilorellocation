import json
import logging
import numpy as np


from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import config
from services.ai_client import chat_completion, is_ai_enabled

class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)


logger = logging.getLogger(__name__)

BATCH_SYSTEM_PROMPT = """你是零售庫存調撥系統的分析助手。你會收到一個商品（Article）下所有調撥建議的摘要數據。

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
[{"id": 0, "ai_note": "...", "risk": "🟢", "needs_review": false}]"""


def _build_batch_context(article: str, recs: List[Dict], mode: str) -> Dict:
    recommendations_payload = []
    for idx, rec in enumerate(recs):
        recommendations_payload.append({
            "id": idx,
            "from_site": rec.get('Transfer Site', ''),
            "from_om": rec.get('Transfer OM', ''),
            "to_site": rec.get('Receive Site', ''),
            "to_om": rec.get('Receive OM', ''),
            "qty": rec.get('Transfer Qty', 0),
            "source_type": rec.get('Source Type', ''),
            "dest_type": rec.get('Destination Type', ''),
            "from_original_stock": rec.get('Source Original Stock', rec.get('source_original_stock', 0)),
            "from_remaining": rec.get('Source After Transfer Stock', rec.get('source_after_transfer', 0)),
            "from_last_month_sold": rec.get('source_last_month_sold_qty', 0),
            "from_mtd_sold": rec.get('source_mtd_sold_qty', 0),
            "to_original_stock": rec.get('Receive Original Stock', rec.get('dest_original_stock', 0)),
            "to_cumulative_received": rec.get('dest_cumulative_received_qty', 0),
            "to_safety_stock": rec.get('Safety Stock', rec.get('dest_safety_stock', 0)),
            "to_last_month_sold": rec.get('dest_last_month_sold_qty', 0),
            "to_mtd_sold": rec.get('dest_mtd_sold_qty', 0),
            "is_cross_om": rec.get('Transfer OM', '') != rec.get('Receive OM', ''),
        })

    total_out_qty = sum(r.get('Transfer Qty', 0) for r in recs)
    sources = set(r.get('Transfer Site', '') for r in recs)
    destinations = set(r.get('Receive Site', '') for r in recs)
    has_cross_om = any(r.get('Transfer OM', '') != r.get('Receive OM', '') for r in recs)

    product_desc = recs[0].get('Product Desc', '') if recs else ''

    return {
        "article": article,
        "product_desc": product_desc,
        "mode": mode,
        "recommendations": recommendations_payload,
        "summary": {
            "total_out_qty": total_out_qty,
            "total_sources": len(sources),
            "total_destinations": len(destinations),
            "has_cross_om": has_cross_om,
        },
    }


def _parse_ai_response(response: str, recs: List[Dict]) -> Dict[int, Dict]:
    if not response or not response.strip():
        return {}

    try:
        parsed = json.loads(response.strip())
        if not isinstance(parsed, list):
            logger.warning("AI response is not a list: %s", type(parsed).__name__)
            return {}
    except json.JSONDecodeError:
        logger.warning("AI response is not valid JSON")
        return {}

    results = {}
    for item in parsed:
        item_id = item.get("id")
        if item_id is None or not isinstance(item_id, int):
            continue
        if item_id < 0 or item_id >= len(recs):
            continue
        ai_note = item.get("ai_note", "").strip()
        if not ai_note:
            continue
        results[item_id] = {
            "ai_note": ai_note,
            "risk": item.get("risk", "🟢"),
            "needs_review": bool(item.get("needs_review", False)),
        }

    return results


def _process_one_article(article: str, recs: List[Dict], mode: str,
                         model: Optional[str] = None,
                         timeout: Optional[int] = None) -> Dict[int, Dict]:
    if not recs:
        return {}

    context = _build_batch_context(article, recs, mode)
    max_tokens = max(256, len(recs) * config.AI_BATCH_NOTES_MAX_TOKENS_PER_REC)

    messages = [
        {"role": "system", "content": BATCH_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False, cls=_NumpyEncoder)},
    ]

    response = chat_completion(
        messages,
        model=model or config.AI_DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=max_tokens,
        cache_namespace=f"batch_notes_{mode}",
    )

    if not response:
        return {}

    return _parse_ai_response(response, recs)


def enrich_notes_with_ai(recommendations: List[Dict], mode: str) -> None:
    if not config.AI_BATCH_NOTES_ENABLED or not is_ai_enabled():
        return

    if not recommendations:
        return

    article_groups: Dict[str, List[Dict]] = defaultdict(list)
    for idx, rec in enumerate(recommendations):
        article_groups[rec['Article']].append(rec)

    timeout = config.AI_BATCH_NOTES_TIMEOUT

    with ThreadPoolExecutor(max_workers=config.AI_BATCH_MAX_WORKERS) as executor:
        future_map = {}
        for article, recs in article_groups.items():
            future = executor.submit(
                _process_one_article, article, recs, mode,
                timeout=timeout,
            )
            future_map[future] = (article, recs)

        for future in as_completed(future_map):
            article, recs = future_map[future]
            try:
                results = future.result(timeout=timeout)
                for idx, ai_data in results.items():
                    rec = recs[idx]
                    ai_note = ai_data['ai_note']
                    risk = ai_data['risk']
                    rec['Notes'] = f"{rec.get('Notes', '')} | 【AI分析: {ai_note}】 | 【AI風險: {risk}】"
                    if ai_data.get('needs_review'):
                        rec['Notes'] += " | 【AI標記: 建議人工審核】"
                    rec['AI Risk'] = risk
                    rec['AI Needs Review'] = ai_data.get('needs_review', False)
            except Exception:
                logger.warning("AI batch notes failed for article: %s", article, exc_info=True)
