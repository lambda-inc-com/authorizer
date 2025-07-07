"""
工作流组合智能体 (Workflow Composer Agent)
负责将分析出的节点组合成完整的工作流JSON
"""

import json
import logging
from typing import Dict, List, Any, Optional
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

logger = logging.getLogger(__name__)


class WorkflowComposer(BaseAgent):
    """工作流组合智能体"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.WORKFLOW_COMPOSER, message_bus, state_manager)
        self.llm_client = llm_client
        self.node_templates = self._load_node_templates()
    
    def _load_node_templates(self) -> Dict[str, Any]:
        """加载节点模板"""
        return {
            "workflowStart": {
                "template": {
                    "name": "WorkflowStart",
                    "type": "workflowStart",
                    "desc": "工作流开始节点，定义工作流的输入参数",
                    "inputs": {},
                    "outputs": {},
                    "configs": {},
                    "nextNodes": []
                }
            },
            "workflowEnd": {
                "template": {
                    "name": "WorkflowEnd",
                    "type": "workflowEnd",
                    "desc": "工作流结束节点，定义工作流的输出结果",
                    "inputs": {},
                    "outputs": {},
                    "configs": {},
                    "nextNodes": ["end"]
                }
            },
            "dbQuery": {
                "template": {
                    "name": "DbQuery",
                    "type": "dbQuery",
                    "desc": "执行数据库查询操作",
                    "inputs": {},
                    "outputs": {
                        "result": {
                            "type": "array",
                            "value": "$currentNodeResult",
                            "desc": "查询结果"
                        }
                    },
                    "configs": {
                        "table": "",
                        "fields": [],
                        "filters": [],
                        "sorts": [],
                        "limit": 100,
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "dbCreate": {
                "template": {
                    "name": "DbCreate",
                    "type": "dbCreate",
                    "desc": "在数据库中创建新记录",
                    "inputs": {},
                    "outputs": {
                        "insertId": {
                            "type": "string",
                            "value": "$currentNodeResult.insertId",
                            "desc": "新创建记录的ID"
                        }
                    },
                    "configs": {
                        "table": "",
                        "data": {},
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "dbUpdate": {
                "template": {
                    "name": "DbUpdate",
                    "type": "dbUpdate",
                    "desc": "更新数据库中的记录",
                    "inputs": {},
                    "outputs": {
                        "affectedRows": {
                            "type": "number",
                            "value": "$currentNodeResult.affectedRows",
                            "desc": "影响的行数"
                        }
                    },
                    "configs": {
                        "table": "",
                        "data": {},
                        "filters": [],
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "dbDelete": {
                "template": {
                    "name": "DbDelete",
                    "type": "dbDelete",
                    "desc": "删除数据库中的记录",
                    "inputs": {},
                    "outputs": {
                        "affectedRows": {
                            "type": "number",
                            "value": "$currentNodeResult.affectedRows",
                            "desc": "删除的行数"
                        }
                    },
                    "configs": {
                        "table": "",
                        "filters": [],
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "http": {
                "template": {
                    "name": "Http",
                    "type": "http",
                    "desc": "发送HTTP请求",
                    "inputs": {},
                    "outputs": {
                        "result": {
                            "type": "object",
                            "value": "$currentNodeResult",
                            "desc": "HTTP响应结果"
                        }
                    },
                    "configs": {
                        "method": "GET",
                        "url": "",
                        "headers": {},
                        "params": {},
                        "queryParams": {},
                        "bodyType": "none",
                        "body": "",
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "llm": {
                "template": {
                    "name": "ChatWithLLM",
                    "type": "llm",
                    "desc": "使用LLM模型进行对话生成",
                    "inputs": {},
                    "outputs": {
                        "response": {
                            "type": "string",
                            "value": "$currentNodeResult",
                            "desc": "LLM生成的回复"
                        }
                    },
                    "configs": {
                        "modelId": "gpt-4",
                        "temperature": 0.7,
                        "maxTokens": 1000,
                        "systemPrompt": ""
                    },
                    "nextNodes": []
                }
            },
            "condition": {
                "template": {
                    "name": "Condition",
                    "type": "condition",
                    "desc": "根据条件判断决定工作流的执行路径",
                    "inputs": {},
                    "outputs": {
                        "result": {
                            "type": "object",
                            "value": "$currentNodeResult",
                            "desc": "条件判断结果"
                        }
                    },
                    "configs": {
                        "conditionGroups": [],
                        "defaultNextNode": ""
                    },
                    "nextNodes": []
                }
            },
            "code": {
                "template": {
                    "name": "Code",
                    "type": "code",
                    "desc": "执行自定义代码逻辑",
                    "inputs": {},
                    "outputs": {
                        "result": {
                            "type": "object",
                            "value": "$currentNodeResult",
                            "desc": "代码执行结果"
                        }
                    },
                    "configs": {
                        "file": {
                            "name": "main.ts",
                            "content": ""
                        },
                        "dependencies": [],
                        "timeout": 30
                    },
                    "nextNodes": []
                }
            },
            "transaction": {
                "template": {
                    "name": "Transaction",
                    "type": "transaction",
                    "desc": "执行数据库事务操作",
                    "inputs": {},
                    "outputs": {
                        "transactionResult": {
                            "type": "object",
                            "value": "$currentNodeResult",
                            "desc": "事务执行结果"
                        }
                    },
                    "configs": {
                        "isolation": "READ_COMMITTED",
                        "timeout": 60
                    },
                    "children": [],
                    "nextNodes": []
                }
            }
        }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """# 工作流组合专家

