"""
CSS 載入工具
"""

from pathlib import Path


def load_css() -> str:
    css_path = Path(__file__).resolve().parent.parent / 'static' / 'styles.css'
    return css_path.read_text(encoding='utf-8')
