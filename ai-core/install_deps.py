#!/usr/bin/env python3
"""
安装工作流生成依赖

快速安装必要的Python包
"""

import subprocess
import sys

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """主安装函数"""
    print("📦 安装工作流生成依赖")
    print("=" * 30)
    
    packages = ["aiohttp", "loguru"]
    
    for package in packages:
        print(f"正在安装 {package}...")
        if install_package(package):
            print(f"✅ {package} 安装成功")
        else:
            print(f"❌ {package} 安装失败")
    
    print("\n🎉 依赖安装完成!")
    print("现在可以运行: python test_workflow.py")

if __name__ == "__main__":
    main() 