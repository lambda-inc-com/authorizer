"""
工作流组合智能体 (Workflow Composer Agent)
负责将分析出的节点组合成完整的工作流JSON
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType
from node_type_manager import node_type_manager

logger = logging.getLogger(__name__)


class WorkflowComposer(BaseAgent):
    """工作流组合智能体 - 动态验证版本"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.WORKFLOW_COMPOSER, message_bus, state_manager)
        self.llm_client = llm_client
        self.node_templates = {}
        # 节点DSL数据将从共享上下文获取
        self.node_dsl_data = {}

    def _parse_sql_select_fields(self, sql: str) -> List[str]:
        """解析SQL SELECT语句，提取返回的字段名"""
        try:
            # 简单的SQL解析，提取SELECT子句中的字段
            sql_clean = sql.strip().upper()
            if not sql_clean.startswith('SELECT'):
                return []
            
            # 找到SELECT和FROM之间的内容
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_clean, re.IGNORECASE | re.DOTALL)
            if not select_match:
                return []
            
            fields_str = select_match.group(1).strip()
            
            # 如果是SELECT *，返回空列表（表示所有字段）
            if fields_str == '*':
                return ['*']
            
            # 分割字段，处理别名
            fields = []
            for field in fields_str.split(','):
                field = field.strip()
                # 处理别名 (field AS alias 或 field alias)
                if ' AS ' in field.upper():
                    alias = field.split(' AS ')[-1].strip()
                    fields.append(alias.lower())
                elif ' ' in field and not field.startswith('('):
                    # 简单的别名形式 (field alias)
                    parts = field.split()
                    if len(parts) >= 2:
                        fields.append(parts[-1].lower())
                    else:
                        fields.append(parts[0].lower())
                else:
                    # 提取字段名（去掉表名前缀）
                    if '.' in field:
                        field = field.split('.')[-1]
                    fields.append(field.lower())
            
            return fields
            
        except Exception as e:
            logger.warning(f"SQL解析失败: {sql} - {str(e)}")
            return []

    def _infer_query_result_structure(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """推断数据库查询节点的结果结构"""
        result_info = {
            "has_data": True,
            "has_affected": True,
            "data_fields": [],
            "business_context": ""
        }
        
        if node.get("type") in ["dbQuery", "dbCreate", "dbUpdate", "dbDelete"]:
            configs = node.get("configs", {})
            sql = configs.get("sql", "")
            table = configs.get("table", "")
            
            if sql:
                # 解析SQL获取字段
                fields = self._parse_sql_select_fields(sql)
                result_info["data_fields"] = fields
                
                # 推断业务上下文
                node_name = node.get("name", "").lower()
                if "query" in node_name or "get" in node_name or "find" in node_name:
                    result_info["business_context"] = "existence_check"
                elif "create" in node_name or "insert" in node_name:
                    result_info["business_context"] = "creation_result"
                elif "update" in node_name:
                    result_info["business_context"] = "update_result"
                elif "delete" in node_name:
                    result_info["business_context"] = "deletion_result"
        
        return result_info

    def _generate_smart_condition_logic(self, condition_node: Dict[str, Any], 
                                      referenced_nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """为条件节点生成智能的判断逻辑"""
        node_name = condition_node.get("name", "")
        configs = condition_node.get("configs", {})
        
        # 分析条件节点的业务意图
        business_intent = self._analyze_condition_business_intent(node_name, condition_node.get("desc", ""))
        
        # 优化后的条件配置
        optimized_configs = configs.copy()
        
        if "conditionGroups" in optimized_configs:
            for group in optimized_configs["conditionGroups"]:
                conditions = group.get("conditions", [])
                for i, condition in enumerate(conditions):
                    left_value = condition.get("left", "")
                    
                    if left_value.startswith("$."):
                        # 解析引用的节点
                        parts = left_value.split(".")
                        if len(parts) >= 2:
                            referenced_node_name = parts[1]
                            if referenced_node_name in referenced_nodes:
                                referenced_node = referenced_nodes[referenced_node_name]
                                # 生成更智能的条件
                                new_condition = self._create_smart_condition(
                                    referenced_node, business_intent, condition
                                )
                                conditions[i] = new_condition
        
        return optimized_configs
    
    def _analyze_condition_business_intent(self, node_name: str, description: str) -> str:
        """分析条件节点的业务意图"""
        text = f"{node_name} {description}".lower()
        
        if any(keyword in text for keyword in ["exists", "存在", "检查", "验证", "valid"]):
            return "existence_check"
        elif any(keyword in text for keyword in ["status", "状态", "active", "enable"]):
            return "status_check"  
        elif any(keyword in text for keyword in ["threshold", "阈值", "limit", "量"]):
            return "threshold_check"
        elif any(keyword in text for keyword in ["permission", "权限", "auth", "authorize"]):
            return "permission_check"
        else:
            return "general_check"
    
    def _create_smart_condition(self, referenced_node: Dict[str, Any], 
                              business_intent: str, original_condition: Dict[str, Any]) -> Dict[str, Any]:
        """基于引用节点和业务意图创建智能条件"""
        node_type = referenced_node.get("type", "")
        node_name = referenced_node.get("name", "")
        
        # 对于数据库查询节点的存在性检查
        if node_type == "dbQuery" and business_intent == "existence_check":
            return {
                "left": f"$.{node_name}.outputs.affected",
                "operator": "greaterThan", 
                "right": 0
            }
        
        # 对于状态检查，尝试从结果数据中获取状态字段
        elif node_type == "dbQuery" and business_intent == "status_check":
            result_info = self._infer_query_result_structure(referenced_node)
            status_fields = [f for f in result_info["data_fields"] if "status" in f.lower()]
            
            if status_fields:
                return {
                    "left": f"$.{node_name}.outputs.data[0].{status_fields[0]}",
                    "operator": "equal",
                    "right": "active"
                }
            else:
                # 回退到存在性检查
                return {
                    "left": f"$.{node_name}.outputs.affected",
                    "operator": "greaterThan",
                    "right": 0
                }
        
        # 默认的存在性检查
        else:
            return {
                "left": f"$.{node_name}.outputs.affected",
                "operator": "greaterThan",
                "right": 0
            }

    async def _load_node_dsl_from_context(self):
        """从共享上下文获取节点DSL数据"""
        try:
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            if node_dsl_data:
                self.node_dsl_data = node_dsl_data
                logger.info(f"✅ WorkflowComposer从共享上下文获取 {len(node_dsl_data)} 个节点DSL数据")
                return True
            else:
                logger.warning("⚠️ WorkflowComposer共享上下文中没有节点DSL数据")
                return False
                
        except Exception as e:
            logger.error(f"❌ WorkflowComposer从共享上下文获取节点DSL数据失败: {str(e)}")
            return False

    def _get_node_required_fields(self, node_type: str) -> List[str]:
        """基于数据库DSL数据动态获取节点必需字段"""
        # 基础必需字段
        base_fields = ["name", "type", "desc", "inputs", "configs"]
        
        # 检查节点类型是否需要额外字段
        if node_type in self.node_dsl_data:
            dsl_data = self.node_dsl_data[node_type]
            schema = dsl_data.get('schema', {})
            
            # 如果schema中定义了outputs，则需要outputs字段
            if 'outputs' in schema:
                base_fields.append("outputs")
            
            # 如果schema中定义了nextNodes，则需要nextNodes字段
            if 'nextNodes' in schema:
                base_fields.append("nextNodes")
        else:
            # 回退到节点类型管理器的判断
            if not node_type_manager.is_condition_like_node(node_type):
                base_fields.extend(["outputs", "nextNodes"])
        
        return base_fields

    def _validate_node_type_dynamically(self, node_type: str) -> bool:
        """基于数据库DSL数据动态验证节点类型"""
        # 首先检查数据库DSL数据
        if self.node_dsl_data and node_type in self.node_dsl_data:
            return True
        
        # 然后检查节点类型管理器
        return node_type_manager.validate_node_type(node_type)

    def _get_node_special_rules(self, node_type: str) -> Dict[str, Any]:
        """基于数据库DSL数据获取节点特殊规则"""
        rules = {}
        
        if node_type in self.node_dsl_data:
            dsl_data = self.node_dsl_data[node_type]
            description = dsl_data.get('description', '').lower()
            schema = dsl_data.get('schema', {})
            
            # 基于描述推断特殊规则
            if '条件' in description or '判断' in description or 'condition' in description:
                rules['no_outputs'] = True
                rules['no_nextNodes'] = True
            
            # 基于schema推断规则
            if 'outputs' not in schema:
                rules['no_outputs'] = True
            if 'nextNodes' not in schema:
                rules['no_nextNodes'] = True
        else:
            # 使用节点类型管理器的判断
            if node_type_manager.is_condition_like_node(node_type):
                rules['no_outputs'] = True
                rules['no_nextNodes'] = True
            elif node_type_manager.is_end_node(node_type):
                rules['nextNodes_must_be_end'] = True
        
        return rules
    
    async def _load_node_templates_from_context(self) -> Dict[str, Any]:
        """从共享上下文获取节点DSL数据"""
        try:
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            if node_dsl_data:
                logger.info(f"✅ 从共享上下文获取 {len(node_dsl_data)} 个节点DSL数据")
                
                # 转换为兼容的模板格式
                templates = {}
                for node_type, dsl_data in node_dsl_data.items():
                    example = dsl_data.get('example', {})
                    templates[node_type] = {
                        "template": example,
                        "description": dsl_data.get('description', ''),
                        "schema": dsl_data.get('schema', {}),
                        "template_content": dsl_data.get('template_content', '')
                    }
                
                return templates
            else:
                logger.warning("⚠️ 共享上下文中没有节点DSL数据，使用默认模板")
                return self._load_node_templates()
                
        except Exception as e:
            logger.error(f"❌ 从共享上下文获取节点DSL数据失败: {str(e)}")
            return self._load_node_templates()
    
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

### 基本引用格式
- `$.节点名.inputs.字段名` - 引用指定节点的输入参数
- `$.节点名.outputs.字段名` - 引用指定节点的输出
- `$.节点名.result.字段名` - 引用Code节点的结果
- `$.currentItem.字段名` - 批处理中的当前项

### ⚠️ 数据库查询节点特殊规范
**所有数据库查询节点（dbQuery/dbCreate/dbUpdate/dbDelete）的 outputs 结构是固定的：**

```json
{
  "outputs": {
    "data": {
      "type": "array",
      "desc": "查询结果数组，包含SQL SELECT的字段"
    },
    "affected": {
      "type": "number", 
      "desc": "受影响的行数"
    }
  }
}
```

### 正确的数据库节点引用方式：

#### 1. 存在性检查（推荐）
❌ 错误：`$.QuerySupplier.{{outputs}}.supplier`
❌ 错误：`$.QuerySupplier.{{outputs}}.supplierExists`
✅ 正确：`$.QuerySupplier.{{outputs}}.affected` (用于判断查询是否有结果)

#### 2. 获取具体字段值
❌ 错误：`$.QuerySupplier.{{outputs}}.supplierId`
✅ 正确：`$.QuerySupplier.{{outputs}}.data[0].id` (从查询结果数组中获取字段)

#### 3. 条件节点中的存在性检查
```json
{{
  "conditions": [
    {{
      "left": "$.QuerySupplier.{{outputs}}.affected",
      "operator": "greaterThan",
      "right": 0
    }}
  ]
}}
```

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
- 工作流名称必须使用英文且以大写字母开头，采用PascalCase格式，如: "UserRegistrationWorkflow"
- 节点名称必须唯一且以大写字母开头，采用PascalCase格式，如: "QuerySupplier", "CreateUser", "CheckUserExists"
- 禁止节点名称重复，每个节点必须有唯一的名称
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
            # 🎯 从共享上下文加载节点DSL数据 (用于动态验证)
            await self._load_node_dsl_from_context()
            
            # 🎯 从共享上下文加载节点模板数据 (兼容性)
            self.node_templates = await self._load_node_templates_from_context()
            
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
            validated_result = await self._validate_composition_result({
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
        
        # 确保节点名称唯一性
        processed_nodes = self._ensure_unique_node_names(processed_nodes)
        
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
            node_type = node.get("type", "")
            if node_type_manager.is_start_node(node_type):
                start_node = node
            elif node_type_manager.is_end_node(node_type):
                end_node = node
            else:
                other_nodes.append(node)
        
        # 如果缺少开始或结束节点，创建它们
        if not start_node:
            actual_start_type = node_type_manager.find_start_node_type() or "start"
            start_node = {
                "name": "WorkflowStart",
                "type": actual_start_type, 
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
            actual_end_type = node_type_manager.find_end_node_type() or "end"
            end_node = {
                "name": "WorkflowEnd",
                "type": actual_end_type,
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
        
        # 修复每个节点的引用和名称格式
        fixed_nodes = []
        for node in nodes:
            # 首先修正节点名称格式
            node = self._fix_node_name_format(node)
            # 然后修复节点引用
            fixed_node = self._fix_single_node_references(node, actual_node_names)
            fixed_nodes.append(fixed_node)
        
        logger.info("节点引用修复完成")
        return fixed_nodes
     
    def _fix_node_name_format(self, node: Dict[str, Any]) -> Dict[str, Any]:
         """修正节点名称格式，确保以大写字母开头的PascalCase格式"""
         import copy
         
         fixed_node = copy.deepcopy(node)
         
         if "name" in fixed_node:
             original_name = fixed_node["name"]
             fixed_name = self._convert_to_pascal_case(original_name)
             
             if fixed_name != original_name:
                 logger.info(f"修正节点名称格式: {original_name} -> {fixed_name}")
                 fixed_node["name"] = fixed_name
         
         return fixed_node
     
    def _convert_to_pascal_case(self, name: str) -> str:
         """将名称转换为PascalCase格式"""
         if not name:
             return name
         
         # 移除非字母数字字符
         import re
         clean_name = re.sub(r'[^a-zA-Z0-9]', '', name)
         
         # 如果名称为空，返回默认名称
         if not clean_name:
             return "DefaultNode"
         
         # 确保第一个字符是大写字母
         if not clean_name[0].isupper():
             clean_name = clean_name[0].upper() + clean_name[1:]
         
         return clean_name
     
    def _ensure_unique_node_names(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
         """确保节点名称唯一性"""
         import copy
         
         logger.info("开始检查并修复节点名称重复...")
         
         unique_nodes = []
         used_names = set()
         
         for node in nodes:
             original_name = node.get("name", "UnknownNode")
             unique_name = self._generate_unique_name(original_name, used_names)
             
             if unique_name != original_name:
                 logger.info(f"修复重复节点名称: {original_name} -> {unique_name}")
                 # 更新节点名称
                 updated_node = copy.deepcopy(node)
                 updated_node["name"] = unique_name
                 
                 # 更新其他节点中对此节点的引用
                 self._update_node_references_in_list(unique_nodes, original_name, unique_name)
                 
                 unique_nodes.append(updated_node)
             else:
                 unique_nodes.append(node)
             
             used_names.add(unique_name)
         
         logger.info("节点名称唯一性检查完成")
         return unique_nodes
     
    def _generate_unique_name(self, base_name: str, used_names: set) -> str:
         """生成唯一的节点名称"""
         if base_name not in used_names:
             return base_name
         
         # 如果名称重复，添加数字后缀
         counter = 1
         while f"{base_name}{counter}" in used_names:
             counter += 1
         
         return f"{base_name}{counter}"
     
    def _update_node_references_in_list(self, nodes: List[Dict[str, Any]], old_name: str, new_name: str):
         """更新节点列表中对指定节点的引用"""
         import copy
         
         for node in nodes:
             # 更新inputs中的引用
             if "inputs" in node:
                 for input_config in node["inputs"].values():
                     if isinstance(input_config, dict) and "value" in input_config:
                         if isinstance(input_config["value"], str):
                             input_config["value"] = input_config["value"].replace(f"$.{old_name}.", f"$.{new_name}.")
             
             # 更新outputs中的引用
             if "outputs" in node:
                 for output_config in node["outputs"].values():
                     if isinstance(output_config, dict) and "value" in output_config:
                         if isinstance(output_config["value"], str):
                             output_config["value"] = output_config["value"].replace(f"$.{old_name}.", f"$.{new_name}.")
             
             # 更新nextNodes中的引用
             if "nextNodes" in node:
                 node["nextNodes"] = [new_name if name == old_name else name for name in node["nextNodes"]]
             
             # 更新configs中的引用（特别是条件节点）
             if "configs" in node:
                 self._update_config_references_for_rename(node["configs"], old_name, new_name)
     
    def _update_config_references_for_rename(self, configs: dict, old_name: str, new_name: str):
         """更新配置中的节点引用"""
         def update_value(obj):
             if isinstance(obj, str):
                 return obj.replace(f"$.{old_name}.", f"$.{new_name}.")
             elif isinstance(obj, dict):
                 for key, value in obj.items():
                     obj[key] = update_value(value)
                 return obj
             elif isinstance(obj, list):
                 return [update_value(item) for item in obj]
             else:
                 return obj
         
         # 递归更新所有配置值
         for key, value in configs.items():
             configs[key] = update_value(value)
     
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
        # 确保所有目标名称都以大写字母开头，采用PascalCase格式
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
        """解析LLM响应 - 增强版"""
        if not response or len(response.strip()) == 0:
            raise ValueError("LLM响应为空")
        
        try:
            # 🎯 多种方式尝试提取JSON
            json_str = None
            
            # 方式1: 尝试从Markdown代码块中提取
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                if json_end > json_start:
                    json_str = response[json_start:json_end].strip()
                    logger.info("🔍 从```json代码块中提取JSON")
            
            # 方式2: 尝试从普通代码块中提取
            elif "```" in response and json_str is None:
                lines = response.split('\n')
                in_code_block = False
                json_lines = []
                
                for line in lines:
                    if line.strip().startswith("```"):
                        if in_code_block:
                            break  # 结束代码块
                        else:
                            in_code_block = True  # 开始代码块
                            continue
                    
                    if in_code_block:
                        json_lines.append(line)
                
                if json_lines:
                    json_str = '\n'.join(json_lines).strip()
                    logger.info("🔍 从普通代码块中提取JSON")
            
            # 方式3: 尝试找到大括号包围的JSON
            if json_str is None:
                # 寻找第一个 { 和最后一个 }
                first_brace = response.find('{')
                last_brace = response.rfind('}')
                
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_str = response[first_brace:last_brace + 1].strip()
                    logger.info("🔍 从大括号中提取JSON")
            
            # 方式4: 直接尝试解析整个响应
            if json_str is None:
                json_str = response.strip()
                logger.info("🔍 直接解析整个响应")
            
            # 🎯 记录提取的JSON用于调试
            json_preview = json_str[:300] + "..." if len(json_str) > 300 else json_str
            logger.info(f"🔍 提取的JSON预览: {json_preview}")
            
            # 尝试解析JSON
            result = json.loads(json_str)
            logger.info("✅ JSON解析成功")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析LLM响应JSON失败: {str(e)}")
            logger.error(f"❌ 尝试解析的JSON字符串: {json_str[:500] if json_str else 'None'}...")
            
            # 🎯 提供更详细的错误信息
            if json_str:
                error_line = e.lineno if hasattr(e, 'lineno') else 'unknown'
                error_col = e.colno if hasattr(e, 'colno') else 'unknown'
                logger.error(f"❌ JSON错误位置: 行 {error_line}, 列 {error_col}")
                
                # 显示错误附近的内容
                if hasattr(e, 'pos') and e.pos < len(json_str):
                    start = max(0, e.pos - 50)
                    end = min(len(json_str), e.pos + 50)
                    context = json_str[start:end]
                    logger.error(f"❌ 错误上下文: ...{context}...")
            
            raise ValueError(f"LLM响应格式不正确: {str(e)}")
    
        except Exception as e:
            logger.error(f"❌ 解析LLM响应时发生未知错误: {str(e)}")
            raise ValueError(f"LLM响应解析失败: {str(e)}")
    
    async def _validate_composition_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证组合结果 - 简化版本（只检查连接关系）"""
        # 检查必需字段
        if "workflow" not in result:
            raise ValueError("组合结果缺少workflow字段")
        
        workflow = result["workflow"]
        
        # # 检查工作流必需字段
        # required_fields = ["name", "description", "version", "nodes"]
        # for field in required_fields:
        #     if field not in workflow:
        #         raise ValueError(f"工作流缺少必需字段: {field}")
        
        # 验证节点
        nodes = workflow["nodes"]
        if not nodes:
            raise ValueError("工作流必须包含至少一个节点")
        
        # 检查节点名称唯一性
        node_names = [node["name"] for node in nodes]
        if len(node_names) != len(set(node_names)):
            raise ValueError("节点名称必须唯一")
        
        # 🎯 暂时注释掉单个节点验证，只保留连接关系验证
        # for node in nodes:
        #     self._validate_node(node)
        
        # 🎯 只验证节点连接关系（nextNodes 引用是否正确）
        self._validate_node_connections(nodes)
        
        # 🎯 验证数据引用并尝试自动修复
        data_reference_errors = self._validate_data_references(nodes)
        if data_reference_errors:
            logger.warning(f"发现 {len(data_reference_errors)} 个数据引用错误:")
            for error in data_reference_errors:
                logger.warning(f"  - {error}")
            
            # 🎯 收集问题并尝试LLM修复
            try:
                logger.info("🔧 正在调用LLM自动修复数据引用错误...")
                corrected_workflow = await self._fix_data_reference_errors_with_llm(workflow, data_reference_errors)
                if corrected_workflow:
                    result["workflow"] = corrected_workflow
                    logger.info("✅ LLM修复完成，重新验证...")
                    
                    # 重新验证修复后的工作流
                    corrected_nodes = corrected_workflow["nodes"]
                    corrected_errors = self._validate_data_references(corrected_nodes)
                    if corrected_errors:
                        logger.warning(f"修复后仍有 {len(corrected_errors)} 个问题:")
                        for error in corrected_errors[:5]:  # 只显示前5个
                            logger.warning(f"  - {error}")
                    else:
                        logger.info("🎉 所有数据引用错误已修复！")
                else:
                    logger.warning("⚠️ LLM修复失败，尝试基础自动修复...")
                    
                    # 🎯 基础自动修复作为回退方案
                    try:
                        basic_fixed_workflow = self._apply_basic_fixes(workflow, data_reference_errors)
                        if basic_fixed_workflow:
                            result["workflow"] = basic_fixed_workflow
                            logger.info("✅ 基础自动修复完成")
                            
                            # 验证基础修复结果
                            basic_fixed_nodes = basic_fixed_workflow["nodes"]
                            basic_fixed_errors = self._validate_data_references(basic_fixed_nodes)
                            if basic_fixed_errors:
                                logger.warning(f"基础修复后仍有 {len(basic_fixed_errors)} 个问题")
                            else:
                                logger.info("🎉 基础修复成功，所有问题已解决！")
                        else:
                            logger.warning("⚠️ 基础自动修复也失败，继续使用原工作流")
                    except Exception as basic_fix_error:
                        logger.error(f"❌ 基础自动修复出错: {str(basic_fix_error)}")
                        logger.warning("⚠️ 继续使用原工作流")
            except Exception as e:
                logger.error(f"❌ LLM修复过程中出错: {str(e)}")
                logger.warning("⚠️ 继续使用原工作流")
        
        logger.info("✅ 工作流验证通过（简化模式：仅检查连接关系）")
        
        return result
    
    def _validate_node(self, node: Dict[str, Any]) -> None:
        """验证单个节点 - 动态验证版本"""
        node_type = node.get("type", "unknown")
        node_name = node.get("name", "unknown")
        
        # 🎯 使用动态方法获取必需字段
        required_fields = self._get_node_required_fields(node_type)
        
        for field in required_fields:
            if field not in node:
                raise ValueError(f"节点 {node_name} 缺少必需字段: {field}")
        
        # 🎯 使用动态方法验证节点类型
        if not self._validate_node_type_dynamically(node_type):
            raise ValueError(f"不支持的节点类型: {node_type}")
            
        # 🎯 使用动态方法获取特殊规则
        special_rules = self._get_node_special_rules(node_type)
        
        # 验证特殊规则
        if special_rules.get('no_outputs', False) and "outputs" in node:
            raise ValueError(f"节点 {node_name} (类型: {node_type}) 不应该包含outputs字段")
        
        if special_rules.get('no_nextNodes', False) and "nextNodes" in node:
            raise ValueError(f"节点 {node_name} (类型: {node_type}) 不应该包含nextNodes字段")
        
        if special_rules.get('nextNodes_must_be_end', False):
            next_nodes = node.get("nextNodes", [])
            if next_nodes != ["end"]:
                raise ValueError(f"节点 {node_name} (类型: {node_type}) 的nextNodes必须是['end']")
    
    def _validate_node_connections(self, nodes: List[Dict[str, Any]]) -> None:
        """验证节点连接关系 - 动态验证版本"""
        node_names = {node["name"] for node in nodes}
        
        # 🎯 使用动态方法检查起始节点
        start_nodes = [node for node in nodes if node_type_manager.is_start_node(node.get("type", ""))]
        start_type_name = node_type_manager.find_start_node_type() or "开始"
        
        if len(start_nodes) != 1:
            raise ValueError(f"工作流必须包含且仅包含一个{start_type_name}节点")
        
        # 🎯 使用动态方法检查结束节点  
        end_nodes = [node for node in nodes if node_type_manager.is_end_node(node.get("type", ""))]
        end_type_name = node_type_manager.find_end_node_type() or "结束"
        
        if len(end_nodes) == 0:
            raise ValueError(f"工作流必须至少包含一个{end_type_name}节点")
        
        # 验证nextNodes引用
        for node in nodes:
            node_type = node.get("type", "")
            node_name = node.get("name", "unknown")

            
            # 🎯 使用动态方法检查特殊规则
            special_rules = self._get_node_special_rules(node_type)
            if special_rules.get('no_nextNodes', False):
                # 有些节点类型不包含nextNodes字段，跳过验证
                continue
            else:
                # 验证nextNodes引用
                next_nodes = node.get("nextNodes", [])
                for next_node in next_nodes:
                    if next_node != "end" and next_node not in node_names:
                        raise ValueError(f"节点 {node_name} 的nextNodes引用了不存在的节点: {next_node}")
    
    def _validate_data_references(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """验证数据引用的正确性 - 确保引用的字段在前置节点的输出中确实存在"""
        errors = []
        suggestions = []
        
        # 构建节点映射
        node_map = {node.get("name", f"node_{i}"): node for i, node in enumerate(nodes)}
        
        for node in nodes:
            node_name = node.get("name", "unknown")
            
            # 检查 inputs 中的数据引用
            inputs = node.get("inputs", {})
            for input_name, input_config in inputs.items():
                if isinstance(input_config, dict) and "value" in input_config:
                    value = input_config["value"]
                    if isinstance(value, str) and value.startswith("$."):
                        # 解析数据引用路径 $.NodeName.outputs.fieldName
                        ref_errors, ref_suggestions = self._validate_single_data_reference_with_suggestions(
                            value, node_map, node_name
                        )
                        errors.extend(ref_errors)
                        suggestions.extend(ref_suggestions)
            
            # 检查 condition 节点的条件引用
            if node.get("type") == "condition":
                configs = node.get("configs", {})
                condition_groups = configs.get("conditionGroups", [])
                for group in condition_groups:
                    conditions = group.get("conditions", [])
                    for condition in conditions:
                        left_value = condition.get("left", "")
                        if isinstance(left_value, str) and left_value.startswith("$."):
                            ref_errors, ref_suggestions = self._validate_single_data_reference_with_suggestions(
                                left_value, node_map, node_name
                            )
                            errors.extend(ref_errors)
                            suggestions.extend(ref_suggestions)
        
        # 将建议添加到错误列表中
        errors.extend(suggestions)
        return errors
    
    def _validate_single_data_reference_with_suggestions(self, reference: str, node_map: Dict[str, Any], current_node: str) -> Tuple[List[str], List[str]]:
        """验证单个数据引用并提供智能建议"""
        errors = []
        suggestions = []
        
        try:
            # 解析引用路径：$.NodeName.outputs.fieldName
            parts = reference.split(".")
            if len(parts) < 4:  # 至少需要 $, NodeName, outputs, fieldName
                errors.append(f"节点 {current_node} 中的数据引用格式不正确: {reference}")
                return errors, suggestions
            
            referenced_node_name = parts[1]
            section = parts[2]  # 通常是 "outputs" 或 "inputs"
            field_path = ".".join(parts[3:])  # 字段路径，可能有嵌套
            
            # 检查引用的节点是否存在
            if referenced_node_name not in node_map:
                errors.append(f"节点 {current_node} 引用了不存在的节点: {referenced_node_name} (在 {reference})")
                return errors, suggestions
            
            referenced_node = node_map[referenced_node_name]
            
            # 检查引用的 section 是否存在
            if section not in referenced_node:
                errors.append(f"节点 {current_node} 引用了 {referenced_node_name} 不存在的section: {section} (在 {reference})")
                
                # 🎯 智能建议：如果是开始节点引用outputs，建议改为inputs
                if section == "outputs" and node_type_manager.is_start_node(referenced_node.get("type", "")):
                    suggestions.append(f"💡 建议: {referenced_node_name} 是开始节点，应使用 inputs 而不是 outputs")
                    suggestions.append(f"   修复: {reference} → $.{referenced_node_name}.inputs.{field_path}")
                
                return errors, suggestions
            
            # 检查字段是否存在（只检查第一级字段）
            section_data = referenced_node[section]
            if isinstance(section_data, dict):
                first_field = parts[3] if len(parts) > 3 else ""
                if first_field and first_field not in section_data:
                    errors.append(f"节点 {current_node} 引用了 {referenced_node_name}.{section} 中不存在的字段: {first_field} (在 {reference})")
                    
                    # 提供可用字段建议
                    available_fields = list(section_data.keys())
                    if available_fields:
                        errors.append(f"  可用字段: {', '.join(available_fields)}")
                    
                    # 🎯 智能建议：特殊处理数据库查询节点
                    if referenced_node.get("type") == "dbQuery":
                        suggestions.extend(self._generate_db_query_suggestions(
                            referenced_node, current_node, first_field, reference
                        ))
        
        except Exception as e:
            errors.append(f"节点 {current_node} 中的数据引用解析失败: {reference} - {str(e)}")
        
        return errors, suggestions
    
    def _generate_db_query_suggestions(self, query_node: Dict[str, Any], current_node: str, missing_field: str, original_ref: str) -> List[str]:
        """为数据库查询节点生成智能建议"""
        suggestions = []
        node_name = query_node.get("name", "")
        
        # 解析SQL获取可用字段
        result_info = self._infer_query_result_structure(query_node)
        data_fields = result_info.get("data_fields", [])
        
        # 如果缺失的字段明显是想要判断存在性
        existence_indicators = ["exists", "found", "valid", "success", "id", "count"]
        if any(indicator in missing_field.lower() for indicator in existence_indicators):
            suggestions.append(f"💡 建议: 用查询结果数量判断 {missing_field}")
            suggestions.append(f"   修复: {original_ref} → $.{node_name}.outputs.affected")
            suggestions.append(f"   条件: $.{node_name}.outputs.affected > 0")
        
        # 如果SQL中有对应的字段
        if data_fields and missing_field.lower() in [f.lower() for f in data_fields]:
            matching_field = next(f for f in data_fields if f.lower() == missing_field.lower())
            suggestions.append(f"💡 建议: 从查询结果数组中获取 {missing_field}")  
            suggestions.append(f"   修复: {original_ref} → $.{node_name}.outputs.data[0].{matching_field}")
        
        # 如果有相似的字段名
        if data_fields:
            similar_fields = [f for f in data_fields if missing_field.lower() in f.lower() or f.lower() in missing_field.lower()]
            if similar_fields:
                suggestions.append(f"💡 建议: 可能想要的字段: {', '.join(similar_fields)}")
                for field in similar_fields[:2]:  # 最多显示2个建议
                    suggestions.append(f"   修复: {original_ref} → $.{node_name}.outputs.data[0].{field}")
        
        return suggestions
    
    def _validate_single_data_reference(self, reference: str, node_map: Dict[str, Any], current_node: str) -> List[str]:
        """验证单个数据引用 - 兼容性方法"""
        errors, _ = self._validate_single_data_reference_with_suggestions(reference, node_map, current_node)
        return errors
    
    async def _fix_data_reference_errors_with_llm(self, workflow: Dict[str, Any], errors: List[str]) -> Optional[Dict[str, Any]]:
        """使用LLM自动修复数据引用错误"""
        try:
            # 分析错误并构造修复提示
            error_summary = self._analyze_data_reference_errors(errors)
            
            system_prompt = """# 工作流数据引用修复专家

你是一个专业的工作流数据引用修复专家，负责修复工作流中的数据引用错误。

## 你的任务
根据检测到的数据引用错误，修复工作流JSON中的错误引用，确保：
1. 所有数据引用路径正确
2. 引用的字段在前置节点的输出中确实存在  
3. 保持业务逻辑的完整性
4. 理解SQL查询结果的字段结构

## 数据库查询节点的输出结构

所有数据库查询节点（dbQuery、dbCreate、dbUpdate、dbDelete）都有固定的输出结构：
```json
{
  "outputs": {
    "data": {
      "type": "array", 
      "desc": "查询结果数组，每项包含SQL SELECT子句中的字段"
    },
    "affected": {
      "type": "number",
      "desc": "受影响的行数"
    }
  }
}
```

## SQL字段解析规则

从SQL语句解析可用字段：
- `SELECT id, name, status FROM users` → data[0] 包含: {id, name, status}
- `SELECT u.id as user_id, u.name FROM users u` → data[0] 包含: {user_id, name}
- `SELECT * FROM products` → data[0] 包含表的所有字段

## 修复规则

### 1. 开始节点引用问题
❌ 错误：`$.StartNode.{{outputs}}.field`
✅ 正确：`$.StartNode.{{inputs}}.field`

### 2. 存在性检查（推荐方式）
❌ 错误：`$.QuerySupplier.{{outputs}}.supplierExists`
✅ 正确：`$.QuerySupplier.{{outputs}}.affected > 0`
- 用查询结果行数判断记录是否存在，这是最可靠的方式

### 3. 获取查询结果中的具体字段
❌ 错误：`$.QuerySupplier.{{outputs}}.supplierId`
✅ 正确：`$.QuerySupplier.{{outputs}}.data[0].id`
- 从SQL `SELECT id, name, status FROM suppliers` 可知data[0]包含{{id, name, status}}

### 4. 条件节点的智能修复
```json
// 供应商存在性检查
{{
  "conditions": [
    {{
      "left": "$.QuerySupplier.{{outputs}}.affected",
      "operator": "greaterThan", 
      "right": 0
    }}
  ]
}}

// 状态检查（如果SQL包含status字段）
{{
  "conditions": [
    {{
      "left": "$.QuerySupplier.{{outputs}}.data[0].status",
      "operator": "equal",
      "right": "active"
    }}
  ]
}}
```

### 5. 字段名映射规则
- `supplierId` → `id` (主键通常是id)
- `supplierExists` → `affected > 0` (存在性检查)
- `productId` → `id` (主键通常是id)
- `isValid` → `affected > 0` or `status == 'active'`

## 输出格式
请直接输出修复后的完整工作流JSON，格式与输入保持一致。

## 注意事项
- 仔细分析每个节点的SQL语句，了解返回的字段结构
- 优先使用 `affected > 0` 进行存在性检查
- 从 `data[0].fieldName` 获取具体字段值
- 保持业务逻辑的合理性
- 确保所有数据引用都能在运行时正确解析"""

            # 分析工作流中的SQL字段结构
            sql_analysis = self._analyze_workflow_sql_structure(workflow)
            
            user_prompt = f"""请修复以下工作流中的数据引用错误：

## 检测到的错误问题
{chr(10).join(f"- {error}" for error in errors[:20])}  # 限制错误数量避免token过多

## 错误分析
{error_summary}

## SQL字段结构分析
{sql_analysis}

## 原始工作流JSON
```json
{json.dumps(workflow, ensure_ascii=False, indent=2)}
```

请根据SQL字段结构分析，修复所有数据引用错误，并提供修复后的完整工作流JSON。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 调用LLM
            response = await self.llm_client.chat_completion(
                messages=messages,
                max_tokens=8000,
                temperature=0.3
            )
            
            # 🎯 添加详细的调试信息
            logger.info(f"🔍 LLM修复响应长度: {len(response) if response else 0}")
            logger.info(f"🔍 LLM修复响应类型: {type(response)}")
            
            if not response:
                logger.error("❌ LLM修复响应为空")
                return None
            
            if len(response.strip()) == 0:
                logger.error("❌ LLM修复响应为空字符串")
                return None
            
            # 🎯 记录响应的前200个字符用于调试
            response_preview = response[:200] + "..." if len(response) > 200 else response
            logger.info(f"🔍 LLM修复响应预览: {response_preview}")
            
            # 解析LLM响应
            try:
                corrected_workflow = self._parse_llm_response(response)
            except Exception as e:
                logger.error(f"❌ LLM响应解析失败: {str(e)}")
                logger.error(f"❌ 原始响应内容: {response[:1000]}...")  # 记录前1000个字符
                return None
            
            # 🎯 验证修复结果的完整性
            if corrected_workflow:
                if "workflow" in corrected_workflow:
                    workflow_data = corrected_workflow["workflow"]
                    # 基本验证：确保包含必要字段
                    if "nodes" in workflow_data and isinstance(workflow_data["nodes"], list):
                        logger.info("✅ LLM修复成功，返回修复后的工作流")
                        return workflow_data
                    else:
                        logger.error("❌ LLM修复结果缺少有效的nodes字段")
                        return None
                elif "nodes" in corrected_workflow and isinstance(corrected_workflow["nodes"], list):
                    logger.info("✅ LLM修复成功，返回修复后的工作流（直接格式）")
                    return corrected_workflow
                else:
                    logger.error("❌ LLM修复结果格式不正确，缺少workflow或nodes字段")
                    logger.error(f"❌ 实际返回的字段: {list(corrected_workflow.keys()) if isinstance(corrected_workflow, dict) else '非字典格式'}")
                    return None
            else:
                logger.error("❌ LLM修复结果为空")
                return None
                
        except Exception as e:
            logger.error(f"❌ LLM修复过程中出错: {str(e)}")
            logger.error(f"❌ 错误类型: {type(e).__name__}")
            
            # 🎯 提供更具体的错误处理建议
            if "timeout" in str(e).lower():
                logger.error("💡 建议: LLM请求超时，可能需要减少输入内容或增加超时时间")
            elif "rate limit" in str(e).lower():
                logger.error("💡 建议: API调用频率限制，请稍后重试")
            elif "token" in str(e).lower():
                logger.error("💡 建议: Token数量可能超出限制，尝试减少输入内容")
            
            return None
    
    def _analyze_data_reference_errors(self, errors: List[str]) -> str:
        """分析数据引用错误的模式"""
        analysis = {
            "start_node_outputs": 0,
            "query_node_missing_fields": 0,
            "condition_reference_errors": 0,
            "field_not_exist": 0
        }
        
        for error in errors:
            if "StartStockIn 不存在的section: outputs" in error:
                analysis["start_node_outputs"] += 1
            elif "outputs 中不存在的字段" in error:
                analysis["query_node_missing_fields"] += 1
            elif "条件" in error or "condition" in error:
                analysis["condition_reference_errors"] += 1
            elif "不存在的字段" in error:
                analysis["field_not_exist"] += 1
        
        summary_parts = []
        if analysis["start_node_outputs"] > 0:
            summary_parts.append(f"开始节点outputs引用错误: {analysis['start_node_outputs']}个")
        if analysis["query_node_missing_fields"] > 0:
            summary_parts.append(f"查询节点字段引用错误: {analysis['query_node_missing_fields']}个")
        if analysis["condition_reference_errors"] > 0:
            summary_parts.append(f"条件节点引用错误: {analysis['condition_reference_errors']}个")
        if analysis["field_not_exist"] > 0:
            summary_parts.append(f"字段不存在错误: {analysis['field_not_exist']}个")
        
        return "； ".join(summary_parts) if summary_parts else "未识别的错误模式"
    
    def _analyze_workflow_sql_structure(self, workflow: Dict[str, Any]) -> str:
        """分析工作流中所有SQL语句的字段结构"""
        analysis_lines = []
        
        nodes = workflow.get("nodes", [])
        db_nodes = [node for node in nodes if node.get("type", "").startswith("db")]
        
        if not db_nodes:
            return "无数据库查询节点"
        
        analysis_lines.append("各节点SQL字段结构:")
        
        for node in db_nodes:
            node_name = node.get("name", "unknown")
            node_type = node.get("type", "")
            configs = node.get("configs", {})
            sql = configs.get("sql", "")
            table = configs.get("table", "")
            
            if sql:
                # 解析SQL字段
                fields = self._parse_sql_select_fields(sql)
                
                analysis_lines.append(f"\n📋 {node_name} ({node_type}):")
                analysis_lines.append(f"   表: {table}")
                analysis_lines.append(f"   SQL: {sql}")
                
                if fields:
                    if '*' in fields:
                        analysis_lines.append(f"   🔍 返回字段: 所有字段 (SELECT *)")
                        analysis_lines.append(f"   📦 data[0] 结构: 包含 {table} 表的所有字段")
                    else:
                        analysis_lines.append(f"   🔍 返回字段: {', '.join(fields)}")
                        analysis_lines.append(f"   📦 data[0] 结构: {{{', '.join(f'{field}: value' for field in fields)}}}")
                else:
                    analysis_lines.append(f"   ⚠️ 无法解析字段结构")
                
                # 添加输出结构说明
                analysis_lines.append(f"   📤 outputs.data: 查询结果数组")
                analysis_lines.append(f"   📤 outputs.affected: 查询行数 (用于存在性检查)")
                
                # 推荐的引用方式
                if fields and '*' not in fields:
                    analysis_lines.append(f"   💡 字段引用示例:")
                    for field in fields[:3]:  # 只显示前3个字段
                        analysis_lines.append(f"      $.{node_name}.outputs.data[0].{field}")
                
                analysis_lines.append(f"   💡 存在性检查: $.{node_name}.outputs.affected > 0")
        
        return "\n".join(analysis_lines)
    
    def _apply_basic_fixes(self, workflow: Dict[str, Any], errors: List[str]) -> Optional[Dict[str, Any]]:
        """应用基础的自动修复规则"""
        try:
            # 深拷贝工作流以避免修改原始数据
            import copy
            fixed_workflow = copy.deepcopy(workflow)
            nodes = fixed_workflow.get("nodes", [])
            
            # 构建节点映射
            node_map = {node.get("name", f"node_{i}"): node for i, node in enumerate(nodes)}
            
            fixes_applied = 0
            
            for node in nodes:
                node_name = node.get("name", "unknown")
                node_type = node.get("type", "")
                
                # 🎯 修复inputs中的数据引用
                if "inputs" in node:
                    fixes_applied += self._fix_node_inputs(node, node_map)
                
                # 🎯 修复condition节点的条件引用
                if node_type == "condition" and "configs" in node:
                    fixes_applied += self._fix_condition_node(node, node_map)
            
            if fixes_applied > 0:
                logger.info(f"✅ 基础修复应用了 {fixes_applied} 个修复")
                return fixed_workflow
            else:
                logger.warning("⚠️ 未应用任何基础修复")
                return None
                
        except Exception as e:
            logger.error(f"❌ 基础修复过程中出错: {str(e)}")
            return None
    
    def _fix_node_inputs(self, node: Dict[str, Any], node_map: Dict[str, Any]) -> int:
        """修复节点inputs中的数据引用"""
        fixes_count = 0
        inputs = node.get("inputs", {})
        
        for input_name, input_config in inputs.items():
            if isinstance(input_config, dict) and "value" in input_config:
                value = input_config["value"]
                if isinstance(value, str) and value.startswith("$."):
                    new_value = self._fix_single_reference(value, node_map)
                    if new_value != value:
                        input_config["value"] = new_value
                        fixes_count += 1
                        logger.info(f"🔧 修复引用: {value} → {new_value}")
        
        return fixes_count
    
    def _fix_condition_node(self, node: Dict[str, Any], node_map: Dict[str, Any]) -> int:
        """修复condition节点的条件引用"""
        fixes_count = 0
        configs = node.get("configs", {})
        condition_groups = configs.get("conditionGroups", [])
        
        for group in condition_groups:
            conditions = group.get("conditions", [])
            for condition in conditions:
                left_value = condition.get("left", "")
                if isinstance(left_value, str) and left_value.startswith("$."):
                    new_value = self._fix_single_reference(left_value, node_map)
                    if new_value != left_value:
                        condition["left"] = new_value
                        # 如果是存在性检查，调整操作符和右值
                        if ".outputs.affected" in new_value:
                            condition["operator"] = "greaterThan"
                            condition["right"] = 0
                        fixes_count += 1
                        logger.info(f"🔧 修复条件: {left_value} → {new_value}")
        
        return fixes_count
    
    def _fix_single_reference(self, reference: str, node_map: Dict[str, Any]) -> str:
        """修复单个数据引用 - 增强版"""
        try:
            parts = reference.split(".")
            if len(parts) < 4:
                return reference
            
            referenced_node_name = parts[1]
            section = parts[2]
            field_path = ".".join(parts[3:])
            
            if referenced_node_name not in node_map:
                return reference
            
            referenced_node = node_map[referenced_node_name]
            referenced_type = referenced_node.get("type", "")
            
            # 🎯 规则1: 开始节点的outputs改为inputs
            if section == "outputs" and node_type_manager.is_start_node(referenced_type):
                if "inputs" in referenced_node and field_path in referenced_node["inputs"]:
                    logger.info(f"🔧 修复开始节点引用: {reference} → $.{referenced_node_name}.inputs.{field_path}")
                    return f"$.{referenced_node_name}.inputs.{field_path}"
            
            # 🎯 规则2: 数据库查询节点的不存在字段修复
            if section == "outputs" and referenced_type == "dbQuery":
                outputs = referenced_node.get("outputs", {})
                if field_path not in outputs:
                    # 🎯 特殊处理：supplier/product/user等实体字段 → 改为存在性检查
                    entity_fields = ["supplier", "product", "user", "customer", "order", "item", "record"]
                    if any(entity in field_path.lower() for entity in entity_fields):
                        logger.info(f"🔧 修复实体引用为存在性检查: {reference} → $.{referenced_node_name}.outputs.affected")
                        return f"$.{referenced_node_name}.outputs.affected"
                    
                    # 🎯 常见的存在性检查字段名
                    existence_fields = ["exists", "found", "valid", "success", "isactive", "isenabled", "count"]
                    if any(keyword in field_path.lower() for keyword in existence_fields):
                        logger.info(f"🔧 修复存在性引用: {reference} → $.{referenced_node_name}.outputs.affected")
                        return f"$.{referenced_node_name}.outputs.affected"
                    
                    # 🎯 尝试从SQL中查找匹配的字段
                    result_info = self._infer_query_result_structure(referenced_node)
                    data_fields = result_info.get("data_fields", [])
                    
                    # 精确匹配
                    for db_field in data_fields:
                        if field_path.lower() == db_field.lower():
                            logger.info(f"🔧 修复字段引用: {reference} → $.{referenced_node_name}.outputs.data[0].{db_field}")
                            return f"$.{referenced_node_name}.outputs.data[0].{db_field}"
                    
                    # 模糊匹配
                    for db_field in data_fields:
                        if field_path.lower() in db_field.lower() or db_field.lower() in field_path.lower():
                            logger.info(f"🔧 修复相似字段引用: {reference} → $.{referenced_node_name}.outputs.data[0].{db_field}")
                            return f"$.{referenced_node_name}.outputs.data[0].{db_field}"
                    
                    # 🎯 如果都没匹配到，默认使用存在性检查
                    logger.info(f"🔧 无匹配字段，修复为存在性检查: {reference} → $.{referenced_node_name}.outputs.affected")
                    return f"$.{referenced_node_name}.outputs.affected"
            
            return reference
            
        except Exception as e:
            logger.warning(f"⚠️ 修复单个引用失败: {reference} - {str(e)}")
            return reference
    
    async def _handle_retry(self, retry_data: Dict[str, Any]) -> None:
        """处理重试请求"""
        logger.info("收到重试请求，开始重新组合工作流")
        await self._execute_task(retry_data) 