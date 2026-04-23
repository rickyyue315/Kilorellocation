import pytest
import pandas as pd
from business_logic import TransferLogic

def test_c1_mode_no_dual_role():
    data = {
        'Article': ['A1', 'A1', 'A1', 'A1'],
        'Site': ['S1', 'S2', 'S3', 'S4'],
        'Inventory Qty': [10, 0, 10, 0],
        'Sales Qty': [1, 5, 1, 5],
        'Target Stock': [2, 10, 2, 10],
        'Type': ['M', 'M', 'M', 'M'],
        'OM': ['OM1', 'OM1', 'OM1', 'OM1'],
        'OM/Non-OM': ['OM', 'OM', 'OM', 'OM'],
        'Min Stock': [1, 1, 1, 1],
        'Safety Stock': [1, 1, 1, 1],
        'Last Month Sold Qty': [5, 5, 5, 5],
        'MTD Sold Qty': [2, 2, 2, 2],
        'Store': ['S1', 'S2', 'S3', 'S4'],
        'Normal/ND': ['Normal', 'Normal', 'Normal', 'Normal']
    }
    df = pd.DataFrame(data)
    
    logic = TransferLogic()
    mode_c1 = logic.mode_c1
    
    try:
        recommendations = logic.generate_transfer_recommendations(df, mode_c1)
    except Exception as e:
        pytest.fail(f"C1 mode recommendation failed: {str(e)}")

    article_sources = {}
    article_dests = {}
    
    for rec in recommendations:
        art = rec['Article']
        src = rec['Transfer Site']
        dst = rec['Receive Site']
        
        if art not in article_sources: article_sources[art] = set()
        if art not in article_dests: article_dests[art] = set()
        
        article_sources[art].add(src)
        article_dests[art].add(dst)
        
    for art in article_sources:
        overlap = article_sources[art] & article_dests[art]
        assert not overlap, f"Dual role detected for article {art} at sites {overlap} in C1 mode"

if __name__ == '__main__':
    pytest.main([__file__])
