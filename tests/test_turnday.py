# -*- coding: utf-8 -*-
"""
測試 Turnday 保底主體（v2.32.0）
覆蓋 services/turnday.py 的覆蓋日數計算、保底取代行為，
以及與調貨模式（Safety / Turnday 兩主體共用同一邏輯）的整合。
"""

from datetime import date
from typing import Any, Dict, List

import pandas as pd
import pytest

from business_logic import TransferLogic
from services.turnday import (
    apply_turnday_floor,
    compute_coverage_days,
    describe_coverage,
)


def _make_row(**overrides) -> Dict[str, Any]:
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
        "Type": "",
    }
    defaults.update(overrides)
    return defaults


def _make_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
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


# ── compute_coverage_days ─────────────────────────────────────────


class TestComputeCoverageDays:
    def test_normal_month(self):
        # 2026-08-15：7月31日 + MTD 15日 = 46
        assert compute_coverage_days(date(2026, 8, 15)) == 46

    def test_february_january_basis(self):
        # 2025-02-10（非閏年）：1月31日 + 10日 = 41
        assert compute_coverage_days(date(2025, 2, 10)) == 41

    def test_march_after_leap_february(self):
        # 2024-03-01（閏年）：2月29日 + 1日 = 30
        assert compute_coverage_days(date(2024, 3, 1)) == 30

    def test_march_after_normal_february(self):
        # 2025-03-01（非閏年）：2月28日 + 1日 = 29
        assert compute_coverage_days(date(2025, 3, 1)) == 29

    def test_year_boundary(self):
        # 2026-01-15：上年12月31日 + 15日 = 46
        assert compute_coverage_days(date(2026, 1, 15)) == 46

    def test_day_one(self):
        # 2026-08-01：7月31日 + 1日 = 32（MTD 最少覆蓋1日）
        assert compute_coverage_days(date(2026, 8, 1)) == 32

    def test_thirty_day_month(self):
        # 2026-05-31：4月30日 + 31日 = 61
        assert compute_coverage_days(date(2026, 5, 31)) == 61

    def test_describe_coverage_contains_total(self):
        text = describe_coverage(date(2026, 8, 15))
        assert "46日" in text
        assert "31日" in text
        assert "15日" in text


# ── apply_turnday_floor ───────────────────────────────────────────


class TestApplyTurndayFloor:
    AS_OF = date(2026, 8, 15)  # 覆蓋日數 46

    def test_replaces_safety_stock(self):
        df = _make_df([_make_row(Site="S1", **{"Effective Sold Qty": 92})])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        # 日銷速 = 92/46 = 2.0 → 保底 = ceil(2.0 × 14) = 28
        assert result.loc[0, "Safety Stock"] == 28

    def test_ceils_fractional_result(self):
        df = _make_df([_make_row(Site="S1", **{"Effective Sold Qty": 5})])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        # 5/46 × 14 = 1.52 → ceil = 2
        assert result.loc[0, "Safety Stock"] == 2

    def test_zero_sales_floor_is_zero(self):
        df = _make_df([_make_row(Site="S1", **{"Effective Sold Qty": 0})])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        assert result.loc[0, "Safety Stock"] == 0

    def test_backs_up_original_safety(self):
        df = _make_df([
            _make_row(Site="S1", **{"Safety Stock": 3, "Effective Sold Qty": 92}),
            _make_row(Site="S2", **{"Safety Stock": 8, "Effective Sold Qty": 0}),
        ])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        assert result.loc[0, "Original Safety Stock"] == 3
        assert result.loc[1, "Original Safety Stock"] == 8
        assert result.loc[1, "Safety Stock"] == 0

    def test_original_df_not_mutated(self):
        df = _make_df([_make_row(Site="S1", **{"Safety Stock": 3, "Effective Sold Qty": 92})])
        apply_turnday_floor(df, self.AS_OF, days=14)
        assert df.loc[0, "Safety Stock"] == 3
        assert "Original Safety Stock" not in df.columns

    def test_daily_sold_rate_column(self):
        df = _make_df([_make_row(Site="S1", **{"Effective Sold Qty": 92})])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        assert result.loc[0, "Daily Sold Rate"] == 2.0

    def test_effective_sold_unchanged(self):
        df = _make_df([_make_row(Site="S1", **{"Effective Sold Qty": 92})])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        assert result.loc[0, "Effective Sold Qty"] == 92

    def test_missing_effective_sold_treated_as_zero(self):
        df = _make_df([_make_row(Site="S1")])
        df = df.drop(columns=["Effective Sold Qty"])
        result = apply_turnday_floor(df, self.AS_OF, days=14)
        assert result.loc[0, "Safety Stock"] == 0

    def test_rejects_non_positive_days(self):
        df = _make_df([_make_row()])
        with pytest.raises(ValueError):
            apply_turnday_floor(df, self.AS_OF, days=0)


