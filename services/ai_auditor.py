import json
import logging
import re
from typing import Optional

import config
from services.ai_client import chat_completion

logger = logging.getLogger(__name__)

_VALID_RISK_LEVELS = frozenset({'低風險', '中風險', '高風險'})
_VALID_SEVERITY = frozenset({'低', '中', '高'})
_MAX_WARNINGS = 8
_MAX_ERROR_ITEM_CHARS = 240
_MAX_SAMPLE_ROWS = 10
_MAX_TOP_ITEMS = 10


def build_audit_payload(
    recommendations: list,
    statistics: dict,
    quality_passed: Optional[bool],
    quality_errors: list,
    mode: str,
) -> dict:
    quality_errors_capped = [str(e)[:_MAX_ERROR_ITEM_CHARS] for e in (quality_errors or [])[:_MAX_SAMPLE_ROWS]]

    total_recommendations = len(recommendations)
    total_transfer_qty = sum(r.get('Transfer Qty', 0) for r in recommendations)

    payload = {
        'mode': mode or '',
        'quality_passed': quality_passed,
        'quality_error_count': len(quality_errors or []),
        'quality_errors': quality_errors_capped,
        'total_recommendations': total_recommendations,
        'total_transfer_qty': total_transfer_qty,
        'unique_articles': statistics.get('unique_articles', 0),
        'unique_oms': statistics.get('unique_oms', 0),
        'source_type_stats': statistics.get('source_type_stats', {}),
        'dest_type_stats': statistics.get('dest_type_stats', {}),
        'top_articles_by_qty': _top_articles_by_qty(recommendations),
        'top_transfer_sites_by_qty': _top_sites_by_qty(recommendations, 'Transfer Site'),
        'top_receive_sites_by_qty': _top_sites_by_qty(recommendations, 'Receive Site'),
        'cross_om_transfer_count': _count_cross_om(recommendations),
        'large_qty_recommendations': _capped_large_qty(recommendations),
    }
    return payload


def _top_articles_by_qty(recommendations: list) -> list:
    agg = {}
    for r in recommendations:
        article = r.get('Article', '')
        agg[article] = agg.get(article, 0) + r.get('Transfer Qty', 0)
    sorted_items = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:_MAX_TOP_ITEMS]
    return [{'article': a, 'qty': q} for a, q in sorted_items]


def _top_sites_by_qty(recommendations: list, site_key: str) -> list:
    agg = {}
    for r in recommendations:
        site = r.get(site_key, '')
        agg[site] = agg.get(site, 0) + r.get('Transfer Qty', 0)
    sorted_items = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:_MAX_TOP_ITEMS]
    return [{'site': s, 'qty': q} for s, q in sorted_items]


def _count_cross_om(recommendations: list) -> int:
    return sum(1 for r in recommendations if r.get('Transfer OM') != r.get('Receive OM'))


def _capped_large_qty(recommendations: list) -> list:
    sorted_recs = sorted(recommendations, key=lambda r: r.get('Transfer Qty', 0), reverse=True)
    fields = ['Article', 'Transfer OM', 'Transfer Site', 'Receive OM', 'Receive Site', 'Transfer Qty', 'Source Type', 'Destination Type']
    return [
        {k: r.get(k, '') for k in fields}
        for r in sorted_recs[:_MAX_SAMPLE_ROWS]
    ]


def build_auditor_messages(payload: dict) -> list:
    system = {
        'role': 'system',
        'content': (
            'You are an inventory audit specialist. '
            'Review the provided transfer recommendations payload and identify potential risks. '
            'Respond with ONLY a single JSON object. Do NOT add any markdown, explanation, or other text before or after the JSON. '
            'JSON keys: risk_level, summary, warnings, positive_checks. '
            'risk_level MUST be one of "低風險", "中風險", "高風險". '
            'summary is a brief risk overview (max 500 chars). '
            'warnings is a list of objects: {severity, title, detail, suggested_check}. '
            'severity must be "低", "中", or "高". Max 8 warnings. '
            'positive_checks is a list of strings noting good aspects. '
            'Answer ALL text content in Traditional Chinese (繁體中文). '
            'Example valid output: {"risk_level":"低風險","summary":"...","warnings":[],"positive_checks":["..."]}'
        ),
    }
    user = {
        'role': 'user',
        'content': json.dumps(payload, ensure_ascii=False, default=str),
    }
    return [system, user]


def _extract_json(text: str) -> str:
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence:
        inner = fence.group(1).strip()
        brace = _find_balanced_json(inner)
        if brace:
            return brace

    return _find_balanced_json(text) or ''


def _find_balanced_json(text: str) -> str:
    start = text.find('{')
    if start == -1:
        return ''
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\' and in_str:
            escape = True
            continue
        if c == '"' and not escape:
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return ''


def parse_audit_response(text: str) -> dict:
    if not text:
        return {'error': 'empty_response'}
    extracted = _extract_json(text)
    if not extracted:
        logger.warning("Auditor JSON parse failed — no JSON object found in response: %r", text[:512])
        return {'error': 'parse_failed'}
    try:
        parsed = json.loads(extracted)
    except json.JSONDecodeError:
        logger.warning("Auditor JSON parse failed — invalid JSON: %r", extracted[:512])
        return {'error': 'parse_failed'}
    if not isinstance(parsed, dict):
        return {'error': 'invalid_type'}
    return _validate_audit_result(parsed)


def _validate_audit_result(raw: dict) -> dict:
    risk_level = raw.get('risk_level', '低風險')
    if risk_level not in _VALID_RISK_LEVELS:
        risk_level = '低風險'

    summary = str(raw.get('summary', ''))[:500]

    warnings = raw.get('warnings', [])
    if not isinstance(warnings, list):
        warnings = []
    validated_warnings = []
    for w in warnings[:_MAX_WARNINGS]:
        if not isinstance(w, dict):
            continue
        severity = w.get('severity', '低')
        if severity not in _VALID_SEVERITY:
            severity = '低'
        validated_warnings.append({
            'severity': severity,
            'title': str(w.get('title', ''))[:160],
            'detail': str(w.get('detail', ''))[:400],
            'suggested_check': str(w.get('suggested_check', ''))[:400],
        })

    positive = raw.get('positive_checks', [])
    if not isinstance(positive, list):
        positive = []
    positive = [str(p)[:200] for p in positive[:8]]

    return {
        'risk_level': risk_level,
        'summary': summary,
        'warnings': validated_warnings,
        'positive_checks': positive,
    }


def audit_recommendations(
    recommendations: list,
    statistics: dict,
    quality_passed: Optional[bool],
    quality_errors: list,
    mode: str,
) -> dict:
    payload = build_audit_payload(recommendations, statistics, quality_passed, quality_errors, mode)
    messages = build_auditor_messages(payload)
    response = chat_completion(
        messages,
        model=config.AI_MODEL_AUDITOR,
        temperature=0.1,
        max_tokens=config.AI_MAX_TOKENS_AUDITOR,
        cache_namespace='auditor',
    )
    return parse_audit_response(response)
