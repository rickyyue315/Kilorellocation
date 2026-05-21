"""
匹配引擎模組 — 核心配對邏輯、前置過濾、轉移量計算、通用模式多回合匹配
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from services.recommendation_factory import build_recommendation, apply_transfer
from strategies.predicates import is_hd_to_hk_restricted


def compute_transfer_qty(logic, source: Dict, dest: Dict, mode: str, current_received_qty: int) -> int:
    transfer_qty = min(source['transferable_qty'], dest['needed_qty'])

    if logic._is_b_special_mode(mode) and 'target_qty' in dest:
        remaining_capacity = dest['target_qty'] - current_received_qty
        transfer_qty = min(transfer_qty, remaining_capacity)
    elif dest['dest_type'] == '重點補0' and 'target_qty' in dest:
        remaining_needed = dest['target_qty'] - current_received_qty
        transfer_qty = min(transfer_qty, remaining_needed)
    elif logic._is_d_family_mode(mode) and 'target_qty' in dest:
        remaining_capacity = dest['target_qty'] - current_received_qty
        transfer_qty = min(transfer_qty, remaining_capacity)

    if logic._is_d_family_mode(mode) and source['rp_type'] == 'ND':
        final_remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
        if final_remaining == 1:
            if source['transferable_qty'] >= transfer_qty + 1:
                transfer_qty += 1
            elif transfer_qty > 1:
                transfer_qty -= 1

    if transfer_qty == 1 and source['transferable_qty'] >= 2:
        if source['source_type'] in ['ND轉出', 'ND清貨轉出', 'RF加強轉出', 'RF過剩轉出']:
            already_out_opt = source.get('total_transferred', 0)
            remaining_after_opt = source['original_stock'] - already_out_opt - 2
            if logic._is_d_family_mode(mode) and source['rp_type'] == 'ND' and remaining_after_opt == 1:
                if source['transferable_qty'] >= 3:
                    transfer_qty = 3
            else:
                if dest['needed_qty'] >= 2 or (mode == logic.mode_a and source['source_type'] == 'RF過剩轉出'):
                    transfer_qty = 2

    transfer_qty = min(transfer_qty, source['transferable_qty'])

    if logic._is_b_special_mode(mode) and 'target_qty' in dest:
        transfer_qty = min(transfer_qty, max(dest['target_qty'] - current_received_qty, 0))
    elif dest['dest_type'] == '重點補0' and 'target_qty' in dest:
        transfer_qty = min(transfer_qty, max(dest['target_qty'] - current_received_qty, 0))
    elif logic._is_d_family_mode(mode) and 'target_qty' in dest:
        transfer_qty = min(transfer_qty, max(dest['target_qty'] - current_received_qty, 0))

    if logic._is_d_family_mode(mode) and source['rp_type'] == 'ND':
        final_remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
        if final_remaining == 1:
            if source['transferable_qty'] >= transfer_qty + 1:
                transfer_qty += 1
            elif transfer_qty > 1:
                transfer_qty -= 1

    return max(transfer_qty, 0)


def can_transfer(logic, source: Dict, dest: Dict, mode: str, article: str,
                 transfer_sites: set, receive_sites: set,
                 source_to_receive_sites: Dict, received_qty_by_site: Dict,
                 source_type_filter: Optional[str] = None) -> bool:
    if source['site'] == dest['site']:
        return False
    if dest['site'] in transfer_sites:
        return False
    if source['site'] in receive_sites:
        return False
    if dest.get('rp_type') == 'ND':
        return False

    if logic.b_special_max_receive_sites_per_source is not None:
        source_site = source.get('site')
        matched_sites = source_to_receive_sites.get(source_site, set())
        if dest.get('site') not in matched_sites and len(matched_sites) >= logic.b_special_max_receive_sites_per_source:
            return False

    if source.get('om') and dest.get('om') and source.get('om') != dest.get('om'):
        if is_hd_to_hk_restricted(source.get('site', ''), dest.get('site', '')):
            return False
        if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
            return False

    if logic._is_b3_family_mode(mode):
        if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
            return False
        if is_hd_to_hk_restricted(source.get('site', ''), dest.get('site', '')):
            return False

    if logic._is_b_special_mode(mode) and str(source.get('store_type', '')).upper() == 'M':
        source_sales_total = logic._get_b_special_sales_total(source)
        dest_sales_total = logic._get_b_special_sales_total(dest)
        if source_sales_total > 0 and source_sales_total > dest_sales_total:
            return False

    receive_site_key = f"{dest['site']}_{article}"
    current_received_qty = received_qty_by_site.get(receive_site_key, 0)

    if logic._is_b_special_mode(mode) and 'target_qty' in dest:
        if current_received_qty >= dest['target_qty']:
            return False

    if dest['dest_type'] == '重點補0' and 'target_qty' in dest:
        if current_received_qty >= dest['target_qty']:
            return False

    if logic._is_d_family_mode(mode) and 'target_qty' in dest:
        if current_received_qty >= dest['target_qty']:
            return False

    return True


def match_by_priority(logic, sources: List[Dict], destinations: List[Dict],
                      recommendations: List[Dict], article: str, group_id: str,
                      product_desc: str, source_priority: int, dest_priority: int,
                      transfer_sites: set, received_qty_by_site: Dict,
                      mode: str,
                      source_type_filter: Optional[str] = None,
                      dest_type_filter: Optional[str] = None,
                      receive_sites: set = None,
                      source_to_receive_sites: Optional[Dict[str, set]] = None,
                      max_receive_sites_per_source: Optional[int] = None):
    if receive_sites is None:
        receive_sites = set()
    if source_to_receive_sites is None:
        source_to_receive_sites = {}

    filtered_sources = [s for s in sources if s['priority'] == source_priority and s['transferable_qty'] > 0]

    if mode == logic.mode_c1:
        filtered_sources.sort(
            key=lambda x: (
                -int(x.get('transferable_qty', 0)),
                int(x.get('effective_sold_qty', 0))
            )
        )

    if source_type_filter:
        filtered_sources = [s for s in filtered_sources if s['source_type'] == source_type_filter]

    filtered_destinations = [d for d in destinations if d['priority'] == dest_priority and d['needed_qty'] > 0]

    if dest_type_filter:
        filtered_destinations = [d for d in filtered_destinations if d['dest_type'] == dest_type_filter]

    for source in filtered_sources:
        source_added_to_transfer = source['site'] in transfer_sites

        for dest in filtered_destinations:
            if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                continue

            if not can_transfer(logic, source, dest, mode, article, transfer_sites, receive_sites,
                                source_to_receive_sites, received_qty_by_site, source_type_filter):
                continue

            receive_site_key = f"{dest['site']}_{article}"
            current_received_qty = received_qty_by_site.get(receive_site_key, 0)

            transfer_qty = compute_transfer_qty(logic, source, dest, mode, current_received_qty)

            if transfer_qty <= 0:
                continue

            notes = logic._create_recommendation_note(source, dest, current_received_qty, transfer_qty, mode)
            recommendation = build_recommendation(article, product_desc, source, dest, transfer_qty, notes, current_received_qty)
            recommendations.append(recommendation)

            apply_transfer(source, dest, transfer_qty, received_qty_by_site, receive_site_key, current_received_qty)

            if source['site'] not in transfer_sites:
                transfer_sites.add(source['site'])

            receive_sites.add(dest['site'])

            source_site = source.get('site')
            matched_sites = source_to_receive_sites.setdefault(source_site, set())
            matched_sites.add(dest['site'])

            if dest['dest_type'] == '重點補0' and received_qty_by_site[receive_site_key] >= dest.get('target_qty', float('inf')):
                dest['needed_qty'] = 0
            elif logic._is_b_special_mode(mode) and 'target_qty' in dest and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                dest['needed_qty'] = 0
            elif logic._is_d_family_mode(mode) and 'target_qty' in dest and received_qty_by_site[receive_site_key] >= dest['target_qty']:
                dest['needed_qty'] = 0


def match_general_mode(logic, sources: List[Dict], destinations: List[Dict],
                       article: str, om: str, product_desc: str, mode: str) -> List[Dict]:
    recommendations = []

    temp_sources = [s.copy() for s in sources]
    for s in temp_sources:
        s['total_transferred'] = 0
    temp_destinations = [d.copy() for d in destinations]

    transfer_sites = set()
    receive_sites = set()
    received_qty_by_site = {}

    if mode == logic.mode_c:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode, None, '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 2, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites)

    if mode == logic.mode_c1:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出', '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出',
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出',
                      receive_sites=receive_sites)

    if mode == logic.mode_c:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出', '重點補0',
                          receive_sites=receive_sites)

    if mode == logic.mode_c1:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出', '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出',
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF加強轉出',
                      receive_sites=receive_sites)

    if mode == logic.mode_c:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出', '重點補0',
                          receive_sites=receive_sites)

    return recommendations
