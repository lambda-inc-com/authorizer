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
                    "nextNodes": []
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
                        "defaultNextNode": ""
                    }
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
            "chatWithLLM": {
                "template": {
                    "name": "LLMChat",
                    "type": "chatWithLLM",
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
- **chatWithLLM**: LLM对话节点（与AI模型交互）
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
- 条件节点不设置nextNodes字段，流向由条件配置决定

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
    "name": "WorkflowName",
    "description": "工作流描述",
    "version": "1.0.0",
    "nodes": [
      {
        "name": "NodeName",
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
        "nextNodes": ["NextNodeName"]
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

## 特别注意
- condition节点不包含nextNodes字段
- condition节点不包含outputs字段
- 其他节点类型必须包含nextNodes字段

## 注意事项
- 工作流名称必须使用英文，采用PascalCase或camelCase格式
- 节点名称必须唯一且使用英文PascalCase命名，如: "QuerySupplier", "CreateUser"
- 数据引用必须使用实际存在的节点名称，禁止使用虚构节点名称
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
            "name": await self._generate_workflow_name(user_requirement),
            "description": f"根据用户需求自动生成的工作流: {user_requirement}",
            "version": "1.0.0",
            "nodes": []
        }
        
        # 处理节点连接关系
        processed_nodes = self._process_node_connections(node_configs)
        
        # 修复节点引用
        processed_nodes = self._fix_node_references(processed_nodes)
        
        # 添加节点到工作流
        workflow["nodes"] = processed_nodes
        
        logger.info(f"成功组合工作流，包含 {len(processed_nodes)} 个节点")
        
        return workflow
    
    async def _generate_workflow_name(self, user_requirement: str) -> str:
        """生成工作流名称 - 交由大模型生成英文名称"""
        try:
            # 构建提示词
            prompt = f"""请根据用户需求生成一个简洁且有意义的英文工作流名称。

用户需求：
{user_requirement}

要求：
1. 名称必须是英文
2. 使用PascalCase格式（首字母大写的驼峰命名）
3. 名称应该准确反映工作流的主要功能
4. 长度控制在50个字符以内
5. 必须以"Workflow"结尾
6. 避免使用特殊字符，只使用字母和数字

示例：
- 用户注册流程 → UserRegistrationWorkflow
- 商品入库管理 → ProductInboundManagementWorkflow
- 订单支付处理 → OrderPaymentProcessingWorkflow

请直接返回工作流名称，不要包含任何其他文字或解释。"""

            # 调用LLM生成工作流名称
            response = await self.llm_client.chat_completion(
                [{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1  # 使用较低温度确保结果稳定
            )
            
            # 清理和验证生成的名称
            workflow_name = response.strip()
            
            # 移除可能的引号或其他包装字符
            workflow_name = workflow_name.strip('"\'`')
            
            # 验证名称格式
            if self._is_valid_workflow_name(workflow_name):
                logger.info(f"LLM生成的工作流名称: {workflow_name}")
                return workflow_name
            else:
                logger.warning(f"LLM生成的工作流名称格式无效: {workflow_name}，使用备用名称")
                return self._generate_fallback_workflow_name(user_requirement)
                
        except Exception as e:
            logger.error(f"LLM生成工作流名称失败: {str(e)}，使用备用名称")
            return self._generate_fallback_workflow_name(user_requirement)
    
    def _is_valid_workflow_name(self, name: str) -> bool:
        """验证工作流名称是否有效"""
        import re
        
        # 检查基本格式
        if not name or len(name) > 50:
            return False
            
        # 检查是否以Workflow结尾
        if not name.endswith("Workflow"):
            return False
            
        # 检查是否只包含字母和数字
        if not re.match(r'^[A-Za-z][A-Za-z0-9]*Workflow$', name):
            return False
            
        # 检查是否是PascalCase格式
        if not name[0].isupper():
            return False
            
        return True
    
    def _generate_fallback_workflow_name(self, user_requirement: str) -> str:
        """生成备用工作流名称"""
        import re
        import hashlib
        
        # 定义关键词到英文名称的映射
        keyword_mapping = {
            "用户": "User",
            "注册": "Registration", 
            "登录": "Login",
            "商品": "Product",
            "入库": "Inbound",
            "出库": "Outbound",
            "库存": "Inventory",
            "订单": "Order",
            "支付": "Payment",
            "查询": "Query",
            "创建": "Create",
            "更新": "Update",
            "删除": "Delete",
            "验证": "Validate",
            "检查": "Check",
            "发送": "Send",
            "通知": "Notification",
            "审核": "Audit",
            "流程": "Process",
            "管理": "Management",
            "供应商": "Supplier",
            "数据": "Data",
            "信息": "Info",
            "系统": "System",
            "操作": "Operation",
            "处理": "Process",
            "批量": "Batch"
        }
        
        # 提取关键词并转换为英文
        english_keywords = []
        for chinese_keyword, english_keyword in keyword_mapping.items():
            if chinese_keyword in user_requirement:
                if english_keyword not in english_keywords:
                    english_keywords.append(english_keyword)
        
        # 如果没有找到关键词，使用通用名称
        if not english_keywords:
            # 使用需求的hash值生成唯一标识
            hash_value = hashlib.md5(user_requirement.encode()).hexdigest()[:8]
            return f"Generated{hash_value.upper()}Workflow"
        
        # 限制关键词数量，最多3个
        english_keywords = english_keywords[:3]
        
        # 生成工作流名称
        workflow_name = "".join(english_keywords) + "Workflow"
        
        return workflow_name
    
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
            # 确保每个节点有正确的nextNodes设置（条件节点除外）
            if node.get("type") != "condition":
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
    
    def _fix_node_references(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """修复节点引用错误"""
        logger.info("开始修复节点引用...")
        
        # 收集所有节点的实际名称
        actual_node_names = set()
        for node in nodes:
            actual_node_names.add(node.get("name", ""))
        
        logger.info(f"实际节点名称: {actual_node_names}")
        
        # 修复每个节点的引用
        fixed_nodes = []
        for node in nodes:
            fixed_node = self._fix_single_node_references(node, actual_node_names)
            fixed_nodes.append(fixed_node)
        
        logger.info("节点引用修复完成")
        return fixed_nodes
    
    def _fix_single_node_references(self, node: Dict[str, Any], actual_node_names: set) -> Dict[str, Any]:
        """修复单个节点的引用"""
        import re
        import copy
        
        # 深拷贝节点避免修改原始数据
        fixed_node = copy.deepcopy(node)
        
        # 修复inputs中的引用
        if "inputs" in fixed_node:
            for input_name, input_config in fixed_node["inputs"].items():
                if isinstance(input_config, dict) and "value" in input_config:
                    original_value = input_config["value"]
                    fixed_value = self._fix_reference_string(original_value, actual_node_names)
                    if fixed_value != original_value:
                        logger.info(f"修复节点 {node.get('name')} 输入 {input_name} 引用: {original_value} -> {fixed_value}")
                        input_config["value"] = fixed_value
        
        # 修复outputs中的引用
        if "outputs" in fixed_node:
            for output_name, output_config in fixed_node["outputs"].items():
                if isinstance(output_config, dict) and "value" in output_config:
                    original_value = output_config["value"]
                    fixed_value = self._fix_reference_string(original_value, actual_node_names)
                    if fixed_value != original_value:
                        logger.info(f"修复节点 {node.get('name')} 输出 {output_name} 引用: {original_value} -> {fixed_value}")
                        output_config["value"] = fixed_value
        
        # 修复configs中的引用
        if "configs" in fixed_node:
            fixed_node["configs"] = self._fix_config_references(fixed_node["configs"], actual_node_names)
        
        return fixed_node
    
    def _fix_reference_string(self, value: str, actual_node_names: set) -> str:
        """修复引用字符串中的节点名称"""
        import re
        
        if not isinstance(value, str):
            return value
        
        # 查找所有节点引用模式 $.NodeName.xxx (支持中文和英文)
        pattern = r'\$\.([a-zA-Z\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*)'
        matches = re.findall(pattern, value)
        
        fixed_value = value
        for referenced_node in matches:
            # 跳过特殊引用
            if referenced_node in ["currentItem", "currentIndex", "context"]:
                continue
            
            # 检查引用的节点是否存在
            if referenced_node not in actual_node_names:
                # 尝试找到最相似的节点名称
                best_match = self._find_best_node_match(referenced_node, actual_node_names)
                if best_match:
                    # 替换引用
                    old_ref = f"$.{referenced_node}"
                    new_ref = f"$.{best_match}"
                    fixed_value = fixed_value.replace(old_ref, new_ref)
                    logger.info(f"修复节点引用: {old_ref} -> {new_ref}")
                else:
                    logger.warning(f"无法找到匹配的节点名称: {referenced_node}")
        
        return fixed_value
    
    def _find_best_node_match(self, target_name: str, actual_node_names: set) -> str:
        """找到最匹配的节点名称"""
        import difflib
        
        # 常见的节点名称映射（包含中文到英文的映射）
        common_mappings = {
            # 英文到英文的映射
            "StartNode": "StartProductInbound",
            "ValidateSupplier": "QuerySupplier",
            "CheckProduct": "QueryProduct",
            "GetProductInfo": "QueryProduct",
            "CheckSupplier": "QuerySupplier",
            "GetUserInfo": "QueryUser",
            "StartProcess": "StartProductInbound",
            "ValidateUser": "QueryUser",
            "CheckUserExists": "QueryUser",
            "GetSupplierInfo": "QuerySupplier",
            "CreateProductRecord": "CreateProduct",
            "UpdateProductRecord": "UpdateProduct",
            "RecordStockMovement": "CreateStockMovement",
            "NotifyWarehouseAdmin": "SendManagerNotification",
            "NotifyAdmin": "SendManagerNotification",
            "CheckProductInfo": "QueryProduct",
            "CheckProductExists": "QueryProduct",
            "ValidateProduct": "QueryProduct",
            "EndProcess": "EndProductInbound",
            "FinishProcess": "EndProductInbound",
            
            # 中文到英文的映射
            "开始入库流程": "StartStockIn",
            "验证供应商": "QuerySupplier",
            "供应商存在判断": "CheckSupplierExists",
            "检查商品信息": "QueryProduct", 
            "商品存在判断": "CheckProductExists",
            "创建新商品": "CreateProduct",
            "库存事务处理": "StockUpdateTransaction",
            "更新库存": "UpdateInventory",
            "记录库存变动": "CreateStockMovement",
            "检查大量入库": "CheckLargeQuantity",
            "发送通知": "SendNotification",
            "结束入库流程": "EndStockIn",
            
            # 更多通用的中文映射
            "开始流程": "StartProcess",
            "开始节点": "StartNode",
            "结束流程": "EndProcess",
            "结束节点": "EndNode",
            "用户验证": "ValidateUser",
            "用户查询": "QueryUser",
            "用户创建": "CreateUser",
            "用户更新": "UpdateUser",
            "用户删除": "DeleteUser",
            "商品查询": "QueryProduct",
            "商品创建": "CreateProduct",
            "商品更新": "UpdateProduct",
            "商品删除": "DeleteProduct",
            "库存查询": "QueryInventory",
            "库存更新": "UpdateInventory",
            "订单查询": "QueryOrder",
            "订单创建": "CreateOrder",
            "订单更新": "UpdateOrder",
            "支付处理": "ProcessPayment",
            "发送邮件": "SendEmail",
            "发送短信": "SendSMS",
            "条件判断": "CheckCondition",
            "数据验证": "ValidateData",
            "文件上传": "UploadFile",
            "文件下载": "DownloadFile",
            "数据导入": "ImportData",
            "数据导出": "ExportData",
            "状态检查": "CheckStatus",
            "权限验证": "ValidatePermission",
            "日志记录": "LogRecord",
            "通知发送": "SendNotification",
            "审核流程": "AuditProcess",
            "批量处理": "BatchProcess",
            "定时任务": "ScheduledTask",
            "数据同步": "SyncData",
            "缓存更新": "UpdateCache",
            "监控检查": "MonitorCheck",
            "报告生成": "GenerateReport",
            "统计分析": "StatisticsAnalysis",
            "配置更新": "UpdateConfig",
            "系统初始化": "SystemInit",
            "清理任务": "CleanupTask"
        }
        
        # 首先检查预定义的映射
        if target_name in common_mappings:
            mapped_name = common_mappings[target_name]
            if mapped_name in actual_node_names:
                return mapped_name
        
        # 使用字符串相似度找到最匹配的节点
        best_match = None
        best_ratio = 0.0
        
        for actual_name in actual_node_names:
            # 计算相似度
            ratio = difflib.SequenceMatcher(None, target_name.lower(), actual_name.lower()).ratio()
            if ratio > best_ratio and ratio > 0.5:  # 至少50%相似度
                best_ratio = ratio
                best_match = actual_name
        
        return best_match
    
    def _fix_config_references(self, configs: dict, actual_node_names: set) -> dict:
        """修复配置中的引用"""
        import copy
        
        fixed_configs = copy.deepcopy(configs)
        
        # 递归处理所有配置值
        def fix_value(obj):
            if isinstance(obj, str):
                return self._fix_reference_string(obj, actual_node_names)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = fix_value(value)
                return obj
            elif isinstance(obj, list):
                return [fix_value(item) for item in obj]
            else:
                return obj
        
        return fix_value(fixed_configs)
    
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
        # 检查必需字段，但根据节点类型决定是否需要outputs和nextNodes
        required_fields = ["name", "type", "desc", "inputs", "configs"]
        
        # condition节点不需要outputs和nextNodes字段
        if node.get("type") != "condition":
            required_fields.extend(["outputs", "nextNodes"])
        
        for field in required_fields:
            if field not in node:
                raise ValueError(f"节点 {node.get('name', 'unknown')} 缺少必需字段: {field}")
        
        # 验证节点类型
        if node["type"] not in self.node_templates:
            raise ValueError(f"不支持的节点类型: {node['type']}")
            
        # 特殊验证：condition节点不应该有outputs和nextNodes字段
        if node.get("type") == "condition":
            if "outputs" in node:
                raise ValueError(f"condition节点 {node.get('name')} 不应该包含outputs字段")
            if "nextNodes" in node:
                raise ValueError(f"condition节点 {node.get('name')} 不应该包含nextNodes字段")
    
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
            elif node["type"] == "condition":
                # 条件节点不包含nextNodes字段，跳过验证
                continue
            else:
                for next_node in node["nextNodes"]:
                    if next_node != "end" and next_node not in node_names:
                        raise ValueError(f"节点 {node['name']} 的nextNodes引用了不存在的节点: {next_node}")
    
    async def _handle_retry(self, retry_data: Dict[str, Any]) -> None:
        """处理重试请求"""
        logger.info("收到重试请求，开始重新组合工作流")
        await self._execute_task(retry_data) 