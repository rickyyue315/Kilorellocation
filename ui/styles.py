"""
CSS 載入工具
"""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _read_css() -> str:
    css_path = Path(__file__).resolve().parent.parent / 'static' / 'styles.css'
    return css_path.read_text(encoding='utf-8')


def load_css() -> str:
    """讀取 styles.css，以 lru_cache 快取避免每次 rerun 都做磁碟 I/O。"""
    return _read_css()

