"""
數據預處理模組 v2.2.0
處理Excel文件讀取、數據清理和驗證
支持七模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/C(重點補0)/D(清貨轉貨)/E(強制轉出)/F(目標優化)
新增：預設店舖資料（OM、Type等），當用戶上傳的Excel缺少這些資料時自動填充
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 預設店舖資料（來自 stores-template.csv）
# 當用戶上傳的Excel缺少OM或Type資料時，系統會根據Site自動填充這些預設值
# ============================================================================
DEFAULT_STORE_DATA = {
    'HA02': {'shop': '駱克', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'S', 'om': 'Ivy', 'type': 'M'},
    'HA06': {'shop': '北角', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Ivy', 'type': 'M'},
    'HA15': {'shop': '新中環', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A3', 'size': 'L', 'om': 'Ivy', 'type': 'M'},
    'HA19': {'shop': '康山', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Violet', 'type': 'L'},
    'HA20': {'shop': '新香港仔', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Queenie', 'type': 'L'},
    'HA21': {'shop': '柴灣新翠', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'S', 'om': 'Candy', 'type': 'L'},
    'HA46': {'shop': '莊士敦道2', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'S', 'om': 'Queenie', 'type': 'M'},
    'HA30': {'shop': '禮頓中心', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'L', 'om': 'Ivy', 'type': 'M'},
    'HA32': {'shop': '皇室堡', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'L', 'om': 'Queenie', 'type': 'M'},
    'HA33': {'shop': '羅素街8號', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'S', 'om': 'Queenie', 'type': 'T'},
    'HA37': {'shop': '新信德', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'XS', 'om': 'Queenie', 'type': 'M'},
    'HA39': {'shop': '金百利', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A3', 'size': 'M', 'om': 'Queenie', 'type': 'T'},
    'HA40': {'shop': '新山頂', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'S', 'om': 'Candy', 'type': 'T'},
    'HA42': {'shop': '啟超道', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B1', 'size': 'S', 'om': 'Queenie', 'type': 'T'},
    'HA43': {'shop': '德己立街2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Ivy', 'type': 'M'},
    'HA44': {'shop': '黃竹坑', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Queenie', 'type': 'M'},
    'HA45': {'shop': '合和商場', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'L', 'om': 'Queenie', 'type': 'M'},
    'HB01': {'shop': '加連威', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'S', 'om': 'Ivy', 'type': 'T'},
    'HB10': {'shop': '彌敦88', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A3', 'size': 'L', 'om': 'Ivy', 'type': 'T'},
    'HB11': {'shop': '德福', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HB12': {'shop': '黃埔', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HB24': {'shop': '始創', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HB25': {'shop': '奧海城', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Candy', 'type': 'L'},
    'HB29': {'shop': '重慶站', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A2', 'size': 'XL', 'om': 'Ivy', 'type': 'T'},
    'HB30': {'shop': '淘大', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Hippo', 'type': 'L'},
    'HB38': {'shop': '新港', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Candy', 'type': 'T'},
    'HB41': {'shop': '九龍城', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'M', 'om': 'Hippo', 'type': 'L'},
    'HB49': {'shop': '新蒲崗', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Hippo', 'type': 'L'},
    'HB56': {'shop': '旺角160', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Eva', 'type': 'T'},
    'HB62': {'shop': '油塘', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'L', 'om': 'Violet', 'type': 'L'},
    'HB63': {'shop': '佐敦道31', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Ivy', 'type': 'M'},
    'HB66': {'shop': 'PopCorn', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Ivy', 'type': 'M'},
    'HB68': {'shop': '新都城', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'S', 'om': 'Ivy', 'type': 'L'},
    'HB69': {'shop': '西九龍', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Violet', 'type': 'L'},
    'HB72': {'shop': '黃大仙', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HB75': {'shop': '東港城2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Ivy', 'type': 'L'},
    'HB77': {'shop': '新樂富', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'XS', 'om': 'Hippo', 'type': 'L'},
    'HB80': {'shop': '新世紀Moko', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HB83': {'shop': '新加拿芬道', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B1', 'size': 'L', 'om': 'Ivy', 'type': 'T'},
    'HB86': {'shop': '新都會駅', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'S', 'om': 'Violet', 'type': 'L'},
    'HB87': {'shop': '西九高鐵站', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B1', 'size': 'XS', 'om': 'Hippo', 'type': 'T'},
    'HB91': {'shop': '南昌站V Walk', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'XS', 'om': 'Violet', 'type': 'L'},
    'HB93': {'shop': '新好望角', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A3', 'size': 'M', 'om': 'Violet', 'type': 'T'},
    'HB94': {'shop': '康城', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Ivy', 'type': 'L'},
    'HB95': {'shop': '觀塘APM2', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'S', 'om': 'Violet', 'type': 'M'},
    'HB96': {'shop': '啟德', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HB97': {'shop': '新旺角文華', 'regional': 'HK', 'class_1': 'A', 'class_2': 'A2', 'size': 'M', 'om': 'Violet', 'type': 'T'},
    'HB98': {'shop': '星光行2', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B1', 'size': 'M', 'om': 'Candy', 'type': 'T'},
    'HBA2': {'shop': '廣東道2', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B1', 'size': 'M', 'om': 'Hippo', 'type': 'T'},
    'HBA3': {'shop': '荷里活廣場2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Hippo', 'type': 'L'},
    'HBA4': {'shop': '中港城2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Candy', 'type': 'T'},
    'HC02': {'shop': '荃灣', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Eva', 'type': 'L'},
    'HC05': {'shop': '上水', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Candy', 'type': 'T'},
    'HC13': {'shop': '沙田中心', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Queenie', 'type': 'M'},
    'HC15': {'shop': '悅來坊', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HC19': {'shop': '錦薈坊', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HC25': {'shop': '新青衣', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'L', 'om': 'Candy', 'type': 'L'},
    'HC26': {'shop': '沙田第一城', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Candy', 'type': 'L'},
    'HC27': {'shop': '大埔超級城', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Queenie', 'type': 'L'},
    'HC31': {'shop': '新屯門', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HC33': {'shop': '太和', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Queenie', 'type': 'L'},
    'HC42': {'shop': '上水新都2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Candy', 'type': 'M'},
    'HC44': {'shop': '新頌富', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Eva', 'type': 'L'},
    'HC45': {'shop': '新馬鞍山', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Candy', 'type': 'L'},
    'HC49': {'shop': '形點', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HC51': {'shop': '新荃灣廣場', 'regional': 'HK', 'class_1': 'D', 'class_2': 'D1', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HC55': {'shop': '新新都會', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'L', 'om': 'Eva', 'type': 'L'},
    'HC60': {'shop': '新大埔新達', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Queenie', 'type': 'L'},
    'HC61': {'shop': '如心廣場', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Eva', 'type': 'M'},
    'HC62': {'shop': '新元朗', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'S', 'om': 'Eva', 'type': 'L'},
    'HC63': {'shop': '新東涌', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Candy', 'type': 'M'},
    'HC64': {'shop': '嘉湖', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'M', 'om': 'Eva', 'type': 'L'},
    'HC66': {'shop': '新沙田', 'regional': 'HK', 'class_1': 'B', 'class_2': 'B2', 'size': 'M', 'om': 'Queenie', 'type': 'M'},
    'HC67': {'shop': '新V City', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C1', 'size': 'M', 'om': 'Hippo', 'type': 'M'},
    'HC68': {'shop': '新大圍', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'XS', 'om': 'Candy', 'type': 'L'},
    'HC69': {'shop': '元朗廣場2', 'regional': 'HK', 'class_1': 'C', 'class_2': 'C2', 'size': 'S', 'om': 'Eva', 'type': 'M'},
    'HD02': {'shop': '高士德', 'regional': 'MO', 'class_1': 'B', 'class_2': 'B1', 'size': 'L', 'om': 'Windy', 'type': 'L'},
    'HD03': {'shop': '議事亭', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A1', 'size': 'XL', 'om': 'Windy', 'type': 'T'},
    'HD09': {'shop': '新威尼斯人', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A1', 'size': 'L', 'om': 'Windy', 'type': 'T'},
    'HD11': {'shop': '新澳門廣場', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A2', 'size': 'L', 'om': 'Windy', 'type': 'T'},
    'HD15': {'shop': '信達廣場', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A3', 'size': 'L', 'om': 'Windy', 'type': 'T'},
    'HD16': {'shop': '澳門南灣中心', 'regional': 'MO', 'class_1': 'C', 'class_2': 'C1', 'size': 'L', 'om': 'Windy', 'type': 'T'},
    'HD18': {'shop': '倫敦人', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A3', 'size': 'XL', 'om': 'Windy', 'type': 'T'},
    'HD19': {'shop': '板樟堂', 'regional': 'MO', 'class_1': 'A', 'class_2': 'A3', 'size': 'L', 'om': 'Windy', 'type': 'T'},
    'HD20': {'shop': '澳門銀河2', 'regional': 'MO', 'class_1': 'B', 'class_2': 'B2', 'size': 'S', 'om': 'Windy', 'type': 'T'},
}

class DataProcessor:
    """數據預處理類 v2.2.0"""
    
    def __init__(self):
        self.required_columns = [
            'Article', 'OM', 'RP Type', 'Site',
            'SaSa Net Stock', 'Pending Received', 'Safety Stock',
            'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ'
        ]
        
        self.optional_columns = [
            'Article Description',  # 商品描述
            'Article Long Text (60 Chars)',  # 商品長描述
            'ALL',  # E1/E2模式：強制轉出標記（不分大小寫）
            'Target',  # F模式：目標接收數量（不分大小寫）
            'Type'  # 附加B模式：Type欄位（不分大小寫）
        ]
        
        self.integer_columns = [
            'SaSa Net Stock', 'Pending Received', 'Safety Stock',
            'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ'
        ]
        
        self.string_columns = ['OM', 'RP Type', 'Site']
        
        # 記錄填充統計
        self.fill_stats = {
            'om_filled': 0,
            'type_filled': 0,
            'sites_not_found': set()
        }
    
    def get_store_default_info(self, site: str) -> Dict:
        """
        根據店舖編號獲取預設資料
        
        Args:
            site: 店舖編號（如 HA02, HA06 等）
            
        Returns:
            預設資料字典，如果找不到則返回空字典
        """
        # 標準化 site（去除前後空白，轉大寫）
        site_normalized = str(site).strip().upper()
        return DEFAULT_STORE_DATA.get(site_normalized, {})
    
    def fill_default_store_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        使用預設資料填充缺失的 OM 和 Type 欄位
        
        當用戶上傳的 Excel 缺少 OM 或 Type 資料時，
        系統會根據 Site 欄位自動從 DEFAULT_STORE_DATA 中填充對應的預設值。
        
        Args:
            df: 輸入 DataFrame
            
        Returns:
            填充後的 DataFrame
        """
        df_filled = df.copy()
        
        # 重置填充統計
        self.fill_stats = {
            'om_filled': 0,
            'type_filled': 0,
            'sites_not_found': set()
        }
        
        # 向量化操作：預先建立 Site → OM/Type 對應字典，避免逐列 iterrows
        site_to_om = {k: v['om'] for k, v in DEFAULT_STORE_DATA.items() if v.get('om')}
        site_to_type = {k: v['type'] for k, v in DEFAULT_STORE_DATA.items() if v.get('type')}
        
        # 標準化 Site 欄位為大寫，用於查詢（與 get_store_default_info 一致）
        if 'Site' not in df_filled.columns:
            return df_filled
        
        sites_upper = df_filled['Site'].fillna('').astype(str).str.strip().str.upper()
        
        # 記錄找不到預設資料的 Site
        all_sites = set(sites_upper[sites_upper != ''].unique())
        known_sites = set(DEFAULT_STORE_DATA.keys())
        self.fill_stats['sites_not_found'] = all_sites - known_sites
        
        # ---- 填充 OM ----
        # 只在 OM 欄位為空或 NaN 時填充
        if 'OM' not in df_filled.columns:
            df_filled['OM'] = ''
        om_empty_mask = df_filled['OM'].isna() | (df_filled['OM'].astype(str).str.strip() == '')
        if om_empty_mask.any():
            default_om_series = sites_upper.map(site_to_om)   # NaN 表示找不到
            fill_mask = om_empty_mask & default_om_series.notna()
            df_filled.loc[fill_mask, 'OM'] = default_om_series[fill_mask]
            self.fill_stats['om_filled'] = int(fill_mask.sum())
        
        # ---- 填充 Type ----
        # 只在 Type 欄位為空或 NaN 時填充
        if 'Type' not in df_filled.columns:
            df_filled['Type'] = ''
        type_empty_mask = df_filled['Type'].isna() | (df_filled['Type'].astype(str).str.strip() == '')
        if type_empty_mask.any():
            default_type_series = sites_upper.map(site_to_type)   # NaN 表示找不到
            fill_mask = type_empty_mask & default_type_series.notna()
            df_filled.loc[fill_mask, 'Type'] = default_type_series[fill_mask]
            self.fill_stats['type_filled'] = int(fill_mask.sum())
        
        # 記錄填充統計
        if self.fill_stats['om_filled'] > 0 or self.fill_stats['type_filled'] > 0:
            logger.info(f"預設資料填充完成 - OM: {self.fill_stats['om_filled']} 筆, Type: {self.fill_stats['type_filled']} 筆")
        
        if self.fill_stats['sites_not_found']:
            logger.warning(f"以下店舖在預設資料中找不到: {self.fill_stats['sites_not_found']}")
        
        return df_filled
    
    def read_excel_file(self, file_path: str) -> pd.DataFrame:
        """
        讀取Excel文件，確保Article欄位為12位文本格式，並標記*ALL*欄位（不分大小寫）
        
        Args:
            file_path: Excel文件路徑
            
        Returns:
            處理後的DataFrame
        """
        try:
            # 讀取Excel文件，指定Article欄位為字符串類型
            dtype_dict = {'Article': str}
            df = pd.read_excel(file_path, dtype=dtype_dict)
            
            # 確保Article欄位為12位文本格式
            if 'Article' in df.columns:
                df['Article'] = df['Article'].astype(str).str.zfill(12)
            
            # 處理*ALL*欄位：無論大小寫，都轉換為標準化的'ALL'欄位
            all_column_names = [col for col in df.columns if col.upper() == 'ALL']
            if all_column_names:
                # 如果存在*ALL*欄位，將其標準化為'ALL'
                for col in all_column_names:
                    if col != 'ALL':
                        df['ALL'] = df[col]
                        df = df.drop(columns=[col])
                logger.info("找到*ALL*欄位用於E1/E2模式")
            else:
                # 創建空的ALL欄位，用於後續邏輯判斷
                df['ALL'] = ""
                logger.info("未找到*ALL*欄位，自動創建空欄位")

            # 處理Target欄位：無論大小寫，都轉換為標準化的'Target'欄位
            target_column_names = [col for col in df.columns if col.upper() == 'TARGET']
            if target_column_names:
                for col in target_column_names:
                    if col != 'Target':
                        df['Target'] = df[col]
                        df = df.drop(columns=[col])
                logger.info("找到Target欄位用於F模式")
            else:
                df['Target'] = ""
                logger.info("未找到Target欄位，自動創建空欄位")

            # 處理Type欄位：無論大小寫，都轉換為標準化的'Type'欄位
            type_column_names = [col for col in df.columns if col.upper() == 'TYPE']
            if type_column_names:
                for col in type_column_names:
                    if col != 'Type':
                        df['Type'] = df[col]
                        df = df.drop(columns=[col])
                logger.info("找到Type欄位用於附加B模式")
            else:
                df['Type'] = ""
                logger.info("未找到Type欄位，自動創建空欄位")
            
            # 處理商品描述欄位
            if 'Article Description' not in df.columns and 'Article Long Text (60 Chars)' in df.columns:
                df['Article Description'] = df['Article Long Text (60 Chars)']
                logger.info("使用'Article Long Text (60 Chars)'作為商品描述")
            elif 'Article Description' not in df.columns and 'Article Long Text (60 Chars)' not in df.columns:
                df['Article Description'] = "N/A"
                logger.warning("未找到商品描述欄位，設置為'N/A'")
            
            logger.info(f"成功讀取Excel文件，共有 {len(df)} 行數據")
            return df
            
        except Exception as e:
            logger.error(f"讀取Excel文件失敗: {str(e)}")
            raise
    
    def validate_columns(self, df: pd.DataFrame) -> bool:
        """
        驗證必需的欄位是否存在
        
        Args:
            df: 輸入DataFrame
            
        Returns:
            驗證結果
        """
        missing_columns = set(self.required_columns) - set(df.columns)
        if missing_columns:
            available_columns = ", ".join(sorted(df.columns))
            missing_str = ", ".join(sorted(missing_columns))
            error_msg = f"缺少必需欄位: {missing_str}\n現有欄位: {available_columns}"
            logger.error(error_msg)
            return False
        
        logger.info("欄位驗證通過")
        return True
    
    def validate_file_format(self, uploaded_file) -> Tuple[bool, str]:
        """
        驗證上傳文件格式
        
        Args:
            uploaded_file: 上傳的文件對象
            
        Returns:
            驗證結果和錯誤消息
        """
        # 檢查文件名是否為空
        if uploaded_file.name == '':
            return False, "文件名不能為空"
        
        # 檢查文件擴展名（不區分大小寫）
        file_name = uploaded_file.name.lower()
        if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            return False, "文件格式不正確，請上傳.xlsx或.xls格式的Excel文件"
        
        # 檢查文件大小（限制為50MB）
        if hasattr(uploaded_file, 'size') and uploaded_file.size > 50 * 1024 * 1024:
            return False, "文件大小超過限制（最大50MB）"
        
        return True, ""
    
    def convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        轉換數據類型並處理錯誤
        
        Args:
            df: 輸入DataFrame
            
        Returns:
            處理後的DataFrame
        """
        df_processed = df.copy()
        
        # 處理整數欄位
        for col in self.integer_columns:
            if col in df_processed.columns:
                # 轉換為數值，錯誤值設為0
                df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0).astype(int)
        
        # 處理字符串欄位
        for col in self.string_columns:
            if col in df_processed.columns:
                # 填充空值為空字符串，並去除前後空白
                df_processed[col] = df_processed[col].fillna("").astype(str).str.strip()
        
        # 驗證RP Type欄位值
        if 'RP Type' in df_processed.columns:
            invalid_rp_types = ~df_processed['RP Type'].isin(['ND', 'RF'])
            if invalid_rp_types.any():
                invalid_values = df_processed.loc[invalid_rp_types, 'RP Type'].unique()
                logger.warning(f"發現無效的RP Type值: {invalid_values}，請檢查原始數據，已自動修正為RF")
                df_processed.loc[invalid_rp_types, 'RP Type'] = 'RF'  # 默認設為RF
        
        logger.info("數據類型轉換完成")
        return df_processed
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        處理缺失值
        
        Args:
            df: 輸入DataFrame
            
        Returns:
            處理後的DataFrame
        """
        df_processed = df.copy()
        
        # Safety Stock缺失值填充為0
        if 'Safety Stock' in df_processed.columns:
            df_processed['Safety Stock'] = df_processed['Safety Stock'].fillna(0)
        
        # MOQ缺失值填充為0
        if 'MOQ' in df_processed.columns:
            df_processed['MOQ'] = df_processed['MOQ'].fillna(0)
        
        # 銷量數據缺失值填充為0
        if 'Last Month Sold Qty' in df_processed.columns:
            df_processed['Last Month Sold Qty'] = df_processed['Last Month Sold Qty'].fillna(0)
        
        if 'MTD Sold Qty' in df_processed.columns:
            df_processed['MTD Sold Qty'] = df_processed['MTD Sold Qty'].fillna(0)
        
        logger.info("缺失值處理完成")
        return df_processed
    
    def correct_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        校正異常值
        
        Args:
            df: 輸入DataFrame
            
        Returns:
            處理後的DataFrame
        """
        df_processed = df.copy()
        
        # 添加Notes欄位（如果不存在）
        if 'Notes' not in df_processed.columns:
            df_processed['Notes'] = ""
        
        # 處理銷量異常值
        sales_columns = ['Last Month Sold Qty', 'MTD Sold Qty']
        
        for col in sales_columns:
            if col in df_processed.columns:
                # 小於0的值設為0
                mask_negative = df_processed[col] < 0
                df_processed.loc[mask_negative, col] = 0
                
                # 大於100,000的值設為100,000並標註
                mask_outlier = df_processed[col] > 100000
                df_processed.loc[mask_outlier, col] = 100000
                df_processed.loc[mask_outlier, 'Notes'] = df_processed.loc[mask_outlier, 'Notes'] + "銷量數據超出範圍;"
        
        logger.info("異常值校正完成")
        return df_processed
    
    def calculate_effective_sold_qty(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算有效銷量
        
        Args:
            df: 輸入DataFrame
            
        Returns:
            添加有效銷量欄位的DataFrame
        """
        df_processed = df.copy()
        
        # 計算有效銷量：優先使用上月銷量，若為0則使用本月銷量
        if 'Last Month Sold Qty' in df_processed.columns and 'MTD Sold Qty' in df_processed.columns:
            df_processed['Effective Sold Qty'] = np.where(
                df_processed['Last Month Sold Qty'] > 0,
                df_processed['Last Month Sold Qty'],
                df_processed['MTD Sold Qty']
            )
        else:
            df_processed['Effective Sold Qty'] = 0
        
        logger.info("有效銷量計算完成")
        return df_processed
    
    def preprocess_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        完整的數據預處理流程
        
        Args:
            file_path: Excel文件路徑
            
        Returns:
            處理後的DataFrame和處理統計信息
        """
        logger.info("開始數據預處理")
        
        # 讀取Excel文件
        df = self.read_excel_file(file_path)
        
        # 驗證欄位
        if not self.validate_columns(df):
            missing_columns = set(self.required_columns) - set(df.columns)
            available_columns = list(df.columns)
            error_details = (
                f"缺少必需欄位: {', '.join(sorted(missing_columns))}\n"
                f"需要的欄位: {', '.join(sorted(self.required_columns))}\n"
                f"現有欄位: {', '.join(sorted(available_columns))}"
            )
            raise ValueError(f"數據欄位驗證失敗\n{error_details}")
        
        # 記錄原始數據統計
        original_stats = {
            'total_rows': len(df),
            'columns': list(df.columns)
        }
        
        # 數據類型轉換
        df = self.convert_data_types(df)
        
        # 【新增】使用預設店舖資料填充缺失的 OM 和 Type
        # 在數據類型轉換後執行，確保 Site 欄位已標準化
        df = self.fill_default_store_data(df)
        
        # 處理缺失值
        df = self.handle_missing_values(df)
        
        # 校正異常值
        df = self.correct_outliers(df)
        
        # 計算有效銷量
        df = self.calculate_effective_sold_qty(df)
        
        # 記錄處理後統計
        processed_stats = {
            'total_rows': len(df),
            'columns': list(df.columns),
            'data_types': df.dtypes.to_dict(),
            'fill_stats': self.fill_stats  # 添加填充統計
        }
        
        logger.info("數據預處理完成")
        
        return df, {
            'original_stats': original_stats,
            'processed_stats': processed_stats
        }