# ── 整合：Safety / Turnday 兩主體 × A 模式（同一邏輯） ────────────────


class TestFloorBodyMatrixWithModeA:
    """
    同一個 A 模式（保守轉貨），分別以 Safety / Turnday 主體運行：
    - 源店 SITE01：Net 40、Effective 5（非最高銷量，可轉出）
    - 收店 SITE02：Net 0、Effective 10（緊急缺貨）
    - AS_OF = 2026-08-15（覆蓋46日）、Turnday 日數 30：
      SITE01 保底 = ceil(5/46×30) = 4；SITE02 保底 = ceil(10/46×30) = 7
    """

    AS_OF = date(2026, 8, 15)
    TURNDAY_DAYS = 30

    def _build_df(self) -> pd.DataFrame:
        return _make_df([
            _make_row(Site="SITE01", **{
                "SaSa Net Stock": 40, "Safety Stock": 3,
                "Last Month Sold Qty": 4, "MTD Sold Qty": 1, "Effective Sold Qty": 5,
            }),
            _make_row(Site="SITE02", **{
                "SaSa Net Stock": 0, "Safety Stock": 3,
                "Last Month Sold Qty": 9, "MTD Sold Qty": 1, "Effective Sold Qty": 10,
            }),
        ])

    def test_safety_body_matches_existing_behavior(self):
        recs = TransferLogic().generate_transfer_recommendations(self._build_df(), "保守轉貨")
        assert len(recs) == 1
        # Safety 主體：接收量 = SITE02 的 Safety Stock = 3
        assert recs[0]["Receive Site"] == "SITE02"
        assert recs[0]["Transfer Qty"] == 3

    def test_turnday_body_flows_through_same_logic(self):
        df = apply_turnday_floor(self._build_df(), self.AS_OF, self.TURNDAY_DAYS)
        assert df.loc[0, "Safety Stock"] == 4   # SITE01 保底 ceil(5/46×30)
        assert df.loc[1, "Safety Stock"] == 7   # SITE02 保底 ceil(10/46×30)

        recs = TransferLogic().generate_transfer_recommendations(df, "保守轉貨")
        assert len(recs) == 1
        rec = recs[0]
        assert rec["Receive Site"] == "SITE02"
        # A 模式轉出上限 = max(40×0.2, 2) = 8；Turnday 接收需求 = 7
        assert rec["Transfer Qty"] == 7
        # 轉出後剩餘庫存不得低於 Turnday 保底（A 模式硬保底：剩餘 33 ≥ 4）
        assert 40 - rec["Transfer Qty"] >= 4

    def test_turnday_recommendation_stamps_floor_value(self):
        df = apply_turnday_floor(self._build_df(), self.AS_OF, self.TURNDAY_DAYS)
        recs = TransferLogic().generate_transfer_recommendations(df, "保守轉貨")
        # 建議上的 Safety 印章 = Turnday 保底值（欄位取代自動流轉）
        assert recs[0]["Safety Stock"] == 4            # 轉出店 SITE01 保底
        assert recs[0]["Receive Safety Stock"] == 7    # 接收店 SITE02 保底
