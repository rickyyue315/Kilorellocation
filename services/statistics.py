"""
Statistics service — computes aggregate stats from transfer recommendations.
"""
from typing import Any, Dict, List


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
            article_stats[article] = {'total_qty': 0, 'count': 0, 'oms': set()}
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
