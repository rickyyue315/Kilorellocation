"""
Statistics service — computes aggregate stats from transfer recommendations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def compute_transfer_statistics(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not recommendations:
        return {}

    total_recommendations = len(recommendations)
    total_transfer_qty = sum(rec['Transfer Qty'] for rec in recommendations)
    unique_articles = len(set(rec['Article'] for rec in recommendations))
    unique_oms = len(set(rec['Transfer OM'] for rec in recommendations))

    article_stats = {}
    for rec in recommendations:
        article = rec['Article']
        if article not in article_stats:
            article_stats[article] = {
                'brand': rec.get('Brand') or rec.get('Product Hierarchy', ''),
                'product_desc': rec.get('Product Desc', ''),
                'total_qty': 0,
                'count': 0,
                'oms': set(),
            }
        article_stats[article]['total_qty'] += rec['Transfer Qty']
        article_stats[article]['count'] += 1
        article_stats[article]['oms'].add(rec['Transfer OM'])
    for article in article_stats:
        article_stats[article]['om_count'] = len(article_stats[article]['oms'])

    om_stats = {}
    for rec in recommendations:
        transfer_om = rec['Transfer OM']
        if transfer_om not in om_stats:
            om_stats[transfer_om] = {'total_qty': 0, 'transfer_qty': 0, 'receive_qty': 0, 'count': 0, 'articles': set()}
        om_stats[transfer_om]['total_qty'] += rec['Transfer Qty']
        om_stats[transfer_om]['transfer_qty'] += rec['Transfer Qty']
        om_stats[transfer_om]['count'] += 1
        om_stats[transfer_om]['articles'].add(rec['Article'])

        receive_om = rec['Receive OM']
        if receive_om not in om_stats:
            om_stats[receive_om] = {'total_qty': 0, 'transfer_qty': 0, 'receive_qty': 0, 'count': 0, 'articles': set()}
        om_stats[receive_om]['receive_qty'] += rec['Transfer Qty']
    for om in om_stats:
        om_stats[om]['article_count'] = len(om_stats[om]['articles'])

    source_type_stats = {}
    for rec in recommendations:
        source_type = rec.get('Source Type', 'Unknown')
        if source_type not in source_type_stats:
            source_type_stats[source_type] = {'count': 0, 'qty': 0}
        source_type_stats[source_type]['count'] += 1
        source_type_stats[source_type]['qty'] += rec['Transfer Qty']

    dest_type_stats = {}
    for rec in recommendations:
        dest_type = rec.get('Destination Type', 'Unknown')
        if dest_type not in dest_type_stats:
            dest_type_stats[dest_type] = {'count': 0, 'qty': 0}
        dest_type_stats[dest_type]['count'] += 1
        dest_type_stats[dest_type]['qty'] += rec['Transfer Qty']

    return {
        'total_recommendations': total_recommendations,
        'total_transfer_qty': total_transfer_qty,
        'unique_articles': unique_articles,
        'unique_oms': unique_oms,
        'article_stats': article_stats,
        'om_stats': om_stats,
        'source_type_stats': source_type_stats,
        'dest_type_stats': dest_type_stats,
    }


def compute_target_fulfillment_stats(recommendations: List[Dict[str, Any]],
                                     df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    From F/F2/F3 recommendations, compute per-(Article, Receive Site) target fulfillment.
    Only considers recs with a 'Target Qty' > 0 that came from target-mode matching.

    If `df` (the raw uploaded DataFrame) is provided, also includes Target>0 rows that
    have zero actual received (no recommendations generated), so every target is visible.

    Returns:
        dict with:
          - total_targets: number of (article, site) pairs with a target
          - fulfilled: count of those where received >= target
          - unfulfilled: count where received < target
          - fulfillment_rate: float 0-100
          - total_gap: sum of all gaps (target - received) where positive
          - details: list of dicts per pair
    """
    from collections import defaultdict

    from services.target_utils import parse_target_series

    fulfillment_map = defaultdict(lambda: {
        'brand': '', 'product_desc': '', 'receive_om': '', 'receive_site': '',
        'rp_type': '', 'target_qty': 0, 'actual_received': 0,
    })

    for rec in recommendations:
        target_qty = rec.get('Target Qty')
        if target_qty is None or target_qty <= 0:
            continue
        key = (rec['Article'], str(rec.get('Receive Site', '')).strip().upper())
        entry = fulfillment_map[key]
        entry['brand'] = rec.get('Brand') or rec.get('Product Hierarchy', '')
        entry['product_desc'] = rec.get('Product Desc', '')
        entry['receive_om'] = rec.get('Receive OM', '')
        entry['receive_site'] = rec.get('Receive Site', '')
        entry['rp_type'] = rec.get('Destination Type', '')
        entry['target_qty'] = int(target_qty)
        entry['actual_received'] += int(rec.get('Transfer Qty', 0))
        entry['article'] = rec['Article']

    if df is not None and 'Target' in df.columns:
        target_series = parse_target_series(df)
        for idx, row in df.iterrows():
            target_qty = target_series.loc[idx]
            if pd.isna(target_qty) or target_qty <= 0:
                continue
            key = (str(row.get('Article', '')), str(row.get('Site', '')).strip().upper())
            if key not in fulfillment_map:
                fulfillment_map[key] = {
                    'brand': str(row.get('Product Hierarchy', row.get('Brand', ''))),
                    'product_desc': str(row.get('Article Description', '')),
                    'receive_om': str(row.get('OM', '')),
                    'receive_site': str(row.get('Site', '')),
                    'rp_type': str(row.get('RP Type', '')),
                    'target_qty': int(target_qty),
                    'actual_received': 0,
                    'article': str(row.get('Article', '')),
                }

    details = []
    total_gap = 0
    total_target_qty = 0
    total_achieved_qty = 0
    fulfilled = 0
    unfulfilled = 0

    for key, entry in fulfillment_map.items():
        target = entry['target_qty']
        actual = entry['actual_received']
        total_target_qty += target
        total_achieved_qty += actual
        gap = max(target - actual, 0)
        if gap <= 0:
            fulfilled += 1
        else:
            unfulfilled += 1
        total_gap += gap
        entry['gap'] = gap
        entry['fulfillment_pct'] = round(actual / target * 100, 1) if target > 0 else 0.0
        entry['status'] = '已達成' if gap <= 0 else f'未達成(缺口{gap}件)'
        details.append(dict(entry))

    total_targets = len(details)
    details.sort(key=lambda x: (x['status'], -x['gap']))

    return {
        'total_targets': total_targets,
        'fulfilled': fulfilled,
        'unfulfilled': unfulfilled,
        'fulfillment_rate': round(fulfilled / total_targets * 100, 1) if total_targets > 0 else 0.0,
        'total_gap': total_gap,
        'total_target_qty': total_target_qty,
        'total_achieved_qty': total_achieved_qty,
        'details': details,
    }


