"""
業務邏輯模組 v1.9.4
實現調貨規則、源/目的地識別和匹配算法
支持三模式系統：A(保守轉貨)/B(加強轉貨)/C(重點補0)
優化接收條件和避免同一SKU的轉出店鋪同時接收
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransferLogic:
    """調貨業務邏輯類 v1.9.4"""
    
    def __init__(self):
        self.transfer_recommendations = []
        self.quality_check_passed = True
        self.quality_errors = []
        self.mode_a = "保守轉貨"  # A模式
        self.mode_b = "加強轉貨"  # B模式
        self.mode_c = "重點補0"  # C模式
    
    def identify_sources(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        識別轉出候選店鋪
        
        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式（保守轉貨、加強轉貨或重點補0）
            
        Returns:
            轉出候選店鋪列表
        """
        sources = []
        
        # 優先級1：ND類型轉出
        nd_sources = group_df[group_df['RP Type'] == 'ND']
        for _, row in nd_sources.iterrows():
            if row['SaSa Net Stock'] > 0:  # 只考慮有庫存的店鋪
                sources.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'transferable_qty': row['SaSa Net Stock'],
                    'priority': 1,
                    'original_stock': row['SaSa Net Stock'],
                    'effective_sold_qty': row['Effective Sold Qty'],
                    'source_type': 'ND轉出'
                })
        
        # 優先級2：RF類型轉出
        rf_sources = group_df[group_df['RP Type'] == 'RF']
        
        # 找出該Article+OM組合中的最高有效銷量
        max_sold_qty = rf_sources['Effective Sold Qty'].max() if not rf_sources.empty else 0
        
        for _, row in rf_sources.iterrows():
            # 條件1：(庫存+在途) > Safety Stock
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            is_stock_above_safety = total_available > row['Safety Stock']
            
            # 條件2：不是最高銷量店鋪
            is_not_highest_sold = row['Effective Sold Qty'] < max_sold_qty
            
            if is_stock_above_safety and is_not_highest_sold:
                # 根據模式計算可轉出數量
                if mode == self.mode_a:
                    # A模式(保守轉貨)
                    # 基礎可轉出 = (庫存+在途) - 安全庫存
                    base_transferable = total_available - row['Safety Stock']
                    
                    # 上限控制 = (庫存+在途) × 20%，但最少2件
                    upper_limit = max(total_available * 0.2, 2)
                    
                    # 實際轉出 = min(基礎可轉出, max(上限控制, 2))
                    actual_transferable = min(base_transferable, upper_limit)
                    
                    # 不能超過實際庫存數量
                    actual_transferable = min(actual_transferable, row['SaSa Net Stock'])
                    
                    # 判斷轉出類型
                    remaining_stock = row['SaSa Net Stock'] - actual_transferable
                    if remaining_stock >= row['Safety Stock']:
                        source_type = 'RF過剩轉出'
                    else:
                        # A模式下不允許剩餘庫存低於安全庫存
                        continue
                        
                elif mode == self.mode_b:
                    # B模式(加強轉貨)
                    # 基礎可轉出 = (庫存+在途) – (MOQ數量+1件)
                    base_transferable = total_available - (row['MOQ'] + 1)
                    
                    # 上限控制 = (庫存+在途) × 50%，但最少2件
                    upper_limit = max(total_available * 0.5, 2)
                    
                    # 實際轉出 = min(基礎可轉出, max(上限控制, 2))
                    actual_transferable = min(base_transferable, upper_limit)
                    
                    # 不能超過實際庫存數量
                    actual_transferable = min(actual_transferable, row['SaSa Net Stock'])
                    
                    # 判斷轉出類型
                    remaining_stock = row['SaSa Net Stock'] - actual_transferable
                    if remaining_stock >= row['Safety Stock']:
                        source_type = 'RF過剩轉出'
                    else:
                        source_type = 'RF加強轉出'
                
                else:
                    # C模式(重點補0) - 與B模式相同的轉出邏輯
                    # 基礎可轉出 = (庫存+在途) – (MOQ數量+1件)
                    base_transferable = total_available - (row['MOQ'] + 1)
                    
                    # 上限控制 = (庫存+在途) × 50%，但最少2件
                    upper_limit = max(total_available * 0.5, 2)
                    
                    # 實際轉出 = min(基礎可轉出, max(上限控制, 2))
                    actual_transferable = min(base_transferable, upper_limit)
                    
                    # 不能超過實際庫存數量
                    actual_transferable = min(actual_transferable, row['SaSa Net Stock'])
                    
                    # 判斷轉出類型
                    remaining_stock = row['SaSa Net Stock'] - actual_transferable
                    if remaining_stock >= row['Safety Stock']:
                        source_type = 'RF過剩轉出'
                    else:
                        source_type = 'RF加強轉出'
                
                if actual_transferable > 0:  # 只考慮有可轉出庫存的店鋪
                    sources.append({
                        'site': row['Site'],
                        'om': row['OM'],
                        'rp_type': row['RP Type'],
                        'transferable_qty': int(actual_transferable),
                        'priority': 2,
                        'original_stock': row['SaSa Net Stock'],
                        'effective_sold_qty': row['Effective Sold Qty'],
                        'source_type': source_type
                    })
        
        # 按優先級排序
        sources.sort(key=lambda x: x['priority'])
        
        return sources
    
    def identify_destinations(self, group_df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        識別接收候選店鋪
        
        Args:
            group_df: 按Article和OM分組的DataFrame
            mode: 轉貨模式（保守轉貨、加強轉貨或重點補0）
            
        Returns:
            接收候選店鋪列表
        """
        destinations = []
        
        # 只考慮RF類型店鋪
        rf_destinations = group_df[group_df['RP Type'] == 'RF']
        
        # 找出該Article+OM組合中的最高有效銷量
        max_sold_qty = rf_destinations['Effective Sold Qty'].max() if not rf_destinations.empty else 0
        
        for _, row in rf_destinations.iterrows():
            total_available = row['SaSa Net Stock'] + row['Pending Received']
            
            # C模式特殊處理：針對(SaSa Net Stock+Pending Received)<=1的店鋪
            if mode == self.mode_c and total_available <= 1:
                # 計算需要補充的數量：根據Safety Stock的50%和3件的最高值來確定補充數量
                target_qty = max(int(row['Safety Stock'] * 0.5), 3)
                needed_qty = target_qty - total_available
                
                if needed_qty > 0:
                    destinations.append({
                        'site': row['Site'],
                        'om': row['OM'],
                        'rp_type': row['RP Type'],
                        'needed_qty': needed_qty,
                        'priority': 1,  # C模式中優先級最高
                        'current_stock': row['SaSa Net Stock'],
                        'pending_received': row['Pending Received'],
                        'safety_stock': row['Safety Stock'],
                        'moq': row['MOQ'],
                        'effective_sold_qty': row['Effective Sold Qty'],
                        'dest_type': '重點補0',
                        'target_qty': target_qty  # 添加目標數量信息
                    })
                continue
            
            # A和B模式的常規處理
            # 優先級1：緊急缺貨補貨
            is_no_stock = row['SaSa Net Stock'] == 0
            has_sales_history = row['Effective Sold Qty'] > 0
            
            if is_no_stock and has_sales_history:
                needed_qty = row['Safety Stock']
                destinations.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'needed_qty': needed_qty,
                    'priority': 1,
                    'current_stock': row['SaSa Net Stock'],
                    'pending_received': row['Pending Received'],
                    'safety_stock': row['Safety Stock'],
                    'moq': row['MOQ'],
                    'effective_sold_qty': row['Effective Sold Qty'],
                    'dest_type': '緊急缺貨補貨',
                    'target_qty': needed_qty  # 添加目標數量信息
                })
                continue
            
            # 優先級2：潛在缺貨補貨
            is_insufficient_stock = total_available < row['Safety Stock']
            is_highest_sold = row['Effective Sold Qty'] == max_sold_qty
            
            if is_insufficient_stock and is_highest_sold:
                needed_qty = row['Safety Stock'] - total_available
                destinations.append({
                    'site': row['Site'],
                    'om': row['OM'],
                    'rp_type': row['RP Type'],
                    'needed_qty': needed_qty,
                    'priority': 2,
                    'current_stock': row['SaSa Net Stock'],
                    'pending_received': row['Pending Received'],
                    'safety_stock': row['Safety Stock'],
                    'moq': row['MOQ'],
                    'effective_sold_qty': row['Effective Sold Qty'],
                    'dest_type': '潛在缺貨補貨',
                    'target_qty': row['Safety Stock']  # 添加目標數量信息
                })
        
        # 按優先級排序
        destinations.sort(key=lambda x: x['priority'])
        
        return destinations
    
    def match_transfers(self, article: str, om: str, sources: List[Dict], 
                       destinations: List[Dict], product_desc: str, mode: str) -> List[Dict]:
        """
        執行轉出與接收的匹配
        
        Args:
            article: 商品編號
            om: OM編號
            sources: 轉出候選店鋪列表
            destinations: 接收候選店鋪列表
            product_desc: 商品描述
            mode: 轉貨模式
            
        Returns:
            匹配成功的調貨建議列表
        """
        recommendations = []
        
        # 複製源和目的地列表，避免修改原始數據
        temp_sources = [s.copy() for s in sources]
        temp_destinations = [d.copy() for d in destinations]
        
        # 記錄已經作為轉出店鋪的站點，避免它們同時作為接收店鋪
        transfer_sites = set()
        
        # 按優先級順序進行匹配
        # 1. ND轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 1, 1, transfer_sites)
        
        # 2. ND轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 1, 2, transfer_sites)
        
        # 3. RF過剩轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 1, transfer_sites, 'RF過剩轉出')
        
        # 4. RF過剩轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 2, transfer_sites, 'RF過剩轉出')
        
        # 5. RF加強轉出 -> 緊急缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 1, transfer_sites, 'RF加強轉出')
        
        # 6. RF加強轉出 -> 潛在缺貨
        self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                               article, om, product_desc, 2, 2, transfer_sites, 'RF加強轉出')
        
        # 7. C模式特殊處理：RF轉出 -> 重點補0
        if mode == self.mode_c:
            self._match_by_priority(temp_sources, temp_destinations, recommendations, 
                                   article, om, product_desc, 2, 1, transfer_sites, None, '重點補0')
        
        return recommendations
    
    def _match_by_priority(self, sources: List[Dict], destinations: List[Dict], 
                          recommendations: List[Dict], article: str, group_id: str, 
                          product_desc: str, source_priority: int, dest_priority: int,
                          transfer_sites: set, source_type_filter: Optional[str] = None,
                          dest_type_filter: Optional[str] = None):
        """
        按指定優先級進行匹配
        
        Args:
            sources: 轉出候選店鋪列表
            destinations: 接收候選店鋪列表
            recommendations: 調貨建議列表
            article: 商品編號
            group_id: 分組ID（OM）
            product_desc: 商品描述
            source_priority: 轉出優先級
            dest_priority: 接收優先級
            transfer_sites: 已經作為轉出店鋪的站點集合
            source_type_filter: 轉出類型過濾器（可選）
            dest_type_filter: 接收類型過濾器（可選）
        """
        # 篩選指定優先級的源和目的地
        filtered_sources = [s for s in sources if s['priority'] == source_priority and s['transferable_qty'] > 0]
        
        # 如果指定了轉出類型過濾器，則按類型篩選
        if source_type_filter:
            filtered_sources = [s for s in filtered_sources if s['source_type'] == source_type_filter]
        
        filtered_destinations = [d for d in destinations if d['priority'] == dest_priority and d['needed_qty'] > 0]
        
        # 如果指定了接收類型過濾器，則按類型篩選
        if dest_type_filter:
            filtered_destinations = [d for d in filtered_destinations if d['dest_type'] == dest_type_filter]
        
        # 執行匹配
        for source in filtered_sources:
            # 將當前轉出店鋪添加到轉出店鋪集合
            transfer_sites.add(source['site'])
            
            for dest in filtered_destinations:
                if source['transferable_qty'] <= 0 or dest['needed_qty'] <= 0:
                    continue
                
                # 避免同一店鋪自我調貨
                if source['site'] == dest['site']:
                    continue
                
                # 避免轉出店鋪同時作為接收店鋪
                if dest['site'] in transfer_sites:
                    continue
                
                # 確定轉移數量
                transfer_qty = min(source['transferable_qty'], dest['needed_qty'])
                
                # 調貨數量優化：如果只有1件，嘗試調高到2件
                if transfer_qty == 1 and source['transferable_qty'] >= 2:
                    # 檢查是否不影響轉出店鋪安全庫存
                    if source['source_type'] in ['ND轉出', 'RF加強轉出']:
                        # ND類型轉出，不影響安全庫存
                        transfer_qty = 2
                    else:
                        # RF過剩轉出類型，需要檢查安全庫存
                        remaining_stock = source['original_stock'] - 2
                        # 這裡簡化處理，實際應根據業務邏輯檢查
                        transfer_qty = 2
                
                # 創建調貨建議
                recommendation = {
                    'Article': article,
                    'Product Desc': product_desc,
                    'Transfer OM': source['om'],
                    'Transfer Site': source['site'],
                    'Receive OM': dest['om'],
                    'Receive Site': dest['site'],
                    'Transfer Qty': transfer_qty,
                    'Original Stock': source['original_stock'],
                    'After Transfer Stock': source['original_stock'] - transfer_qty,
                    'Safety Stock': 0,  # 需要從原始數據獲取
                    'MOQ': 0,  # 需要從原始數據獲取
                    'Source Priority': source['priority'],
                    'Destination Priority': dest['priority'],
                    'Source Type': source['source_type'],
                    'Destination Type': dest['dest_type'],
                    'Notes': ''
                }
                
                # 添加目標數量信息（如果有）
                if 'target_qty' in dest:
                    recommendation['Target Qty'] = dest['target_qty']
                
                recommendations.append(recommendation)
                
                # 更新剩餘可轉出數量和需求數量
                source['transferable_qty'] -= transfer_qty
                dest['needed_qty'] -= transfer_qty
    
    def generate_transfer_recommendations(self, df: pd.DataFrame, mode: str) -> List[Dict]:
        """
        生成所有調貨建議
        
        Args:
            df: 預處理後的DataFrame
            mode: A模式(保守轉貨)、B模式(加強轉貨)或C模式(重點補0)
            
        Returns:
            調貨建議列表
        """
        logger.info(f"開始生成調貨建議 - {mode}")
        
        # 驗證模式
        if mode not in [self.mode_a, self.mode_b, self.mode_c]:
            raise ValueError(f"無效的轉貨模式: {mode}")
        
        # 按Article和OM分組數據
        grouped = df.groupby(['Article', 'OM'])
        
        all_recommendations = []
        
        # 記錄所有已經作為轉出店鋪的站點，避免它們同時作為接收店鋪
        global_transfer_sites = set()
        
        for group_keys, group_df in grouped:
            # 獲取商品描述
            product_desc = group_df['Article Description'].iloc[0] if 'Article Description' in group_df.columns else ""
            
            # 識別轉出候選店鋪
            sources = self.identify_sources(group_df, mode)
            
            # 識別接收候選店鋪
            destinations = self.identify_destinations(group_df, mode)
            
            # 執行匹配
            article, om = group_keys
            recommendations = self.match_transfers(article, om, sources, destinations, product_desc, mode)
            
            # 更新全局轉出店鋪集合
            for rec in recommendations:
                global_transfer_sites.add(rec['Transfer Site'])
            
            # 更新安全庫存和MOQ信息
            for rec in recommendations:
                # 從原始數據中獲取安全庫存和MOQ
                source_data = df[(df['Article'] == rec['Article']) & (df['Site'] == rec['Transfer Site'])]
                if not source_data.empty:
                    rec['Safety Stock'] = source_data['Safety Stock'].iloc[0]
                    rec['MOQ'] = source_data['MOQ'].iloc[0]
            
            all_recommendations.extend(recommendations)
        
        logger.info(f"共生成 {len(all_recommendations)} 條調貨建議")
        
        self.transfer_recommendations = all_recommendations
        return all_recommendations
    
    def perform_quality_checks(self, df: pd.DataFrame) -> bool:
        """
        執行質量檢查
        
        Args:
            df: 原始數據DataFrame
            
        Returns:
            質量檢查是否通過
        """
        logger.info("開始執行質量檢查")
        
        self.quality_errors = []
        self.quality_check_passed = True
        
        # 檢查1：轉出與接收的Article必須完全一致
        for rec in self.transfer_recommendations:
            if 'Article' not in rec:
                self.quality_errors.append(f"調貨建議中缺少Article欄位: {rec}")
                self.quality_check_passed = False
        
        # 檢查2：Transfer Qty必須為正整數
        for rec in self.transfer_recommendations:
            if not isinstance(rec['Transfer Qty'], int) or rec['Transfer Qty'] <= 0:
                self.quality_errors.append(f"轉移數量必須為正整數: {rec}")
                self.quality_check_passed = False
        
        # 檢查3：Transfer Qty不得超過轉出店鋪的原始SaSa Net Stock
        for rec in self.transfer_recommendations:
            transfer_site = rec['Transfer Site']
            article = rec['Article']
            
            # 查找轉出店鋪的原始庫存
            source_data = df[(df['Article'] == article) & (df['Site'] == transfer_site)]
            if not source_data.empty:
                original_stock = source_data['SaSa Net Stock'].iloc[0]
                if rec['Transfer Qty'] > original_stock:
                    self.quality_errors.append(f"轉移數量超過原始庫存: {rec}")
                    self.quality_check_passed = False
        
        # 檢查4：Transfer Site和Receive Site不能相同
        for rec in self.transfer_recommendations:
            if rec['Transfer Site'] == rec['Receive Site']:
                self.quality_errors.append(f"轉出店鋪和接收店鋪不能相同: {rec}")
                self.quality_check_passed = False
        
        # 檢查5：最終輸出的Article欄位必須是12位文本格式
        for rec in self.transfer_recommendations:
            if not isinstance(rec['Article'], str) or len(rec['Article']) != 12:
                self.quality_errors.append(f"Article欄位必須是12位文本格式: {rec}")
                self.quality_check_passed = False
        
        # 檢查6：同一SKU的轉出店鋪不能同時作為接收店鋪
        transfer_sites_by_article = {}
        receive_sites_by_article = {}
        
        for rec in self.transfer_recommendations:
            article = rec['Article']
            
            # 記錄轉出店鋪
            if article not in transfer_sites_by_article:
                transfer_sites_by_article[article] = set()
            transfer_sites_by_article[article].add(rec['Transfer Site'])
            
            # 記錄接收店鋪
            if article not in receive_sites_by_article:
                receive_sites_by_article[article] = set()
            receive_sites_by_article[article].add(rec['Receive Site'])
        
        # 檢查是否有重疊
        for article in transfer_sites_by_article:
            if article in receive_sites_by_article:
                overlap = transfer_sites_by_article[article] & receive_sites_by_article[article]
                if overlap:
                    self.quality_errors.append(f"同一SKU {article} 的轉出店鋪同時作為接收店鋪: {overlap}")
                    self.quality_check_passed = False
        
        if self.quality_check_passed:
            logger.info("質量檢查通過")
        else:
            logger.error(f"質量檢查失敗，發現 {len(self.quality_errors)} 個錯誤")
            for error in self.quality_errors:
                logger.error(error)
        
        return self.quality_check_passed
    
    def get_transfer_statistics(self) -> Dict:
        """
        獲取調貨統計信息
        
        Returns:
            統計信息字典
        """
        if not self.transfer_recommendations:
            return {}
        
        # 總調貨建議數量
        total_recommendations = len(self.transfer_recommendations)
        
        # 總調貨件數
        total_transfer_qty = sum(rec['Transfer Qty'] for rec in self.transfer_recommendations)
        
        # 涉及產品數量
        unique_articles = len(set(rec['Article'] for rec in self.transfer_recommendations))
        
        # 涉及OM數量
        unique_oms = len(set(rec['Transfer OM'] for rec in self.transfer_recommendations))
        
        # 按Article統計
        article_stats = {}
        for rec in self.transfer_recommendations:
            article = rec['Article']
            if article not in article_stats:
                article_stats[article] = {
                    'total_qty': 0,
                    'count': 0,
                    'oms': set()
                }
            article_stats[article]['total_qty'] += rec['Transfer Qty']
            article_stats[article]['count'] += 1
            article_stats[article]['oms'].add(rec['Transfer OM'])
        
        # 轉換set為count
        for article in article_stats:
            article_stats[article]['om_count'] = len(article_stats[article]['oms'])
        
        # 按OM統計
        om_stats = {}
        for rec in self.transfer_recommendations:
            om = rec['Transfer OM']
            if om not in om_stats:
                om_stats[om] = {
                    'total_qty': 0,
                    'count': 0,
                    'articles': set()
                }
            om_stats[om]['total_qty'] += rec['Transfer Qty']
            om_stats[om]['count'] += 1
            om_stats[om]['articles'].add(rec['Article'])
        
        # 轉換set為count
        for om in om_stats:
            om_stats[om]['article_count'] = len(om_stats[om]['articles'])
        
        # 轉出類型分析
        source_type_stats = {}
        for rec in self.transfer_recommendations:
            source_type = rec.get('Source Type', 'Unknown')
            if source_type not in source_type_stats:
                source_type_stats[source_type] = {'count': 0, 'qty': 0}
            source_type_stats[source_type]['count'] += 1
            source_type_stats[source_type]['qty'] += rec['Transfer Qty']
        
        # 接收類型分析
        dest_type_stats = {}
        for rec in self.transfer_recommendations:
            dest_type = rec.get('Destination Type', 'Unknown')
            if dest_type not in dest_type_stats:
                dest_type_stats[dest_type] = {'count': 0, 'qty': 0}
            dest_type_stats[dest_type]['count'] += 1
            dest_type_stats[dest_type]['qty'] += rec['Transfer Qty']
        
        return {
            'total_recommendations': total_recommendations,
            'total_transfer_qty': total_transfer_qty,
            'unique_articles': unique_articles,
            'unique_oms': unique_oms,
            'article_stats': article_stats,
            'om_stats': om_stats,
            'source_type_stats': source_type_stats,
            'dest_type_stats': dest_type_stats
        }