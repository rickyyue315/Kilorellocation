import pytest
from models.mode_registry import (
    ModeDef, MODE_DEFS, REGISTRY,
    get_mode_def, get_mode_def_by_code,
    get_all_mode_names, get_mode_families,
    get_ui_options, get_receive_limit_codes,
    get_extra_ui_flags, get_cross_om_grouping_names,
    get_cross_om_matching_names, get_source_filter_names,
    get_codes_needing_column,
)
from models.mode import MODE_NAME_MAP, MODE_DESCRIPTIONS, RECEIVE_SITE_LIMIT_MODE_CODES


class TestModeDef:
    def test_frozen(self):
        d = ModeDef("X", "test", "desc", "mode_x")
        with pytest.raises(AttributeError):
            d.code = "Y"

    def test_defaults(self):
        d = ModeDef("X", "test", "desc", "mode_x")
        assert d.families == frozenset()
        assert d.cross_om_grouping is False
        assert d.source_filter is True
        assert d.strategy_key is None
        assert d.receive_site_limit is False
        assert d.source_method is None
        assert d.dest_method is None


class TestModeDefsList:
    def test_count(self):
        assert len(MODE_DEFS) == 27

    def test_unique_codes(self):
        codes = [d.code for d in MODE_DEFS]
        assert len(codes) == len(set(codes))

    def test_unique_names(self):
        names = [d.name for d in MODE_DEFS]
        assert len(names) == len(set(names))

    def test_unique_attr_names(self):
        attrs = [d.attr_name for d in MODE_DEFS]
        assert len(attrs) == len(set(attrs))


class TestRegistry:
    def test_registry_keyed_by_name(self):
        assert len(REGISTRY) == 27
        assert "保守轉貨" in REGISTRY
        assert "精簡SKU(跨OM)" in REGISTRY

    def test_get_mode_def(self):
        d = get_mode_def("保守轉貨")
        assert d is not None
        assert d.code == "A"
        assert d.name == "保守轉貨"

    def test_get_mode_def_missing(self):
        assert get_mode_def("nonexistent") is None

    def test_get_mode_def_by_code(self):
        d = get_mode_def_by_code("A")
        assert d is not None
        assert d.name == "保守轉貨"

    def test_get_mode_def_by_code_simplified(self):
        d = get_mode_def_by_code("精簡SKU(跨OM)")
        assert d is not None
        assert d.name == "精簡SKU(跨OM)"


class TestDerivedQueries:
    def test_get_all_mode_names(self):
        names = get_all_mode_names()
        assert len(names) == 27
        assert "保守轉貨" in names
        assert "精簡SKU(限同OM)" in names

    def test_get_mode_families(self):
        families = get_mode_families()
        assert 'b_special' in families
        assert len(families['b_special']) == 8
        assert 'b3_family' in families
        assert len(families['b3_family']) == 4
        assert 'b_tourist_no_source' in families
        assert len(families['b_tourist_no_source']) == 4
        assert 'b_l_retain' in families
        assert len(families['b_l_retain']) == 4
        assert 'd_family' in families
        assert len(families['d_family']) == 2
        assert 'nd_transfer' in families
        assert len(families['nd_transfer']) == 3
        assert 'simplified_sku' in families
        assert len(families['simplified_sku']) == 3

    def test_get_ui_options(self):
        opts = get_ui_options()
        assert len(opts) == 27
        assert opts[0] == "A: 保守轉貨"

    def test_get_receive_limit_codes(self):
        codes = get_receive_limit_codes()
        assert "B2" in codes
        assert "E1" in codes
        assert "ND1" in codes
        assert "A" not in codes
        assert "B" not in codes
        assert "C" not in codes

    def test_get_extra_ui_flags(self):
        flags = get_extra_ui_flags()
        assert 'f2_hd_transfer' in flags
        assert 'F2' in flags['f2_hd_transfer']

    def test_get_cross_om_grouping_names(self):
        names = get_cross_om_grouping_names()
        assert "強制轉出(跨OM)" in names
        assert "附加B3(跨OM特別模式)" in names
        assert "精簡SKU(跨OM)" in names
        assert "精簡SKU(限同OM)" not in names
        assert "保守轉貨" not in names

    def test_get_cross_om_matching_names(self):
        names = get_cross_om_matching_names()
        assert "精簡SKU(跨OM)" in names
        assert "保守轉貨" not in names

    def test_get_source_filter_names(self):
        names = get_source_filter_names()
        assert "附加B(特別模式)" in names
        assert "保守轉貨" not in names
        assert "強制轉出" in names
        assert "精簡SKU(限同OM)" in names
        assert len(names) == 21

    def test_get_codes_needing_column(self):
        e_modes = get_codes_needing_column('ALL')
        assert len(e_modes) == 3
        assert "強制轉出" in e_modes


class TestBackwardCompatModePy:
    def test_mode_name_map_count(self):
        assert len(MODE_NAME_MAP) == 27

    def test_mode_name_map_a(self):
        assert MODE_NAME_MAP["A"] == "保守轉貨"

    def test_mode_name_map_simplified(self):
        assert MODE_NAME_MAP["精簡SKU(限同OM)"] == "精簡SKU(限同OM)"

    def test_mode_descriptions_count(self):
        assert len(MODE_DESCRIPTIONS) == 27

    def test_receive_site_limit_codes(self):
        assert len(RECEIVE_SITE_LIMIT_MODE_CODES) == len(get_receive_limit_codes())
        assert "B2" in RECEIVE_SITE_LIMIT_MODE_CODES
        assert "A" not in RECEIVE_SITE_LIMIT_MODE_CODES
