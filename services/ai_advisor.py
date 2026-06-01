import json
import logging
import re
from typing import Optional

import pandas as pd

import config
from models.mode_registry import MODE_DEFS, get_mode_def_by_code
from services.ai_client import chat_completion

logger = logging.getLogger(__name__)

_VALID_CONFIDENCE = frozenset({'low', 'medium', 'high'})
_MAX_REASON_ITEMS = 5
_MAX_REASON_CHARS = 160
_MAX_WARNING_CHARS = 160


def build_df_summary(df: pd.DataFrame, processing_stats: Optional[dict] = None) -> dict:
    total_rows = len(df)
    unique_articles = df['Article'].nunique()
    unique_oms = df['OM'].nunique()
    unique_sites = df['Site'].nunique()

    rp_type_counts = {}
    if 'RP Type' in df.columns:
        rp_type_counts = df['RP Type'].value_counts().to_dict()

    nd_count = rp_type_counts.get('ND', 0)
    rf_count = rp_type_counts.get('RF', 0)
    nd_ratio = round(nd_count / total_rows, 3) if total_rows else 0
    rf_ratio = round(rf_count / total_rows, 3) if total_rows else 0

    net_stock_col = 'SaSa Net Stock' if 'SaSa Net Stock' in df.columns else None
    pending_col = 'Pending Received' if 'Pending Received' in df.columns else None
    safety_col = 'Safety Stock' if 'Safety Stock' in df.columns else None

    zero_stock_count = 0
    low_stock_count = 0
    stock_over_safety_count = 0
    if net_stock_col is not None and pending_col is not None:
        total_avail = df[net_stock_col].fillna(0) + df[pending_col].fillna(0)
        zero_stock_count = int((total_avail == 0).sum())
        low_stock_count = int((total_avail <= 1).sum())
        if safety_col is not None:
            stock_over_safety_count = int((total_avail > df[safety_col].fillna(0)).sum())

    has_type_column = 'Type' in df.columns
    type_counts = {}
    if has_type_column:
        type_series = df['Type'].dropna().astype(str)
        type_counts = type_series.value_counts().head(10).to_dict()

    has_target_column = 'Target' in df.columns
    target_positive_rows = 0
    target_positive_sites = 0
    if has_target_column:
        target_vals = pd.to_numeric(df['Target'], errors='coerce').fillna(0)
        target_positive_rows = int((target_vals > 0).sum())
        target_positive_sites = df.loc[target_vals > 0, 'Site'].nunique()

    has_all_column = 'ALL' in df.columns
    all_marked_rows = 0
    if has_all_column:
        all_marked_rows = int(df['ALL'].notna().sum())

    om_distribution_top10 = {}
    if 'OM' in df.columns:
        om_distribution_top10 = df['OM'].value_counts().head(10).to_dict()

    site_count_by_om_top10 = {}
    if 'OM' in df.columns and 'Site' in df.columns:
        site_count_by_om_top10 = {om: int(df[df['OM'] == om]['Site'].nunique()) for om in df['OM'].value_counts().head(10).index}

    cross_om_article_count = 0
    if 'OM' in df.columns and 'Article' in df.columns:
        om_per_article = df.groupby('Article')['OM'].nunique()
        cross_om_article_count = int((om_per_article > 1).sum())

    invalid_rp_type_count = 0
    if processing_stats:
        invalid_rp_type_count = processing_stats.get('processed_stats', {}).get('invalid_rp_type_count', 0)

    return {
        'total_rows': total_rows,
        'unique_articles': unique_articles,
        'unique_oms': unique_oms,
        'unique_sites': unique_sites,
        'rp_type_counts': rp_type_counts,
        'nd_ratio': nd_ratio,
        'rf_ratio': rf_ratio,
        'zero_stock_count': zero_stock_count,
        'low_stock_count': low_stock_count,
        'stock_over_safety_count': stock_over_safety_count,
        'has_type_column': has_type_column,
        'type_counts': type_counts,
        'has_target_column': has_target_column,
        'target_positive_rows': target_positive_rows,
        'target_positive_sites': target_positive_sites,
        'has_all_column': has_all_column,
        'all_marked_rows': all_marked_rows,
        'cross_om_article_count': cross_om_article_count,
        'om_distribution_top10': om_distribution_top10,
        'site_count_by_om_top10': site_count_by_om_top10,
        'invalid_rp_type_count': invalid_rp_type_count,
    }


def build_mode_options() -> list:
    return [
        {
            'code': d.code,
            'name': d.name,
            'description': d.description,
            'cross_om_matching': d.cross_om_matching,
            'receive_site_limit': d.receive_site_limit,
            'required_columns': sorted(d.required_columns),
        }
        for d in MODE_DEFS
    ]


def build_advisor_messages(summary: dict, mode_options: list) -> list:
    system = {
        'role': 'system',
        'content': (
            'You are an inventory reallocation mode advisor. '
            'Given a data summary and a list of available transfer modes, '
            'recommend the most suitable mode code. '
            'Consider ND/RF ratios, stock levels, cross-OM needs, Type/ALL/Target columns. '
            'Output ONLY valid JSON with keys: mode_code, mode_name, confidence, reasons, warnings. '
            'mode_code MUST be one of the provided option codes. '
            'confidence MUST be one of "low", "medium", "high". '
            'reasons is a list of 1-5 strings (max 160 chars each). '
            'warnings is a list of 0-5 strings (max 160 chars each). '
            'Answer ALL text content in Traditional Chinese (繁體中文). '
            'Do NOT output anything other than the JSON object.'
        ),
    }
    user = {
        'role': 'user',
        'content': json.dumps(
            {'data_summary': summary, 'available_modes': mode_options},
            ensure_ascii=False,
            default=str,
        ),
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


def parse_advisor_response(text: str) -> dict:
    if not text:
        return {'error': 'empty_response'}
    try:
        parsed = json.loads(_extract_json(text))
    except json.JSONDecodeError:
        logger.warning("Advisor JSON parse failed")
        return {'error': 'parse_failed', 'raw_text': text[:500]}
    if not isinstance(parsed, dict):
        return {'error': 'invalid_type'}
    return _validate_advisor_result(parsed)


def _validate_advisor_result(raw: dict) -> dict:
    code = raw.get('mode_code', '')
    mode_def = get_mode_def_by_code(code)
    if mode_def is None:
        return {'error': 'invalid_mode_code', 'code': code, 'raw_text': json.dumps(raw, ensure_ascii=False)[:500]}

    confidence = raw.get('confidence', 'low')
    if confidence not in _VALID_CONFIDENCE:
        confidence = 'low'

    reasons = raw.get('reasons', [])
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(r)[:_MAX_REASON_CHARS] for r in reasons[:_MAX_REASON_ITEMS]]

    warnings = raw.get('warnings', [])
    if not isinstance(warnings, list):
        warnings = []
    warnings = [str(w)[:_MAX_WARNING_CHARS] for w in warnings[:_MAX_REASON_ITEMS]]

    return {
        'mode_code': code,
        'mode_name': mode_def.name,
        'confidence': confidence,
        'reasons': reasons,
        'warnings': warnings,
    }


def recommend_mode(df: pd.DataFrame, processing_stats: Optional[dict] = None) -> dict:
    summary = build_df_summary(df, processing_stats)
    mode_options = build_mode_options()
    messages = build_advisor_messages(summary, mode_options)

    response = chat_completion(
        messages,
        model=config.AI_MODEL_ADVISOR,
        temperature=0.1,
        max_tokens=config.AI_MAX_TOKENS_ADVISOR,
        cache_namespace='advisor',
    )
    return parse_advisor_response(response)
