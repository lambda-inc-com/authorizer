"""
增强版工作流生成器快速开始示例

演示如何使用新的工作流生成系统
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# 添加当前目录到路径，确保可以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agents.ultimate_workflow_generator import (
    UltimateWorkflowGeneratorAgent, 
    create_workflow_with_ultimate_generator
)
from utils.workflow_validator import validate_workflow_dict
from loguru import logger


async def example_1_simple_workflow():
    """示例1：生成简单的用户注册工作流"""
    logger.info("🔥 示例1：生成简单的用户注册工作流")
    
    result = await create_workflow_with_ultimate_generator(
        task_description="创建一个用户注册工作流，包括邮箱验证、信息保存到数据库、发送欢迎邮件",
        scenario="user_management",
        auto_validate=True,
        auto_optimize=True
    )
    
    if result["success"]:
        workflow = result["workflow"]
        logger.success(f"✅ 工作流生成成功！包含 {len(workflow['nodes'])} 个节点")
        
        # 显示节点类型
        node_types = [node["type"] for node in workflow["nodes"]]
        logger.info(f"📋 节点类型: {', '.join(node_types)}")
        
        # 验证信息
        if "validation" in result:
            validation = result["validation"]
            logger.info(f"🔍 验证结果: {'通过' if validation['is_valid'] else '失败'}")
            if validation["warnings"]:
                logger.warning(f"⚠️ 警告: {len(validation['warnings'])} 个")
    else:
        logger.error(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    return result


async def example_2_data_processing():
    """示例2：生成数据处理工作流"""
    logger.info("🔥 示例2：生成数据处理工作流")
    
    result = await create_workflow_with_ultimate_generator(
        task_description="从数据库查询用户行为数据，使用AI分析用户偏好，生成个性化推荐报告",
        scenario="data_processing",
        context={
            "data_source": "用户行为数据库",
            "analysis_type": "偏好分析和推荐",
            "output_format": "JSON报告"
        },
        parameters={
            "complexity_level": "medium",
            "include_error_handling": True,
            "priority_focus": "数据质量"
        },
        auto_validate=True,
        auto_optimize=True
    )
    
    if result["success"]:
        workflow = result["workflow"]
        logger.success(f"✅ 数据处理工作流生成成功！")
        
        # 显示模型信息
        if "model_info" in result:
            model = result["model_info"]
            logger.info(f"🤖 使用模型: {model.get('model_name', '未知')}")
            
        # 显示验证分数
        if "validation_score" in result:
            score = result["validation_score"]
            logger.info(f"📊 验证分数: {score}")
    else:
        logger.error(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    return result


async def example_3_api_integration():
    """示例3：生成API集成工作流"""
    logger.info("🔥 示例3：生成API集成工作流")
    
    result = await create_workflow_with_ultimate_generator(
        task_description="调用天气API获取城市天气信息，处理数据格式，保存到数据库并发送通知",
        scenario="api_integration",
        parameters={
            "complexity_level": "simple",
            "include_error_handling": True,
            "priority_focus": "稳定性"
        },
        auto_validate=True,
        auto_optimize=True
    )
    
    if result["success"]:
        workflow = result["workflow"]
        logger.success(f"✅ API集成工作流生成成功！")
        
        # 检查是否包含HTTP节点
        has_http = any(node["type"] == "http" for node in workflow["nodes"])
        logger.info(f"🌐 包含HTTP节点: {'是' if has_http else '否'}")
    else:
        logger.error(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    return result


async def example_4_advanced_usage():
    """示例4：高级用法演示"""
    logger.info("🔥 示例4：高级用法演示")
    
    # 创建生成器实例
    generator = UltimateWorkflowGeneratorAgent()
    
    # 查看支持的场景
    scenarios = generator.get_supported_scenarios()
    logger.info(f"🎯 支持的场景数量: {len(scenarios)}")
    
    # 查看可用模型
    models = generator.get_available_models()
    logger.info(f"🤖 可用模型数量: {len(models)}")
    
    # 生成复杂业务流程
    result = await generator.generate_workflow(
        task_description="电商订单处理：验证库存、计算价格、处理支付、扣减库存、创建订单、发送确认邮件，支持事务回滚",
        scenario="business_process",
        context={
            "business_domain": "电商平台",
            "transaction_requirements": "ACID事务支持",
            "notification_channels": "邮件和短信"
        },
        parameters={
            "complexity_level": "high",
            "include_error_handling": True,
            "priority_focus": "数据一致性"
        },
        auto_validate=True,
        auto_optimize=True
    )
    
    if result["success"]:
        workflow = result["workflow"]
        logger.success(f"✅ 复杂业务流程生成成功！")
        
        # 检查是否包含事务节点
        has_transaction = any(node["type"] == "transaction" for node in workflow["nodes"])
        logger.info(f"⚡ 包含事务节点: {'是' if has_transaction else '否'}")
        
        # 显示优化信息
        if result.get("optimized", False):
            logger.info("🔧 工作流已自动优化")
    else:
        logger.error(f"❌ 生成失败: {result.get('error', '未知错误')}")
    
    return result


async def example_5_validation_demo():
    """示例5：验证功能演示"""
    logger.info("🔥 示例5：验证功能演示")
    
    # 创建一个测试工作流
    test_workflow = {
        "nodes": [
            {
                "name": "WorkflowStart",
                "type": "workflowStart",
                "desc": "开始节点",
                "inputs": {
                    "userInput": {
                        "type": "string",
                        "value": "test input",
                        "desc": "用户输入"
                    }
                },
                "outputs": {},
                "configs": {},
                "nextNodes": ["ProcessData"]
            },
            {
                "name": "ProcessData",
                "type": "code",
                "desc": "处理数据",
                "inputs": {
                    "data": {
                        "type": "string",
                        "value": "$prevNode.outputs.userInput",
                        "desc": "要处理的数据"
                    }
                },
                "outputs": {
                    "result": {
                        "type": "string",
                        "value": "$currentNodeResult",
                        "desc": "处理结果"
                    }
                },
                "configs": {
                    "file": {
                        "name": "process.ts",
                        "content": "function main(inputs) { return inputs.data.toUpperCase(); }"
                    },
                    "timeout": 30
                },
                "nextNodes": ["WorkflowEnd"]
            },
            {
                "name": "WorkflowEnd",
                "type": "workflowEnd",
                "desc": "结束节点",
                "inputs": {
                    "finalResult": {
                        "type": "string",
                        "value": "$prevNode.outputs.result",
                        "desc": "最终结果"
                    }
                },
                "outputs": {},
                "configs": {},
                "nextNodes": ["end"]
            }
        ]
    }
    
    # 验证工作流
    is_valid, errors, warnings = validate_workflow_dict(test_workflow)
    
    logger.info(f"🔍 验证结果: {'通过' if is_valid else '失败'}")
    logger.info(f"❌ 错误数量: {len(errors)}")
    logger.info(f"⚠️ 警告数量: {len(warnings)}")
    
    if errors:
        logger.error("错误列表:")
        for error in errors:
            logger.error(f"  - {error}")
    
    if warnings:
        logger.warning("警告列表:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    return {"is_valid": is_valid, "errors": errors, "warnings": warnings}


def save_example_result(result: dict, filename: str):
    """保存示例结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(os.path.dirname(__file__), f"{filename}_{timestamp}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 结果已保存到: {filepath}")
    return filepath


