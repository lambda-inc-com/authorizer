"""
多智能体工作流生成系统使用示例
Example Usage of Multi-Agent Workflow Generation System
"""

import asyncio
import json
import logging
from workflow_generation_system import WorkflowGenerationSystem, LLMClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def example_1_basic_usage():
    """示例1: 基本使用"""
    print("🔥 示例1: 基本工作流生成")
    print("=" * 50)
    
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 用户需求
    user_requirement = """
    我需要创建一个用户注册工作流：
    1. 验证用户输入的邮箱和密码
    2. 检查邮箱是否已存在
    3. 如果不存在，创建新用户
    4. 发送欢迎邮件
    5. 返回注册结果
    """
    
    try:
        # 生成工作流
        result = await system.generate_workflow_from_requirement(user_requirement)
        
        if result["success"]:
            workflow = result["workflow"]
            print(f"✅ 工作流生成成功!")
            print(f"   工作流名称: {workflow['name']}")
            print(f"   节点数量: {len(workflow['nodes'])}")
            print(f"   工作流描述: {workflow['description']}")
            
            # 打印节点信息
            print("\n📋 节点列表:")
            for i, node in enumerate(workflow['nodes'], 1):
                print(f"   {i}. {node['name']} ({node['type']})")
            
            # 获取生成历史
            history_result = await system.get_generation_history()
            if history_result["success"]:
                print(f"\n📚 生成历史记录: {len(history_result['generation_history'])} 条")
        else:
            print(f"❌ 工作流生成失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")


async def example_2_validation_only():
    """示例2: 独立验证工作流"""
    print("\n🔍 示例2: 工作流验证")
    print("=" * 50)
    
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 一个示例工作流（故意包含一些问题）
    test_workflow = {
        "name": "测试工作流",
        "description": "用于测试验证功能的工作流",
        "version": "1.0.0",
        "nodes": [
            {
                "name": "WorkflowStart",
                "type": "workflowStart",
                "desc": "开始节点",
                "inputs": {},
                "outputs": {},
                "configs": {},
                "nextNodes": ["QueryUser"]
            },
            {
                "name": "QueryUser",
                "type": "dbQuery",
                "desc": "查询用户",
                "inputs": {},
                "outputs": {
                    "userData": {
                        "type": "object",
                        "value": "$currentNodeResult",
                        "desc": "用户数据"
                    }
                },
                "configs": {
                    "table": "users",
                    "fields": ["id", "name", "email"]
                    # 缺少filters，会被验证器发现
                },
                "nextNodes": ["WorkflowEnd"]
            },
            {
                "name": "WorkflowEnd",
                "type": "workflowEnd",
                "desc": "结束节点",
                "inputs": {},
                "outputs": {},
                "configs": {},
                "nextNodes": ["end"]
            }
        ]
    }
    
    try:
        # 验证工作流
        validation_result = await system.validate_workflow(test_workflow)
        
        if validation_result["success"]:
            val_result = validation_result["validation_result"]
            
            print(f"📊 验证结果:")
            print(f"   通过验证: {val_result['validation_result']['is_valid']}")
            print(f"   总体评分: {val_result['validation_result']['overall_score']}")
            print(f"   错误数量: {val_result['validation_result']['error_count']}")
            print(f"   警告数量: {val_result['validation_result']['warning_count']}")
            
            # 显示详细验证结果
            if val_result['all_errors']:
                print(f"\n❌ 发现的错误:")
                for error in val_result['all_errors']:
                    print(f"   - {error}")
            
            if val_result['all_warnings']:
                print(f"\n⚠️ 发现的警告:")
                for warning in val_result['all_warnings']:
                    print(f"   - {warning}")
        else:
            print(f"❌ 验证失败: {validation_result['error']}")
    
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")


async def example_3_system_status():
    """示例3: 系统状态查询"""
    print("\n📊 示例3: 系统状态")
    print("=" * 50)
    
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 获取系统状态
    status = system.get_system_status()
    
    print(f"🖥️ 系统状态:")
    print(f"   系统就绪: {status['system_ready']}")
    print(f"   智能体数量: {len(status['agents_status'])}")
    
    print(f"\n🤖 智能体状态:")
    for role, agent_status in status['agents_status'].items():
        busy_status = "忙碌" if agent_status['is_busy'] else "空闲"
        print(f"   - {role}: {busy_status}")
    
    print(f"\n📨 消息总线状态:")
    bus_status = status['message_bus_status']
    print(f"   订阅者数量: {bus_status['subscribers_count']}")
    print(f"   消息历史: {bus_status['message_history_count']} 条")


