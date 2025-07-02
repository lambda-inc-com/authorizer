#!/usr/bin/env python3
"""
工作流生成测试脚本

使用方法:
python test_workflow.py
"""

import asyncio
import json
import os
from datetime import datetime

# 简单的.env文件加载器
def load_env_file():
    """加载.env文件中的环境变量"""
    env_paths = [
        "../server/.env",  # server目录下的.env
        "../.env",         # 项目根目录的.env
        ".env"             # 当前目录的.env
    ]
    
    loaded_vars = {}
    for env_path in env_paths:
        try:
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # 去掉引号
                            value = value.strip().strip('"').strip("'")
                            loaded_vars[key] = value
                            # 设置到环境变量中
                            os.environ[key] = value
                print(f"✅ 加载了 .env 文件: {env_path}")
                break
        except Exception as e:
            continue
    
    return loaded_vars

# 检查环境变量
def check_environment():
    """检查环境变量设置"""
    # 首先尝试加载.env文件
    print("🔄 尝试加载 .env 文件...")
    load_env_file()
    
    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "CLAUDE_API_KEY": os.getenv("CLAUDE_API_KEY"), 
        "XAI_API_KEY": os.getenv("XAI_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY")
    }
    
    print("🔍 检查环境变量:")
    available_keys = []
    for key, value in api_keys.items():
        if value:
            print(f"✅ {key}: 已设置")
            available_keys.append(key)
        else:
            print(f"❌ {key}: 未设置")
    
    if not available_keys:
        print("\n⚠️ 没有设置任何API密钥!")
        print("请设置至少一个API密钥:")
        print("export OPENAI_API_KEY='your-key'")
        print("export CLAUDE_API_KEY='your-key'")
        print("export XAI_API_KEY='your-key'")
        print("export DEEPSEEK_API_KEY='your-key'")
        return False
    
    print(f"\n✅ 共有 {len(available_keys)} 个API密钥可用")
    return True

# 安装依赖检查
def check_dependencies():
    """检查必要的依赖"""
    print("\n📦 检查依赖:")
    required_packages = ['aiohttp', 'loguru']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            print(f"❌ {package}: 需要安装")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️ 缺少依赖: {', '.join(missing)}")
        print("安装命令: pip install " + " ".join(missing))
        return False
    
    return True

# 简单测试
async def simple_test():
    """简单的工作流生成测试"""
    print("\n🚀 开始工作流生成测试...")
    
    try:
        # 添加当前目录到Python路径
        import sys
        sys.path.insert(0, '.')
        
        # 导入智能体
        from agents.enhanced_workflow_generator import create_workflow_with_model, EnhancedWorkflowGeneratorAgent
        from services.unified_llm_client import UnifiedLLMClient
        
        print("✅ 智能体模块导入成功")
        
        # 检查可用模型
        client = UnifiedLLMClient()
        available_models = client.get_enabled_models()
        
        if not available_models:
            print("❌ 没有可用的模型，请检查配置和API密钥")
            return
        
        print(f"✅ 找到 {len(available_models)} 个可用模型:")
        for model in available_models:
            status = "✅" if model['has_api_key'] else "❌"
            print(f"  {status} {model['key']}: {model['provider']} - {model['model_name']}")
        
        # 选择第一个可用模型进行测试
        test_model = available_models[0]['key']
        print(f"\n🎯 使用模型进行测试: {test_model}")
        
        # 测试任务
        task_description = "创建用户注册流程工作流，包括邮箱验证、信息填写和账户激活步骤"
        
        print(f"📝 任务描述: {task_description}")
        print("⏳ 正在生成工作流...")
        
        # 调用工作流生成
        result = await create_workflow_with_model(
            model_key=test_model,
            task_description=task_description,
            context={"业务类型": "用户管理", "平台": "Web应用"},
            parameters={"complexity_level": "medium"}
        )
        
        if result.success:
            workflow_data = result.result
            print(f"\n🎉 工作流生成成功!")
            print(f"📊 统计信息:")
            print(f"  模型: {workflow_data['model_used']['model_name']}")
            print(f"  提供商: {workflow_data['model_used']['provider']}")
            print(f"  节点数量: {workflow_data['node_count']}")
            print(f"  连接数量: {workflow_data['edge_count']}")
            print(f"  执行时间: {result.execution_time:.2f}秒")
            
            # 显示部分节点信息
            nodes = workflow_data['workflow'].get('nodes', [])
            print(f"\n📦 工作流节点:")
            for i, node in enumerate(nodes[:5], 1):
                node_type = node.get('type', 'unknown')
                node_label = node.get('data', {}).get('label', node_type)
                print(f"  {i}. {node_label} ({node_type})")
            
            if len(nodes) > 5:
                print(f"  ... 还有 {len(nodes) - 5} 个节点")
            
            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_workflow_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(workflow_data['workflow'], f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 工作流已保存: {filename}")
            print(f"📄 完整结果数据已保存: test_result_{timestamp}.json")
            
            # 保存完整结果
            with open(f"test_result_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump({
                    "success": result.success,
                    "workflow_data": workflow_data,
                    "execution_time": result.execution_time,
                    "test_info": {
                        "model_used": test_model,
                        "task_description": task_description,
                        "timestamp": timestamp
                    }
                }, f, indent=2, ensure_ascii=False)
            
            return True
        else:
            print(f"\n❌ 工作流生成失败: {result.error}")
            return False
            
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保您在 ai-core 目录中运行此脚本")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

