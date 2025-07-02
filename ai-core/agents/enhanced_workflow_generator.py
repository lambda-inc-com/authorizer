"""
增强版工作流生成智能体

支持灵活的多模型选择，包括OpenAI、Claude、xAI等
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentConfig, AgentCapability
from ..services.unified_llm_client import UnifiedLLMClient, ModelSelector
from ..prompts.simple_prompts import get_workflow_system_prompt, build_user_prompt
from loguru import logger


class EnhancedWorkflowGeneratorAgent(BaseAgent):
    """增强版工作流生成智能体"""
    
    def __init__(self, preferred_model: str = None, **kwargs):
        """
        初始化智能体
        
        Args:
            preferred_model: 首选模型key (如: openai_gpt-4, xai_grok-3-latest)
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.llm_client = UnifiedLLMClient()
        self.model_selector = ModelSelector()
        self.preferred_model = preferred_model
        
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            name="增强版工作流生成器",
            description="支持多模型的工作流节点定义生成器，可灵活选择OpenAI、Claude、xAI等模型",
            capabilities=[
                AgentCapability.TEXT_GENERATION,
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.CODE_GENERATION
            ],
            model_preferences={
                "task_type": "workflow_generation",
                "prefer_speed": False
            },
            max_iterations=3,
            timeout=180
        )
    
    async def execute_with_model(
        self,
        model_key: str,
        task_description: str,
        context: Dict[str, Any] = None,
        parameters: Dict[str, Any] = None
    ):
        """
        使用指定模型执行工作流生成
        
        Args:
            model_key: 模型配置key (如: openai_gpt-4)
            task_description: 任务描述
            context: 上下文信息
            parameters: 执行参数
            
        Returns:
            执行结果
        """
        # 临时设置首选模型
        original_preferred = self.preferred_model
        self.preferred_model = model_key
        
        try:
            result = await self.execute(task_description, context, parameters)
            return result
        finally:
            # 恢复原始设置
            self.preferred_model = original_preferred
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """列出所有可用的模型"""
        return self.llm_client.get_enabled_models()
    
    def get_model_recommendations(self) -> List[str]:
        """获取针对工作流生成的推荐模型"""
        return self.model_selector.get_model_recommendations("workflow_generation")
    
    async def _execute_core_logic(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行核心逻辑
        
        Args:
            task_description: 用户需求描述
            context: 上下文信息
            parameters: 执行参数
            
        Returns:
            包含工作流节点定义的结果
        """
        logger.info(f"🔧 开始生成工作流: {task_description}")
        
        # 选择最佳模型
        model_key = await self._select_optimal_model(parameters)
        logger.info(f"🎯 选择模型: {model_key}")
        
        # 构建提示词
        system_prompt = get_workflow_system_prompt()
        user_prompt = build_user_prompt(task_description, context, parameters)
        
        # 调用LLM生成工作流
        async with self.llm_client as client:
            response = await client.chat(
                model_key=model_key,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=8000
            )
        
        # 解析和验证生成的工作流
        workflow_definition = await self._parse_and_validate_workflow(response["content"])
        
        # 优化工作流
        optimized_workflow = await self._optimize_workflow(workflow_definition)
        
        return {
            "workflow": optimized_workflow,
            "node_count": len(optimized_workflow.get("nodes", [])),
            "edge_count": len(optimized_workflow.get("edges", [])),
            "description": task_description,
            "generated_at": datetime.now().isoformat(),
            "agent_version": "2.0.0",
            "model_used": {
                "key": model_key,
                "provider": response.get("provider"),
                "model_name": response.get("model"),
                "usage": response.get("usage", {})
            }
        }
    
    async def _select_optimal_model(self, parameters: Dict[str, Any]) -> str:
        """
        选择最优模型
        
        Args:
            parameters: 执行参数
            
        Returns:
            选择的模型key
        """
        # 1. 如果指定了首选模型，直接使用
        if self.preferred_model:
            available_models = [model["key"] for model in self.llm_client.get_enabled_models()]
            if self.preferred_model in available_models:
                logger.info(f"✅ 使用首选模型: {self.preferred_model}")
                return self.preferred_model
            else:
                logger.warning(f"⚠️ 首选模型不可用: {self.preferred_model}")
        
        # 2. 如果参数中指定了模型
        if "preferred_model" in parameters:
            model_key = parameters["preferred_model"]
            available_models = [model["key"] for model in self.llm_client.get_enabled_models()]
            if model_key in available_models:
                logger.info(f"✅ 使用参数指定模型: {model_key}")
                return model_key
        
        # 3. 根据任务复杂度和偏好选择
        complexity_level = parameters.get("complexity_level", "medium")
        prefer_speed = parameters.get("prefer_speed", False)
        
        if complexity_level == "simple" or prefer_speed:
            # 简单任务或优先速度：选择较快的模型
            return self.model_selector.select_best_model("workflow_generation", prefer_speed=True)
        else:
            # 复杂任务：选择质量最佳的模型
            return self.model_selector.select_best_model("workflow_generation", prefer_speed=False)
    
    async def _parse_and_validate_workflow(self, workflow_json: str) -> Dict[str, Any]:
        """解析和验证工作流定义"""
        try:
            # 清理可能的markdown格式
            if "```json" in workflow_json:
                workflow_json = workflow_json.split("```json")[1].split("```")[0]
            elif "```" in workflow_json:
                workflow_json = workflow_json.split("```")[1].split("```")[0]
            
            workflow = json.loads(workflow_json)
            
            # 验证基本结构
            if "nodes" not in workflow or "edges" not in workflow:
                raise ValueError("工作流必须包含nodes和edges字段")
            
            # 验证节点
            node_ids = set()
            for node in workflow["nodes"]:
                if "id" not in node or "type" not in node:
                    raise ValueError("每个节点必须包含id和type字段")
                
                if node["id"] in node_ids:
                    raise ValueError(f"节点ID重复: {node['id']}")
                node_ids.add(node["id"])
            
            # 验证边连接
            for edge in workflow["edges"]:
                if "source" not in edge or "target" not in edge:
                    raise ValueError("每条边必须包含source和target字段")
                
                if edge["source"] not in node_ids or edge["target"] not in node_ids:
                    raise ValueError(f"边引用了不存在的节点: {edge}")
            
            logger.info("✅ 工作流验证通过")
            return workflow
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValueError(f"生成的工作流JSON格式错误: {e}")
        except Exception as e:
            logger.error(f"工作流验证失败: {e}")
            raise ValueError(f"工作流验证失败: {e}")
    
    async def _optimize_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """优化工作流"""
        logger.info("🔧 优化工作流布局和连接...")
        
        nodes = workflow["nodes"]
        edges = workflow["edges"]
        
        # 优化节点位置 - 自动布局
        self._optimize_node_positions(nodes, edges)
        
        # 添加缺失的边ID
        for edge in edges:
            if "id" not in edge:
                edge["id"] = f"xy-edge__{edge['source']}-{edge['target']}"
        
        # 确保开始和结束节点存在
        has_start = any(node["type"] == "workflowStart" for node in nodes)
        has_end = any(node["type"] == "workflowEnd" for node in nodes)
        
        if not has_start:
            logger.warning("⚠️ 工作流缺少开始节点")
        if not has_end:
            logger.warning("⚠️ 工作流缺少结束节点")
        
        logger.success("✅ 工作流优化完成")
        return workflow
    
    def _optimize_node_positions(self, nodes: List[Dict], edges: List[Dict]):
        """优化节点位置布局"""
        # 构建节点层级关系
        node_levels = {}
        start_nodes = [node for node in nodes if node["type"] == "workflowStart"]
        
        if start_nodes:
            # 从开始节点开始计算层级
            queue = [(start_nodes[0]["id"], 0)]
            visited = set()
            
            while queue:
                node_id, level = queue.pop(0)
                if node_id in visited:
                    continue
                
                visited.add(node_id)
                node_levels[node_id] = level
                
                # 找到所有连接的下级节点
                for edge in edges:
                    if edge["source"] == node_id and edge["target"] not in visited:
                        queue.append((edge["target"], level + 1))
        
        # 根据层级重新布局
        x_spacing = 350  # 节点水平间距
        y_spacing = 200  # 节点垂直间距
        
        level_counts = {}
        for node in nodes:
            node_id = node["id"]
            level = node_levels.get(node_id, 0)
            
            if level not in level_counts:
                level_counts[level] = 0
            
            # 设置位置
            node["position"] = {
                "x": level * x_spacing + 50,
                "y": level_counts[level] * y_spacing + 100
            }
            
            level_counts[level] += 1
    
    async def _additional_pre_checks(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ):
        """额外的前置检查"""
        if not task_description or len(task_description.strip()) < 10:
            raise ValueError("任务描述太短，请提供更详细的需求描述")
        
        # 检查是否有可用的模型
        available_models = self.llm_client.get_enabled_models()
        if not available_models:
            raise ValueError("没有可用的启用模型，请检查配置和API密钥")
        
        # 检查是否是工作流相关需求
        workflow_keywords = [
            "工作流", "流程", "自动化", "步骤", "节点", 
            "workflow", "process", "automation", "flow"
        ]
        
        if not any(keyword in task_description.lower() for keyword in workflow_keywords):
            logger.warning("⚠️ 任务描述可能不是工作流相关需求")


# 便捷的工厂函数
async def create_workflow_with_model(
    model_key: str,
    task_description: str,
    context: Dict[str, Any] = None,
    parameters: Dict[str, Any] = None
):
    """
    使用指定模型创建工作流的便捷函数
    
    Args:
        model_key: 模型配置key
        task_description: 任务描述
        context: 上下文信息
        parameters: 执行参数
        
    Returns:
        执行结果
    """
    agent = EnhancedWorkflowGeneratorAgent(preferred_model=model_key)
    return await agent.execute(task_description, context, parameters)


# 模型选择助手函数
def list_workflow_models():
    """列出适合工作流生成的模型"""
    selector = ModelSelector()
    client = UnifiedLLMClient()
    
    available_models = client.get_enabled_models()
    recommendations = selector.get_model_recommendations("workflow_generation")
    
    print("📋 可用模型列表:")
    for model in available_models:
        is_recommended = "⭐" if model["key"] in recommendations else "  "
        status = "✅" if model["has_api_key"] else "❌"
        print(f"{is_recommended} {status} {model['key']}: {model['provider']} - {model['model_name']}")
    
    print(f"\n🎯 推荐用于工作流生成的模型:")
    for model_key in recommendations:
        print(f"  - {model_key}")
    
    return available_models, recommendations


# 使用示例
async def demo_enhanced_workflow_generator():
    """增强版工作流生成器演示"""
    
    print("🚀 增强版工作流生成智能体演示")
    print("=" * 50)
    
    # 列出可用模型
    available_models, recommendations = list_workflow_models()
    
    if not available_models:
        print("❌ 没有可用的模型，请检查配置和API密钥")
        return
    
    # 创建智能体
    agent = EnhancedWorkflowGeneratorAgent()
    
    # 测试案例
    test_cases = [
        {
            "name": "智能客服",
            "description": "创建智能客服工作流，支持问题分类和多模型回答",
            "context": {"domain": "客户服务"},
            "model": recommendations[0] if recommendations else available_models[0]["key"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 测试案例: {test_case['name']}")
        print(f"使用模型: {test_case['model']}")
        
        try:
            result = await agent.execute_with_model(
                model_key=test_case["model"],
                task_description=test_case["description"],
                context=test_case["context"],
                parameters={"complexity_level": "medium"}
            )
            
            if result.success:
                print(f"✅ 生成成功!")
                print(f"   节点数: {result.result['node_count']}")
                print(f"   模型: {result.result['model_used']['model_name']}")
                print(f"   提供商: {result.result['model_used']['provider']}")
                
            else:
                print(f"❌ 生成失败: {result.error}")
                
        except Exception as e:
            print(f"❌ 执行异常: {str(e)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_enhanced_workflow_generator()) 