你是一个专业的工作流组合专家，负责将需求分析阶段识别的节点组合成完整的、可执行的工作流JSON。

## 你的任务
1. 根据需求分析结果，为每个节点生成详细的配置
2. 建立正确的节点连接关系（nextNodes）
3. 设置合适的数据流引用（inputs/outputs）
4. 确保工作流的逻辑合理性和可执行性

## 核心原则
1. **数据流一致性**: 确保节点间的数据传递路径正确
2. **业务逻辑完整性**: 工作流要能完整实现用户需求
3. **配置准确性**: 每个节点的配置要准确且完整
4. **连接关系正确**: nextNodes要反映正确的执行顺序

## 数据引用规范
- `$prevNode.outputs.fieldName` - 引用前一个节点的输出
- `$currentNode.inputs.fieldName` - 引用当前节点的输入
- `$currentNodeResult` - 引用当前节点的执行结果

## 节点连接规则
- 每个节点（除condition外）必须指定nextNodes
- workflowStart必须作为第一个节点
- workflowEnd必须作为最后一个节点，nextNodes为["end"]
- 条件节点通过内部配置决定流向

## 输出格式
请严格按照以下JSON格式输出完整的工作流：
```json
{
  "workflow": {
    "name": "工作流名称",
    "description": "工作流描述",
    "version": "1.0.0",
    "nodes": [
      {
        "name": "节点名称",
        "type": "节点类型",
        "desc": "节点描述",
        "inputs": {
          "字段名": {
            "type": "数据类型",
            "value": "数据来源",
            "desc": "字段描述"
          }
        },
        "outputs": {
          "字段名": {
            "type": "数据类型",
            "value": "数据来源",
            "desc": "字段描述"
          }
        },
        "configs": {
          "配置项": "配置值"
        },
        "nextNodes": ["下一个节点名称"]
      }
    ]
  },
  "composition_notes": {
    "data_flow": ["数据流说明"],
    "business_logic": ["业务逻辑说明"],
    "key_decisions": ["关键决策说明"]
  }
}
```

## 注意事项
- 节点名称必须唯一且使用PascalCase
- 必须为每个节点提供合适的inputs和outputs
- 数据库操作节点必须指定table
- HTTP节点必须指定method和url
- 条件节点必须配置conditionGroups
- 确保数据流的连贯性和完整性"""
    
    def _get_user_prompt(self, user_requirement: str, analyzed_nodes: List[Dict[str, Any]], retry_info: Optional[Dict[str, Any]] = None) -> str:
        """获取用户提示词"""
        base_prompt = f"""请根据用户需求和需求分析结果，生成完整的工作流JSON配置。

**用户需求：**
{user_requirement}

**需求分析结果：**
{json.dumps(analyzed_nodes, ensure_ascii=False, indent=2)}

**节点模板参考：**
{json.dumps(self.node_templates, ensure_ascii=False, indent=2)}"""
        
        if retry_info:
            base_prompt += f"""

**重试信息：**
上一次生成的工作流存在以下问题：
{json.dumps(retry_info.get('errors', []), ensure_ascii=False, indent=2)}

