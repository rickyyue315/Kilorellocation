"""
模式邏輯審查 — 模擬工作台
以真實 business_logic.TransferLogic 跑出每個模式的實際輸出，
確保文件內的示例數字與程式一致。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from business_logic import TransferLogic  # noqa: E402
from models.mode_registry import get_mode_def_by_code  # noqa: E402

ARTICLE = "000000000001"
COLS = [
    "Article", "Article Description", "OM", "RP Type", "Site",
    "SaSa Net Stock", "Pending Received", "Safety Stock",
    "Last Month Sold Qty", "MTD Sold Qty", "MOQ",
    "Type", "Target", "ALL", "Supply source", "Last 2 Month Sold Qty",
]


def row(site, om, rp="RF", net=0, pending=0, safety=0, lm=0, mtd=0,
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
        "Last 2 Month Sold Qty": last_m if (last_m := last2m) is not None else lm,
    }


def make_df(rows):
    df = pd.DataFrame(rows, columns=COLS)
    df["Effective Sold Qty"] = df["Last Month Sold Qty"] + df["MTD Sold Qty"]
    return df


def run(name, rows, mode_code, **params):
    df = make_df(rows)
    logic = TransferLogic(**params)
    mode_def = get_mode_def_by_code(mode_code)
    mode = mode_def.name if mode_def else mode_code
    recs = logic.generate_transfer_recommendations(df, mode)

    print("=" * 78)
    print(f"{name} / {mode}")
    print("-" * 78)
    print(f"{'Site':<7}{'OM':<8}{'RP':<4}{'Type':<5}{'Net':>4}{'Pend':>5}{'Saf':>4}"
          f"{'LM':>4}{'MTD':>4}{'Tgt':>5}{'ALL':>4}")
    for r in rows:
        print(f"{r['Site']:<7}{r['OM']:<8}{r['RP Type']:<4}{r['Type']:<5}"
              f"{r['SaSa Net Stock']:>4}{r['Pending Received']:>5}{r['Safety Stock']:>4}"
              f"{r['Last Month Sold Qty']:>4}{r['MTD Sold Qty']:>4}"
              f"{str(r['Target']):>5}{str(r['ALL']):>4}")
    print("-" * 78)
    if not recs:
        print("(no recommendations)")
    for rec in recs:
        print(f"{rec['Transfer Site']:>7} -> {rec['Receive Site']:<7} "
              f"qty={rec['Transfer Qty']:>3}  {rec['Source Type']:<22} | "
              f"{rec['Destination Type']:<18} | {rec['Notes']}")
    print()


def main():
    # ── A / B ──────────────────────────────────────────────
    ab = [
        row("HD001", "Ivy", net=10, safety=4, lm=1),
        row("HD003", "Ivy", net=10, safety=4, lm=3),
        row("HD002", "Ivy", net=0, safety=8, lm=4, mtd=2),
    ]
    run("A/B", ab, "A")
    run("A/B", ab, "B")

    # ── A1 ─────────────────────────────────────────────────
    a1 = [
        row("HA010", "Ivy", rp="ND", net=6, safety=0, lm=0),
        row("HD020", "Ivy", net=0, safety=5, lm=3),
    ]
    run("A1", a1, "A")
    run("A1", a1, "A1")

    # ── B2 family ──────────────────────────────────────────
    b2 = [
        row("HA030", "Ivy", rp="ND", net=6, lm=0),
        row("HL001", "Ivy", net=8, safety=2, lm=1, type_="L"),
        row("HL002", "Ivy", net=2, safety=2, lm=0, type_="L"),
        row("HT001", "Ivy", net=0, safety=12, lm=6, type_="T"),
        row("HM001", "Ivy", net=2, safety=4, lm=1, type_="M"),
        row("HT002", "Ivy", net=8, safety=2, lm=0, type_="T"),
    ]
    for m in ["B2", "B2a", "B2L", "B2La"]:
        run("B2-family", b2, m)

    # ── C / C1 / C2 ────────────────────────────────────────
    c = [
        row("HD101", "Ivy", net=10, safety=2, lm=1),
        row("HD102", "Ivy", net=4, safety=3, lm=2),
        row("HD103", "Ivy", net=0, safety=4, lm=3),
        row("HD104", "Ivy", net=1, safety=6, lm=0),
    ]
    for m in ["C", "C1"]:
        run("C-family", c, m)

    c2 = c + [
        row("KD201", "Katy", net=20, safety=5, lm=0),
        row("KD202", "Katy", net=0, safety=4, lm=2),
    ]
    run("C2", c2, "C2")

    # ── D / D2 ─────────────────────────────────────────────
    d = [
        row("HA301", "Ivy", rp="ND", net=6, lm=0),
        row("HA302", "Ivy", rp="ND", net=5, lm=2),
        row("HD301", "Ivy", net=10, safety=4, lm=0),
        row("HD302", "Ivy", net=0, safety=6, lm=2),
        row("HD303", "Ivy", net=0, safety=5, lm=1),
    ]
    for m in ["D", "D2"]:
        run("D-family", d, m)

    # D2 2-site 對比
    d2sites = [row("HA310", "Ivy", rp="ND", net=20, lm=0)] + [
        row(f"HD31{i}", "Ivy", net=0, safety=8, lm=1) for i in range(1, 4)
    ]
    run("D2-2site", d2sites, "D2", d2_site_limit_mode="unlimited")
    run("D2-2site", d2sites, "D2", d2_site_limit_mode="2site_original")
    run("D2-2site", d2sites, "D2", d2_site_limit_mode="2site_optimized")

    # ── E1 / E1b / E2 ──────────────────────────────────────
    e = [
        row("HD401", "Ivy", net=10, safety=4, all_="1", lm=1),
        row("HD402", "Ivy", net=4, safety=4, all_="1", lm=0),
        row("HD403", "Ivy", net=0, safety=2, lm=0),
        row("HT404", "Ivy", net=1, safety=1, lm=0, type_="T"),
        row("HM405", "Ivy", net=1, safety=1, lm=0, type_="M"),
        row("KD406", "Katy", net=0, safety=4, lm=3),
    ]
    for m in ["E1", "E1b"]:
        run("E-family", e, m)
    run("E2", e, "E2")

    # ── F / F2 / F3 / NST ──────────────────────────────────
    f = [
        row("HT501", "Ivy", net=2, safety=4, lm=5, target=6),
        row("HA502", "Ivy", rp="ND", net=0, safety=4, lm=2, target=3),
        row("HD503", "Ivy", net=12, safety=4, lm=1),
        row("HD504", "Ivy", net=8, safety=4, lm=3),
        row("HD505", "Ivy", net=16, safety=4, lm=9),
        row("HD506", "Ivy", net=0, safety=4, lm=1),
    ]
    for m in ["F", "F2", "F3", "NST"]:
        run("F-family", f, m)

    # ── ND1–ND4 ────────────────────────────────────────────
    nd = [
        row("HA601", "Ivy", rp="ND", net=10, lm=0),
        row("HA602", "Ivy", rp="ND", net=20, lm=2),
        row("HA603", "Ivy", rp="ND", net=5, lm=4),
        row("HA604", "Ivy", rp="ND", net=0, safety=4, lm=2),
        row("HA605", "Ivy", rp="ND", net=1, safety=4, lm=2),
        row("HD606", "Ivy", net=0, safety=4, lm=5),
    ]
    for m in ["ND1", "ND3", "ND4"]:
        run("ND-family", nd, m)
    nd2 = nd + [
        row("KA607", "Katy", rp="ND", net=0, safety=6, lm=4),
        row("KA608", "Katy", rp="ND", net=8, lm=0),
    ]
    run("ND2", nd2, "ND2")

    # ── SKU family ─────────────────────────────────────────
    sku = [
        row("HD701", "Ivy", net=20, safety=4, lm=3, last2m=3),
        row("HA702", "Ivy", rp="ND", net=5, lm=0),
        row("HD703", "Ivy", net=2, safety=8, lm=5, last2m=5),
        row("KD704", "Katy", net=3, safety=8, lm=6, last2m=6),
    ]
    for m in ["精簡SKU(限同OM)", "精簡SKU(跨OM)", "精簡SKU(退D001)"]:
        run("SKU-family", sku, m)
    run("SKU-family(不退D001)", sku, "精簡SKU(限同OM)", sku_return_d001=False)


if __name__ == "__main__":
    main()
