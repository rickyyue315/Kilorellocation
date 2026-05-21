"""
模式定義 — 名稱映射、描述、接收限制模式列表
（v2.14.0 起由 mode_registry.py 衍生，保持向後兼容匯出）
"""

from typing import Dict, List

from models.mode_registry import MODE_DEFS


MODE_NAME_MAP: Dict[str, str] = {d.code: d.name for d in MODE_DEFS}

MODE_DESCRIPTIONS: Dict[str, str] = {
    f"{d.code}: {d.name}": d.description for d in MODE_DEFS
}

RECEIVE_SITE_LIMIT_MODE_CODES: List[str] = [
    d.code for d in MODE_DEFS if d.receive_site_limit
]