def compute_nd_clearance_stats(
    recommendations: List[Dict[str, Any]],
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    D/D2 模式 — ND 清貨完成度分析。

    統計 Source Type == 'ND清貨轉出' 的 recommendation，計算每家 ND 店舖
    是否完全清出；若提供 df，則補上符合清貨條件但無任何 recommendation 的
    店舖（完全未清出）。

    Returns:
        dict with:
          - total_nd_sites
          - fully_cleared_sites
          - not_fully_cleared_sites
          - total_remaining_qty
          - article_summary (per-SKU aggregate)
          - details (per-store detail)
    """
    from collections import defaultdict

    # ── 從 recommendations 彙整 ──
    nd_site_map = defaultdict(lambda: {
        'article': '', 'brand': '', 'product_desc': '', 'transfer_om': '',
        'transfer_site': '', 'original_stock': 0, 'total_transferred': 0,
    })

    for rec in recommendations:
        if rec.get('Source Type') != 'ND清貨轉出':
            continue
        key = (rec['Article'], str(rec.get('Transfer Site', '')).strip().upper())
        entry = nd_site_map[key]
        entry['article'] = rec['Article']
        entry['brand'] = rec.get('Brand') or rec.get('Product Hierarchy', '')
        entry['product_desc'] = rec.get('Product Desc', '')
        entry['transfer_om'] = rec.get('Transfer OM', '')
        entry['transfer_site'] = rec.get('Transfer Site', '')
        entry['original_stock'] = rec.get('Original Stock', 0)
        entry['total_transferred'] += rec.get('Transfer Qty', 0)

    # ── 若提供 df，補上無 recommendation 的 ND 清貨來源 ──
    if df is not None and not df.empty:
        nd_sources = df[
            (df['RP Type'] == 'ND')
            & (df['SaSa Net Stock'] > 0)
            & (df['Last Month Sold Qty'] == 0)
            & (df['MTD Sold Qty'] == 0)
        ]
        for _, row in nd_sources.iterrows():
            site_key = str(row.get('Site', '')).strip().upper()
            article = str(row.get('Article', ''))
            detail_key = (article, site_key)
            if detail_key in nd_site_map:
                continue
            nd_site_map[detail_key] = {
                'article': article,
                'brand': str(row.get('Product Hierarchy', row.get('Brand', ''))),
                'product_desc': str(row.get('Article Description', '')),
                'transfer_om': str(row.get('OM', '')),
                'transfer_site': str(row.get('Site', '')),
                'original_stock': int(row.get('SaSa Net Stock', 0)),
                'total_transferred': 0,
            }

    # ── 計算明細與彙總 ──
    details = []
    article_agg: Dict[str, Dict] = {}

    for entry in nd_site_map.values():
        original = entry['original_stock']
        transferred = entry['total_transferred']
        remaining = original - transferred
        is_fully_cleared = remaining <= 0

        detail = {
            'article': entry['article'],
            'brand': entry['brand'],
            'product_desc': entry['product_desc'],
            'transfer_om': entry['transfer_om'],
            'transfer_site': entry['transfer_site'],
            'original_stock': original,
            'total_transferred_qty': transferred,
            'after_transfer_stock': max(remaining, 0),
            'is_fully_cleared': is_fully_cleared,
        }
        details.append(detail)

        # SKU 彙總
        art = entry['article']
        if art not in article_agg:
            article_agg[art] = {
                'article': art,
                'brand': entry['brand'],
                'product_desc': entry['product_desc'],
                'total_nd_sites': 0,
                'not_fully_cleared_site_count': 0,
                'total_remaining_qty': 0,
            }
        article_agg[art]['total_nd_sites'] += 1
        if not is_fully_cleared:
            article_agg[art]['not_fully_cleared_site_count'] += 1
            article_agg[art]['total_remaining_qty'] += max(remaining, 0)

    total_nd_sites = len(details)
    fully_cleared = sum(1 for d in details if d['is_fully_cleared'])
    not_fully_cleared = total_nd_sites - fully_cleared
    total_remaining_qty = sum(d['after_transfer_stock'] for d in details if not d['is_fully_cleared'])

    article_summary = sorted(article_agg.values(), key=lambda x: -x['total_remaining_qty'])
    details.sort(key=lambda x: (x['article'], x['transfer_site']))

    return {
        'total_nd_sites': total_nd_sites,
        'fully_cleared_sites': fully_cleared,
        'not_fully_cleared_sites': not_fully_cleared,
        'total_remaining_qty': total_remaining_qty,
        'article_summary': article_summary,
        'details': details,
    }