async def main():
    """主函数：运行所有示例"""
    logger.info("🚀 增强版工作流生成器快速开始示例")
    logger.info("=" * 60)
    
    examples = [
        ("简单用户注册工作流", example_1_simple_workflow),
        # ("数据处理工作流", example_2_data_processing),
        # ("API集成工作流", example_3_api_integration),
        # ("高级用法演示", example_4_advanced_usage),
        # ("验证功能演示", example_5_validation_demo)
    ]
    
    results = {}
    
    for name, example_func in examples:
        logger.info(f"\n{'='*20} {name} {'='*20}")
        
        try:
            result = await example_func()
            results[name] = result
            logger.success(f"✅ {name} 完成")
        except Exception as e:
            logger.error(f"❌ {name} 执行失败: {str(e)}")
            results[name] = {"success": False, "error": str(e)}
        
        logger.info("-" * 60)
    
    # 生成总结
    logger.info("\n📊 执行总结:")
    successful = sum(1 for result in results.values() if result.get("success", False))
    total = len(examples)
    logger.info(f"成功: {successful}/{total}")
    
    if successful > 0:
        logger.success("🎉 系统运行正常！")
    else:
        logger.error("❌ 系统可能存在问题，请检查配置")
    
    # 保存所有结果
    save_example_result(results, "quick_start_results")
    
    return results


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # 运行示例
    asyncio.run(main()) 