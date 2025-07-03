"""
需求分析智能体 (Requirement Analyzer Agent)
负责分析用户需求，识别所需的节点类型和数量
"""

import json
import logging
from typing import Dict, List, Any, Optional
from ..multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

logger = logging.getLogger(__name__)


class RequirementAnalyzer(BaseAgent):
    """需求分析智能体"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.REQUIREMENT_ANALYZER, message_bus, state_manager)
        self.llm_client = llm_client
        self.node_types_info = self._load_node_types_info()
    
    def _load_node_types_info(self) -> Dict[str, Any]:
        """加载节点类型信息"""
        return {
            "workflowStart": {
                "description": "工作流开始节点，定义工作流的输入参数和触发方式",
                "usage": "必须作为工作流的起始点，定义工作流的输入参数",
                "required": True
            },
            "workflowEnd": {
                "description": "工作流结束节点，定义工作流的输出结果", 
                "usage": "必须作为工作流的终止点，定义最终输出结果",
                "required": True
            },
            "dbQuery": {
                "description": "数据库查询节点，用于执行数据库查询操作",
                "usage": "当需要从数据库中查询数据时使用，支持条件过滤、排序和分页",
                "scenarios": ["查询用户信息", "获取订单列表", "检索产品数据", "统计分析"]
            },
            "dbCreate": {
                "description": "数据库创建节点，用于在数据库中创建新记录",
                "usage": "当需要向数据库插入新数据时使用",
                "scenarios": ["创建用户", "添加订单", "插入日志", "保存配置"]
            },
            "dbUpdate": {
                "description": "数据库更新节点，用于更新数据库中的记录",
                "usage": "当需要修改现有数据时使用",
                "scenarios": ["更新用户信息", "修改订单状态", "调整库存", "更新配置"]
            },
            "dbDelete": {
                "description": "数据库删除节点，用于删除数据库中的记录",
                "usage": "当需要删除数据时使用，必须提供WHERE条件",
                "scenarios": ["删除用户", "清理过期数据", "移除订单", "删除日志"]
            },
            "http": {
                "description": "HTTP请求节点，用于发送HTTP请求",
                "usage": "当需要调用外部API或服务时使用",
                "scenarios": ["调用第三方API", "发送通知", "数据同步", "外部验证"]
            },
            "llm": {
                "description": "LLM对话节点，用于与大型语言模型进行交互",
                "usage": "当需要AI处理文本、生成内容或智能分析时使用",
                "scenarios": ["文本生成", "内容摘要", "智能分析", "自动回复"]
            },
            "condition": {
                "description": "条件判断节点，用于根据条件决定工作流的执行路径",
                "usage": "当需要根据数据进行条件判断和分支处理时使用",
                "scenarios": ["用户权限检查", "数据验证", "状态判断", "业务规则"]
            },
            "code": {
                "description": "代码执行节点，用于执行自定义代码逻辑",
                "usage": "当需要执行复杂的数据处理或业务逻辑时使用",
                "scenarios": ["数据转换", "复杂计算", "格式化处理", "业务逻辑"]
            },
            "transaction": {
                "description": "数据库事务节点，用于将多个数据库操作包装在一个事务中",
                "usage": "当需要保证多个数据库操作的原子性时使用",
                "scenarios": ["转账操作", "订单创建", "批量更新", "复杂业务流程"]
            }
        }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """# 工作流需求分析专家

你是一个专业的工作流需求分析专家，专门负责分析用户的业务需求，并识别出完成该需求所需的所有工作流节点。

## 你的任务
1. 仔细分析用户的需求描述
2. 识别出需要哪些类型的节点来完成这个需求
3. 为每个节点提供清晰的用途说明和配置建议
4. 确保节点的选择合理且完整

## 可用节点类型
- **workflowStart**: 工作流开始节点（必需）
- **workflowEnd**: 工作流结束节点（必需）  
- **dbQuery**: 数据库查询节点
- **dbCreate**: 数据库创建节点
- **dbUpdate**: 数据库更新节点
- **dbDelete**: 数据库删除节点
- **http**: HTTP请求节点
- **llm**: LLM对话节点
- **condition**: 条件判断节点
- **code**: 代码执行节点
- **transaction**: 数据库事务节点

