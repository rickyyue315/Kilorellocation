"""
Statistics service — computes aggregate stats from transfer recommendations.
"""
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
