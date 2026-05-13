"""
Quality check service — performs validation on transfer recommendations.
"""
import logging
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def run_quality_checks(
    recommendations: List[Dict[str, Any]],
    df: pd.DataFrame,
    skip_nd_check: bool = False,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    passed = True

    df_indexed = df.set_index(['Article', 'Site'])

    # 檢查1：轉出與接收的Article必須完全一致
    for rec in recommendations:
        if 'Article' not in rec:
            errors.append(f"調貨建議中缺少Article欄位: {rec}")
            passed = False

    # 檢查2：Transfer Qty必須為正整數
    for rec in recommendations:
        if not isinstance(rec['Transfer Qty'], int) or rec['Transfer Qty'] <= 0:
            errors.append(f"轉移數量必須為正整數: {rec}")
            passed = False

    # 檢查3：同一來源的累計Transfer Qty不得超過轉出店鋪的原始SaSa Net Stock
    cumulative_transfers_by_source = {}
    for rec in recommendations:
        source_key = (rec['Article'], rec['Transfer Site'])
        cumulative_transfers_by_source[source_key] = cumulative_transfers_by_source.get(source_key, 0) + rec['Transfer Qty']

    for (article, transfer_site), total_qty in cumulative_transfers_by_source.items():
        key = (article, transfer_site)
        if key in df_indexed.index:
            original_stock = df_indexed.at[key, 'SaSa Net Stock']
            if total_qty > original_stock:
                errors.append(f"累計轉移數量({total_qty})超過原始庫存({original_stock}) - Article: {article}, Site: {transfer_site}")
                passed = False

    # 檢查4：Transfer Site和Receive Site不能相同
    for rec in recommendations:
        if rec['Transfer Site'] == rec['Receive Site']:
            errors.append(f"轉出店鋪和接收店鋪不能相同: {rec}")
            passed = False

    # 檢查5：最終輸出的Article欄位必須是12位文本格式
    for rec in recommendations:
        if not isinstance(rec['Article'], str) or len(rec['Article']) != 12:
            errors.append(f"Article欄位必須是12位文本格式: {rec}")
            passed = False

    # 檢查6：同一SKU的轉出店鋪不能同時作為接收店鋪
    transfer_sites_by_article = {}
    receive_sites_by_article = {}
    for rec in recommendations:
        article = rec['Article']
        if article not in transfer_sites_by_article:
            transfer_sites_by_article[article] = set()
        transfer_sites_by_article[article].add(rec['Transfer Site'])
        if article not in receive_sites_by_article:
            receive_sites_by_article[article] = set()
        receive_sites_by_article[article].add(rec['Receive Site'])

    for article in transfer_sites_by_article:
        if article in receive_sites_by_article:
            overlap = transfer_sites_by_article[article] & receive_sites_by_article[article]
            if overlap:
                errors.append(f"同一SKU {article} 的轉出店鋪同時作為接收店鋪: {overlap}")
                passed = False

    # 檢查7：接收店鋪不能是ND類型
    if not skip_nd_check:
        for rec in recommendations:
            receive_site = rec['Receive Site']
            article = rec['Article']
            key = (article, receive_site)
            if key in df_indexed.index:
                rp_type = df_indexed.at[key, 'RP Type']
                if rp_type == 'ND':
                    errors.append(f"ND店鋪不能作為接收店鋪 - Site: {receive_site}, Article: {article}")
                    passed = False

    # 檢查8：對於C模式(重點補0)，檢查接收店鋪的累計接收數量是否超過目標數量
    receive_site_stats = {}
    for rec in recommendations:
        if rec.get('Destination Type') == '重點補0':
            key = (rec['Article'], rec['Receive Site'])
            if key not in receive_site_stats:
                receive_site_stats[key] = {
                    'target_qty': rec.get('Target Qty', 0),
                    'total_received': 0
                }
            receive_site_stats[key]['total_received'] += rec['Transfer Qty']

    for key, stats in receive_site_stats.items():
        article, site = key
        if stats['total_received'] > stats['target_qty']:
            errors.append(f"同一SKU {article} 的接收店鋪 {site} 累計接收數量超過目標數量: {stats['total_received']} > {stats['target_qty']}")
            passed = False

    return passed, errors
