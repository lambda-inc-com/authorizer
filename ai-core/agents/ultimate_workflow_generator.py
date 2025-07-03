"""
终极版工作流生成智能体

集成最新的节点规范、提示词模板和验证器，提供最专业的工作流生成服务
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from base_agent import BaseAgent, AgentConfig, AgentCapability
from services.unified_llm_client import UnifiedLLMClient, ModelSelector
from prompts.enhanced_workflow_prompts import EnhancedWorkflowPromptTemplates
from utils.workflow_validator import WorkflowValidator, validate_workflow_dict
from loguru import logger


class UltimateWorkflowGeneratorAgent(BaseAgent):
    """终极版工作流生成智能体"""
    
    def __init__(self, preferred_model: str = None, **kwargs):
        """
        初始化智能体
        
        Args:
            preferred_model: 首选模型key
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.llm_client = UnifiedLLMClient()
        self.model_selector = ModelSelector()
        self.preferred_model = preferred_model
        self.prompt_templates = EnhancedWorkflowPromptTemplates()
        self.validator = WorkflowValidator()
        
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            name="终极版工作流生成器",
            description="基于最新节点规范的专业工作流生成器，支持完整的验证和优化",
            capabilities=[
                AgentCapability.TEXT_GENERATION,
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.CODE_GENERATION
            ],
            model_preferences={
                "task_type": "workflow_generation",
                "prefer_speed": False,
                "quality_focus": True
            },
            max_iterations=5,
            timeout=300
        )
    
    async def _execute_core_logic(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行核心逻辑 - 基类抽象方法的实现"""
        return await self.generate_workflow(
            task_description=task_description,
            context=context,
            parameters=parameters
        )
    
    async def generate_workflow(
        self,
        task_description: str,
        scenario: str = None,
        context: Dict[str, Any] = None,
        parameters: Dict[str, Any] = None,
        auto_validate: bool = True,
        auto_optimize: bool = True
    ) -> Dict[str, Any]:
        """
        生成工作流
        
        Args:
            task_description: 任务描述
            scenario: 场景类型 (user_management, data_processing, api_integration, ai_workflow, business_process)
            context: 上下文信息
            parameters: 生成参数
            auto_validate: 是否自动验证
            auto_optimize: 是否自动优化
            
        Returns:
            生成结果
        """
        logger.info(f"🚀 开始生成工作流: {task_description}")
        
        # 设置默认参数
        if parameters is None:
            parameters = {}
            
        if context is None:
            context = {}
            
        # 添加场景特定提示词
        if scenario:
            scenario_prompts = self.prompt_templates.get_scenario_specific_prompts()
            if scenario in scenario_prompts:
                context["scenario_guidance"] = scenario_prompts[scenario]
        
        # 多次尝试生成，直到通过验证
        max_attempts = 3
        best_result = None
        best_validation_score = -1
        
        for attempt in range(max_attempts):
            logger.info(f"🔄 尝试第 {attempt + 1} 次生成")
            
            try:
                # 生成工作流
                generation_result = await self._generate_single_workflow(
                    task_description, context, parameters
                )
                
                if not generation_result["success"]:
                    logger.warning(f"⚠️ 第 {attempt + 1} 次生成失败: {generation_result.get('error')}")
                    continue
                
                workflow = generation_result["workflow"]
                
                # 验证工作流
                if auto_validate:
                    validation_result = self._validate_workflow(workflow)
                    generation_result["validation"] = validation_result
                    
                    # 计算验证分数
                    validation_score = self._calculate_validation_score(validation_result)
                    generation_result["validation_score"] = validation_score
                    
                    logger.info(f"📊 验证分数: {validation_score}")
                    
                    # 如果验证通过，直接返回
                    if validation_result["is_valid"]:
                        logger.success(f"✅ 工作流生成成功并通过验证")
                        
                        # 优化工作流
                        if auto_optimize:
                            optimized_workflow = await self._optimize_workflow(workflow, validation_result)
                            generation_result["workflow"] = optimized_workflow
                            generation_result["optimized"] = True
                            
                        return generation_result
                    
                    # 记录最佳结果
                    if validation_score > best_validation_score:
                        best_validation_score = validation_score
                        best_result = generation_result
                        
                else:
                    # 不验证直接返回
                    return generation_result
                    
            except Exception as e:
                logger.error(f"❌ 第 {attempt + 1} 次生成异常: {str(e)}")
                continue
        
        # 如果所有尝试都失败了，返回最佳结果或错误
        if best_result:
            logger.warning(f"⚠️ 返回最佳结果 (验证分数: {best_validation_score})")
            return best_result
        else:
            logger.error("❌ 所有生成尝试都失败了")
            return {
                "success": False,
                "error": "所有生成尝试都失败了",
                "workflow": None,
                "attempts": max_attempts
            }
    
    async def _generate_single_workflow(
        self,
        task_description: str,
        context: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成单个工作流"""
        try:
            # 选择最佳模型
            model_key = await self._select_optimal_model(parameters)
            logger.info(f"🎯 选择模型: {model_key}")
            
            # 构建提示词
            system_prompt = self.prompt_templates.get_system_prompt()
            user_prompt = self.prompt_templates.build_user_prompt(
                task_description, context, parameters
            )
            
            # 记录提示词长度
            logger.debug(f"📝 系统提示词长度: {len(system_prompt)} 字符")
            logger.debug(f"📝 用户提示词长度: {len(user_prompt)} 字符")
            
            # 调用LLM生成工作流
            async with self.llm_client as client:
                response = await client.chat(
                    model_key=model_key,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=12000  # 增加token限制以支持复杂工作流
                )
            
            # 解析工作流
            workflow = await self._parse_workflow_response(response["content"])
            
            return {
                "success": True,
                "workflow": workflow,
                "model_info": {
                    "key": model_key,
                    "provider": response.get("provider"),
                    "model_name": response.get("model"),
                    "usage": response.get("usage", {})
                },
                "generated_at": datetime.now().isoformat(),
                "agent_version": "3.0.0"
            }
            
        except Exception as e:
            logger.error(f"❌ 工作流生成异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow": None
            }
    
    async def _parse_workflow_response(self, response_content: str) -> Dict[str, Any]:
        """解析工作流响应"""
        try:
            # 清理响应内容
            content = response_content.strip()
            
            # 移除可能的markdown格式
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 3:
                    content = parts[1]
            
            # 解析JSON
            workflow = json.loads(content)
            
            # 确保基本结构
            if "nodes" not in workflow:
                raise ValueError("工作流缺少 nodes 字段")
                
            return workflow
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析错误: {str(e)}")
            logger.debug(f"原始内容: {response_content[:500]}...")
            raise ValueError(f"无法解析JSON格式的工作流: {str(e)}")
        except Exception as e:
            logger.error(f"❌ 工作流解析异常: {str(e)}")
            raise
    
    def _validate_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流"""
        try:
            is_valid, errors, warnings = validate_workflow_dict(workflow)
            
            return {
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "summary": self.validator.get_validation_summary() if hasattr(self.validator, 'get_validation_summary') else ""
            }
            
        except Exception as e:
            logger.error(f"❌ 验证异常: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"验证异常: {str(e)}"],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
                "summary": f"验证过程中发生异常: {str(e)}"
            }
    
    def _calculate_validation_score(self, validation_result: Dict[str, Any]) -> float:
        """计算验证分数"""
        if validation_result["is_valid"]:
            # 基础分数100，每个警告扣5分
            return max(0, 100 - validation_result["warning_count"] * 5)
        else:
            # 有错误的情况下，最高50分，每个错误扣10分，每个警告扣2分
            return max(0, 50 - validation_result["error_count"] * 10 - validation_result["warning_count"] * 2)
    
    async def _optimize_workflow(
        self, 
        workflow: Dict[str, Any], 
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """优化工作流"""
        logger.info("🔧 开始优化工作流")
        
        optimized_workflow = workflow.copy()
        
        # 基本优化
        optimized_workflow = self._optimize_node_order(optimized_workflow)
        optimized_workflow = self._optimize_error_handling(optimized_workflow)
        optimized_workflow = self._optimize_performance(optimized_workflow)
        
        logger.success("✅ 工作流优化完成")
        return optimized_workflow
    
    def _optimize_node_order(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """优化节点顺序"""
        # 简单的节点顺序优化：确保开始节点在前，结束节点在后
        nodes = workflow.get("nodes", [])
        
        start_nodes = [node for node in nodes if node.get("type") == "workflowStart"]
        end_nodes = [node for node in nodes if node.get("type") == "workflowEnd"]
        other_nodes = [node for node in nodes if node.get("type") not in ["workflowStart", "workflowEnd"]]
        
        # 重新排序
        workflow["nodes"] = start_nodes + other_nodes + end_nodes
        
        return workflow
    
    def _optimize_error_handling(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """优化错误处理"""
        # 为关键节点添加超时设置
        for node in workflow.get("nodes", []):
            configs = node.get("configs", {})
            node_type = node.get("type")
            
            # 为数据库和HTTP节点添加超时
            if node_type in ["dbQuery", "dbCreate", "dbUpdate", "dbDelete", "http"]:
                if "timeout" not in configs:
                    configs["timeout"] = 30
                    
            # 为LLM节点添加合理的token限制
            if node_type == "llm":
                if "maxTokens" not in configs:
                    configs["maxTokens"] = 2000
                    
        return workflow
    
    def _optimize_performance(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """优化性能"""
        # 为数据库查询节点添加限制
        for node in workflow.get("nodes", []):
            if node.get("type") == "dbQuery":
                configs = node.get("configs", {})
                if "limit" not in configs:
                    configs["limit"] = 100  # 默认限制100条记录
                    
        return workflow
    
    async def _select_optimal_model(self, parameters: Dict[str, Any]) -> str:
        """选择最优模型"""
        # 1. 使用首选模型
        if self.preferred_model:
            available_models = [model["key"] for model in self.llm_client.get_enabled_models()]
            if self.preferred_model in available_models:
                return self.preferred_model
        
        # 2. 使用参数指定的模型
        if "preferred_model" in parameters:
            model_key = parameters["preferred_model"]
            available_models = [model["key"] for model in self.llm_client.get_enabled_models()]
            if model_key in available_models:
                return model_key
        
        # 3. 根据复杂度选择
        complexity_level = parameters.get("complexity_level", "medium")
        
        if complexity_level == "simple":
            return self.model_selector.select_best_model("workflow_generation", prefer_speed=True)
        else:
            return self.model_selector.select_best_model("workflow_generation", prefer_speed=False)
    
    def get_supported_scenarios(self) -> List[Dict[str, str]]:
        """获取支持的场景"""
        scenario_prompts = self.prompt_templates.get_scenario_specific_prompts()
        return [
            {
                "key": key,
                "name": {
                    "user_management": "用户管理",
                    "data_processing": "数据处理", 
                    "api_integration": "API集成",
                    "ai_workflow": "AI工作流",
                    "business_process": "业务流程"
                }.get(key, key),
                "description": prompt.strip()
            }
            for key, prompt in scenario_prompts.items()
        ]
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型"""
        return self.llm_client.get_enabled_models()
    
    def get_validation_rules(self) -> Dict[str, str]:
        """获取验证规则"""
        return self.prompt_templates.get_validation_rules()
    
    def get_optimization_suggestions(self) -> List[str]:
        """获取优化建议"""
        return self.prompt_templates.get_optimization_suggestions()


async def create_workflow_with_ultimate_generator(
    task_description: str,
    scenario: str = None,
    model_key: str = None,
    context: Dict[str, Any] = None,
    parameters: Dict[str, Any] = None,
    auto_validate: bool = True,
    auto_optimize: bool = True
) -> Dict[str, Any]:
    """
    使用终极版生成器创建工作流
    
    Args:
        task_description: 任务描述
        scenario: 场景类型
        model_key: 指定模型
        context: 上下文信息
        parameters: 生成参数
        auto_validate: 是否自动验证
        auto_optimize: 是否自动优化
        
    Returns:
        生成结果
    """
    generator = UltimateWorkflowGeneratorAgent(preferred_model=model_key)
    
    return await generator.generate_workflow(
        task_description=task_description,
        scenario=scenario,
        context=context,
        parameters=parameters,
        auto_validate=auto_validate,
        auto_optimize=auto_optimize
    )


async def batch_generate_workflows(
    tasks: List[Dict[str, Any]],
    model_key: str = None,
    auto_validate: bool = True,
    auto_optimize: bool = True
) -> List[Dict[str, Any]]:
    """
    批量生成工作流
    
    Args:
        tasks: 任务列表，每个任务包含 task_description, scenario, context, parameters
        model_key: 指定模型
        auto_validate: 是否自动验证
        auto_optimize: 是否自动优化
        
    Returns:
        生成结果列表
    """
    generator = UltimateWorkflowGeneratorAgent(preferred_model=model_key)
    results = []
    
    for i, task in enumerate(tasks):
        logger.info(f"📋 处理任务 {i+1}/{len(tasks)}: {task.get('task_description', '未知任务')}")
        
        try:
            result = await generator.generate_workflow(
                task_description=task.get("task_description", ""),
                scenario=task.get("scenario"),
                context=task.get("context"),
                parameters=task.get("parameters"),
                auto_validate=auto_validate,
                auto_optimize=auto_optimize
            )
            
            result["task_index"] = i
            result["task_info"] = task
            results.append(result)
            
        except Exception as e:
            logger.error(f"❌ 任务 {i+1} 处理失败: {str(e)}")
            results.append({
                "success": False,
                "error": str(e),
                "task_index": i,
                "task_info": task
            })
    
    return results


if __name__ == "__main__":
    import asyncio
    
    async def demo():
        """演示终极版工作流生成器"""
        print("🚀 终极版工作流生成器演示")
        
        # 示例任务
        task = "创建一个用户注册工作流，包括邮箱验证、信息保存到数据库、发送欢迎邮件"
        
        result = await create_workflow_with_ultimate_generator(
            task_description=task,
            scenario="user_management",
            auto_validate=True,
            auto_optimize=True
        )
        
        print(f"生成结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    asyncio.run(demo()) 