## 分析原则
1. **完整性**: 确保包含完成需求所需的所有节点
2. **准确性**: 每个节点的用途和配置必须准确
3. **合理性**: 节点的选择要符合业务逻辑
4. **可行性**: 确保节点组合能够实现用户需求

## 输出格式
请严格按照以下JSON格式输出：
```json
{
  "analysis": {
    "requirement_summary": "需求总结",
    "key_actions": ["关键行为1", "关键行为2"],
    "data_entities": ["数据实体1", "数据实体2"],
    "business_rules": ["业务规则1", "业务规则2"]
  },
  "required_nodes": [
    {
      "type": "节点类型",
      "purpose": "节点用途说明",
      "description": "详细描述",
      "suggested_name": "建议的节点名称",
      "key_configs": {
        "配置项1": "配置值或说明",
        "配置项2": "配置值或说明"
      }
    }
  ],
  "workflow_complexity": "简单/中等/复杂",
  "estimated_nodes_count": 数字
}
```

## 注意事项
- 必须包含workflowStart和workflowEnd节点
- 仔细考虑数据流和业务逻辑
- 对于复杂的业务规则，建议使用condition节点
- 对于需要保证数据一致性的操作，考虑使用transaction节点
- 提供的节点名称要具有描述性且符合PascalCase规范"""
    
    def _get_user_prompt(self, user_requirement: str) -> str:
        """获取用户提示词"""
        return f"""请分析以下用户需求，并识别出完成该需求所需的所有工作流节点：

**用户需求：**
{user_requirement}

**节点类型参考信息：**
{json.dumps(self.node_types_info, ensure_ascii=False, indent=2)}

请根据需求分析的原则，仔细分析用户需求，并按照指定的JSON格式输出结果。"""
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理需求分析任务"""
        try:
            # 获取共享上下文
            context = await self.state_manager.get_context()
            user_requirement = context.user_requirement
            
            logger.info(f"开始分析用户需求: {user_requirement}")
            
            # 构造LLM请求
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": self._get_user_prompt(user_requirement)}
            ]
            
            # 调用LLM进行需求分析
            response = await self.llm_client.chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.3,
                max_tokens=2000
            )
            
            # 解析LLM响应
            analysis_result = self._parse_llm_response(response)
            
            # 验证分析结果
            validated_result = self._validate_analysis_result(analysis_result)
            
            # 更新共享上下文
            await self.state_manager.update_context({
                "analyzed_nodes": validated_result["required_nodes"]
            })
            
            # 记录生成历史
            await self.state_manager.add_generation_history(
                "requirement_analysis",
                validated_result
            )
            
            logger.info(f"需求分析完成，识别出 {len(validated_result['required_nodes'])} 个节点")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"需求分析失败: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试从响应中提取JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败: {str(e)}")
            raise ValueError(f"LLM响应格式不正确: {str(e)}")
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证分析结果"""
        # 检查必需字段
        required_fields = ["analysis", "required_nodes", "workflow_complexity", "estimated_nodes_count"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"分析结果缺少必需字段: {field}")
        
        # 检查是否包含开始和结束节点
        node_types = [node["type"] for node in result["required_nodes"]]
        if "workflowStart" not in node_types:
            result["required_nodes"].insert(0, {
                "type": "workflowStart",
                "purpose": "工作流开始节点",
                "description": "定义工作流的输入参数和触发方式",
                "suggested_name": "WorkflowStart",
                "key_configs": {}
            })
        
        if "workflowEnd" not in node_types:
            result["required_nodes"].append({
                "type": "workflowEnd",
                "purpose": "工作流结束节点",
                "description": "定义工作流的输出结果",
                "suggested_name": "WorkflowEnd",
                "key_configs": {}
            })
        
        # 验证节点类型
        for node in result["required_nodes"]:
            if node["type"] not in self.node_types_info:
                raise ValueError(f"不支持的节点类型: {node['type']}")
        
        # 更新节点数量
        result["estimated_nodes_count"] = len(result["required_nodes"])
        
        return result 