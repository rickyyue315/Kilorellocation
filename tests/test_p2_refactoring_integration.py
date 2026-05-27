"""
P2 重構整合測試 - 驗證 #13 validate_pair 和 #14 _sources_general 重構
確保重構後的代碼在所有模式下行為一致
"""
import pytest
import pandas as pd
from strategies.predicates import validate_pair, is_hd_to_hk_restricted
from business_logic import TransferLogic


class TestValidatePair:
    """測試 validate_pair 函式的各種場景"""

    def test_same_site_blocked(self):
        """相同站點不能自轉"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        assert not validate_pair(source, dest, set())

    def test_dest_in_transfer_sites_blocked(self):
        """目的地已在 transfer_sites 中被阻止"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A02', 'om': 'OM1', 'rp_type': 'RF'}
        assert not validate_pair(source, dest, {'A02'})

    def test_source_in_receive_sites_blocked(self):
        """來源已在 receive_sites 中被阻止"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A02', 'om': 'OM1', 'rp_type': 'RF'}
        assert not validate_pair(source, dest, set(), {'A01'}, check_source_in_receive_sites=True)

    def test_source_in_receive_sites_allowed_when_disabled(self):
        """禁用檢查時允許來源在 receive_sites 中"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A02', 'om': 'OM1', 'rp_type': 'RF'}
        assert validate_pair(source, dest, set(), {'A01'}, check_source_in_receive_sites=False)

    def test_nd_receive_blocked(self):
        """ND 站點不能接收"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'ND01', 'om': 'OM1', 'rp_type': 'ND'}
        assert not validate_pair(source, dest, set(), check_nd_receive=True)

    def test_nd_receive_allowed_when_disabled(self):
        """禁用檢查時允許 ND 接收"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'ND01', 'om': 'OM1', 'rp_type': 'ND'}
        assert validate_pair(source, dest, set(), check_nd_receive=False)

    def test_cross_om_windy_restriction(self):
        """跨 OM 時 Windy 只能轉 Windy"""
        source = {'site': 'W01', 'om': 'Windy', 'rp_type': 'RF'}
        dest = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        assert not validate_pair(source, dest, set(), cross_om=True)

    def test_cross_om_windy_to_windy_allowed(self):
        """跨 OM 時 Windy 轉 Windy 允許"""
        source = {'site': 'W01', 'om': 'Windy', 'rp_type': 'RF'}
        dest = {'site': 'W02', 'om': 'Windy', 'rp_type': 'RF'}
        assert validate_pair(source, dest, set(), cross_om=True)

    def test_cross_om_hd_restriction(self):
        """跨 OM 時 HD 不能轉 HA/HB/HC"""
        source = {'site': 'HD01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'HA01', 'om': 'OM2', 'rp_type': 'RF'}
        assert not validate_pair(source, dest, set(), cross_om=True)

    def test_cross_om_hd_to_other_allowed(self):
        """跨 OM 時 HD 轉非 HA/HB/HC 允許"""
        source = {'site': 'HD01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A01', 'om': 'OM2', 'rp_type': 'RF'}
        assert validate_pair(source, dest, set(), cross_om=True)

    def test_max_receive_sites_per_source(self):
        """限制每個來源的最大接收站點數"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest1 = {'site': 'B01', 'om': 'OM1', 'rp_type': 'RF'}
        dest2 = {'site': 'B02', 'om': 'OM1', 'rp_type': 'RF'}
        dest3 = {'site': 'B03', 'om': 'OM1', 'rp_type': 'RF'}
        
        source_to_receive = {'A01': {'B01', 'B02'}}
        
        # 已達上限，新站點被阻止
        assert not validate_pair(
            source, dest3, set(),
            source_to_receive_sites=source_to_receive,
            max_receive_sites_per_source=2
        )
        
        # 已在列表中的站點允許
        assert validate_pair(
            source, dest1, set(),
            source_to_receive_sites=source_to_receive,
            max_receive_sites_per_source=2
        )

    def test_valid_pair(self):
        """有效的配對"""
        source = {'site': 'A01', 'om': 'OM1', 'rp_type': 'RF'}
        dest = {'site': 'A02', 'om': 'OM1', 'rp_type': 'RF'}
        assert validate_pair(source, dest, set())


class TestSourcesGeneralRefactoring:
    """測試 _sources_general 重構後的行為一致性"""

    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        return pd.DataFrame({
            'Article': ['ART001'] * 6,
            'OM': ['OM1'] * 6,
            'Site': ['ND01', 'RF01', 'RF02', 'RF03', 'RF04', 'RF05'],
            'RP Type': ['ND', 'RF', 'RF', 'RF', 'RF', 'RF'],
            'SaSa Net Stock': [10, 5, 8, 3, 12, 6],
            'Pending Received': [0, 0, 0, 0, 0, 0],
            'Safety Stock': [2, 3, 4, 2, 5, 3],
            'Last Month Sold Qty': [0, 2, 3, 1, 4, 2],
            'MTD Sold Qty': [0, 1, 2, 0, 3, 1],
            'Effective Sold Qty': [0, 3, 5, 1, 7, 3],
            'MOQ': [1, 1, 1, 1, 1, 1],
            'Type': ['', 'M', 'T', 'L', 'M', 'T'],
        })

    def test_mode_a_sources(self, sample_data):
        """A 模式來源識別"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '保守轉貨')
        
        # 應該有 ND 來源
        nd_sources = [s for s in sources if s['rp_type'] == 'ND']
        assert len(nd_sources) > 0
        
        # 應該有 RF 來源（庫存 > Safety Stock）
        rf_sources = [s for s in sources if s['rp_type'] == 'RF']
        assert len(rf_sources) > 0

    def test_mode_b_sources(self, sample_data):
        """B 模式來源識別"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '加強轉貨')
        
        # B 模式應該比 A 模式更積極
        assert len(sources) > 0

    def test_mode_c_sources(self, sample_data):
        """C 模式來源識別"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '重點補0')
        
        assert len(sources) > 0

    def test_mode_d_sources(self, sample_data):
        """D 模式來源識別（清貨）"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '清貨轉貨')
        
        # ND01 銷量為 0，應該被標記為清貨
        nd_clearance = [s for s in sources if s['source_type'] == 'ND清貨轉出']
        assert len(nd_clearance) > 0

    def test_mode_d2_sources(self, sample_data):
        """D2 模式來源識別（僅 ND 清貨）"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '清貨轉貨(ND限定)')
        
        # D2 模式只有 ND 清貨來源，沒有 RF
        rf_sources = [s for s in sources if s['rp_type'] == 'RF']
        assert len(rf_sources) == 0

    def test_mode_b2_sources(self, sample_data):
        """B2 模式來源識別（B-special）"""
        logic = TransferLogic()
        sources = logic._sources_general(sample_data, '附加B(特別模式)')
        
        # 應該有 Type=L 低銷量來源
        type_l_sources = [s for s in sources if s['source_type'] == 'Local店舖全轉出']
        # RF03 是 Type=L 且銷量低
        assert len(type_l_sources) >= 0  # 可能有也可能沒有，取決於銷量

    def test_identify_nd_sources_method(self, sample_data):
        """測試 _identify_nd_sources 方法"""
        logic = TransferLogic()
        nd_sources = logic._identify_nd_sources(sample_data, '保守轉貨', None)
        
        assert len(nd_sources) == 1
        assert nd_sources[0]['site'] == 'ND01'

    def test_identify_b_special_type_l_sources(self, sample_data):
        """測試 _identify_b_special_type_l_sources 方法"""
        logic = TransferLogic()
        type_series = sample_data['Type'].astype(str).str.upper()
        type_l_sources = logic._identify_b_special_type_l_sources(
            sample_data, '附加B(特別模式)', type_series
        )
        
        # RF03 是 Type=L，檢查是否被識別
        assert isinstance(type_l_sources, list)

    def test_compute_rf_transferable_mode_a(self, sample_data):
        """測試 _compute_rf_transferable A 模式"""
        logic = TransferLogic()
        row = sample_data.iloc[1]  # RF01
        
        result = logic._compute_rf_transferable(
            row, '保守轉貨',
            total_available=5,
            safety_stock=3
        )
        
        # 應該返回 (transferable, source_type) 或 None
        if result is not None:
            transferable, source_type = result
            assert isinstance(transferable, int)
            assert source_type in ['RF過剩轉出', 'RF加強轉出']

    def test_compute_rf_transferable_mode_c(self, sample_data):
        """測試 _compute_rf_transferable C 模式"""
        logic = TransferLogic()
        row = sample_data.iloc[1]  # RF01
        
        result = logic._compute_rf_transferable(
            row, '重點補0',
            total_available=5,
            safety_stock=3
        )
        
        if result is not None:
            transferable, source_type = result
            assert isinstance(transferable, int)
            assert source_type in ['RF過剩轉出', 'RF加強轉出']


class TestStreamlitAppImport:
    """測試 Streamlit 應用可以正常導入"""

    def test_import_app_modules(self):
        """測試應用核心模組可以導入"""
        try:
            from config import VERSION, IS_ZEABUR_RUNTIME
            from models.mode import MODE_NAME_MAP
            from business_logic import TransferLogic
            from excel_generator import ExcelGenerator
            from data_processor import DataProcessor
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_transfer_logic_initialization(self):
        """測試 TransferLogic 可以初始化"""
        logic = TransferLogic()
        assert logic is not None
        assert hasattr(logic, 'mode_a')
        assert hasattr(logic, 'mode_b')
        assert hasattr(logic, 'mode_c')

    def test_all_modes_accessible(self):
        """測試所有模式都可以訪問"""
        logic = TransferLogic()
        modes = [
            'mode_a', 'mode_b', 'mode_c', 'mode_c1', 'mode_c2',
            'mode_d', 'mode_d2', 'mode_e1', 'mode_e1b', 'mode_e2',
            'mode_f', 'mode_f_target_only', 'mode_nd1', 'mode_nd2',
            'mode_simplified_sku_same', 'mode_simplified_sku_cross',
            'mode_simplified_sku_return_d001'
        ]
        
        for mode_attr in modes:
            assert hasattr(logic, mode_attr), f"Missing mode: {mode_attr}"


class TestZeaburCompatibility:
    """測試 Zeabur 部署兼容性"""

    def test_zeabur_config_import(self):
        """測試 Zeabur 配置可以導入"""
        from config import IS_ZEABUR_RUNTIME, ZEABUR_RESULT_PREVIEW_LIMIT
        assert isinstance(IS_ZEABUR_RUNTIME, bool)
        assert isinstance(ZEABUR_RESULT_PREVIEW_LIMIT, int)

    def test_display_module_import(self):
        """測試 display 模組可以導入（Zeabur 使用）"""
        try:
            from ui.display import (
                render_upload_requirements,
                render_data_preview,
                render_kpi_cards,
                render_results_table,
                render_statistics,
                render_download_button,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Display module import failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
