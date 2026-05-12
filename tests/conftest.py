import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Set

import pandas as pd
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from business_logic import TransferLogic


@pytest.fixture
def logic():
    return TransferLogic()


def make_row(**overrides) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "Article": "000000000001",
        "Article Description": "Test Product",
        "OM": "OM1",
        "Site": "SITE01",
        "RP Type": "RF",
        "SaSa Net Stock": 10,
        "Pending Received": 0,
        "Safety Stock": 3,
        "Last Month Sold Qty": 2,
        "MTD Sold Qty": 1,
        "Last 2 Month Sold Qty": 2,
        "MOQ": 1,
        "Effective Sold Qty": 3,
        "Type": "R",
    }
    defaults.update(overrides)
    return defaults


def make_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ["Pending Received", "Safety Stock", "MOQ", "Effective Sold Qty"]:
        if col not in df.columns:
            df[col] = 0
    if "Article Description" not in df.columns:
        df["Article Description"] = "Test Product"
    if "ALL" not in df.columns:
        df["ALL"] = ""
    if "Target" not in df.columns:
        df["Target"] = ""
    if "Type" not in df.columns:
        df["Type"] = ""
    return df


def assert_no_dual_role(recs: List[Dict], label: str = ""):
    by_article_src: Dict[str, Set[str]] = defaultdict(set)
    by_article_dst: Dict[str, Set[str]] = defaultdict(set)
    for r in recs:
        by_article_src[r["Article"]].add(r["Transfer Site"])
        by_article_dst[r["Article"]].add(r["Receive Site"])
    for art in by_article_src:
        overlap = by_article_src[art] & by_article_dst.get(art, set())
        assert not overlap, f"{label} Article {art} dual-role: {overlap}"


def assert_nd_never_receives(recs: List[Dict], df: pd.DataFrame, label: str = ""):
    nd_sites = set(df.loc[df["RP Type"] == "ND", "Site"])
    for r in recs:
        assert r["Receive Site"] not in nd_sites, (
            f"{label} ND site {r['Receive Site']} received Article {r['Article']}"
        )
