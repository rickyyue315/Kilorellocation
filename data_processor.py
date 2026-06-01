"""
數據預處理模組 v2.15.0
處理Excel文件讀取、數據清理和驗證
支持二十七模式系統：A(保守轉貨)/B(加強轉貨)/B2(附加B特別模式)/B2a(附加B2a特別模式)/B2L(附加B2L特別模式)/B2La(附加B2La特別模式)/B3(附加B跨OM特別模式)/B3a(附加B3a跨OM特別模式)/B3L(附加B3L跨OM特別模式)/B3La(附加B3La跨OM特別模式)/C(重點補0)/C1(重點補0-只補0/1)/C2(附加C跨OM重點補0)/D(清貨轉貨)/D2(清貨轉貨ND限定)/E1(強制轉出)/E1b(強制轉出優先類型接收)/E2(強制轉出跨OM)/F(目標優化)/F2(F指定模式)/F3(目標性補0)/ND1(ND同OM轉貨)/ND2(ND混合OM轉貨)/ND3(ND限同OM轉貨-補0)/精簡SKU(限同OM)/精簡SKU(跨OM)/精簡SKU(退D001)
新增：預設店舖資料（OM、Type等），當用戶上傳的Excel缺少這些資料時自動填充
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

from config import (
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, INTEGER_COLUMNS, STRING_COLUMNS,
    OUTLIER_CAP, FILE_SIZE_LIMIT_BYTES,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_store_data_cache = None


def _load_store_data():
    global _store_data_cache
    if _store_data_cache is None:
        path = Path(__file__).parent / 'data' / 'stores.json'
        with open(path, 'r', encoding='utf-8') as f:
            _store_data_cache = json.load(f)
    return _store_data_cache


DEFAULT_STORE_DATA = _load_store_data()

class DataProcessor:
    """數據預處理類 v2.10.0"""
    
    def __init__(self):
        self.required_columns = list(REQUIRED_COLUMNS)
        self.optional_columns = list(OPTIONAL_COLUMNS)
        self.integer_columns = list(INTEGER_COLUMNS)
        self.string_columns = list(STRING_COLUMNS)
        
        # 記錄填充統計
        self.fill_stats = {
            'om_filled': 0,
            'type_filled': 0,
            'sites_not_found': set()
        }
    
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
        df_filled = df
        
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
    
    def read_excel_file(self, file_path_or_buffer) -> pd.DataFrame:
        """
        讀取Excel文件，確保Article欄位為12位文本格式，並標記*ALL*欄位（不分大小寫）
        
        Args:
            file_path_or_buffer: Excel文件路徑或 BytesIO 緩衝區
            
        Returns:
            處理後的DataFrame
        """
        try:
            dtype_dict = {'Article': str}
            # calamine 引擎（Rust 實作）比 openpyxl 快 5-10 倍；若未安裝則 fallback
            try:
                df = pd.read_excel(file_path_or_buffer, dtype=dtype_dict, engine='calamine')
            except Exception:
                df = pd.read_excel(file_path_or_buffer, dtype=dtype_dict)
            
            # 確保Article欄位為12位文本格式（補零不足12位；截斷超過12位）
            if 'Article' in df.columns:
                df['Article'] = df['Article'].astype(str).str.zfill(12).str[-12:]
            
            # 處理*ALL*欄位：無論大小寫，都轉換為標準化的'ALL'欄位
            all_column_names = [col for col in df.columns if col.upper() == 'ALL']
            if all_column_names:
                # 優先保留已命名為 'ALL' 的欄位；若無則取第一個改名
                canonical = 'ALL' if 'ALL' in all_column_names else all_column_names[0]
                rename_map = {col: 'ALL' for col in all_column_names if col != 'ALL'}
                if rename_map:
                    df = df.rename(columns=rename_map)
                # 移除重複欄位（若有多個原始 ALL 欄位）
                duplicate_cols = [col for col in df.columns if col == 'ALL']
                if len(duplicate_cols) > 1:
                    df = df.loc[:, ~df.columns.duplicated(keep='first')]
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
            
            # 處理Supply source欄位：無論大小寫，都轉換為標準化的'Supply source'欄位
            supply_source_cols = [col for col in df.columns if col.upper().replace(' ', '') == 'SUPPLYSOURCE']
            if supply_source_cols:
                canonical = 'Supply source' if 'Supply source' in supply_source_cols else supply_source_cols[0]
                rename_map = {col: 'Supply source' for col in supply_source_cols if col != 'Supply source'}
                if rename_map:
                    df = df.rename(columns=rename_map)
                duplicate_cols = [col for col in df.columns if col == 'Supply source']
                if len(duplicate_cols) > 1:
                    df = df.loc[:, ~df.columns.duplicated(keep='first')]
                logger.info("找到Supply source欄位")
            else:
                df['Supply source'] = None
                logger.info("未找到Supply source欄位，自動創建空欄位")

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
        if hasattr(uploaded_file, 'size') and uploaded_file.size > FILE_SIZE_LIMIT_BYTES:
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
        df_processed = df
        
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
                invalid_count = int(invalid_rp_types.sum())
                logger.warning(f"發現無效的RP Type值: {invalid_values}，請檢查原始數據，已自動修正為RF")
                df_processed.loc[invalid_rp_types, 'RP Type'] = 'RF'  # 默認設為RF
                # 記錄至 Notes 欄位（供後續 preprocess_data 回傳 stats 並於界面顯示）
                if 'Notes' in df_processed.columns:
                    df_processed.loc[invalid_rp_types, 'Notes'] = (
                        df_processed.loc[invalid_rp_types, 'Notes'].astype(str)
                        + f"RP Type無效已修正為RF;"
                    )
                # 將無效值列表和計數存入實例屬性，供呼叫方讀取
                self._invalid_rp_type_values = list(invalid_values)
                self._invalid_rp_type_count = invalid_count
            else:
                self._invalid_rp_type_values = []
                self._invalid_rp_type_count = 0
        
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
        df_processed = df
        
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
        df_processed = df
        
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
                mask_outlier = df_processed[col] > OUTLIER_CAP
                df_processed.loc[mask_outlier, col] = OUTLIER_CAP
                df_processed.loc[mask_outlier, 'Notes'] = df_processed.loc[mask_outlier, 'Notes'] + "銷量數據超出範圍;"
        
        # Safety Stock 和 MOQ 負值校正
        for col in ['Safety Stock', 'MOQ']:
            if col in df_processed.columns:
                mask_negative = df_processed[col] < 0
                if mask_negative.any():
                    df_processed.loc[mask_negative, col] = 0
                    df_processed.loc[mask_negative, 'Notes'] = (
                        df_processed.loc[mask_negative, 'Notes'].astype(str) + f"{col}負值已校正為0;"
                    )
        
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
        df_processed = df
        
        # 計算有效銷量：上月銷量 + 本月MTD銷量
        if 'Last Month Sold Qty' in df_processed.columns and 'MTD Sold Qty' in df_processed.columns:
            df_processed['Effective Sold Qty'] = (
                df_processed['Last Month Sold Qty'] + df_processed['MTD Sold Qty']
            )
        else:
            df_processed['Effective Sold Qty'] = 0
        
        logger.info("有效銷量計算完成")
        return df_processed
    
    def preprocess_data(self, file_path_or_buffer) -> Tuple[pd.DataFrame, Dict]:
        """
        完整的數據預處理流程
        
        Args:
            file_path_or_buffer: Excel文件路徑或 BytesIO 緩衝區
            
        Returns:
            處理後的DataFrame和處理統計信息
        """
        logger.info("開始數據預處理")
        
        # 讀取Excel文件
        df = self.read_excel_file(file_path_or_buffer)
        
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
            'fill_stats': self.fill_stats,  # 添加填充統計
            # 無效 RP Type 修正資訊（供界面顯示警告）
            'invalid_rp_types': getattr(self, '_invalid_rp_type_values', []),
            'invalid_rp_type_count': getattr(self, '_invalid_rp_type_count', 0)
        }
        
        logger.info("數據預處理完成")
        
        return df, {
            'original_stats': original_stats,
            'processed_stats': processed_stats
        }