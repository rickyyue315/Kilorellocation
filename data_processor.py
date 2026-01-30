"""
數據預處理模組 v1.9.1
處理Excel文件讀取、數據清理和驗證
支持雙模式系統：A(保守轉貨)/B(加強轉貨)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """數據預處理類 v1.9.1"""
    
    def __init__(self):
        self.required_columns = [
            'Article', 'OM', 'RP Type', 'Site',
            'SaSa Net Stock', 'Pending Received', 'Safety Stock',
            'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ'
        ]
        
        self.optional_columns = [
            'Article Description',  # 商品描述
            'Article Long Text (60 Chars)',  # 商品長描述
            'ALL',  # E模式：強制轉出標記（不分大小寫）
            'Target'  # F模式：目標接收數量（不分大小寫）
        ]
        
        self.integer_columns = [
            'SaSa Net Stock', 'Pending Received', 'Safety Stock',
            'Last Month Sold Qty', 'MTD Sold Qty', 'MOQ'
        ]
        
        self.string_columns = ['OM', 'RP Type', 'Site']
    
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
                logger.info("找到*ALL*欄位用於E模式")
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
                # 填充空值為空字符串
                df_processed[col] = df_processed[col].fillna("").astype(str)
        
        # 驗證RP Type欄位值
        if 'RP Type' in df_processed.columns:
            invalid_rp_types = ~df_processed['RP Type'].isin(['ND', 'RF'])
            if invalid_rp_types.any():
                logger.warning(f"發現無效的RP Type值，已自動修正: {df_processed.loc[invalid_rp_types, 'RP Type'].unique()}")
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
            'data_types': df.dtypes.to_dict()
        }
        
        logger.info("數據預處理完成")
        
        return df, {
            'original_stats': original_stats,
            'processed_stats': processed_stats
        }