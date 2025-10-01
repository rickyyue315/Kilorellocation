"""
依賴安裝腳本 v1.8
解決可能的依賴衝突問題
"""

import subprocess
import sys
import importlib

def check_package(package_name):
    """
    檢查包是否已安裝
    
    Args:
        package_name: 包名
        
    Returns:
        是否已安裝
    """
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name, version=None):
    """
    安裝包
    
    Args:
        package_name: 包名
        version: 版本要求
        
    Returns:
        是否安裝成功
    """
    try:
        if version:
            package_spec = f"{package_name}>={version}"
        else:
            package_spec = package_name
        
        print(f"正在安裝 {package_spec}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
        return True
    except subprocess.CalledProcessError:
        print(f"安裝 {package_name} 失敗")
        return False

def main():
    """
    主函數
    """
    print("檢查並安裝依賴包...")
    print("=" * 50)
    
    # 定義核心依賴包
    core_packages = {
        "pandas": "2.0.0",
        "openpyxl": "3.1.0",
        "streamlit": "1.28.0",
        "numpy": "1.24.0",
        "xlsxwriter": "3.1.0",
        "matplotlib": "3.7.0",
        "seaborn": "0.12.0"
    }
    
    # 檢查並安裝每個包
    all_installed = True
    for package, version in core_packages.items():
        if check_package(package):
            print(f"✅ {package} 已安裝")
        else:
            print(f"❌ {package} 未安裝")
            if install_package(package, version):
                print(f"✅ {package} 安裝成功")
            else:
                print(f"❌ {package} 安裝失敗")
                all_installed = False
    
    print("=" * 50)
    if all_installed:
        print("✅ 所有依賴包安裝成功！")
        return 0
    else:
        print("❌ 部分依賴包安裝失敗，請手動安裝")
        return 1

if __name__ == "__main__":
    exit(main())