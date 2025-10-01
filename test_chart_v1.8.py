"""
測試圖表生成功能 v1.8
驗證matplotlib圖表生成是否正常工作
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from datetime import datetime

# 設置matplotlib中文字體
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_sample_data():
    """
    創建示例數據
    """
    # 創建示例OM統計數據
    om_names = ['OM001', 'OM002', 'OM003', 'OM004', 'OM005']
    
    # A模式數據
    nd_transfer_a = [20, 15, 30, 10, 25]
    rf_excess_a = [15, 20, 10, 25, 15]
    urgent_receive_a = [25, 15, 20, 15, 20]
    potential_receive_a = [10, 10, 15, 10, 5]
    
    # B模式數據
    rf_enhanced_b = [25, 30, 20, 30, 25]
    
    return om_names, nd_transfer_a, rf_excess_a, rf_enhanced_b, urgent_receive_a, potential_receive_a

def test_chart_a_mode():
    """
    測試A模式圖表生成
    """
    print("測試A模式圖表生成...")
    
    # 獲取示例數據
    om_names, nd_transfer, rf_excess, _, urgent_receive, potential_receive = create_sample_data()
    
    # 創建圖表
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 準備數據
    y_pos = np.arange(len(om_names))
    width = 0.2
    
    # 繪製四條形圖
    ax.barh(y_pos + width*1.5, nd_transfer, width, label='ND Transfer Out', color='skyblue')
    ax.barh(y_pos + width*0.5, rf_excess, width, label='RF Excess Transfer Out', color='lightgreen')
    ax.barh(y_pos - width*0.5, urgent_receive, width, label='Urgent Shortage Receive', color='salmon')
    ax.barh(y_pos - width*1.5, potential_receive, width, label='Potential Shortage Receive', color='gold')
    
    # 設置圖表標籤和標題
    ax.set_yticks(y_pos)
    ax.set_yticklabels(om_names)
    ax.invert_yaxis()  # 標籤從上到下
    ax.set_xlabel('Transfer Quantity')
    ax.set_title('OM Transfer vs Receive Analysis (A Mode - Conservative)')
    ax.legend()
    
    # 保存圖表
    chart_path = f"test_chart_a_mode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"A模式圖表已保存: {chart_path}")
    return chart_path

def test_chart_b_mode():
    """
    測試B模式圖表生成
    """
    print("測試B模式圖表生成...")
    
    # 獲取示例數據
    om_names, nd_transfer, _, rf_enhanced, urgent_receive, potential_receive = create_sample_data()
    
    # 創建圖表
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 準備數據
    y_pos = np.arange(len(om_names))
    width = 0.2
    
    # 繪製四條形圖
    ax.barh(y_pos + width*1.5, nd_transfer, width, label='ND Transfer Out', color='skyblue')
    ax.barh(y_pos + width*0.5, rf_enhanced, width, label='RF Enhanced Transfer Out', color='lightgreen')
    ax.barh(y_pos - width*0.5, urgent_receive, width, label='Urgent Shortage Receive', color='salmon')
    ax.barh(y_pos - width*1.5, potential_receive, width, label='Potential Shortage Receive', color='gold')
    
    # 設置圖表標籤和標題
    ax.set_yticks(y_pos)
    ax.set_yticklabels(om_names)
    ax.invert_yaxis()  # 標籤從上到下
    ax.set_xlabel('Transfer Quantity')
    ax.set_title('OM Transfer vs Receive Analysis (B Mode - Enhanced)')
    ax.legend()
    
    # 保存圖表
    chart_path = f"test_chart_b_mode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"B模式圖表已保存: {chart_path}")
    return chart_path

def test_seaborn_chart():
    """
    測試Seaborn圖表生成
    """
    print("測試Seaborn圖表生成...")
    
    # 創建示例數據
    om_names, nd_transfer, rf_excess, _, urgent_receive, potential_receive = create_sample_data()
    
    # 準備DataFrame
    data = {
        'OM': om_names * 4,
        'Type': ['ND Transfer Out'] * len(om_names) + 
                ['RF Excess Transfer Out'] * len(om_names) + 
                ['Urgent Shortage Receive'] * len(om_names) + 
                ['Potential Shortage Receive'] * len(om_names),
        'Quantity': nd_transfer + rf_excess + urgent_receive + potential_receive
    }
    df = pd.DataFrame(data)
    
    # 創建圖表
    plt.figure(figsize=(12, 8))
    sns.barplot(x='Quantity', y='OM', hue='Type', data=df)
    plt.title('OM Transfer vs Receive Analysis (Seaborn)')
    plt.xlabel('Transfer Quantity')
    plt.ylabel('OM')
    plt.legend()
    
    # 保存圖表
    chart_path = f"test_chart_seaborn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Seaborn圖表已保存: {chart_path}")
    return chart_path

def run_all_tests():
    """
    運行所有測試
    """
    print("開始運行圖表測試...")
    print("=" * 50)
    
    try:
        # 測試A模式圖表
        chart_a = test_chart_a_mode()
        
        # 測試B模式圖表
        chart_b = test_chart_b_mode()
        
        # 測試Seaborn圖表
        chart_seaborn = test_seaborn_chart()
        
        print("=" * 50)
        print("✅ 所有圖表測試通過！圖表生成功能正常。")
        print(f"生成的圖表文件:")
        print(f"  - A模式圖表: {chart_a}")
        print(f"  - B模式圖表: {chart_b}")
        print(f"  - Seaborn圖表: {chart_seaborn}")
        
        return True
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ 圖表測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    # 運行測試
    success = run_all_tests()
    
    # 退出碼
    exit(0 if success else 1)