"""
模式定義 — 枚舉、名稱映射、描述、純函式謂詞
"""

from enum import Enum
from typing import Dict


class Mode(Enum):
    A = "A"
    B = "B"
    B2 = "B2"
    B2a = "B2a"
    B2L = "B2L"
    B2La = "B2La"
    B3 = "B3"
    B3a = "B3a"
    B3L = "B3L"
    B3La = "B3La"
    C = "C"
    C1 = "C1"
    C2 = "C2"
    D = "D"
    D2 = "D2"
    E1 = "E1"
    E1b = "E1b"
    E2 = "E2"
    F = "F"
    F2 = "F2"
    ND1 = "ND1"
    ND2 = "ND2"
    SIMPLIFIED_SKU_SAME = "精簡SKU(限同OM)"
    SIMPLIFIED_SKU_CROSS = "精簡SKU(跨OM)"


MODE_NAME_MAP: Dict[str, str] = {
    "A": "保守轉貨",
    "B": "加強轉貨",
    "B2": "附加B(特別模式)",
    "B2a": "附加B2a(特別模式-T遊客鋪不出貨)",
    "B2L": "附加B2L(特別模式-Type=L保留2件)",
    "B2La": "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
    "B3": "附加B3(跨OM特別模式)",
    "B3a": "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "B3L": "附加B3L(跨OM特別模式-Type=L保留2件)",
    "B3La": "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
    "C": "重點補0",
    "C1": "重點補0-只補0/1",
    "C2": "附加C2(跨OM重點補0)",
    "D": "清貨轉貨",
    "D2": "清貨轉貨(ND限定)",
    "E1": "強制轉出",
    "E1b": "強制轉出(優先類型接收)",
    "E2": "強制轉出(跨OM)",
    "F": "目標優化",
    "F2": "F指定模式",
    "ND1": "ND同OM轉貨",
    "ND2": "ND混合OM轉貨",
    "精簡SKU(限同OM)": "精簡SKU(限同OM)",
    "精簡SKU(跨OM)": "精簡SKU(跨OM)",
}

MODE_DESCRIPTIONS: Dict[str, str] = {
    "A: 保守轉貨": "轉出後保留安全庫存，單件自動上調至2件",
    "B: 加強轉貨": "積極處理滯銷品",
    "B2: 附加B(特別模式)": "B模式 + Type=L全轉出 + Mix高銷量保護",
    "B2a: 附加B2a(特別模式-T遊客鋪不出貨)": "B2 + Type=T遊客鋪不出貨 + Mix高銷量保護",
    "B2L: 附加B2L(特別模式-Type=L保留2件)": "B2L模式 + Type=L低銷量保留2件 + Mix高銷量保護",
    "B2La: 附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)": "B2L + Type=T遊客鋪不出貨 + Mix高銷量保護",
    "B3: 附加B(跨OM特別模式)": "B2 + 跨OM配對 + Mix高銷量保護",
    "B3a: 附加B3a(跨OM特別模式-T遊客鋪不出貨)": "B3 + Type=T遊客鋪不出貨 + Mix高銷量保護",
    "B3L: 附加B3L(跨OM特別模式-Type=L保留2件)": "B3L模式 + 跨OM配對 + Type=L低銷量保留2件 + Mix高銷量保護",
    "B3La: 附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)": "B3L + Type=T遊客鋪不出貨 + Mix高銷量保護",
    "C: 重點補0": "補充庫存≤1的店舖",
    "C1: 重點補0(只補0/1)": "僅補total_available≤1，不回落一般缺貨",
    "C2: 附加C(跨OM重點補0)": "C模式 + 跨OM配對",
    "D: 清貨轉貨": "清理無銷售ND店舖",
    "D2: 清貨轉貨(ND限定)": "僅ND清貨轉出，RF不轉出",
    "E1: 強制轉出": "標記商品強制轉出(僅同OM)",
    "E1b: 強制轉出(優先類型接收)": "標記商品強制轉出(僅同OM，接收端優先Type=T/M)",
    "E2: 強制轉出(跨OM)": "標記商品強制轉出(可跨OM)",
    "F: 目標優化": "依Target目標分配",
    "F2: F指定模式": "僅Target店舖可接收，集中調貨，可設定HD轉出選項",
    "ND1: ND同OM轉貨": "ND店舖互轉(同OM)，按銷量智能排序",
    "ND2: ND混合OM轉貨": "ND店舖互轉(跨OM)，Windy只轉Windy",
    "精簡SKU(限同OM): 精簡SKU限同OM": "精簡SKU模式：同OM轉貨，RF上限=Max(Safety×2,2月銷量×2)，剩餘退回D001",
    "精簡SKU(跨OM): 精簡SKU跨OM": "精簡SKU模式：跨OM轉貨(Windy限制)，RF上限=Max(Safety×2,2月銷量×2)，剩餘退回D001",
}

_B_SPECIAL_NAMES = {
    "附加B(特別模式)",
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "附加B2L(特別模式-Type=L保留2件)",
    "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加B3L(跨OM特別模式-Type=L保留2件)",
    "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
}

_B3_FAMILY_NAMES = {
    "附加B3(跨OM特別模式)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加B3L(跨OM特別模式-Type=L保留2件)",
    "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
}

_B_TOURIST_NO_SOURCE_NAMES = {
    "附加B2a(特別模式-T遊客鋪不出貨)",
    "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
    "附加B3a(跨OM特別模式-T遊客鋪不出貨)",
    "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
}

_B_L_RETAIN_NAMES = {
    "附加B2L(特別模式-Type=L保留2件)",
    "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)",
    "附加B3L(跨OM特別模式-Type=L保留2件)",
    "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)",
}

_D_FAMILY_NAMES = {"清貨轉貨", "清貨轉貨(ND限定)"}

_ND_TRANSFER_NAMES = {"ND同OM轉貨", "ND混合OM轉貨"}

_SIMPLIFIED_SKU_NAMES = {"精簡SKU(限同OM)", "精簡SKU(跨OM)"}


def is_b_special_mode(mode_name: str) -> bool:
    return mode_name in _B_SPECIAL_NAMES


def is_b3_family_mode(mode_name: str) -> bool:
    return mode_name in _B3_FAMILY_NAMES


def is_b_tourist_no_source_mode(mode_name: str) -> bool:
    return mode_name in _B_TOURIST_NO_SOURCE_NAMES


def is_b_l_retain_mode(mode_name: str) -> bool:
    return mode_name in _B_L_RETAIN_NAMES


def is_d_family_mode(mode_name: str) -> bool:
    return mode_name in _D_FAMILY_NAMES


def is_nd_transfer_mode(mode_name: str) -> bool:
    return mode_name in _ND_TRANSFER_NAMES


def is_simplified_sku_mode(mode_name: str) -> bool:
    return mode_name in _SIMPLIFIED_SKU_NAMES


def mode_name_to_code(mode_name: str) -> str:
    for code, name in MODE_NAME_MAP.items():
        if name == mode_name:
            return code
    return mode_name


RECEIVE_SITE_LIMIT_MODE_CODES = [
    "B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La",
    "E1", "E1b", "E2", "ND1", "ND2",
]
