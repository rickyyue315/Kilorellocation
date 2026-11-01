"""審查文件用示範場景 — 全部以真實邏輯執行，輸出供文件引用。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sim_lab import make_df, row  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from business_logic import TransferLogic  # noqa: E402
from models.mode_registry import get_mode_def_by_code  # noqa: E402

SCENARIOS = {
    # ── A / B ──────────────────────────────────────────────
    "AB": [
        row("HC001", "Ivy", net=10, safety=4, lm=1),
        row("HC003", "Ivy", net=10, safety=4, lm=3),
        row("HA002", "Ivy", net=0, safety=8, lm=4, mtd=2),
    ],
    "A1": [
        row("HA010", "Ivy", rp="ND", net=6, lm=0),
        row("HA020", "Ivy", net=0, safety=5, lm=3),
    ],
    # ── B2（Type=L 保留） ─────────────────────────────────
    "B2L": [
        row("HL001", "Ivy", net=8, safety=2, lm=1, type_="L"),
        row("HL002", "Ivy", net=2, safety=2, lm=0, type_="L"),
        row("HT001", "Ivy", net=0, safety=12, lm=6, type_="T"),
    ],
    # ── B2a（T 不出貨） ───────────────────────────────────
    "B2A": [
        row("HT002", "Ivy", net=8, safety=2, lm=0, type_="T"),
        row("HM001", "Ivy", net=4, safety=2, lm=0, type_="M"),
        row("HM003", "Ivy", net=0, safety=6, lm=3, type_="M"),
    ],
    # ── B2La（L 保留 + T 不出） ───────────────────────────
    "B2LA": [
        row("HL001", "Ivy", net=8, safety=2, lm=1, type_="L"),
        row("HT002", "Ivy", net=8, safety=2, lm=0, type_="T"),
        row("HM003", "Ivy", net=0, safety=12, lm=3, type_="M"),
    ],
    # ── B3 家族（跨 OM + L/T） ────────────────────────────
    "B3": [
        row("HL961", "Ivy", net=8, safety=2, lm=1, type_="L"),
        row("HT962", "Ivy", net=8, safety=2, lm=0, type_="T"),
        row("KT963", "Katy", net=0, safety=12, lm=5, type_="T"),
    ],
    # ── C / C1 / C2 ───────────────────────────────────────
    "C": [
        row("HC101", "Ivy", net=10, safety=2, lm=1),
        row("HC102", "Ivy", net=4, safety=3, lm=2),
        row("HA103", "Ivy", net=0, safety=4, lm=3),
        row("HA104", "Ivy", net=1, safety=6, lm=0),
    ],
    "C2": [
        row("HC101", "Ivy", net=10, safety=2, lm=1),
        row("HC102", "Ivy", net=4, safety=3, lm=2),
        row("HA103", "Ivy", net=0, safety=4, lm=3),
        row("HA104", "Ivy", net=1, safety=6, lm=0),
        row("HC105", "Ivy", net=20, safety=5, lm=0),
        row("KA202", "Katy", net=0, safety=4, lm=2),
    ],
    # ── D / D2 ─────────────────────────────────────────────
    "D": [
        row("HA301", "Ivy", rp="ND", net=6, lm=0),
        row("HA302", "Ivy", rp="ND", net=5, lm=2),
        row("HC301", "Ivy", net=10, safety=4, lm=0),
        row("HD302", "Ivy", net=0, safety=6, lm=2),
        row("HD303", "Ivy", net=0, safety=5, lm=1),
    ],
    "D2SITE": [
        row("HA310", "Ivy", rp="ND", net=20, lm=0),
        row("HD311", "Ivy", net=0, safety=8, lm=1),
        row("HD312", "Ivy", net=0, safety=8, lm=1),
        row("HD313", "Ivy", net=0, safety=8, lm=1),
    ],
    # ── E1 / E1b / E2 ─────────────────────────────────────
    "E": [
        row("HC401", "Ivy", net=10, safety=4, all_="1", lm=1),
        row("HC402", "Ivy", net=4, safety=4, all_="1", lm=0),
        row("HD403", "Ivy", net=0, safety=2, lm=0),
        row("HT404", "Ivy", net=1, safety=1, lm=0, type_="T"),
        row("HM405", "Ivy", net=1, safety=1, lm=0, type_="M"),
        row("KD406", "Katy", net=0, safety=4, lm=3),
    ],
    # ── F 家族 ─────────────────────────────────────────────
    "F": [
        row("HT501", "Ivy", net=2, safety=4, lm=5, target=6, type_="T"),
        row("HA502", "Ivy", rp="ND", net=0, safety=4, lm=2, target=3),
        row("HT507", "Ivy", net=0, safety=4, lm=3, target=6, type_="T"),
        row("HC503", "Ivy", net=12, safety=4, lm=1),
        row("HC504", "Ivy", net=8, safety=4, lm=3),
        row("HC505", "Ivy", net=16, safety=4, lm=9),
        row("HC506", "Ivy", net=0, safety=4, lm=1),
    ],
    # ── ND 家族 ────────────────────────────────────────────
    "ND": [
        row("HA601", "Ivy", rp="ND", net=10, lm=0),
        row("HA602", "Ivy", rp="ND", net=20, lm=2),
        row("HA603", "Ivy", rp="ND", net=5, lm=4),
        row("HA604", "Ivy", rp="ND", net=0, safety=4, lm=2),
        row("HA605", "Ivy", rp="ND", net=1, safety=4, lm=2),
        row("HA607", "Ivy", rp="ND", net=0, safety=4, lm=0),
        row("HC606", "Ivy", net=0, safety=4, lm=5),
    ],
    "ND2": [
        row("HA601", "Ivy", rp="ND", net=10, lm=0),
        row("HA602", "Ivy", rp="ND", net=20, lm=2),
        row("HA604", "Ivy", rp="ND", net=0, safety=4, lm=2),
        row("HC606", "Ivy", net=0, safety=4, lm=5),
        row("KA607", "Katy", rp="ND", net=0, safety=6, lm=4),
        row("KA608", "Katy", rp="ND", net=8, lm=0),
    ],
    # ── SKU 家族 ───────────────────────────────────────────
    "SKU": [
        row("HC701", "Ivy", net=20, safety=4, lm=3, last2m=3),
        row("HA702", "Ivy", rp="ND", net=5, lm=0),
        row("HC703", "Ivy", net=2, safety=8, lm=5, last2m=5),
        row("KC704", "Katy", net=3, safety=8, lm=6, last2m=6),
    ],
}

# mode code → (scenario key, extra params)
RUNS = {
    "A": [("AB", {})],
    "A1": [("A1", {})],
    "B": [("AB", {})],
    "B2": [("B2L", {}), ("B2A", {})],
    "B2a": [("B2A", {})],
    "B2L": [("B2L", {})],
    "B2La": [("B2LA", {})],
    "B3": [("B3", {})],
    "B3a": [("B3", {})],
    "B3L": [("B3", {})],
    "B3La": [("B3", {})],
    "C": [("C", {})],
    "C1": [("C", {}), ("C", {"c1_threshold": 0})],
    "C2": [("C2", {})],
    "D": [("D", {})],
    "D2": [("D", {}), ("D2SITE", {}), ("D2SITE", {"d2_site_limit_mode": "2site_original"}),
           ("D2SITE", {"d2_site_limit_mode": "2site_optimized"})],
    "E1": [("E", {})],
    "E1b": [("E", {})],
    "E2": [("E", {})],
    "F": [("F", {})],
    "F2": [("F", {})],
    "F3": [("F", {})],
    "NST": [("F", {})],
    "ND1": [("ND", {})],
    "ND2": [("ND2", {})],
    "ND3": [("ND", {})],
    "ND4": [("ND", {})],
    "精簡SKU(限同OM)": [("SKU", {})],
    "精簡SKU(跨OM)": [("SKU", {})],
    "精簡SKU(退D001)": [("SKU", {})],
}


def execute(code, scenario_key, params):
    rows = SCENARIOS[scenario_key]
    df = make_df(rows)
    logic = TransferLogic(**params)
    name = get_mode_def_by_code(code).name
    recs = logic.generate_transfer_recommendations(df, name)
    return {
        "code": code,
        "mode": name,
        "scenario": scenario_key,
        "params": params,
        "rows": rows,
        "recs": recs,
        "quality": logic.perform_quality_checks(df, name),
    }


if __name__ == "__main__":
    for code, runs in RUNS.items():
        for key, params in runs:
            res = execute(code, key, params)
            print("=" * 90)
            print(f"{code} / {key} / {params}")
            print(f"{'Site':<8}{'RP':<3}{'Type':<5}{'Net':>4}{'Pend':>5}{'Saf':>4}{'LM':>4}{'MTD':>4}{'Tgt':>5}{'ALL':>4}")
            for r in res["rows"]:
                print(f"{r['Site']:<8}{r['RP Type']:<3}{r['Type']:<5}{r['SaSa Net Stock']:>4}"
                      f"{r['Pending Received']:>5}{r['Safety Stock']:>4}{r['Last Month Sold Qty']:>4}"
                      f"{r['MTD Sold Qty']:>4}{str(r['Target']):>5}{str(r['ALL']):>4}")
            for rec in res["recs"]:
                print(f"   {rec['Transfer Site']:>7} -> {rec['Receive Site']:<7} "
                      f"{rec['Transfer Qty']:>3} | {rec['Source Type']:<24} | {rec['Destination Type']}")
            if not res["recs"]:
                print("   (no recommendations)")
            print("   QC:", res["quality"])
