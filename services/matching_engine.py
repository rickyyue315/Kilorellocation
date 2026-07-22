"""
匹配引擎模組 — 核心配對邏輯、前置過濾、轉移量計算、通用模式多回合匹配

架構說明（效能擴展準備）：
- can_transfer / compute_transfer_qty 接近純函式，僅依賴 logic 的：
  - MODE_FAMILIES（可用 frozen dict 替代）
  - b_special_max_receive_sites_per_source（數值）
  - _is_*_mode() 方法（可用 frozenset membership 替代）
  - _get_b_special_sales_total()（純計算）
- match_by_priority / match_general_mode 透過 can_transfer/compute_transfer_qty 間接純函式化
- 若需平行化：
  1. 將 logic 依賴提取為 frozen dataclass ModeContext
  2. 各函式改為 (ctx: ModeContext, ...) 簽名
  3. 使用 multiprocessing.Pool 或 concurrent.futures 按 Article 分組平行執行
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from services.recommendation_factory import build_recommendation, apply_transfer
from strategies.predicates import is_hd_to_hk_restricted


def _clamp_target_qty(is_b_special: bool, is_d_family: bool, dest: Dict,
                      transfer_qty: int, current_received_qty: int) -> int:
    if 'target_qty' not in dest:
        return transfer_qty
    if is_b_special or dest['dest_type'] == '重點補0' or is_d_family:
        return min(transfer_qty, max(dest['target_qty'] - current_received_qty, 0))
    return transfer_qty


def _adjust_d_family_remainder(is_d_family: bool, source: Dict, transfer_qty: int) -> int:
    if not is_d_family or source['rp_type'] != 'ND':
        return transfer_qty
    final_remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
    if final_remaining != 1:
        return transfer_qty
    if source['transferable_qty'] >= transfer_qty + 1:
        return transfer_qty + 1
    if transfer_qty > 1:
        return transfer_qty - 1
    return transfer_qty


def _adjust_a1_remainder(logic, mode: str, source: Dict, dest: Dict, transfer_qty: int,
                         current_received_qty: int = 0) -> int:
    if mode != logic.mode_a1:
        return transfer_qty
    final_remaining = source['original_stock'] - source.get('total_transferred', 0) - transfer_qty
    if final_remaining != 1:
        return transfer_qty
    if source['transferable_qty'] >= transfer_qty + 1:
        target_qty = dest.get('target_qty')
        max_receive = (target_qty + 1) if target_qty is not None and target_qty > 0 else (current_received_qty + transfer_qty + 1)
        if current_received_qty + transfer_qty + 1 <= max_receive:
            return transfer_qty + 1
    if transfer_qty > 1:
        return transfer_qty - 1
    return transfer_qty


def prep_temp_lists(sources: List[Dict], destinations: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    temp_sources = [{**s, 'total_transferred': 0} for s in sources]
    temp_destinations = [d.copy() for d in destinations]
    return temp_sources, temp_destinations


def compute_transfer_qty(logic, source: Dict, dest: Dict, mode: str, current_received_qty: int) -> int:
    is_b_special = logic._is_b_special_mode(mode)
    is_d_family = logic._is_d_family_mode(mode)

    transfer_qty = min(source['transferable_qty'], dest['needed_qty'])

    transfer_qty = _clamp_target_qty(is_b_special, is_d_family, dest, transfer_qty, current_received_qty)
    transfer_qty = _adjust_d_family_remainder(is_d_family, source, transfer_qty)
    transfer_qty = _adjust_a1_remainder(logic, mode, source, dest, transfer_qty, current_received_qty)

    if transfer_qty == 1 and source['transferable_qty'] >= 2:
        if source['source_type'] in ('ND轉出', 'ND清貨轉出', 'RF加強轉出', 'RF過剩轉出'):
            already_out_opt = source.get('total_transferred', 0)
            remaining_after_opt = source['original_stock'] - already_out_opt - 2
            if is_d_family and source['rp_type'] == 'ND' and remaining_after_opt == 1:
                if source['transferable_qty'] >= 3:
                    transfer_qty = 3
            else:
                if dest['needed_qty'] >= 2 or (mode in (logic.mode_a, logic.mode_a1) and source['source_type'] == 'RF過剩轉出'):
                    transfer_qty = 2

    transfer_qty = min(transfer_qty, source['transferable_qty'])

    transfer_qty = _clamp_target_qty(is_b_special, is_d_family, dest, transfer_qty, current_received_qty)
    transfer_qty = _adjust_d_family_remainder(is_d_family, source, transfer_qty)
    transfer_qty = _adjust_a1_remainder(logic, mode, source, dest, transfer_qty, current_received_qty)

    if mode == logic.mode_c1 and transfer_qty < 2:
        return 0

    return max(transfer_qty, 0)


def can_transfer(logic, source: Dict, dest: Dict, mode: str, article: str,
                 transfer_sites: set, receive_sites: set,
                 source_to_receive_sites: Dict, received_qty_by_site: Dict,
                 source_type_filter: Optional[str] = None,
                 max_receive_sites_per_source: Optional[int] = None) -> bool:
    if source['site'] == dest['site']:
        return False
    if dest['site'] in transfer_sites:
        return False
    if source['site'] in receive_sites:
        return False
    if dest.get('rp_type') == 'ND':
        return False

    limit = max_receive_sites_per_source if max_receive_sites_per_source is not None else logic.b_special_max_receive_sites_per_source
    if limit is not None:
        source_site = source.get('site')
        matched_sites = source_to_receive_sites.get(source_site, set())
        if dest.get('site') not in matched_sites and len(matched_sites) >= limit:
            return False

    is_cross_om = bool(source.get('om') and dest.get('om') and source.get('om') != dest.get('om'))
    if is_cross_om:
        if is_hd_to_hk_restricted(source.get('site', ''), dest.get('site', '')):
            return False
        if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
            return False
    elif logic._is_b3_family_mode(mode):
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

    is_b_special = logic._is_b_special_mode(mode)
    is_d_family = logic._is_d_family_mode(mode)

    if 'target_qty' in dest and (is_b_special or dest['dest_type'] == '重點補0' or is_d_family):
        if current_received_qty >= dest['target_qty']:
            return False

    return True


def _mark_dest_saturated(mode: str, dest: Dict, received_qty_by_site: Dict,
                         receive_site_key: str, is_b_special: bool, is_d_family: bool):
    received = received_qty_by_site.get(receive_site_key, 0)
    if 'target_qty' in dest and (dest['dest_type'] == '重點補0' or is_b_special or is_d_family):
        if received >= dest['target_qty']:
            dest['needed_qty'] = 0


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

    is_b_special = logic._is_b_special_mode(mode)
    is_d_family = logic._is_d_family_mode(mode)

    for source in filtered_sources:
        for dest in filtered_destinations:
            if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                continue

            if not can_transfer(logic, source, dest, mode, article, transfer_sites, receive_sites,
                                source_to_receive_sites, received_qty_by_site, source_type_filter,
                                max_receive_sites_per_source):
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

            _mark_dest_saturated(mode, dest, received_qty_by_site, receive_site_key, is_b_special, is_d_family)


def match_d2_mode(logic, sources: List[Dict], destinations: List[Dict],
                  article: str, om: str, product_desc: str, mode: str) -> List[Dict]:
    recommendations = []
    temp_sources, temp_destinations = prep_temp_lists(sources, destinations)
    transfer_sites = set()
    receive_sites = set()
    received_qty_by_site = {}
    source_to_receive_sites = {}
    max_receive = 2

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites,
                      source_to_receive_sites=source_to_receive_sites,
                      max_receive_sites_per_source=max_receive)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 2, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites,
                      source_to_receive_sites=source_to_receive_sites,
                      max_receive_sites_per_source=max_receive)

    return recommendations


def match_general_mode(logic, sources: List[Dict], destinations: List[Dict],
                       article: str, om: str, product_desc: str, mode: str) -> List[Dict]:
    recommendations = []

    temp_sources, temp_destinations = prep_temp_lists(sources, destinations)

    transfer_sites = set()
    receive_sites = set()
    received_qty_by_site = {}

    is_c_mode = (mode == logic.mode_c)
    is_c1_mode = (mode == logic.mode_c1)

    if is_c_mode:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode, None, '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 1, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 1, 2, transfer_sites, received_qty_by_site, mode,
                      receive_sites=receive_sites)

    if is_c_mode:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出', '重點補0',
                          receive_sites=receive_sites)

    if is_c1_mode:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出', '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出',
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF過剩轉出',
                      receive_sites=receive_sites)

    if is_c_mode:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出', '重點補0',
                          receive_sites=receive_sites)

    if is_c1_mode:
        match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                          article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出', '重點補0',
                          receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 1, transfer_sites, received_qty_by_site, mode, 'RF加強轉出',
                      receive_sites=receive_sites)

    match_by_priority(logic, temp_sources, temp_destinations, recommendations,
                      article, om, product_desc, 2, 2, transfer_sites, received_qty_by_site, mode, 'RF加強轉出',
                      receive_sites=receive_sites)

    return recommendations
