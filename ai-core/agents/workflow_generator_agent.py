"""
工作流生成智能体 - Workflow Generator Agent

专门用于根据用户需求自动生成工作流节点定义的智能体
"""

import json
import uuid
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BaseAgent, AgentConfig, AgentCapability
from loguru import logger


class WorkflowGeneratorAgent(BaseAgent):
    """工作流生成智能体"""
    
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            name="工作流生成器",
            description="根据用户需求自动生成工作流节点定义，支持多种节点类型的智能编排",
            capabilities=[
                AgentCapability.TEXT_GENERATION,
                AgentCapability.WORKFLOW_ORCHESTRATION,
                AgentCapability.CODE_GENERATION
            ],
            model_preferences={
                "primary_model": "gpt-4",
                "fallback_model": "deepseek-chat"
            },
            max_iterations=3,
            timeout=180
        )
    
    async def _execute_core_logic(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行工作流生成逻辑
        
        Args:
            task_description: 用户需求描述
            context: 上下文信息
            parameters: 执行参数
            
        Returns:
            包含工作流节点定义的结果
        """
        logger.info(f"🔧 开始生成工作流: {task_description}")
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        # 构建用户提示词
        user_prompt = self._build_user_prompt(task_description, context, parameters)
        
        # 调用LLM生成工作流
        response = await self._call_model(
            model_name=self.config.model_preferences.get("primary_model", "gpt-4"),
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
            "agent_version": "1.0.0"
        }
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        from ..prompts.simple_prompts import get_workflow_system_prompt
        return get_workflow_system_prompt()

    def _build_user_prompt(self, task_description: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> str:
        """构建用户提示词"""
        from ..prompts.simple_prompts import build_user_prompt
        return build_user_prompt(task_description, context, parameters)
    
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
        for i, edge in enumerate(edges):
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
    
    def _generate_unique_id(self) -> str:
        """生成唯一ID"""
        return str(uuid.uuid4()).replace("-", "")
    
    async def _additional_pre_checks(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ):
        """额外的前置检查"""
        if not task_description or len(task_description.strip()) < 10:
            raise ValueError("任务描述太短，请提供更详细的需求描述")
        
        # 检查是否是工作流相关需求
        workflow_keywords = [
            "工作流", "流程", "自动化", "步骤", "节点", 
            "workflow", "process", "automation", "flow"
        ]
        
        if not any(keyword in task_description.lower() for keyword in workflow_keywords):
            logger.warning("⚠️ 任务描述可能不是工作流相关需求")


# 示例使用函数
async def generate_workflow_example():
    """工作流生成示例"""
    
    # 模拟服务依赖
    class MockModelService:
        async def chat(self, **kwargs):
            return {"content": """
{
  "nodes": [
    {
      "id": "start001",
      "type": "workflowStart",
      "position": {"x": 50, "y": 100},
      "data": {
        "showInputs": true,
        "showOutputs": false,
        "label": "工作流开始",
        "inputs": [
          {
            "id": "input001",
            "attrName": "userQuery",
            "label": "用户查询",
            "valueType": "string",
            "value": null,
            "isDynamic": true,
            "editable": true,
            "removable": true
          }
        ],
        "outputs": []
      }
    },
    {
      "id": "llm001",
      "type": "chatWithLLM",
      "position": {"x": 400, "y": 100},
      "data": {
        "showInputs": true,
        "showOutputs": true,
        "label": "LLM分析",
        "inputs": [
          {
            "id": "model001",
            "attrName": "modelId",
            "label": "模型",
            "valueType": "modelId",
            "value": {"value": "gpt-4", "labelPath": ["OpenAI", "GPT-4"]},
            "editable": false,
            "removable": false
          },
          {
            "id": "system001",
            "attrName": "systemPrompt",
            "label": "系统提示",
            "valueType": "longText",
            "value": "你是一个专业的分析助手",
            "editable": false,
            "removable": false
          },
          {
            "id": "user001",
            "attrName": "userInput",
            "label": "用户输入",
            "valueType": "longText",
            "isDynamic": true,
            "valuePath": ["start001", "inputs", "input001"],
            "editable": false,
            "removable": false
          }
        ],
        "outputs": [
          {
            "id": "output001",
            "attrName": "modelOutput",
            "label": "分析结果",
            "valueType": "string",
            "editable": false,
            "removable": false
          }
        ]
      }
    },
    {
      "id": "end001",
      "type": "workflowEnd",
      "position": {"x": 750, "y": 100},
      "data": {
        "showInputs": false,
        "showOutputs": true,
        "label": "工作流结束",
        "inputs": [],
        "outputs": [
          {
            "id": "result001",
            "attrName": "result",
            "label": "最终结果",
            "valueType": "string",
            "isDynamic": true,
            "valuePath": ["llm001", "outputs", "output001"],
            "editable": true,
            "removable": true
          }
        ]
      }
    }
  ],
  "edges": [
    {
      "source": "start001",
      "target": "llm001",
      "id": "xy-edge__start001-llm001"
    },
    {
      "source": "llm001",
      "target": "end001",
      "id": "xy-edge__llm001-end001"
    }
  ]
}
            """}
    
    # 创建智能体实例
    agent = WorkflowGeneratorAgent(
        model_service=MockModelService(),
        workflow_engine=None,
        data_processor=None
    )
    
    # 执行工作流生成
    result = await agent.execute(
        task_description="创建一个智能问答工作流，能够接收用户问题并通过LLM生成回答",
        context={
            "domain": "通用问答",
            "target_users": "普通用户"
        },
        parameters={
            "complexity_level": "simple",
            "include_error_handling": True
        }
    )
    
    return result


if __name__ == "__main__":
    import asyncio
    
    # 运行示例
    result = asyncio.run(generate_workflow_example())
    print("生成的工作流:")
    print(json.dumps(result.result["workflow"], indent=2, ensure_ascii=False)) 