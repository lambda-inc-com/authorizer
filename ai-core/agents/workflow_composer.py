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
        """加载节点模板 - 使用新的DSL规范"""
        return {
            "workflowStart": {
                "template": {
                    "name": "WorkflowStart",
                    "type": "workflowStart",
                    "desc": "工作流开始节点，定义工作流的输入参数和触发方式",
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
                    "desc": "工作流结束节点，定义工作流的API响应输出结果",
                    "inputs": {},
                    "outputs": {
                        "code": {
                            "type": "number",
                            "desc": "HTTP状态码"
                        },
                        "data": {
                            "type": "object",
                            "desc": "响应数据（可以是字符串、对象或数组）"
                        },
                        "message": {
                            "type": "string",
                            "desc": "响应消息"
                        }
                    },
                    "configs": {},
                    "nextNodes": ["end"]
                }
            },
            "dbQuery": {
                "template": {
                    "name": "DbQuery",
                    "type": "dbQuery",
                    "desc": "数据库查询节点，执行SELECT查询操作",
                    "inputs": {},
                    "outputs": {
                        "affected": {
                            "type": "number",
                            "desc": "查询返回的行数"
                        },
                        "data": {
                            "type": "array",
                            "desc": "查询结果数据"
                        }
                    },
                    "configs": {
                        "table": "",
                        "sql": ""
                    },
                    "nextNodes": []
                }
            },
            "dbCreate": {
                "template": {
                    "name": "DbCreate",
                    "type": "dbCreate",
                    "desc": "数据库创建节点，执行INSERT插入操作",
                    "inputs": {},
                    "outputs": {
                        "affected": {
                            "type": "number",
                            "desc": "影响的行数"
                        },
                        "insertId": {
                            "type": "string",
                            "desc": "新插入记录的ID"
                        }
                    },
                    "configs": {
                        "table": "",
                        "sql": ""
                    },
                    "nextNodes": []
                }
            },
            "dbUpdate": {
                "template": {
                    "name": "DbUpdate",
                    "type": "dbUpdate",
                    "desc": "数据库更新节点，执行UPDATE更新操作",
                    "inputs": {},
                    "outputs": {
                        "affected": {
                            "type": "number",
                            "desc": "影响的行数"
                        }
                    },
                    "configs": {
                        "table": "",
                        "sql": ""
                    },
                    "nextNodes": []
                }
            },
            "dbDelete": {
                "template": {
                    "name": "DbDelete",
                    "type": "dbDelete",
                    "desc": "数据库删除节点，执行DELETE删除操作",
                    "inputs": {},
                    "outputs": {
                        "affected": {
                            "type": "number",
                            "desc": "影响的行数"
                        }
                    },
                    "configs": {
                        "table": "",
                        "sql": ""
                    },
                    "nextNodes": []
                }
            },
            "transaction": {
                "template": {
                    "name": "Transaction",
                    "type": "transaction",
                    "desc": "数据库事务节点，将多个数据库操作包装在一个事务中",
                    "inputs": {},
                    "outputs": {
                        "committed": {
                            "type": "boolean",
                            "desc": "事务是否成功提交"
                        },
                        "affectedTotal": {
                            "type": "number",
                            "desc": "事务中所有操作影响的总行数"
                        },
                        "childResults": {
                            "type": "array",
                            "desc": "所有子节点的执行结果数组"
                        },
                        "executionTime": {
                            "type": "number",
                            "desc": "事务执行耗时，单位毫秒"
                        }
                    },
                    "configs": {
                        "isolation": "READ_COMMITTED",
                        "timeout": 60,
                        "children": []
                    },
                    "nextNodes": []
                }
            },
            "batch": {
                "template": {
                    "name": "Batch",
                    "type": "batch",
                    "desc": "批量处理节点，实现Map-Reduce模式的批量数据处理",
                    "inputs": {},
                    "outputs": {
                        "totalProcessed": {
                            "type": "number",
                            "desc": "处理的总数量"
                        },
                        "successCount": {
                            "type": "number",
                            "desc": "成功处理的数量"
                        },
                        "failureCount": {
                            "type": "number",
                            "desc": "失败处理的数量"
                        },
                        "aggregatedResult": {
                            "type": "object",
                            "desc": "根据reduce策略聚合的结果"
                        },
                        "executionTime": {
                            "type": "number",
                            "desc": "批处理执行耗时，单位毫秒"
                        }
                    },
                    "configs": {
                        "concurrency": 1,
                        "timeout": 60,
                        "continueOnError": False,
                        "mapConfig": {
                            "dataSource": "",
                            "itemVariable": "$.currentItem",
                            "indexVariable": "$.currentIndex"
                        },
                        "reduceConfig": {
                            "strategy": "collect",
                            "targetField": ""
                        },
                        "child": {}
                    },
                    "nextNodes": []
                }
            },
            "condition": {
                "template": {
                    "name": "Condition",
                    "type": "condition",
                    "desc": "条件判断节点，根据条件决定工作流的执行路径",
                    "inputs": {},
                    "configs": {
                        "conditionGroups": [],
                        "groupRelationship": "AND",
                        "defaultNextNode": ""
                    },
                    "nextNodes": []
                }
            },
            "workflow": {
                "template": {
                    "name": "Workflow",
                    "type": "workflow",
                    "desc": "工作流节点，调用其他已定义的工作流实现复用",
                    "inputs": {},
                    "outputs": {
                        "executionStatus": {
                            "type": "string",
                            "desc": "执行状态(success/failed/timeout)"
                        },
                        "executionTime": {
                            "type": "number",
                            "desc": "执行耗时(毫秒)"
                        },
                        "executionMetadata": {
                            "type": "object",
                            "desc": "执行详情"
                        }
                    },
                    "configs": {
                        "workflowId": "",
                        "version": "latest",
                        "inputMappings": [],
                        "outputMappings": [],
                        "maxDepth": 3,
                        "timeout": 60,
                        "allowFailure": False,
                        "retryCount": 0
                    },
                    "nextNodes": []
                }
            },
            "http": {
                "template": {
                    "name": "Http",
                    "type": "http",
                    "desc": "HTTP请求节点，发送HTTP请求到外部服务",
                    "inputs": {},
                    "outputs": {
                        "code": {
                            "type": "number",
                            "desc": "HTTP状态码"
                        },
                        "data": {
                            "type": "object",
                            "desc": "响应数据"
                        },
                        "message": {
                            "type": "string",
                            "desc": "响应消息"
                        }
                    },
                    "configs": {
                        "method": "GET",
                        "url": "",
                        "timeout": 30,
                        "params": {},
                        "queryParams": {},
                        "headers": {},
                        "bodyType": "none",
                        "body": ""
                    },
                    "nextNodes": []
                }
            },
            "llm": {
                "template": {
                    "name": "LLMChat",
                    "type": "llm",
                    "desc": "LLM对话节点，与大型语言模型进行交互",
                    "inputs": {},
                    "outputs": {
                        "thinking": {
                            "type": "string",
                            "desc": "AI思考过程"
                        },
                        "response": {
                            "type": "string",
                            "desc": "AI生成的回复"
                        },
                        "tokens": {
                            "type": "object",
                            "desc": "Token使用情况"
                        }
                    },
                    "configs": {
                        "modelId": "",
                        "systemPrompt": "",
                        "temperature": 0.7,
                        "maxTokens": 1000,
                        "topP": 0.9,
                        "frequencyPenalty": 0,
                        "presencePenalty": 0
                    },
                    "nextNodes": []
                }
            },
            "code": {
                "template": {
                    "name": "Code",
                    "type": "code",
                    "desc": "代码执行节点，执行自定义JavaScript代码逻辑",
                    "inputs": {},
                    "outputs": {},
                    "configs": {
                        "file": {
                            "name": "main.js",
                            "content": ""
                        },
                        "dependencies": []
                    },
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

## 支持的节点类型
- **workflowStart**: 工作流开始节点（必需）
- **workflowEnd**: 工作流结束节点（必需，必须返回标准API响应格式）
- **dbQuery**: 数据库查询节点（SELECT操作）
- **dbCreate**: 数据库创建节点（INSERT操作）
- **dbUpdate**: 数据库更新节点（UPDATE操作）
- **dbDelete**: 数据库删除节点（DELETE操作）
- **transaction**: 数据库事务节点（包装多个数据库操作）
- **batch**: 批量处理节点（Map-Reduce模式批量处理）
- **condition**: 条件判断节点（决定执行路径）
- **workflow**: 工作流节点（调用其他工作流）
- **http**: HTTP请求节点（调用外部API）
- **llm**: LLM对话节点（与AI模型交互）
- **code**: 代码执行节点（执行JavaScript代码）

## 核心原则
1. **数据流一致性**: 确保节点间的数据传递路径正确
2. **业务逻辑完整性**: 工作流要能完整实现用户需求
3. **配置准确性**: 每个节点的配置要准确且完整
4. **连接关系正确**: nextNodes要反映正确的执行顺序

## 数据引用规范
- `$.节点名.inputs.字段名` - 引用指定节点的输入参数
- `$.节点名.outputs.字段名` - 引用指定节点的输出
- `$.节点名.result.字段名` - 引用Code节点的结果
- `$.currentItem.字段名` - 批处理中的当前项

## 节点连接规则
- 每个节点（除condition外）必须指定nextNodes
- workflowStart必须作为第一个节点
- workflowEnd必须作为最后一个节点，nextNodes为["end"]
- 条件节点通过内部配置决定流向

## workflowEnd节点要求
workflowEnd节点必须返回标准的API响应格式，包含：
- **code**: HTTP状态码（200成功，201创建，400错误等）
- **data**: 响应数据（可以是字符串、对象或数组）
- **message**: 响应消息（操作结果描述）

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
- 数据库操作节点必须指定table和sql
- HTTP节点必须指定method和url
- 条件节点必须配置conditionGroups
- workflowEnd必须包含code、data、message输出字段
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
        """处理工作流组合任务 - 增强版，直接使用已生成的节点"""
        try:
            # 获取共享上下文
            context = await self.state_manager.get_context()
            user_requirement = context.user_requirement
            analyzed_nodes = context.analyzed_nodes  # 这里包含已生成的节点配置
            
            # 检查是否是重试请求
            retry_info = task_data.get('errors') if 'errors' in task_data else None
            
            logger.info(f"开始组合工作流，节点数量: {len(analyzed_nodes)}")
            
            # 提取节点配置
            node_configs = []
            for analyzed_node in analyzed_nodes:
                if "node_config" in analyzed_node:
                    node_configs.append(analyzed_node["node_config"])
                else:
                    # 兼容旧格式
                    node_configs.append(analyzed_node)
            
            # 直接组合工作流，不再调用LLM
            logger.info("直接组合已生成的节点配置")
            composed_workflow = await self._compose_workflow_from_nodes(
                user_requirement, node_configs, retry_info
            )
            
            # 验证组合结果
            validated_result = self._validate_composition_result({
                "workflow": composed_workflow,
                "composition_notes": {
                    "data_flow": ["节点间通过$prevNode.outputs和$currentNode.inputs进行数据传递"],
                    "business_logic": ["按照需求分析智能体生成的节点顺序执行"],
                    "key_decisions": ["使用RequirementAnalyzer已生成的完整节点配置"]
                }
            })
            
            # 更新共享上下文
            await self.state_manager.update_context({
                "composed_workflow": validated_result["workflow"]
            })
            
            # 记录生成历史
            await self.state_manager.add_generation_history(
                "enhanced_workflow_composition",
                validated_result
            )
            
            logger.info("增强版工作流组合完成")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"增强版工作流组合失败: {str(e)}")
            raise
    
    async def _compose_workflow_from_nodes(self, user_requirement: str, 
                                         node_configs: List[Dict[str, Any]], 
                                         retry_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """直接从节点配置组合工作流"""
        
        # 基础工作流结构
        workflow = {
            "name": self._generate_workflow_name(user_requirement),
            "description": f"根据用户需求自动生成的工作流: {user_requirement}",
            "version": "1.0.0",
            "nodes": [],
            "edges": []
        }
        
        # 处理节点连接关系
        processed_nodes = self._process_node_connections(node_configs)
        
        # 添加节点到工作流
        workflow["nodes"] = processed_nodes
        
        # 生成边关系
        workflow["edges"] = self._generate_edges(processed_nodes)
        
        logger.info(f"成功组合工作流，包含 {len(processed_nodes)} 个节点")
        
        return workflow
    
    def _generate_workflow_name(self, user_requirement: str) -> str:
        """生成工作流名称"""
        # 简单的名称生成逻辑，可以根据需要优化
        import re
        name = re.sub(r'[^\w\s]', '', user_requirement)
        name = re.sub(r'\s+', '_', name.strip())
        return f"Workflow_{name[:50]}" if name else "AutoGeneratedWorkflow"
    
    def _process_node_connections(self, node_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理节点连接关系"""
        processed_nodes = []
        
        # 确保有开始和结束节点
        start_node = None
        end_node = None
        other_nodes = []
        
        for node in node_configs:
            if node.get("type") == "workflowStart":
                start_node = node
            elif node.get("type") == "workflowEnd":
                end_node = node
            else:
                other_nodes.append(node)
        
        # 如果缺少开始或结束节点，创建它们
        if not start_node:
            start_node = {
                "name": "WorkflowStart",
                "type": "workflowStart", 
                "desc": "工作流开始节点",
                "inputs": {
                    "parameters": {
                        "type": "object",
                        "value": {},
                        "desc": "工作流输入参数"
                    }
                },
                "outputs": {},
                "configs": {},
                "nextNodes": []
            }
        
        if not end_node:
            end_node = {
                "name": "WorkflowEnd",
                "type": "workflowEnd",
                "desc": "工作流结束节点", 
                "inputs": {
                    "finalResult": {
                        "type": "object",
                        "value": "$prevNode.outputs.result",
                        "desc": "最终结果"
                    }
                },
                "outputs": {
                    "code": {
                        "type": "number",
                        "value": "200",
                        "desc": "HTTP状态码"
                    },
                    "data": {
                        "type": "string",
                        "value": "操作成功",
                        "desc": "响应数据"
                    },
                    "message": {
                        "type": "string",
                        "value": "操作完成",
                        "desc": "响应消息"
                    }
                },
                "configs": {},
                "nextNodes": ["end"]
            }
        
        # 构建节点链
        processed_nodes = [start_node]
        
        # 添加中间节点
        for i, node in enumerate(other_nodes):
            # 确保每个节点有正确的nextNodes设置
            if i < len(other_nodes) - 1:
                node["nextNodes"] = [other_nodes[i + 1]["name"]]
            else:
                node["nextNodes"] = [end_node["name"]]
            processed_nodes.append(node)
        
        # 设置开始节点的连接
        if other_nodes:
            start_node["nextNodes"] = [other_nodes[0]["name"]]
        else:
            start_node["nextNodes"] = [end_node["name"]]
        
        # 添加结束节点
        processed_nodes.append(end_node)
        
        return processed_nodes
    
    def _generate_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """生成边关系"""
        edges = []
        
        for node in nodes:
            for next_node_name in node.get("nextNodes", []):
                if next_node_name != "end":
                    edges.append({
                        "source": node["name"],
                        "target": next_node_name
                    })
        
        return edges
    
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
        # 检查必需字段，但根据节点类型决定是否需要outputs
        required_fields = ["name", "type", "desc", "inputs", "configs", "nextNodes"]
        
        # condition节点不需要outputs字段
        if node.get("type") != "condition":
            required_fields.append("outputs")
        
        for field in required_fields:
            if field not in node:
                raise ValueError(f"节点 {node.get('name', 'unknown')} 缺少必需字段: {field}")
        
        # 验证节点类型
        if node["type"] not in self.node_templates:
            raise ValueError(f"不支持的节点类型: {node['type']}")
            
        # 特殊验证：condition节点不应该有outputs字段
        if node.get("type") == "condition" and "outputs" in node:
            raise ValueError(f"condition节点 {node.get('name')} 不应该包含outputs字段")
    
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