# 多模型对比测试
async def multi_model_test():
    """多模型对比测试"""
    print("\n🏆 多模型对比测试")
    print("=" * 50)
    
    try:
        # 添加当前目录到Python路径
        import sys
        sys.path.insert(0, '.')
        
        from agents.enhanced_workflow_generator import create_workflow_with_model
        from services.unified_llm_client import UnifiedLLMClient
        
        client = UnifiedLLMClient()
        available_models = client.get_enabled_models()
        
        if len(available_models) < 2:
            print("⚠️ 只有一个可用模型，跳过对比测试")
            return
        
        task = "创建智能客服工作流，支持问题分类、知识库查询和人工转接"
        
        results = {}
        for i, model in enumerate(available_models[:3], 1):  # 最多测试3个模型
            model_key = model['key']
            print(f"\n🔄 [{i}/{min(3, len(available_models))}] 测试 {model['provider']} - {model['model_name']}")
            
            try:
                result = await create_workflow_with_model(
                    model_key=model_key,
                    task_description=task,
                    context={"业务类型": "客服系统"},
                    parameters={"complexity_level": "medium"}
                )
                
                if result.success:
                    results[model_key] = {
                        "success": True,
                        "provider": result.result['model_used']['provider'],
                        "model_name": result.result['model_used']['model_name'],
                        "node_count": result.result['node_count'],
                        "edge_count": result.result['edge_count'],
                        "execution_time": result.execution_time
                    }
                    print(f"  ✅ 成功 | 节点:{result.result['node_count']} | 耗时:{result.execution_time:.2f}s")
                else:
                    results[model_key] = {"success": False, "error": result.error}
                    print(f"  ❌ 失败: {result.error}")
                    
            except Exception as e:
                results[model_key] = {"success": False, "error": str(e)}
                print(f"  ❌ 异常: {str(e)}")
        
        # 显示对比结果
        print(f"\n📊 对比结果:")
        successful = {k: v for k, v in results.items() if v.get("success")}
        if successful:
            sorted_results = sorted(successful.items(), key=lambda x: x[1]["node_count"], reverse=True)
            for i, (model_key, data) in enumerate(sorted_results, 1):
                rank = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
                print(f"{rank} {data['provider']} - {data['model_name']}")
                print(f"    节点数: {data['node_count']} | 连接数: {data['edge_count']} | 耗时: {data['execution_time']:.2f}s")
        
    except Exception as e:
        print(f"❌ 对比测试失败: {str(e)}")

# 主函数
async def main():
    """主测试函数"""
    print("🧪 工作流生成测试脚本")
    print("=" * 50)
    
    # 环境检查
    if not check_environment():
        return
    
    if not check_dependencies():
        return
    
    print("\n✅ 环境检查通过，开始测试...")
    
    # 基础测试
    basic_success = await simple_test()
    
    if basic_success:
        print("\n" + "="*50)
        choice = input("是否进行多模型对比测试? (y/n): ").lower().strip()
        if choice in ['y', 'yes', '是']:
            await multi_model_test()
    
    print(f"\n🎉 测试完成!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试运行异常: {e}") 