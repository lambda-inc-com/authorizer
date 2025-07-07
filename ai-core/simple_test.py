#!/usr/bin/env python3
"""
简单的工作流生成测试
用户输入需求，生成工作流并保存为JSON文件
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from workflow_generation_system import WorkflowGenerationSystem

def get_safe_filename(name: str) -> str:
    """生成安全的文件名"""
    # 移除不安全字符
    safe_chars = []
    for char in name:
        if char.isalnum() or char in ['_', '-', ' ']:
            safe_chars.append(char)
        else:
            safe_chars.append('_')
    
    safe_name = ''.join(safe_chars).strip()
    # 限制长度
    if len(safe_name) > 50:
        safe_name = safe_name[:50]
    
    return safe_name

def save_workflow(workflow_data: dict, workflow_name: str):
    """保存工作流到JSON文件"""
    # 创建保存目录
    save_dir = Path("generated_workflows")
    save_dir.mkdir(exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = get_safe_filename(workflow_name)
    filename = f"{safe_name}_{timestamp}.json"
    filepath = save_dir / filename
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f, ensure_ascii=False, indent=2)
    
    return filepath

async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 工作流生成系统 - 简单测试")
    print("=" * 60)
    
    # 检查API密钥
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ 错误：未找到 CLAUDE_API_KEY 环境变量")
        print("请设置环境变量：export CLAUDE_API_KEY=your_api_key")
        return
    
    print(f"✅ API密钥已配置（前6位：{api_key[:6]}...）")
    
    # 初始化系统
    try:
        system = WorkflowGenerationSystem()
        print("✅ 系统初始化成功")
    except Exception as e:
        print(f"❌ 系统初始化失败：{e}")
        return
    
    while True:
        print("\n" + "="*60)
        print("请输入您的需求（输入 'quit' 退出）:")
        print("="*60)
        
        # 获取用户输入
        user_input = input("🎯 需求描述: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '退出']:
            print("👋 再见！")
            break
        
        if not user_input:
            print("❌ 请输入有效的需求描述")
            continue
        
        print(f"\n🔄 正在生成工作流...")
        print(f"需求：{user_input}")
        
        try:
            # 生成工作流
            result = await system.generate_workflow_from_requirement(user_input)
            
            if result.get("success"):
                workflow = result.get("workflow")
                workflow_name = workflow.get("name", "未命名工作流")
                
                print(f"\n✅ 工作流生成成功！")
                print(f"📝 工作流名称：{workflow_name}")
                print(f"📋 工作流描述：{workflow.get('description', '无描述')}")
                print(f"🔢 节点数量：{len(workflow.get('nodes', []))}")
                
                # 保存工作流
                filepath = save_workflow(result, workflow_name)
                print(f"💾 工作流已保存到：{filepath}")
                
                # 显示基本信息
                print("\n🏗️ 工作流节点:")
                for i, node in enumerate(workflow.get("nodes", []), 1):
                    print(f"  {i}. {node.get('name')} ({node.get('type')})")
                
            else:
                print(f"\n❌ 工作流生成失败：{result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"\n❌ 生成过程中发生错误：{str(e)}")
            print("请检查网络连接和API密钥配置")

if __name__ == "__main__":
    asyncio.run(main()) 