async def example_4_complex_workflow():
    """示例4: 复杂工作流生成"""
    print("\n🚀 示例4: 复杂工作流生成")
    print("=" * 50)
    
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 复杂的用户需求
    complex_requirement = """
    我需要创建一个电商订单处理工作流：
    
    1. 接收订单信息（用户ID、商品列表、收货地址）
    2. 验证用户身份和余额
    3. 检查商品库存
    4. 如果库存充足：
       a. 创建订单记录
       b. 扣减库存
       c. 扣减用户余额
       d. 创建支付记录
       e. 发送订单确认邮件
    5. 如果库存不足：
       a. 返回库存不足错误
       b. 发送库存不足通知
    6. 更新用户订单历史
    7. 返回处理结果
    
    整个过程需要保证数据一致性，如果任何步骤失败都要回滚。
    """
    
    try:
        print("🔧 开始生成复杂工作流...")
        result = await system.generate_workflow_from_requirement(complex_requirement)
        
        if result["success"]:
            workflow = result["workflow"]
            print(f"✅ 复杂工作流生成成功!")
            print(f"   工作流名称: {workflow['name']}")
            print(f"   节点数量: {len(workflow['nodes'])}")
            
            # 分析节点类型分布
            node_types = {}
            for node in workflow['nodes']:
                node_type = node['type']
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            print(f"\n📈 节点类型分布:")
            for node_type, count in node_types.items():
                print(f"   - {node_type}: {count} 个")
            
            # 保存工作流到文件
            with open("generated_complex_workflow.json", "w", encoding="utf-8") as f:
                json.dump(workflow, f, ensure_ascii=False, indent=2)
            print(f"\n💾 工作流已保存到: generated_complex_workflow.json")
            
        else:
            print(f"❌ 复杂工作流生成失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")


async def example_5_batch_generation():
    """示例5: 批量生成工作流"""
    print("\n⚡ 示例5: 批量工作流生成")
    print("=" * 50)
    
    # 多个需求
    requirements = [
        "创建一个简单的用户登录验证工作流",
        "创建一个文件上传和处理工作流",
        "创建一个数据备份工作流"
    ]
    
    print(f"📋 准备批量生成 {len(requirements)} 个工作流...")
    
    try:
        # 创建系统实例
        system = WorkflowGenerationSystem()
        
        # 并发生成多个工作流
        tasks = [
            system.generate_workflow_from_requirement(req) 
            for req in requirements
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"\n📊 批量生成结果:")
        success_count = 0
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"   {i}. ❌ 失败: {str(result)}")
            elif result.get("success"):
                success_count += 1
                workflow_name = result["workflow"]["name"]
                node_count = len(result["workflow"]["nodes"])
                print(f"   {i}. ✅ 成功: {workflow_name} ({node_count} 节点)")
            else:
                print(f"   {i}. ❌ 失败: {result.get('error', '未知错误')}")
        
        print(f"\n🎯 成功率: {success_count}/{len(requirements)} ({success_count/len(requirements)*100:.1f}%)")
    
    except Exception as e:
        print(f"❌ 批量生成异常: {str(e)}")


async def main():
    """主函数"""
    print("🌟 多智能体工作流生成系统 - 使用示例")
    print("=" * 70)
    
    try:
        # 运行所有示例
        await example_1_basic_usage()
        # await example_2_validation_only()
        # await example_3_system_status()
        # await example_4_complex_workflow()
        # await example_5_batch_generation()
        
        print("\n" + "=" * 70)
        print("🎉 所有示例运行完成!")
        print("💡 提示: 查看生成的 generated_complex_workflow.json 文件")
        print("📖 更多信息请参考: README_MultiAgent_Workflow_Generator.md")
        
    except Exception as e:
        print(f"\n❌ 主程序异常: {str(e)}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main()) 