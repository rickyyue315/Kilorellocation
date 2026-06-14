"""
Predicate functions shared across strategies
"""

from typing import Any, Dict, Optional, Set


def is_hd_to_hk_restricted(source_site: str, dest_site: str) -> bool:
    """Check if HD site is restricted from transferring to HA/HB/HC sites."""
    if not isinstance(source_site, str) or not source_site.upper().startswith('HD'):
        return False
    if not isinstance(dest_site, str):
        return False
    return dest_site.upper().startswith(('HA', 'HB', 'HC'))


def validate_pair(
    source: Dict[str, Any],
    dest: Dict[str, Any],
    transfer_sites: Set[str],
    receive_sites: Optional[Set[str]] = None,
    check_nd_receive: bool = True,
    check_source_in_receive_sites: bool = True,
    cross_om: bool = False,
    allow_hd_to_hk: bool = False,
    source_to_receive_sites: Optional[Dict[str, Set[str]]] = None,
    max_receive_sites_per_source: Optional[int] = None,
) -> bool:
    """
    Validate if a source-destination pair can transfer.
    
    Returns True if the pair is valid for transfer, False if blocked.
    
    Args:
        source: Source store dict
        dest: Destination store dict
        transfer_sites: Set of sites already acting as sources
        receive_sites: Set of sites already acting as destinations
        check_nd_receive: If True, block ND stores from receiving
        check_source_in_receive_sites: If True, block sources that are already destinations
        cross_om: If True, apply cross-OM constraints (Windy→Windy, HD→HK)
        allow_hd_to_hk: If True and cross_om is True, allow HD→HA/HB/HC transfers
        source_to_receive_sites: Dict tracking which sites each source has sent to
        max_receive_sites_per_source: Max number of distinct destinations per source
    """
    if source['site'] == dest['site']:
        return False
    
    if dest['site'] in transfer_sites:
        return False
    
    if check_source_in_receive_sites and receive_sites and source['site'] in receive_sites:
        return False
    
    if check_nd_receive and dest.get('rp_type') == 'ND':
        return False
    
    if cross_om:
        if source.get('om') == 'Windy' and dest.get('om') != 'Windy':
            return False
        if not allow_hd_to_hk and is_hd_to_hk_restricted(source['site'], dest['site']):
            return False
    
    if max_receive_sites_per_source is not None and source_to_receive_sites is not None:
        matched_sites = source_to_receive_sites.get(source['site'], set())
        if dest['site'] not in matched_sites and len(matched_sites) >= max_receive_sites_per_source:
            return False
    
    return True
