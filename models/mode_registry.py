from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set


@dataclass(frozen=True)
class ModeDef:
    code: str
    name: str
    description: str
    attr_name: str
    families: FrozenSet[str] = frozenset()
    cross_om_grouping: bool = False
    cross_om_matching: bool = False
    source_filter: bool = True
    strategy_key: Optional[str] = None
    receive_site_limit: bool = False
    extra_ui_options: FrozenSet[str] = frozenset()
    required_columns: FrozenSet[str] = frozenset()
    source_method: Optional[str] = None
    dest_method: Optional[str] = None


MODE_DEFS: List[ModeDef] = [
    ModeDef("A", "保守轉貨", "轉出後保留安全庫存，單件自動上調至2件",
            attr_name="mode_a", source_filter=False),
    ModeDef("B", "加強轉貨", "積極處理滯銷品",
            attr_name="mode_b", source_filter=False),
    ModeDef("B2", "附加B(特別模式)", "B模式 + Type=L全轉出 + Mix高銷量保護",
            attr_name="mode_b_special",
            families=frozenset({'b_special'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2a", "附加B2a(特別模式-T遊客鋪不出貨)", "B2 + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b_special_a",
            families=frozenset({'b_special', 'b_tourist_no_source'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2L", "附加B2L(特別模式-Type=L保留2件)", "B2L模式 + Type=L低銷量保留2件 + Mix高銷量保護",
            attr_name="mode_b2l",
            families=frozenset({'b_special', 'b_l_retain'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B2La", "附加B2La(特別模式-Type=L保留2件-T遊客鋪不出貨)", "B2L + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b2la",
            families=frozenset({'b_special', 'b_tourist_no_source', 'b_l_retain'}),
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3", "附加B3(跨OM特別模式)", "B2 + 跨OM配對 + Mix高銷量保護",
            attr_name="mode_b3",
            families=frozenset({'b_special', 'b3_family'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3a", "附加B3a(跨OM特別模式-T遊客鋪不出貨)", "B3 + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b3a",
            families=frozenset({'b_special', 'b3_family', 'b_tourist_no_source'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3L", "附加B3L(跨OM特別模式-Type=L保留2件)", "B3L模式 + 跨OM配對 + Type=L低銷量保留2件 + Mix高銷量保護",
            attr_name="mode_b3l",
            families=frozenset({'b_special', 'b3_family', 'b_l_retain'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("B3La", "附加B3La(跨OM特別模式-Type=L保留2件-T遊客鋪不出貨)", "B3L + Type=T遊客鋪不出貨 + Mix高銷量保護",
            attr_name="mode_b3la",
            families=frozenset({'b_special', 'b3_family', 'b_tourist_no_source', 'b_l_retain'}),
            cross_om_grouping=True, cross_om_matching=True,
            strategy_key='b_special', dest_method='_dests_b_special', receive_site_limit=True),
    ModeDef("C", "重點補0", "補充庫存≤1的店舖",
            attr_name="mode_c", source_filter=False),
    ModeDef("C1", "重點補0-只補0/1 (或自選數量)", "僅補total_available≤N（N可自訂），不回落一般缺貨",
            attr_name="mode_c1",
            dest_method='_dests_c1_mode', source_filter=False,
            extra_ui_options=frozenset({'c1_threshold', 'c1_ceiling'})),
    ModeDef("C2", "附加C2(跨OM重點補0)", "C模式 + 跨OM配對",
            attr_name="mode_c2",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='c2_mode'),
    ModeDef("D", "清貨轉貨", "清理無銷售ND店舖",
            attr_name="mode_d",
            families=frozenset({'d_family'}),
            dest_method='_dests_d_mode', source_filter=False),
    ModeDef("D2", "清貨轉貨(ND限定)", "僅ND清貨轉出，RF不轉出",
            attr_name="mode_d2",
            families=frozenset({'d_family'}),
            dest_method='_dests_d_mode', source_filter=False,
            extra_ui_options=frozenset({'d2_enable_2site_limit'})),
    ModeDef("E1", "強制轉出", "標記商品強制轉出(僅同OM)",
            attr_name="mode_e1",
            source_filter=True, strategy_key='e1_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("E1b", "強制轉出(優先類型接收)", "標記商品強制轉出(僅同OM，接收端優先Type=T/M)",
            attr_name="mode_e1b",
            source_filter=True, strategy_key='e1_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("E2", "強制轉出(跨OM)", "標記商品強制轉出(可跨OM)",
            attr_name="mode_e2",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='e2_mode', receive_site_limit=True,
            required_columns=frozenset({'ALL'}),
            source_method='_sources_e_mode', dest_method='_dests_e_mode'),
    ModeDef("F", "目標優化", "依Target目標分配",
            attr_name="mode_f",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f_fulfill_small_first'})),
    ModeDef("F2", "F指定模式", "僅Target店舖可接收，集中調貨，可設定HD轉出選項；Windy目標店優先從同OM無Target店提取",
            attr_name="mode_f_target_only",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first'})),
    ModeDef("F3", "目標性補0", "F2 + RF轉出後保留2件 + RF按最高庫存優先轉出 + RF跨OM不降級",
            attr_name="mode_f3",
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='f_mode',
            source_method='_sources_f_mode', dest_method='_dests_f_mode',
            extra_ui_options=frozenset({'f2_hd_transfer', 'f_fulfill_small_first'})),
    ModeDef("ND1", "ND同OM轉貨", "ND店舖互轉(同OM)，按銷量智能排序",
            attr_name="mode_nd1",
            families=frozenset({'nd_transfer'}), source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd_mode', dest_method='_dests_nd_mode'),
    ModeDef("ND2", "ND混合OM轉貨", "ND店舖互轉(跨OM)，Windy只轉Windy",
            attr_name="mode_nd2",
            families=frozenset({'nd_transfer'}),
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd_mode', dest_method='_dests_nd_mode'),
    ModeDef("ND3", "ND限同OM轉貨(補0)", "ND同OM轉貨，轉出保留3件，只補零庫存ND店",
            attr_name="mode_nd3",
            families=frozenset({'nd_transfer'}), source_filter=True,
            strategy_key='nd_mode', receive_site_limit=True,
            source_method='_sources_nd3_mode', dest_method='_dests_nd3_mode'),
    ModeDef("精簡SKU(限同OM)", "精簡SKU(限同OM)", "精簡SKU同OM轉貨",
            attr_name="mode_simplified_sku_same",
            families=frozenset({'simplified_sku'}), source_filter=True,
            strategy_key='simplified_sku',
            source_method='_sources_simplified_sku', dest_method='_dests_simplified_sku'),
    ModeDef("精簡SKU(跨OM)", "精簡SKU(跨OM)", "精簡SKU跨OM轉貨",
            attr_name="mode_simplified_sku_cross",
            families=frozenset({'simplified_sku'}),
            cross_om_grouping=True, cross_om_matching=True, source_filter=True,
            strategy_key='simplified_sku',
            source_method='_sources_simplified_sku', dest_method='_dests_simplified_sku'),
    ModeDef("精簡SKU(退D001)", "精簡SKU(退D001)", "精簡SKU全數退回D001",
            attr_name="mode_simplified_sku_return_d001",
            families=frozenset({'simplified_sku'}),
            source_filter=True,
            cross_om_grouping=True,
            cross_om_matching=True,
            strategy_key='simplified_sku_return_d001',
            source_method='_sources_simplified_sku'),
]


def _build_indices() -> Dict[str, ModeDef]:
    by_name = {}
    for d in MODE_DEFS:
        by_name[d.name] = d
    return by_name


REGISTRY: Dict[str, ModeDef] = _build_indices()

_BY_CODE: Dict[str, ModeDef] = {d.code: d for d in MODE_DEFS}
_BY_ATTR: Dict[str, ModeDef] = {d.attr_name: d for d in MODE_DEFS}


def get_mode_def(mode_name: str) -> Optional[ModeDef]:
    return REGISTRY.get(mode_name)


def get_mode_def_by_code(code: str) -> Optional[ModeDef]:
    return _BY_CODE.get(code)


def get_all_mode_names() -> Set[str]:
    return {d.name for d in MODE_DEFS}


def get_mode_families() -> Dict[str, Set[str]]:
    families: Dict[str, Set[str]] = {}
    for d in MODE_DEFS:
        for f in d.families:
            families.setdefault(f, set()).add(d.name)
    return families


def get_ui_options() -> List[str]:
    return [f"{d.code}: {d.name}" for d in MODE_DEFS]


def get_receive_limit_codes() -> List[str]:
    return [d.code for d in MODE_DEFS if d.receive_site_limit]


def get_extra_ui_flags() -> Dict[str, Set[str]]:
    flags: Dict[str, Set[str]] = {}
    for d in MODE_DEFS:
        for flag in d.extra_ui_options:
            flags.setdefault(flag, set()).add(d.code)
    return flags


def get_cross_om_grouping_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.cross_om_grouping}


def get_cross_om_matching_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.cross_om_matching}


def get_source_filter_names() -> Set[str]:
    return {d.name for d in MODE_DEFS if d.source_filter}


def get_codes_needing_column(col: str) -> Set[str]:
    return {d.name for d in MODE_DEFS if col in d.required_columns}
