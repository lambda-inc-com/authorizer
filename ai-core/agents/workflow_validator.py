"""
工作流验证智能体 (Workflow Validator Agent)
负责验证生成的工作流JSON是否符合规范和要求
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

logger = logging.getLogger(__name__)


class WorkflowValidator(BaseAgent):
    """工作流验证智能体"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.WORKFLOW_VALIDATOR, message_bus, state_manager)
        self.llm_client = llm_client
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """加载验证规则"""
        return {
            "structure_rules": {
                "required_workflow_fields": ["name", "description", "version", "nodes"],
                "required_node_fields": ["name", "type", "desc", "inputs", "outputs", "configs", "nextNodes"],
                "valid_node_types": [
                    "workflowStart", "workflowEnd", "dbQuery", "dbCreate", "dbUpdate", 
                    "dbDelete", "transaction", "batch", "condition", "workflow", 
                    "http", "llm", "code"
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
                    "nextNodes_rules": "can_be_empty",
                    "no_outputs": True
                },
                "workflow": {
                    "required_configs": ["workflowId", "inputMappings", "outputMappings"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "http": {
                    "required_configs": ["method", "url"],
                    "required_outputs": ["code", "data", "message"],
                    "nextNodes_rules": "must_not_be_empty"
                },
                "llm": {
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
        
        # 合并验证结果
        return self._merge_validation_results(
            structure_result,
            config_result,
            logic_result,
            executability_result
        )
    
    def _validate_structure(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流结构"""
        errors = []
        warnings = []
        
        # 检查工作流必需字段
        for field in self.validation_rules["structure_rules"]["required_workflow_fields"]:
            if field not in workflow:
                errors.append(f"工作流缺少必需字段: {field}")
        
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
        # 检查必需字段，但根据节点类型决定是否需要outputs
        required_fields = ["name", "type", "desc", "inputs", "configs", "nextNodes"]
        
        # 检查是否需要outputs字段
        node_type = node.get("type")
        rules = self.validation_rules["node_specific_rules"].get(node_type, {})
        needs_outputs = not rules.get("no_outputs", False)
        
        if needs_outputs:
            required_fields.append("outputs")
        
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
            errors.append("节点名称必须唯一")
        
        # 检查起始和结束节点
        start_nodes = [node for node in nodes if node.get("type") == "workflowStart"]
        end_nodes = [node for node in nodes if node.get("type") == "workflowEnd"]
        
        if len(start_nodes) != 1:
            errors.append("工作流必须包含且仅包含一个workflowStart节点")
        
        if len(end_nodes) != 1:
            errors.append("工作流必须包含且仅包含一个workflowEnd节点")
        
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
        for i, result in enumerate(results):
            category_name = ["structure_validation", "configuration_validation", "logic_validation", "executability_validation"][i]
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