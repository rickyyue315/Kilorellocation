"""
Excel輸出模組 v1.9.7
生成調貨建議和統計摘要的Excel文件
支持三模式系統：A(保守轉貨)/B(加強轉貨)/C(重點補0)
增加詳細Notes分類資訊
"""

import pandas as pd
import numpy as np
from datetime import datetime
import xlsxwriter
from typing import Dict, List, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelGenerator:
    """Excel輸出類 v1.9.7"""
    
    def __init__(self):
        self.output_filename = ""
    
    def generate_filename(self) -> str:
        """
        生成輸出文件名
        
        Returns:
            格式化的文件名
        """
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"調貨建議_{current_date}.xlsx"
        self.output_filename = filename
        return filename
    
    def _generate_remark(self, source_type: str, dest_type: str) -> str:
        """
        生成簡潔的Remark，顯示轉出分類到接收分類的映射
        
        Args:
            source_type: 轉出分類 (e.g., 'ND轉出', 'RF過剩轉出', 'RF加強轉出')
            dest_type: 接收分類 (e.g., '重點補0', '緊急缺貨補貨', '潛在缺貨補貨')
            
        Returns:
            簡潔的Remark字符串
        """
        return f"{source_type} → {dest_type}"
    
    def create_transfer_recommendations_sheet(self, writer, recommendations: List[Dict]):
        """
        創建調貨建議工作表
        
        Args:
            writer: ExcelWriter對象
            recommendations: 調貨建議列表
        """
        logger.info("創建調貨建議工作表")
        
        # 準備數據
        df_data = []
        for rec in recommendations:
            # 生成Remark
            source_type = rec.get('Source Type', '')
            dest_type = rec.get('Destination Type') or rec.get('Receive Type', '')
            remark = self._generate_remark(source_type, dest_type) if source_type and dest_type else ''
            
            df_data.append({
                'Article': rec['Article'],
                'Product Desc': rec['Product Desc'],
                'Transfer OM': rec['Transfer OM'],
                'Transfer Site': rec['Transfer Site'],
                'Receive OM': rec['Receive OM'],
                'Receive Site': rec['Receive Site'],
                'Transfer Qty': rec['Transfer Qty'],
                'Original Stock': rec['Original Stock'],
                'After Transfer Stock': rec['After Transfer Stock'],
                'Safety Stock': rec['Safety Stock'],
                'MOQ': rec['MOQ'],
                'Remark': remark,
                'Notes': rec.get('Notes', ''),
                # 新增銷售數據欄位
                'Transfer Site Last Month Sold Qty': rec.get('Transfer Site Last Month Sold Qty', 0),
                'Transfer Site MTD Sold Qty': rec.get('Transfer Site MTD Sold Qty', 0),
                'Receive Site Last Month Sold Qty': rec.get('Receive Site Last Month Sold Qty', 0),
                'Receive Site MTD Sold Qty': rec.get('Receive Site MTD Sold Qty', 0)
            })
        
        # 創建DataFrame
        df = pd.DataFrame(df_data)
        
        # 寫入Excel
        df.to_excel(writer, sheet_name='調貨建議 (Transfer Recommendations)', index=False)
        
        # 獲取工作簿和工作表對象
        workbook = writer.book
        worksheet = writer.sheets['調貨建議 (Transfer Recommendations)']
        
        # 設置列寬
        worksheet.set_column('A:A', 15)  # Article
        worksheet.set_column('B:B', 30)  # Product Desc
        worksheet.set_column('C:C', 15)  # Transfer OM
        worksheet.set_column('D:D', 15)  # Transfer Site
        worksheet.set_column('E:E', 15)  # Receive OM
        worksheet.set_column('F:F', 15)  # Receive Site
        worksheet.set_column('G:G', 12)  # Transfer Qty
        worksheet.set_column('H:H', 15)  # Original Stock
        worksheet.set_column('I:I', 18)  # After Transfer Stock
        worksheet.set_column('J:J', 12)  # Safety Stock
        worksheet.set_column('K:K', 8)   # MOQ
        worksheet.set_column('L:L', 35)  # Remark - 簡潔的轉出→接收映射
        worksheet.set_column('M:M', 25)  # Transfer Site Last Month Sold Qty
        worksheet.set_column('N:N', 20)  # Transfer Site MTD Sold Qty
        worksheet.set_column('O:O', 25)  # Receive Site Last Month Sold Qty
        worksheet.set_column('P:P', 20)  # Receive Site MTD Sold Qty
        worksheet.set_column('Q:Q', 60)  # Notes - 增加寬度以顯示詳細分類信息
        
        # 添加標題格式
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 應用標題格式
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # 添加數據格式
        data_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top'
        })
        
        # Notes欄位的特殊格式（換行和自動高度）
        notes_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top',
            'font_size': 9,
            'align': 'left'
        })
        
        # 應用數據格式
        for row_num in range(1, len(df) + 1):
            for col_num in range(len(df.columns)):
                if col_num == 16:  # Notes欄位 (第Q列，索引為16)
                    # 設置Notes欄位自動換行和更適合的高度
                    worksheet.write(row_num, col_num, df.iloc[row_num-1, col_num], notes_format)
                else:
                    worksheet.write(row_num, col_num, df.iloc[row_num-1, col_num], data_format)
                    
        # 設置Notes欄位自動換行
        worksheet.set_column('Q:Q', 60)  # Notes欄位寬度
        worksheet.set_row(0, 40)  # 標題行高度
        for row_num in range(1, len(df) + 1):
            worksheet.set_row(row_num, 60)  # 數據行高度，特別是Notes欄位
    
    def create_summary_dashboard_sheet(self, writer, statistics: Dict):
        """
        創建統計摘要工作表
        
        Args:
            writer: ExcelWriter對象
            statistics: 統計信息字典
        """
        logger.info("創建統計摘要工作表")
        
        workbook = writer.book
        worksheet = workbook.add_worksheet('統計摘要 (Summary Dashboard)')
        
        # 設置格式
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        kpi_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        kpi_value_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#D7E4BC',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        
        data_format = workbook.add_format({
            'border': 1
        })
        
        # 標題
        worksheet.merge_range('A1:B1', '調貨建議統計摘要', title_format)
        
        # KPI橫幅
        worksheet.write('A3', '總調貨建議數量', kpi_format)
        worksheet.write('B3', statistics.get('total_recommendations', 0), kpi_value_format)
        
        worksheet.write('A4', '總調貨件數', kpi_format)
        worksheet.write('B4', statistics.get('total_transfer_qty', 0), kpi_value_format)
        
        worksheet.write('A5', '涉及產品數量', kpi_format)
        worksheet.write('B5', statistics.get('unique_articles', 0), kpi_value_format)
        
        worksheet.write('A6', '涉及OM數量', kpi_format)
        worksheet.write('B6', statistics.get('unique_oms', 0), kpi_value_format)
        
        # 按Article統計
        row = 8
        worksheet.write(f'A{row}', '按Article統計', header_format)
        worksheet.write(f'B{row}', '總調貨件數', header_format)
        worksheet.write(f'C{row}', '調貨行數', header_format)
        worksheet.write(f'D{row}', '涉及OM數量', header_format)
        
        article_stats = statistics.get('article_stats', {})
        for article, stats in article_stats.items():
            row += 1
            worksheet.write(f'A{row}', article, data_format)
            worksheet.write(f'B{row}', stats['total_qty'], data_format)
            worksheet.write(f'C{row}', stats['count'], data_format)
            worksheet.write(f'D{row}', stats['om_count'], data_format)
        
        # 空白行
        row += 2
        
        # 按OM統計
        worksheet.write(f'A{row}', '按OM統計', header_format)
        worksheet.write(f'B{row}', '總調貨件數', header_format)
        worksheet.write(f'C{row}', '調貨行數', header_format)
        worksheet.write(f'D{row}', '涉及Article數量', header_format)
        
        om_stats = statistics.get('om_stats', {})
        for om, stats in om_stats.items():
            row += 1
            worksheet.write(f'A{row}', om, data_format)
            worksheet.write(f'B{row}', stats['total_qty'], data_format)
            worksheet.write(f'C{row}', stats['count'], data_format)
            worksheet.write(f'D{row}', stats['article_count'], data_format)
        
        # 空白行
        row += 2
        
        # 轉出類型分析
        worksheet.write(f'A{row}', '轉出類型分析', header_format)
        worksheet.write(f'B{row}', '建議數量', header_format)
        worksheet.write(f'C{row}', '總件數', header_format)
        
        source_type_stats = statistics.get('source_type_stats', {})
        for source_type, stats in source_type_stats.items():
            row += 1
            worksheet.write(f'A{row}', source_type, data_format)
            worksheet.write(f'B{row}', stats['count'], data_format)
            worksheet.write(f'C{row}', stats['qty'], data_format)
        
        # 空白行
        row += 2
        
        # 接收類型分析
        worksheet.write(f'A{row}', '接收類型分析', header_format)
        worksheet.write(f'B{row}', '建議數量', header_format)
        worksheet.write(f'C{row}', '總件數', header_format)
        
        dest_type_stats = statistics.get('dest_type_stats', {})
        for dest_type, stats in dest_type_stats.items():
            row += 1
            worksheet.write(f'A{row}', dest_type, data_format)
            worksheet.write(f'B{row}', stats['count'], data_format)
            worksheet.write(f'C{row}', stats['qty'], data_format)
        
        # 設置列寬
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        
        # 設置行高
        worksheet.set_row(0, 25)  # 標題行
        worksheet.set_row(2, 20)  # KPI標題行
        worksheet.set_row(3, 20)  # KPI值行
        worksheet.set_row(4, 20)  # KPI值行
        worksheet.set_row(5, 20)  # KPI值行
        worksheet.set_row(6, 20)  # KPI值行
    
    def generate_excel_file(self, recommendations: List[Dict], statistics: Dict, 
                           output_path: Optional[str] = None) -> str:
        """
        生成完整的Excel文件
        
        Args:
            recommendations: 調貨建議列表
            statistics: 統計信息字典
            output_path: 輸出路徑（可選）
            
        Returns:
            生成的文件路徑
        """
        logger.info("開始生成Excel文件")
        
        # 生成文件名
        filename = self.generate_filename()
        
        # 確定完整路徑
        if output_path:
            filepath = f"{output_path}/{filename}"
        else:
            filepath = filename
        
        # 創建ExcelWriter對象
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            # 創建調貨建議工作表
            self.create_transfer_recommendations_sheet(writer, recommendations)
            
            # 創建統計摘要工作表
            self.create_summary_dashboard_sheet(writer, statistics)
        
        logger.info(f"Excel文件生成完成: {filepath}")
        return filepath