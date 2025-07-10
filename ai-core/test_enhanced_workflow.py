"""
增强版多智能体工作流生成系统测试
Enhanced Multi-Agent Workflow Generation System Test
"""

import asyncio
import json
import logging
from workflow_generation_system import WorkflowGenerationSystem

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



async def test_specific_requirement():
    """测试特定需求"""
    
    system = WorkflowGenerationSystem()
    
    # 用户自定义需求
    custom_requirement = """
    我想创建一个商品入库流程：
    1. 首先验证供应商信息是否存在
    2. 检查商品信息，如果商品不存在则创建新商品
    3. 更新库存数量
    4. 记录库存变动历史
    5. 如果入库数量超过1000件，需要发送通知给仓库管理员
    """
    
    print("🚀 测试自定义需求:")
    print(custom_requirement)
    print()
    
    try:
        result = await system.generate_workflow_from_requirement(custom_requirement)
        
        if result.get("success"):
            workflow = result["workflow"]
            print("✅ 自定义工作流生成成功!")
            
            # 输出详细的生成过程信息
            generation_history = result.get("generation_history", [])
            for step in generation_history:
                stage = step.get("stage", "Unknown")
                print(f"\n📋 阶段: {stage}")
                
                if stage == "enhanced_requirement_analysis":
                    analysis = step.get("result", {}).get("analysis", {})
                    print(f"  需求总结: {analysis.get('requirement_summary', 'N/A')}")
                    print(f"  关键行为: {', '.join(analysis.get('key_actions', []))}")
                    print(f"  数据实体: {', '.join(analysis.get('data_entities', []))}")
                    
                    generated_nodes = step.get("result", {}).get("generated_nodes", [])
                    print(f"  生成的节点数量: {len(generated_nodes)}")
                    for node_info in generated_nodes:
                        node_config = node_info.get("node_config", {})
                        print(f"    - {node_config.get('name', 'Unknown')} ({node_config.get('type', 'Unknown')})")
            
            # 保存到文件
            with open("generated_workflows/custom_workflow.json", 'w', encoding='utf-8') as f:
                json.dump(workflow, f, ensure_ascii=False, indent=2)
            print("\n💾 自定义工作流已保存到: generated_workflows/custom_workflow.json")
            
        else:
            print("❌ 自定义工作流生成失败!")
            print(f"错误信息: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 自定义测试失败: {str(e)}")
        logger.error("自定义测试失败", exc_info=True)


async def main():
    """主函数"""
    print("🤖 增强版多智能体工作流生成系统测试")
    print("Enhanced Multi-Agent Workflow Generation System Test")
    print()

    
    # 测试自定义需求
    await test_specific_requirement()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main()) 