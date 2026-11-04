# -*- coding: utf-8 -*-
"""精簡SKU(限同OM) 剩餘庫存處理選項（退D001／不退D001）測試。"""

import pandas as pd

from business_logic import TransferLogic

ARTICLE = "000000000001"
COLUMNS = [
    "Article", "Article Description", "OM", "RP Type", "Site",
    "SaSa Net Stock", "Pending Received", "Safety Stock",
    "Last Month Sold Qty", "MTD Sold Qty", "MOQ",
    "Type", "Target", "ALL", "Supply source", "Last 2 Month Sold Qty",
]


def _row(site, om, rp="RF", net=0, pending=0, safety=0, lm=0, mtd=0,
         type_="", target="", all_="", supply=None, last2m=None, moq=1):
    return {
        "Article": ARTICLE,
        "Article Description": "TEST SKU",
        "OM": om,
        "RP Type": rp,
        "Site": site,
        "SaSa Net Stock": net,
        "Pending Received": pending,
        "Safety Stock": safety,
        "Last Month Sold Qty": lm,
        "MTD Sold Qty": mtd,
        "MOQ": moq,
        "Type": type_,
        "Target": target,
        "ALL": all_,
        "Supply source": supply,
        "Last 2 Month Sold Qty": lm if last2m is None else last2m,
    }


def _make_df(hd701_net=20):
    rows = [
        # 超 Cap 的 RF 來源：Cap = max(4×2, 3×2) = 8，可轉 net−8
        _row("HD701", "Ivy", net=hd701_net, safety=4, lm=3, last2m=3),
        # ND 來源全轉 5 件
        _row("HA702", "Ivy", rp="ND", net=5, lm=0),
        # RF 接收店：Cap = max(8×2, 5×2) = 16，欠 14
        _row("HD703", "Ivy", net=2, safety=8, lm=5, last2m=5),
        # 其他 OM 的接收店（限同OM 模式不應配對）
        _row("KD704", "Katy", net=3, safety=8, lm=6, last2m=6),
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["Effective Sold Qty"] = df["Last Month Sold Qty"] + df["MTD Sold Qty"]
    return df


def _run(mode, hd701_net=20, **kwargs):
    logic = TransferLogic(**kwargs)
    return logic.generate_transfer_recommendations(_make_df(hd701_net), mode)


def test_same_om_returns_d001_by_default():
    recs = _run("精簡SKU(限同OM)")
    d001 = [r for r in recs if r["Receive Site"] == "D001"]
    assert sum(r["Transfer Qty"] for r in d001) == 3
    assert sum(r["Transfer Qty"] for r in recs if r["Receive Site"] != "D001") == 14


def test_same_om_can_disable_d001_return():
    recs = _run("精簡SKU(限同OM)", sku_return_d001=False)
    assert all(r["Receive Site"] != "D001" for r in recs)
    assert sum(r["Transfer Qty"] for r in recs) == 14


def test_cross_om_keeps_d001_behaviour_regardless_of_option():
    recs = _run("精簡SKU(跨OM)", hd701_net=40, sku_return_d001=False)
    # 跨 OM 模式不受限同 OM 選項影響，仍會把配不完的貨退回 D001。
    # HD701 可轉 32：HD703 收 14、KD704 收 13；HD701 剩 5、HA702 ND 5 件亦無處可去 → 合計 10 件退 D001。
    d001 = [r for r in recs if r["Receive Site"] == "D001"]
    assert sum(r["Transfer Qty"] for r in d001) == 10


def test_return_all_mode_unaffected_by_option():
    recs = _run("精簡SKU(退D001)", sku_return_d001=False)
    assert recs
    assert all(r["Receive Site"] == "D001" for r in recs)
