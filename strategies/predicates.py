"""
Predicate functions shared across strategies
"""

from typing import Any, Dict


def is_hd_to_hk_restricted(source_site: str, dest_site: str) -> bool:
    """Check if HD site is restricted from transferring to HA/HB/HC sites."""
    if not isinstance(source_site, str) or not source_site.upper().startswith('HD'):
        return False
    if not isinstance(dest_site, str):
        return False
    return dest_site.upper().startswith(('HA', 'HB', 'HC'))