请修复这些问题并重新生成工作流。

**上一次生成的工作流：**
{json.dumps(retry_info.get('previous_workflow', {}), ensure_ascii=False, indent=2)}"""
        
        base_prompt += """

请按照工作流组合的核心原则，生成完整的、可执行的工作流JSON。特别注意：
1. 确保数据流的连贯性
2. 正确设置节点连接关系
3. 为每个节点提供准确的配置
4. 保证工作流能够完整实现用户需求"""
        
        return base_prompt
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流组合任务"""
        try:
            # 获取共享上下文
            context = await self.state_manager.get_context()
            user_requirement = context.user_requirement
            analyzed_nodes = context.analyzed_nodes
            
            # 检查是否是重试请求
            retry_info = task_data.get('errors') if 'errors' in task_data else None
            
            logger.info(f"开始组合工作流，节点数量: {len(analyzed_nodes)}")
            
            # 构造LLM请求
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": self._get_user_prompt(user_requirement, analyzed_nodes, retry_info)}
            ]
            
            # 调用LLM进行工作流组合
            response = await self.llm_client.chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.2,
                max_tokens=4000
            )
            
            # 解析LLM响应
            composition_result = self._parse_llm_response(response)
            
            # 验证组合结果
            validated_result = self._validate_composition_result(composition_result)
            
            # 更新共享上下文
            await self.state_manager.update_context({
                "composed_workflow": validated_result["workflow"]
            })
            
            # 记录生成历史
            await self.state_manager.add_generation_history(
                "workflow_composition",
                validated_result
            )
            
            logger.info("工作流组合完成")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"工作流组合失败: {str(e)}")
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
    
    def _validate_composition_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证组合结果"""
        # 检查必需字段
        if "workflow" not in result:
            raise ValueError("组合结果缺少workflow字段")
        
        workflow = result["workflow"]
        
        # 检查工作流必需字段
        required_fields = ["name", "description", "version", "nodes"]
        for field in required_fields:
            if field not in workflow:
                raise ValueError(f"工作流缺少必需字段: {field}")
        
        # 验证节点
        nodes = workflow["nodes"]
        if not nodes:
            raise ValueError("工作流必须包含至少一个节点")
        
        # 检查节点名称唯一性
        node_names = [node["name"] for node in nodes]
        if len(node_names) != len(set(node_names)):
            raise ValueError("节点名称必须唯一")
        
        # 验证每个节点
        for node in nodes:
            self._validate_node(node)
        
        # 验证节点连接关系
        self._validate_node_connections(nodes)
        
        return result
    
    def _validate_node(self, node: Dict[str, Any]) -> None:
        """验证单个节点"""
        # 检查必需字段
        required_fields = ["name", "type", "desc", "inputs", "outputs", "configs", "nextNodes"]
        for field in required_fields:
            if field not in node:
                raise ValueError(f"节点 {node.get('name', 'unknown')} 缺少必需字段: {field}")
        
        # 验证节点类型
        if node["type"] not in self.node_templates:
            raise ValueError(f"不支持的节点类型: {node['type']}")
    
    def _validate_node_connections(self, nodes: List[Dict[str, Any]]) -> None:
        """验证节点连接关系"""
        node_names = {node["name"] for node in nodes}
        
        # 检查起始节点
        start_nodes = [node for node in nodes if node["type"] == "workflowStart"]
        if len(start_nodes) != 1:
            raise ValueError("工作流必须包含且仅包含一个workflowStart节点")
        
        # 检查结束节点
        end_nodes = [node for node in nodes if node["type"] == "workflowEnd"]
        if len(end_nodes) != 1:
            raise ValueError("工作流必须包含且仅包含一个workflowEnd节点")
        
        # 验证nextNodes引用
        for node in nodes:
            if node["type"] == "workflowEnd":
                if node["nextNodes"] != ["end"]:
                    raise ValueError("workflowEnd节点的nextNodes必须是['end']")
            else:
                for next_node in node["nextNodes"]:
                    if next_node != "end" and next_node not in node_names:
                        raise ValueError(f"节点 {node['name']} 的nextNodes引用了不存在的节点: {next_node}")
    
    async def _handle_retry(self, retry_data: Dict[str, Any]) -> None:
        """处理重试请求"""
        logger.info("收到重试请求，开始重新组合工作流")
        await self._execute_task(retry_data) 