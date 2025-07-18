"""
工作流验证智能体 (Workflow Validator Agent)
负责验证生成的工作流JSON是否符合规范和要求
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType
from node_type_manager import node_type_manager

logger = logging.getLogger(__name__)


class WorkflowValidator(BaseAgent):
    """工作流验证智能体"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.WORKFLOW_VALIDATOR, message_bus, state_manager)
        self.llm_client = llm_client
        self.validation_rules = self._load_validation_rules()
        # 节点DSL数据将在process_task时从共享上下文获取
        self.node_dsl_data = {}
    
    async def _load_node_dsl_from_context(self):
        """从共享上下文获取节点DSL数据"""
        try:
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            if node_dsl_data:
                self.node_dsl_data = node_dsl_data
                logger.info(f"✅ WorkflowValidator从共享上下文获取 {len(node_dsl_data)} 个节点DSL数据")
                
                # 更新验证规则中的有效节点类型
                valid_node_types = list(node_dsl_data.keys())
                if valid_node_types:
                    self.validation_rules["structure_rules"]["valid_node_types"] = valid_node_types
                    logger.info(f"📋 更新有效节点类型: {', '.join(valid_node_types)}")
                    
            else:
                logger.warning("⚠️ WorkflowValidator共享上下文中没有节点DSL数据，使用默认验证规则")
                
        except Exception as e:
            logger.error(f"❌ WorkflowValidator从共享上下文获取节点DSL数据失败: {str(e)}")

    def _load_validation_rules(self) -> Dict[str, Any]:
        """加载验证规则"""
        return {
            "structure_rules": {
                "required_workflow_fields": ["name", "description", "version", "nodes"],
                "required_node_fields": ["name", "type", "desc", "inputs", "outputs", "configs", "nextNodes"],
                "valid_node_types": [
                    "workflowStart", "workflowEnd", "dbQuery", "dbCreate", "dbUpdate", 
                    "dbDelete", "transaction", "batch", "condition", "workflow", 
                    "http", "chatWithLLM", "code"
                ]
            },
            "business_rules": {
                "must_have_start_node": True,
                "must_have_end_node": True,
                "unique_node_names": True,
                "valid_data_references": True,
                "connected_workflow": True
            },
            "node_specific_rules": {
                "workflowStart": {
                    "required_configs": [],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "workflowEnd": {
                    "required_configs": [],
                    "required_outputs": ["code", "data", "message"],
                    "nextNodes_rules": "must_be_end"
                },
                "dbQuery": {
                    "required_configs": ["table", "sql"],
                    "required_outputs": ["affected", "data"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "dbCreate": {
                    "required_configs": ["table", "sql"],
                    "required_outputs": ["affected", "insertId"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "dbUpdate": {
                    "required_configs": ["table", "sql"],
                    "required_outputs": ["affected"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "dbDelete": {
                    "required_configs": ["table", "sql"],
                    "required_outputs": ["affected"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "transaction": {
                    "required_configs": ["children"],
                    "required_outputs": ["committed", "affectedTotal", "childResults", "executionTime"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "batch": {
                    "required_configs": ["mapConfig", "reduceConfig", "child"],
                    "required_outputs": ["totalProcessed", "successCount", "failureCount", "aggregatedResult", "executionTime"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "condition": {
                    "required_configs": ["conditionGroups"],
                    "no_outputs": True,
                    "no_nextNodes": True
                },
                "workflow": {
                    "required_configs": ["workflowId", "inputMappings", "outputMappings"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "http": {
                    "required_configs": ["method", "url"],
                    "required_outputs": ["code", "data"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "chatWithLLM": {
                    "required_configs": ["modelId"],
                    "required_outputs": ["thinking", "response", "tokens"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "code": {
                    "required_configs": ["file"],
                    "nextNodes_rules": "must_not_be_empty"
                }
            }
        }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """# 工作流验证专家

你是一个专业的工作流验证专家，负责全面验证工作流JSON配置的正确性、完整性和可执行性。

## 你的任务
1. 检查工作流的结构完整性
2. 验证节点配置的正确性
3. 检查数据流的一致性
4. 验证业务逻辑的合理性
5. 识别潜在的执行问题

## 验证维度
### 1. 结构验证
- 必需字段完整性
- 节点类型有效性
- 数据类型正确性
- JSON格式规范性

### 2. 配置验证
- 节点配置完整性
- 数据库操作配置（表名、字段等）
- HTTP请求配置（方法、URL等）
- 条件判断配置（条件组、操作符等）

### 3. 逻辑验证
- 工作流连通性
- 数据流一致性
- 节点连接关系
- 业务逻辑完整性

### 4. 可执行性验证
- 数据引用路径正确性
- 节点依赖关系合理性
- 循环引用检测
- 死链检测

## 验证输出格式
请严格按照以下JSON格式输出验证结果：
```json
{
  "validation_result": {
    "is_valid": true/false,
    "overall_score": 0-100,
    "error_count": 数字,
    "warning_count": 数字
  },
  "detailed_results": {
    "structure_validation": {
      "passed": true/false,
      "errors": ["错误描述"],
      "warnings": ["警告描述"]
    },
    "configuration_validation": {
      "passed": true/false,
      "errors": ["错误描述"],
      "warnings": ["警告描述"]
    },
    "logic_validation": {
      "passed": true/false,
      "errors": ["错误描述"],
      "warnings": ["警告描述"]
    },
    "executability_validation": {
      "passed": true/false,
      "errors": ["错误描述"],
      "warnings": ["警告描述"]
    }
  },
  "suggestions": [
    {
      "type": "error/warning/optimization",
      "description": "建议描述",
      "node": "相关节点名称",
      "solution": "解决方案"
    }
  ],
  "compliance_check": {
    "node_specification_compliance": true/false,
    "data_flow_compliance": true/false,
    "business_logic_compliance": true/false
  }
}
```

## 验证原则
1. **零容忍错误**: 任何结构性错误都会导致验证失败
2. **警告不阻塞**: 警告不会导致验证失败，但会影响评分
3. **全面检查**: 检查所有可能的问题点
4. **建设性建议**: 提供具体的改进建议

## 评分标准
- 100分: 完美工作流，无错误无警告
- 80-99分: 良好工作流，无错误但有少量警告
- 60-79分: 可接受工作流，有少量错误或较多警告
- 60分以下: 不合格工作流，有严重错误

## 注意事项
- 仔细检查每个节点的配置完整性
- 验证数据引用路径的正确性
- 确保工作流的执行路径是完整的
- 检查业务逻辑的合理性
- 提供具体的修复建议"""
    
    def _get_user_prompt(self, workflow: Dict[str, Any], user_requirement: str) -> str:
        """获取用户提示词"""
        return f"""请对以下工作流进行全面验证：

**用户原始需求：**
{user_requirement}

**待验证的工作流：**
{json.dumps(workflow, ensure_ascii=False, indent=2)}

**验证规则参考：**
{json.dumps(self.validation_rules, ensure_ascii=False, indent=2)}

请按照验证专家的标准，对工作流进行全面的验证，并提供详细的验证报告和改进建议。"""
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理工作流验证任务"""
        try:
            # 🎯 从共享上下文加载节点DSL数据
            await self._load_node_dsl_from_context()
            
            # 获取共享上下文
            context = await self.state_manager.get_context()
            workflow = context.composed_workflow
            user_requirement = context.user_requirement
            
            logger.info("开始验证工作流")
            
            # 执行全面验证
            validation_results = self._perform_comprehensive_validation(workflow)
            
            # 更新共享上下文
            errors = []
            for category, result in validation_results["detailed_results"].items():
                errors.extend(result.get("errors", []))
            
            await self.state_manager.update_context({
                "validation_errors": errors
            })
            
            # 记录生成历史
            await self.state_manager.add_generation_history(
                "workflow_validation",
                validation_results
            )
            
            logger.info(f"工作流验证完成，是否通过: {validation_results['validation_result']['is_valid']}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"工作流验证失败: {str(e)}")
            raise
    
    def _perform_comprehensive_validation(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """执行全面验证"""
        # 1. 结构验证
        structure_result = self._validate_structure(workflow)
        
        # 2. 配置验证
        config_result = self._validate_configuration(workflow)
        
        # 3. 逻辑验证
        logic_result = self._validate_logic(workflow)
        
        # 4. 可执行性验证
        executability_result = self._validate_executability(workflow)
        
        # 5. 节点引用验证
        reference_result = self._validate_node_references(workflow)
        
        # 合并验证结果
        return self._merge_validation_results(
            structure_result,
            config_result,
            logic_result,
            executability_result,
            reference_result
        )
    
    def _validate_structure(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流结构"""
        errors = []
        warnings = []
        
        # 检查工作流必需字段
        for field in self.validation_rules["structure_rules"]["required_workflow_fields"]:
            if field not in workflow:
                errors.append(f"工作流缺少必需字段: {field}")
        
                 # 检查工作流名称是否使用英文且以大写字母开头
        if "name" in workflow:
             workflow_name = workflow["name"]
             if not self._is_english_name(workflow_name):
                 errors.append(f"工作流名称 '{workflow_name}' 必须使用英文且以大写字母开头，采用PascalCase格式（如：UserRegistrationWorkflow）")
        
        # 检查节点
        if "nodes" in workflow:
            nodes = workflow["nodes"]
            
            # 检查节点数量
            if len(nodes) < 2:
                errors.append("工作流必须至少包含开始节点和结束节点")
            
            # 检查每个节点的结构
            for i, node in enumerate(nodes):
                node_errors = self._validate_node_structure(node, i)
                errors.extend(node_errors)
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_node_structure(self, node: Dict[str, Any], index: int) -> List[str]:
        """验证节点结构"""
        errors = []
        
        # 检查节点必需字段
        for field in self.validation_rules["structure_rules"]["required_node_fields"]:
            if field not in node:
                errors.append(f"节点 {index} 缺少必需字段: {field}")
        
        # 检查节点类型
        if "type" in node:
            if node["type"] not in self.validation_rules["structure_rules"]["valid_node_types"]:
                errors.append(f"节点 {node.get('name', index)} 的类型 {node['type']} 无效")
        
                 # 检查节点名称是否使用英文且以大写字母开头
        if "name" in node:
             node_name = node["name"]
             if not self._is_english_name(node_name):
                 errors.append(f"节点 '{node_name}' 的名称必须使用英文且以大写字母开头，采用PascalCase格式（如：QueryUser、CreateOrder）")
        
        return errors
    
    def _validate_configuration(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证节点配置"""
        errors = []
        warnings = []
        
        if "nodes" not in workflow:
            return {"passed": False, "errors": ["工作流缺少nodes字段"], "warnings": []}
        
        for node in workflow["nodes"]:
            node_errors, node_warnings = self._validate_node_configuration(node)
            errors.extend(node_errors)
            warnings.extend(node_warnings)
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_node(self, node: Dict[str, Any]) -> None:
        """验证单个节点"""
        # 检查必需字段，但根据节点类型决定是否需要outputs和nextNodes
        required_fields = ["name", "type", "desc", "inputs", "configs"]
        
        # 检查是否需要outputs字段
        node_type = node.get("type")
        rules = self.validation_rules["node_specific_rules"].get(node_type, {})
        needs_outputs = not rules.get("no_outputs", False)
        needs_nextNodes = not rules.get("no_nextNodes", False)
        
        if needs_outputs:
            required_fields.append("outputs")
        if needs_nextNodes:
            required_fields.append("nextNodes")
        
        for field in required_fields:
            if field not in node:
                raise ValueError(f"节点 {node.get('name', 'unknown')} 缺少必需字段: {field}")
        
        # 验证节点类型
        if node["type"] not in self.validation_rules["structure_rules"]["valid_node_types"]:
            raise ValueError(f"不支持的节点类型: {node['type']}")
        
        # 验证节点特定配置
        if node["type"] in self.validation_rules["node_specific_rules"]:
            rules = self.validation_rules["node_specific_rules"][node["type"]]
            
            # 检查必需配置
            if "required_configs" in rules:
                for config in rules["required_configs"]:
                    if config not in node.get("configs", {}):
                        raise ValueError(f"节点 {node['name']} 缺少必需配置: {config}")
                    elif not node["configs"][config]:
                        # 对于某些字段允许为空数组或空对象
                        if config in ["children", "inputMappings", "outputMappings"] and isinstance(node["configs"][config], (list, dict)):
                            continue
                        raise ValueError(f"节点 {node['name']} 的配置 {config} 不能为空")
            
            # 检查必需输出字段 (仅对需要outputs的节点)
            if needs_outputs and "required_outputs" in rules:
                for output_field in rules["required_outputs"]:
                    if output_field not in node.get("outputs", {}):
                        raise ValueError(f"节点 {node['name']} 缺少必需输出字段: {output_field}")
            
            # 检查不应该有outputs的节点
            if rules.get("no_outputs", False) and "outputs" in node:
                raise ValueError(f"节点 {node['name']} 不应该包含outputs字段")
            
            # 检查nextNodes规则
            if "nextNodes_rules" in rules:
                nextNodes = node.get("nextNodes", [])
                rule = rules["nextNodes_rules"]
                
                if rule == "must_not_be_empty" and not nextNodes:
                    raise ValueError(f"节点 {node['name']} 的nextNodes不能为空")
                elif rule == "must_be_end" and nextNodes != ["end"]:
                    raise ValueError(f"节点 {node['name']} 的nextNodes必须是['end']")
    
    def _validate_node_configuration(self, node: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """验证单个节点配置"""
        errors = []
        warnings = []
        
        node_name = node.get("name", "unknown")
        node_type = node.get("type", "unknown")
        
        # 检查节点特定配置
        if node_type in self.validation_rules["node_specific_rules"]:
            rules = self.validation_rules["node_specific_rules"][node_type]
            
            # 检查必需配置
            if "required_configs" in rules:
                for config in rules["required_configs"]:
                    if config not in node.get("configs", {}):
                        errors.append(f"节点 {node_name} 缺少必需配置: {config}")
                    elif not node["configs"][config]:
                        errors.append(f"节点 {node_name} 的配置 {config} 不能为空")
            
            # 检查nextNodes规则
            if "nextNodes_rules" in rules:
                nextNodes = node.get("nextNodes", [])
                rule = rules["nextNodes_rules"]
                
                if rule == "must_not_be_empty" and not nextNodes:
                    errors.append(f"节点 {node_name} 的nextNodes不能为空")
                elif rule == "must_be_end" and nextNodes != ["end"]:
                    errors.append(f"节点 {node_name} 的nextNodes必须是['end']")
        
        # 检查数据库节点特定配置
        if node_type.startswith("db"):
            self._validate_db_node_config(node, errors, warnings)
        
        # 检查HTTP节点特定配置
        if node_type == "http":
            self._validate_http_node_config(node, errors, warnings)
        
        # 检查条件节点特定配置
        if node_type == "condition":
            self._validate_condition_node_config(node, errors, warnings)
        
        return errors, warnings
    
    def _validate_db_node_config(self, node: Dict[str, Any], errors: List[str], warnings: List[str]):
        """验证数据库节点配置"""
        configs = node.get("configs", {})
        node_name = node.get("name", "unknown")
        
        # 检查表名
        if "table" in configs:
            table = configs["table"]
            if not isinstance(table, str) or not table.strip():
                errors.append(f"节点 {node_name} 的table配置必须是非空字符串")
        
        # 检查字段配置
        if "data" in configs:
            data = configs["data"]
            if not isinstance(data, dict):
                errors.append(f"节点 {node_name} 的data配置必须是对象")
            elif not data:
                warnings.append(f"节点 {node_name} 的data配置为空")
        
        # 检查过滤条件
        if "filters" in configs:
            filters = configs["filters"]
            if not isinstance(filters, list):
                errors.append(f"节点 {node_name} 的filters配置必须是数组")
    
    def _validate_http_node_config(self, node: Dict[str, Any], errors: List[str], warnings: List[str]):
        """验证HTTP节点配置"""
        configs = node.get("configs", {})
        node_name = node.get("name", "unknown")
        
        # 检查HTTP方法
        if "method" in configs:
            method = configs["method"]
            valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
            if method not in valid_methods:
                errors.append(f"节点 {node_name} 的method配置必须是有效的HTTP方法")
        
        # 检查URL
        if "url" in configs:
            url = configs["url"]
            if not isinstance(url, str) or not url.strip():
                errors.append(f"节点 {node_name} 的url配置必须是非空字符串")
    
    def _validate_condition_node_config(self, node: Dict[str, Any], errors: List[str], warnings: List[str]):
        """验证条件节点配置"""
        configs = node.get("configs", {})
        node_name = node.get("name", "unknown")
        
        # 检查conditionGroups配置
        if "conditionGroups" not in configs:
            errors.append(f"节点 {node_name} 缺少conditionGroups配置")
        elif not isinstance(configs["conditionGroups"], list):
            errors.append(f"节点 {node_name} 的conditionGroups配置必须是数组")
        elif not configs["conditionGroups"]:
            warnings.append(f"节点 {node_name} 的conditionGroups配置为空")
        else:
            valid_operators = [
                "equal", "notEqual", "greaterThan", "greaterThanEqual", 
                "lessThan", "lessThanEqual", "isNull", "isNotNull", 
                "include", "notInclude"
            ]
            
            for group_index, group in enumerate(configs["conditionGroups"]):
                # 检查条件组必需字段
                if "conditions" not in group:
                    errors.append(f"条件组 {group_index} 缺少conditions配置")
                elif not isinstance(group["conditions"], list):
                    errors.append(f"条件组 {group_index} 的conditions配置必须是数组")
                elif not group["conditions"]:
                    warnings.append(f"条件组 {group_index} 的conditions配置为空")
                else:
                    # 验证每个条件
                    for condition_index, condition in enumerate(group["conditions"]):
                        if "left" not in condition:
                            errors.append(f"条件组 {group_index} 的条件 {condition_index} 缺少left配置")
                        elif not isinstance(condition["left"], str):
                            errors.append(f"条件组 {group_index} 的条件 {condition_index} 的left配置必须是字符串")
                        
                        if "operator" not in condition:
                            errors.append(f"条件组 {group_index} 的条件 {condition_index} 缺少operator配置")
                        elif condition["operator"] not in valid_operators:
                            errors.append(f"条件组 {group_index} 的条件 {condition_index} 的operator配置无效，支持的操作符：{', '.join(valid_operators)}")
                        
                        if "right" not in condition:
                            errors.append(f"条件组 {group_index} 的条件 {condition_index} 缺少right配置")
                
                if "relationship" not in group:
                    errors.append(f"条件组 {group_index} 缺少relationship配置")
                elif group["relationship"] not in ["AND", "OR"]:
                    errors.append(f"条件组 {group_index} 的relationship配置必须是'AND'或'OR'")
                
                if "nextNode" not in group:
                    errors.append(f"条件组 {group_index} 缺少nextNode配置")
                elif not isinstance(group["nextNode"], str):
                    errors.append(f"条件组 {group_index} 的nextNode配置必须是字符串")
        
        # 检查defaultNextNode配置（可选）
        if "defaultNextNode" in configs:
            if not isinstance(configs["defaultNextNode"], str):
                errors.append(f"节点 {node_name} 的defaultNextNode配置必须是字符串")
            elif not configs["defaultNextNode"].strip():
                warnings.append(f"节点 {node_name} 的defaultNextNode配置为空字符串")
        
        # 检查条件节点不应该有nextNodes字段
        if "nextNodes" in node:
            errors.append(f"节点 {node_name} 不应该包含nextNodes字段，条件节点的流向由条件配置决定")
        
        # 检查条件节点不应该有outputs字段
        if "outputs" in node:
            errors.append(f"节点 {node_name} 不应该包含outputs字段，条件节点不产生数据输出")
        
    def _validate_logic(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流逻辑"""
        errors = []
        warnings = []
        
        if "nodes" not in workflow:
            return {"passed": False, "errors": ["工作流缺少nodes字段"], "warnings": []}
        
        nodes = workflow["nodes"]
        
        # 检查节点名称唯一性
        node_names = [node.get("name", f"node_{i}") for i, node in enumerate(nodes)]
        if len(node_names) != len(set(node_names)):
            # 找出重复的节点名称
            duplicates = []
            seen = set()
            for name in node_names:
                if name in seen and name not in duplicates:
                    duplicates.append(name)
                seen.add(name)
            errors.append(f"节点名称必须唯一，发现重复的节点名称: {', '.join(duplicates)}")
        
        # 检查起始和结束节点
        start_nodes = [node for node in nodes if node_type_manager.is_start_node(node.get("type", ""))]
        end_nodes = [node for node in nodes if node_type_manager.is_end_node(node.get("type", ""))]
        condition_nodes = [node for node in nodes if node.get("type") == "condition"]
        
        start_type_name = node_type_manager.find_start_node_type() or "开始"
        end_type_name = node_type_manager.find_end_node_type() or "结束"
        
        if len(start_nodes) != 1:
            errors.append(f"工作流必须包含且仅包含一个{start_type_name}节点")
        
        if len(end_nodes) == 0:
            errors.append(f"工作流必须至少包含一个{end_type_name}节点")
        elif len(end_nodes) > 1:
            # 如果有多个结束节点，检查是否有条件节点来合理化这种设计
            if len(condition_nodes) == 0:
                warnings.append(f"工作流包含{len(end_nodes)}个结束节点，但没有条件节点。建议使用条件节点来管理不同的结束路径")
            else:
                # 有条件节点的情况下，多个结束节点是合理的
                pass
        
        # 检查节点连接关系
        connectivity_errors = self._validate_connectivity(nodes)
        errors.extend(connectivity_errors)
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_connectivity(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """验证节点连通性"""
        errors = []
        
        # 构建节点映射
        node_map = {node.get("name", f"node_{i}"): node for i, node in enumerate(nodes)}
        node_names = set(node_map.keys())
        
        # 检查nextNodes引用
        for node in nodes:
            node_name = node.get("name", "unknown")
            next_nodes = node.get("nextNodes", [])
            
            for next_node in next_nodes:
                if next_node != "end" and next_node not in node_names:
                    errors.append(f"节点 {node_name} 引用了不存在的节点: {next_node}")
        
        return errors
    
    def _validate_executability(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证可执行性"""
        errors = []
        warnings = []
        
        if "nodes" not in workflow:
            return {"passed": False, "errors": ["工作流缺少nodes字段"], "warnings": []}
        
        nodes = workflow["nodes"]
        
        # 检查数据引用路径
        data_flow_errors = self._validate_data_flow(nodes)
        errors.extend(data_flow_errors)
        
        # 检查循环引用
        cycle_errors = self._detect_cycles(nodes)
        errors.extend(cycle_errors)
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_data_flow(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """验证数据流"""
        errors = []
        
        # 构建节点映射
        node_map = {node.get("name", f"node_{i}"): node for i, node in enumerate(nodes)}
        
        for node in nodes:
            node_name = node.get("name", "unknown")
            
            # 检查inputs中的数据引用
            inputs = node.get("inputs", {})
            for input_name, input_config in inputs.items():
                if isinstance(input_config, dict) and "value" in input_config:
                    value = input_config["value"]
                    if isinstance(value, str) and value.startswith("$"):
                        # 验证数据引用路径
                        if not self._is_valid_data_reference(value):
                            errors.append(f"节点 {node_name} 的输入 {input_name} 包含无效的数据引用: {value}")
        
        return errors
    
    def _is_valid_data_reference(self, reference: str) -> bool:
        """验证数据引用是否有效"""
        # 简单的数据引用验证
        if reference.startswith("$prevNode.outputs."):
            return True
        elif reference.startswith("$currentNode.inputs."):
            return True
        elif reference == "$currentNodeResult":
            return True
        elif reference.startswith("$."):
            return True
        else:
            return False
    
    def _detect_cycles(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """检测循环引用"""
        errors = []
        
        # 构建有向图
        graph = {}
        for node in nodes:
            node_name = node.get("name", f"node_{nodes.index(node)}")
            next_nodes = [n for n in node.get("nextNodes", []) if n != "end"]
            graph[node_name] = next_nodes
        
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_name: str) -> bool:
            if node_name in rec_stack:
                return True
            if node_name in visited:
                return False
            
            visited.add(node_name)
            rec_stack.add(node_name)
            
            for neighbor in graph.get(node_name, []):
                if has_cycle(neighbor):
                    return True
            
            rec_stack.remove(node_name)
            return False
        
        for node_name in graph:
            if node_name not in visited:
                if has_cycle(node_name):
                    errors.append(f"检测到循环引用，涉及节点: {node_name}")
                    break
        
        return errors
    
    def _merge_validation_results(self, *results) -> Dict[str, Any]:
        """合并验证结果"""
        all_errors = []
        all_warnings = []
        detailed_results = {}
        
        # 收集所有验证结果
        category_names = ["structure_validation", "configuration_validation", "logic_validation", "executability_validation", "reference_validation"]
        for i, result in enumerate(results):
            category_name = category_names[i] if i < len(category_names) else f"validation_{i}"
            detailed_results[category_name] = result
            
            # 收集错误和警告
            all_errors.extend(result.get("errors", []))
            all_warnings.extend(result.get("warnings", []))
        
        # 计算总体结果
        is_valid = len(all_errors) == 0
        overall_score = max(0, 100 - len(all_errors) * 10 - len(all_warnings) * 2)
        
        return {
            "validation_result": {
                "is_valid": is_valid,
                "overall_score": overall_score,
                "error_count": len(all_errors),
                "warning_count": len(all_warnings)
            },
            "detailed_results": detailed_results,
            "all_errors": all_errors,
            "all_warnings": all_warnings
        }
    
    def _is_english_name(self, name: str) -> bool:
        """检查名称是否使用英文字符且以大写字母开头（PascalCase格式）"""
        import re
        # 检查是否只包含英文字母和数字，必须以大写字母开头，采用PascalCase格式
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    
    def _validate_node_references(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证节点引用的准确性"""
        errors = []
        warnings = []
        
        if "nodes" not in workflow:
            return {"passed": False, "errors": ["工作流缺少nodes字段"], "warnings": []}
        
        # 收集所有节点名称
        node_names = set()
        for node in workflow["nodes"]:
            if "name" in node:
                node_names.add(node["name"])
        
        # 检查每个节点中的引用
        for node in workflow["nodes"]:
            node_name = node.get("name", "unknown")
            
            # 检查inputs中的引用
            if "inputs" in node:
                for input_name, input_config in node["inputs"].items():
                    if "value" in input_config:
                        ref_errors = self._check_reference_validity(input_config["value"], node_names, node_name, f"inputs.{input_name}")
                        errors.extend(ref_errors)
            
            # 检查outputs中的引用
            if "outputs" in node:
                for output_name, output_config in node["outputs"].items():
                    if "value" in output_config:
                        ref_errors = self._check_reference_validity(output_config["value"], node_names, node_name, f"outputs.{output_name}")
                        errors.extend(ref_errors)
        
        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _check_reference_validity(self, value: str, node_names: set, current_node: str, field_path: str) -> List[str]:
        """检查引用的有效性"""
        errors = []
        
        if not isinstance(value, str):
            return errors
        
        # 检查是否包含节点引用
        import re
        references = re.findall(r'\$\.([a-zA-Z][a-zA-Z0-9_]*)', value)
        
        for ref_node in references:
            if ref_node not in node_names and ref_node != "currentItem" and ref_node != "currentIndex":
                errors.append(f"节点 {current_node} 的字段 {field_path} 引用了不存在的节点: {ref_node}")
        
        return errors 