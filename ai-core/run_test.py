#!/usr/bin/env python3
"""
多智能体工作流生成系统 - 测试运行脚本
Multi-Agent Workflow Generation System - Test Runner
"""

import asyncio
import sys
import traceback
from workflow_generation_system import WorkflowGenerationSystem

async def run_simple_test():
    """运行简单测试"""
    print("🚀 启动多智能体工作流生成系统测试")
    print("=" * 60)
    
    try:
        # 创建系统实例
        print("📦 正在初始化系统...")
        system = WorkflowGenerationSystem()
        
        # 检查系统状态
        print("🔍 检查系统状态...")
        status = system.get_system_status()
        print(f"   系统就绪: {status['system_ready']}")
        print(f"   智能体数量: {len(status['agents_status'])}")
        
        if not status['system_ready']:
            print("❌ 系统未就绪，请检查配置")
            return False
        
        # 测试用户需求
        test_requirement = "创建一个简单的用户查询工作流，输入用户ID，查询用户信息并返回结果"
        
        print(f"\n🎯 测试需求: {test_requirement}")
        print("\n⏳ 正在生成工作流...")
        
        # 生成工作流
        result = await system.generate_workflow_from_requirement(test_requirement)
        
        if result["success"]:
            workflow = result["workflow"]
            print(f"✅ 测试成功!")
            print(f"   工作流名称: {workflow['name']}")
            print(f"   节点数量: {len(workflow['nodes'])}")
            print(f"   工作流版本: {workflow['version']}")
            
            # 显示节点信息
            print(f"\n📋 生成的节点:")
            for i, node in enumerate(workflow['nodes'], 1):
                print(f"   {i}. {node['name']} ({node['type']})")
            
            return True
        else:
            print(f"❌ 测试失败: {result['error']}")
            return False
    
    except Exception as e:
        print(f"❌ 测试过程中发生异常:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        print(f"\n📋 详细错误堆栈:")
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🌟 多智能体工作流生成系统 - 快速测试")
    print("=" * 60)
    
    # 运行测试
    success = await run_simple_test()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试完成! 系统运行正常")
        print("💡 要运行完整示例，请执行: python example_usage.py")
    else:
        print("❌ 测试失败! 请检查系统配置")
        print("🔧 troubleshooting:")
        print("   1. 检查所有依赖是否正确安装")
        print("   2. 确认 Python 版本 >= 3.7")
        print("   3. 检查文件路径和权限")
    
    print("📖 详细文档: README_MultiAgent_Workflow_Generator.md")
    
    return success

if __name__ == "__main__":
    try:
        # 运行测试
        success = asyncio.run(main())
        
        # 设置退出代码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 意外错误: {str(e)}")
        sys.exit(1) 