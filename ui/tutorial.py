"""教學分頁 — 30 模式邏輯審查（docs/KiLo_30模式邏輯審查.html 以 iframe 嵌入）
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_AUDIT_HTML_PATH = Path(__file__).resolve().parent.parent / 'docs' / 'KiLo_30模式邏輯審查.html'

# 嵌入 iframe 時隱藏文件內置目錄：它與 hero 標題重複，亦會與 Streamlit 側邊欄爭位。
# 下載的 HTML 仍保留完整目錄，不受此 CSS 影響。
_AUDIT_EMBED_CSS = """
<style id="kilo-audit-embed">
  .toc{display:none!important}
  .main{margin-left:0!important}
  .hero{padding:32px 0 26px;margin-bottom:24px}
</style>
"""


@st.cache_data(show_spinner=False, max_entries=2)
def _load_audit_html(path: str, mtime: float) -> str:
    """讀取完整邏輯審查 HTML；mtime 用作 cache key，重建文件後即自動更新。"""
    return Path(path).read_text(encoding="utf-8")


def _render_audit_page():
    """完整邏輯審查（docs/KiLo_30模式邏輯審查.html）以 iframe 嵌入。"""
    if not _AUDIT_HTML_PATH.exists():
        st.error("找不到 `docs/KiLo_30模式邏輯審查.html`。請先執行 `python audit/build_doc.py` 重建文件。")
        return

    mtime = _AUDIT_HTML_PATH.stat().st_mtime
    raw_html = _load_audit_html(str(_AUDIT_HTML_PATH), mtime)
    audit_html = raw_html
    if "</head>" in audit_html:
        audit_html = audit_html.replace("</head>", _AUDIT_EMBED_CSS + "</head>", 1)

    info_col, dl_col = st.columns([3.4, 1])
    with info_col:
        st.caption("需要目錄跳轉、全螢幕閱讀或列印（A4 橫向）？請下載 HTML。")
    with dl_col:
        st.download_button(
            "⬇️ 下載完整 HTML",
            data=raw_html.encode("utf-8"),
            file_name="KiLo_30模式邏輯審查.html",
            mime="text/html",
            help="下載後以瀏覽器開啟，可用目錄跳轉、全螢幕閱讀或列印為 PDF。",
        )

    components.html(audit_html, height=1250, scrolling=True)


def render_tutorial_page():
    _render_audit_page()
