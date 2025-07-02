"""
终极版工作流生成器测试脚本

用于测试基于新节点规范的工作流生成功能
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# 添加当前目录到路径，确保可以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from agents.ultimate_workflow_generator import UltimateWorkflowGeneratorAgent, create_workflow_with_ultimate_generator
from utils.workflow_validator import validate_workflow_dict
from prompts.enhanced_workflow_prompts import EnhancedWorkflowPromptTemplates
from loguru import logger


class WorkflowGeneratorTester:
    """工作流生成器测试器"""
    
    def __init__(self):
        self.test_scenarios = self._get_test_scenarios()
        self.results = []
        
    def _get_test_scenarios(self) -> List[Dict[str, Any]]:
        """获取测试场景"""
        return [
            {
                "name": "用户注册工作流",
                "description": "创建一个用户注册工作流，包括邮箱验证、信息保存到数据库、发送欢迎邮件",
                "scenario": "user_management",
                "expected_nodes": ["workflowStart", "condition", "dbCreate", "http", "workflowEnd"],
                "complexity": "medium"
            },
            {
                "name": "数据分析工作流",
                "description": "从数据库查询用户数据，使用AI分析用户行为模式，生成报告",
                "scenario": "data_processing", 
                "expected_nodes": ["workflowStart", "dbQuery", "code", "llm", "workflowEnd"],
                "complexity": "medium"
            },
            {
                "name": "API集成工作流",
                "description": "调用第三方API获取天气信息，处理数据后保存到数据库",
                "scenario": "api_integration",
                "expected_nodes": ["workflowStart", "http", "code", "dbCreate", "workflowEnd"],
                "complexity": "simple"
            },
            {
                "name": "AI对话工作流",
                "description": "接收用户输入，使用AI生成回复，记录对话历史到数据库",
                "scenario": "ai_workflow",
                "expected_nodes": ["workflowStart", "llm", "dbCreate", "workflowEnd"],
                "complexity": "simple"
            },
            {
                "name": "复杂业务流程",
                "description": "订单处理流程：验证库存、计算价格、扣减库存、创建订单、发送通知，支持事务回滚",
                "scenario": "business_process",
                "expected_nodes": ["workflowStart", "dbQuery", "condition", "transaction", "http", "workflowEnd"],
                "complexity": "high"
            }
        ]
    
    async def run_all_tests(self, model_key: str = None) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("🧪 开始运行工作流生成器测试")
        
        test_results = {
            "start_time": datetime.now().isoformat(),
            "total_tests": len(self.test_scenarios),
            "passed": 0,
            "failed": 0,
            "test_details": [],
            "summary": {}
        }
        
        for i, scenario in enumerate(self.test_scenarios):
            logger.info(f"📋 测试场景 {i+1}/{len(self.test_scenarios)}: {scenario['name']}")
            
            result = await self._test_single_scenario(scenario, model_key)
            test_results["test_details"].append(result)
            
            if result["success"]:
                test_results["passed"] += 1
                logger.success(f"✅ 测试通过: {scenario['name']}")
            else:
                test_results["failed"] += 1
                logger.error(f"❌ 测试失败: {scenario['name']} - {result.get('error', '未知错误')}")
        
        test_results["end_time"] = datetime.now().isoformat()
        test_results["success_rate"] = test_results["passed"] / test_results["total_tests"] * 100
        
        # 生成摘要
        test_results["summary"] = self._generate_test_summary(test_results)
        
        logger.info(f"🎯 测试完成: {test_results['passed']}/{test_results['total_tests']} 通过 ({test_results['success_rate']:.1f}%)")
        
        return test_results
    
    async def _test_single_scenario(self, scenario: Dict[str, Any], model_key: str = None) -> Dict[str, Any]:
        """测试单个场景"""
        test_result = {
            "scenario_name": scenario["name"],
            "scenario_info": scenario,
            "success": False,
            "error": None,
            "workflow": None,
            "validation": None,
            "performance": {},
            "model_info": None
        }
        
        try:
            start_time = datetime.now()
            
            # 生成工作流
            generation_result = await create_workflow_with_ultimate_generator(
                task_description=scenario["description"],
                scenario=scenario["scenario"],
                model_key=model_key,
                parameters={
                    "complexity_level": scenario["complexity"],
                    "include_error_handling": True,
                    "priority_focus": "功能完整性"
                },
                auto_validate=True,
                auto_optimize=True
            )
            
            end_time = datetime.now()
            test_result["performance"]["generation_time"] = (end_time - start_time).total_seconds()
            
            if not generation_result.get("success", False):
                test_result["error"] = generation_result.get("error", "生成失败")
                return test_result
            
            workflow = generation_result["workflow"]
            test_result["workflow"] = workflow
            test_result["model_info"] = generation_result.get("model_info", {})
            test_result["validation"] = generation_result.get("validation", {})
            
            # 验证工作流
            validation_success = self._validate_generated_workflow(workflow, scenario)
            
            if validation_success:
                test_result["success"] = True
            else:
                test_result["error"] = "工作流验证失败"
            
            # 性能指标
            test_result["performance"]["node_count"] = len(workflow.get("nodes", []))
            test_result["performance"]["validation_score"] = generation_result.get("validation_score", 0)
            
        except Exception as e:
            test_result["error"] = str(e)
            logger.exception(f"测试场景异常: {scenario['name']}")
        
        return test_result
    
    def _validate_generated_workflow(self, workflow: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """验证生成的工作流"""
        try:
            # 基础验证
            is_valid, errors, warnings = validate_workflow_dict(workflow)
            
            if not is_valid:
                logger.error(f"工作流验证失败: {errors}")
                return False
            
            # 检查是否包含预期的节点类型
            nodes = workflow.get("nodes", [])
            node_types = [node.get("type") for node in nodes]
            expected_nodes = scenario.get("expected_nodes", [])
            
            missing_nodes = []
            for expected_type in expected_nodes:
                if expected_type not in node_types:
                    missing_nodes.append(expected_type)
            
            if missing_nodes:
                logger.warning(f"缺少预期的节点类型: {missing_nodes}")
                # 不强制要求完全匹配，只记录警告
            
            # 检查节点数量是否合理
            if len(nodes) < 3:  # 至少要有开始、处理、结束节点
                logger.error(f"节点数量过少: {len(nodes)}")
                return False
            
            # 检查是否有开始和结束节点
            has_start = any(node.get("type") == "workflowStart" for node in nodes)
            has_end = any(node.get("type") == "workflowEnd" for node in nodes)
            
            if not has_start or not has_end:
                logger.error(f"缺少开始或结束节点: start={has_start}, end={has_end}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证过程异常: {str(e)}")
            return False
    
    def _generate_test_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试摘要"""
        summary = {
            "overall_success": results["success_rate"] >= 80,  # 80%以上成功率认为通过
            "performance_stats": {
                "avg_generation_time": 0,
                "avg_node_count": 0,
                "avg_validation_score": 0
            },
            "common_issues": [],
            "recommendations": []
        }
        
        # 计算性能统计
        valid_tests = [test for test in results["test_details"] if test["success"]]
        
        if valid_tests:
            times = [test["performance"].get("generation_time", 0) for test in valid_tests]
            node_counts = [test["performance"].get("node_count", 0) for test in valid_tests]
            scores = [test["performance"].get("validation_score", 0) for test in valid_tests]
            
            summary["performance_stats"]["avg_generation_time"] = sum(times) / len(times)
            summary["performance_stats"]["avg_node_count"] = sum(node_counts) / len(node_counts)
            summary["performance_stats"]["avg_validation_score"] = sum(scores) / len(scores)
        
        # 分析常见问题
        failed_tests = [test for test in results["test_details"] if not test["success"]]
        error_types = {}
        
        for test in failed_tests:
            error = test.get("error", "未知错误")
            error_types[error] = error_types.get(error, 0) + 1
        
        summary["common_issues"] = list(error_types.keys())
        
        # 生成建议
        if results["success_rate"] < 80:
            summary["recommendations"].append("需要优化提示词模板或节点规范")
        
        if summary["performance_stats"]["avg_generation_time"] > 30:
            summary["recommendations"].append("考虑优化生成速度或使用更快的模型")
        
        if summary["performance_stats"]["avg_validation_score"] < 90:
            summary["recommendations"].append("需要改进工作流质量和验证规则")
        
        return summary
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """保存测试结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workflow_test_results_{timestamp}.json"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 测试结果已保存到: {filepath}")
        return filepath


async def test_prompt_templates():
    """测试提示词模板"""
    logger.info("🧪 测试提示词模板")
    
    templates = EnhancedWorkflowPromptTemplates()
    
    # 测试系统提示词
    system_prompt = templates.get_system_prompt()
    assert len(system_prompt) > 1000, "系统提示词长度不足"
    logger.success("✅ 系统提示词测试通过")
    
    # 测试用户提示词构建
    user_prompt = templates.build_user_prompt(
        "测试任务描述",
        {"test_context": "测试上下文"},
        {"complexity_level": "medium"}
    )
    assert "测试任务描述" in user_prompt, "用户提示词不包含任务描述"
    logger.success("✅ 用户提示词构建测试通过")
    
    # 测试场景提示词
    scenarios = templates.get_scenario_specific_prompts()
    assert len(scenarios) >= 5, "场景提示词数量不足"
    logger.success("✅ 场景提示词测试通过")


async def test_validator():
    """测试验证器"""
    logger.info("🧪 测试工作流验证器")
    
    # 测试有效的工作流
    valid_workflow = {
        "nodes": [
            {
                "name": "WorkflowStart",
                "type": "workflowStart",
                "desc": "开始节点",
                "inputs": {
                    "userInput": {
                        "type": "string",
                        "value": "test",
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
                        "desc": "数据"
                    }
                },
                "outputs": {
                    "result": {
                        "type": "string",
                        "value": "$currentNodeResult",
                        "desc": "结果"
                    }
                },
                "configs": {
                    "file": {
                        "name": "process.ts",
                        "content": "function main(inputs) { return inputs.data; }"
                    }
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
    
    is_valid, errors, warnings = validate_workflow_dict(valid_workflow)
    assert is_valid, f"有效工作流验证失败: {errors}"
    logger.success("✅ 有效工作流验证测试通过")
    
    # 测试无效的工作流
    invalid_workflow = {
        "nodes": [
            {
                "name": "invalid_node",  # 无效的命名格式
                "type": "invalid_type",  # 无效的节点类型
                "desc": "无效节点"
                # 缺少必填字段
            }
        ]
    }
    
    is_valid, errors, warnings = validate_workflow_dict(invalid_workflow)
    assert not is_valid, "无效工作流应该验证失败"
    assert len(errors) > 0, "应该有错误信息"
    logger.success("✅ 无效工作流验证测试通过")


async def main():
    """主测试函数"""
    logger.info("🚀 开始终极版工作流生成器测试")
    
    try:
        # 测试基础组件
        await test_prompt_templates()
        await test_validator()
        
        # 测试工作流生成器
        tester = WorkflowGeneratorTester()
        
        # 可以指定特定模型进行测试
        # model_key = "openai_gpt-4"  # 或其他可用模型
        model_key = None  # 使用默认模型选择
        
        results = await tester.run_all_tests(model_key)
        
        # 保存结果
        result_file = tester.save_results(results)
        
        # 打印摘要
        logger.info("📊 测试摘要:")
        logger.info(f"   总测试数: {results['total_tests']}")
        logger.info(f"   通过数: {results['passed']}")
        logger.info(f"   失败数: {results['failed']}")
        logger.info(f"   成功率: {results['success_rate']:.1f}%")
        
        summary = results["summary"]
        logger.info(f"   平均生成时间: {summary['performance_stats']['avg_generation_time']:.2f}秒")
        logger.info(f"   平均节点数: {summary['performance_stats']['avg_node_count']:.1f}")
        logger.info(f"   平均验证分数: {summary['performance_stats']['avg_validation_score']:.1f}")
        
        if summary["common_issues"]:
            logger.warning(f"   常见问题: {', '.join(summary['common_issues'])}")
        
        if summary["recommendations"]:
            logger.info("💡 改进建议:")
            for rec in summary["recommendations"]:
                logger.info(f"   - {rec}")
        
        # 判断整体测试结果
        if summary["overall_success"]:
            logger.success("🎉 终极版工作流生成器测试整体通过！")
        else:
            logger.error("❌ 终极版工作流生成器测试需要改进")
            
        return results
        
    except Exception as e:
        logger.exception("❌ 测试过程中发生异常")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 运行测试
    results = asyncio.run(main())
    
    # 退出码
    exit_code = 0 if results.get("summary", {}).get("overall_success", False) else 1
    sys.exit(exit_code) 