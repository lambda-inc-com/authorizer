"""
工作流验证器

用于验证工作流定义是否符合节点规范和最佳实践
"""

import json
import re
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class WorkflowValidator:
    """工作流验证器"""
    
    # 支持的节点类型
    SUPPORTED_NODE_TYPES = {
        "workflowStart", "workflowEnd", "dbQuery", "dbCreate", 
        "dbUpdate", "dbDelete", "transaction", "http", "llm", 
        "condition", "code"
    }
    
    # 支持的数据类型
    SUPPORTED_DATA_TYPES = {
        "string", "number", "boolean", "object", "array"
    }
    
    # 条件操作符
    CONDITION_OPERATORS = {
        "equal", "notEqual", "greaterThan", "greaterThanEqual",
        "lessThan", "lessThanEqual", "isNull", "isNotNull",
        "include", "notInclude"
    }
    
    # HTTP方法
    HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_workflow(self, workflow: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证完整的工作流
        
        Args:
            workflow: 工作流定义
            
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # 基本结构验证
        if not self._validate_basic_structure(workflow):
            return False, self.errors, self.warnings
            
        nodes = workflow.get("nodes", [])
        
        # 验证每个节点
        for node in nodes:
            self._validate_node(node)
            
        # 验证工作流完整性
        self._validate_workflow_integrity(nodes)
        
        # 验证数据流
        self._validate_data_flow(nodes)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_basic_structure(self, workflow: Dict[str, Any]) -> bool:
        """验证基本结构"""
        if not isinstance(workflow, dict):
            self.errors.append("工作流必须是一个对象")
            return False
            
        if "nodes" not in workflow:
            self.errors.append("工作流必须包含 nodes 字段")
            return False
            
        if not isinstance(workflow["nodes"], list):
            self.errors.append("nodes 必须是一个数组")
            return False
            
        if len(workflow["nodes"]) == 0:
            self.errors.append("工作流至少要包含一个节点")
            return False
            
        return True
    
    def _validate_node(self, node: Dict[str, Any]) -> None:
        """验证单个节点"""
        node_name = node.get("name", "未知节点")
        
        # 验证必填字段
        required_fields = ["name", "type", "desc", "inputs", "outputs", "configs", "nextNodes"]
        for field in required_fields:
            if field not in node:
                self.errors.append(f"节点 '{node_name}' 缺少必填字段: {field}")
                
        # 验证节点类型
        node_type = node.get("type")
        if node_type not in self.SUPPORTED_NODE_TYPES:
            self.errors.append(f"节点 '{node_name}' 的类型 '{node_type}' 不被支持")
            
        # 验证节点名称
        if not self._validate_node_name(node.get("name")):
            self.errors.append(f"节点名称 '{node_name}' 不符合命名规范")
            
        # 验证输入输出
        self._validate_inputs_outputs(node)
        
        # 验证配置
        self._validate_node_configs(node)
        
        # 验证nextNodes
        self._validate_next_nodes(node)
    
    def _validate_node_name(self, name: str) -> bool:
        """验证节点名称"""
        if not name:
            return False
            
        # 检查是否为PascalCase
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            return False
            
        return True
    
    def _validate_inputs_outputs(self, node: Dict[str, Any]) -> None:
        """验证输入输出参数"""
        node_name = node.get("name", "未知节点")
        
        # 验证inputs
        inputs = node.get("inputs", {})
        if inputs and isinstance(inputs, dict):
            for input_name, input_def in inputs.items():
                self._validate_parameter_definition(input_def, f"节点 '{node_name}' 的输入参数 '{input_name}'")
                
        # 验证outputs
        outputs = node.get("outputs", {})
        if outputs and isinstance(outputs, dict):
            for output_name, output_def in outputs.items():
                self._validate_parameter_definition(output_def, f"节点 '{node_name}' 的输出参数 '{output_name}'")
    
    def _validate_parameter_definition(self, param_def: Dict[str, Any], context: str) -> None:
        """验证参数定义"""
        if not isinstance(param_def, dict):
            self.errors.append(f"{context} 必须是一个对象")
            return
            
        # 验证type字段
        param_type = param_def.get("type")
        if param_type not in self.SUPPORTED_DATA_TYPES:
            self.errors.append(f"{context} 的数据类型 '{param_type}' 不被支持")
            
        # 验证value字段的引用格式
        value = param_def.get("value")
        if isinstance(value, str) and value.startswith("$"):
            if not self._validate_reference_syntax(value):
                self.errors.append(f"{context} 的引用语法 '{value}' 不正确")
    
    def _validate_reference_syntax(self, reference: str) -> bool:
        """验证引用语法"""
        # 匹配模式：$prevNode.outputs.字段名 或 $currentNode.inputs.字段名 或 $currentNodeResult
        patterns = [
            r'^\$prevNode\.outputs\.[a-zA-Z][a-zA-Z0-9]*$',
            r'^\$currentNode\.inputs\.[a-zA-Z][a-zA-Z0-9]*$',
            r'^\$currentNodeResult$'
        ]
        
        return any(re.match(pattern, reference) for pattern in patterns)
    
    def _validate_node_configs(self, node: Dict[str, Any]) -> None:
        """验证节点配置"""
        node_type = node.get("type")
        node_name = node.get("name", "未知节点")
        configs = node.get("configs", {})
        
        if node_type == "dbQuery":
            self._validate_db_query_configs(configs, node_name)
        elif node_type == "dbCreate":
            self._validate_db_create_configs(configs, node_name)
        elif node_type == "dbUpdate":
            self._validate_db_update_configs(configs, node_name)
        elif node_type == "dbDelete":
            self._validate_db_delete_configs(configs, node_name)
        elif node_type == "http":
            self._validate_http_configs(configs, node_name)
        elif node_type == "condition":
            self._validate_condition_configs(configs, node_name)
        elif node_type == "code":
            self._validate_code_configs(configs, node_name)
        elif node_type == "llm":
            self._validate_llm_configs(configs, node_name)
        elif node_type == "transaction":
            self._validate_transaction_configs(configs, node_name)
    
    def _validate_db_query_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证数据库查询配置"""
        if "table" not in configs:
            self.errors.append(f"节点 '{node_name}' 缺少必填配置: table")
            
        # 验证filters格式
        filters = configs.get("filters", [])
        if filters:
            for i, filter_item in enumerate(filters):
                self._validate_filter_item(filter_item, f"节点 '{node_name}' 的过滤条件 {i+1}")
    
    def _validate_db_create_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证数据库创建配置"""
        required_fields = ["table", "data"]
        for field in required_fields:
            if field not in configs:
                self.errors.append(f"节点 '{node_name}' 缺少必填配置: {field}")
    
    def _validate_db_update_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证数据库更新配置"""
        required_fields = ["table", "data", "filters"]
        for field in required_fields:
            if field not in configs:
                self.errors.append(f"节点 '{node_name}' 缺少必填配置: {field}")
                
        # 验证filters
        filters = configs.get("filters", [])
        if not filters:
            self.warnings.append(f"节点 '{node_name}' 建议添加过滤条件以避免全表更新")
    
    def _validate_db_delete_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证数据库删除配置"""
        required_fields = ["table", "filters"]
        for field in required_fields:
            if field not in configs:
                self.errors.append(f"节点 '{node_name}' 缺少必填配置: {field}")
                
        # 验证filters
        filters = configs.get("filters", [])
        if not filters:
            self.errors.append(f"节点 '{node_name}' 必须提供过滤条件以避免全表删除")
    
    def _validate_http_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证HTTP配置"""
        required_fields = ["method", "url", "bodyType"]
        for field in required_fields:
            if field not in configs:
                self.errors.append(f"节点 '{node_name}' 缺少必填配置: {field}")
                
        method = configs.get("method")
        if method not in self.HTTP_METHODS:
            self.errors.append(f"节点 '{node_name}' 的HTTP方法 '{method}' 不被支持")
    
    def _validate_condition_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证条件配置"""
        if "conditionGroups" not in configs:
            self.errors.append(f"节点 '{node_name}' 缺少必填配置: conditionGroups")
            return
            
        condition_groups = configs["conditionGroups"]
        if not isinstance(condition_groups, list) or not condition_groups:
            self.errors.append(f"节点 '{node_name}' 的 conditionGroups 必须是非空数组")
            return
            
        for i, group in enumerate(condition_groups):
            self._validate_condition_group(group, f"节点 '{node_name}' 的条件组 {i+1}")
    
    def _validate_condition_group(self, group: Dict[str, Any], context: str) -> None:
        """验证条件组"""
        required_fields = ["conditions", "relationship", "nextNode"]
        for field in required_fields:
            if field not in group:
                self.errors.append(f"{context} 缺少必填字段: {field}")
                
        conditions = group.get("conditions", [])
        for i, condition in enumerate(conditions):
            self._validate_condition_item(condition, f"{context} 的条件 {i+1}")
    
    def _validate_condition_item(self, condition: Dict[str, Any], context: str) -> None:
        """验证单个条件"""
        required_fields = ["left", "operator", "right"]
        for field in required_fields:
            if field not in condition:
                self.errors.append(f"{context} 缺少必填字段: {field}")
                
        operator = condition.get("operator")
        if operator not in self.CONDITION_OPERATORS:
            self.errors.append(f"{context} 的操作符 '{operator}' 不被支持")
    
    def _validate_filter_item(self, filter_item: Dict[str, Any], context: str) -> None:
        """验证过滤条件"""
        required_fields = ["field", "operator"]
        for field in required_fields:
            if field not in filter_item:
                self.errors.append(f"{context} 缺少必填字段: {field}")
                
        operator = filter_item.get("operator")
        if operator not in {"=", "!=", ">", ">=", "<", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"}:
            self.errors.append(f"{context} 的操作符 '{operator}' 不被支持")
    
    def _validate_code_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证代码配置"""
        if "file" not in configs:
            self.errors.append(f"节点 '{node_name}' 缺少必填配置: file")
            return
            
        file_config = configs["file"]
        if not isinstance(file_config, dict):
            self.errors.append(f"节点 '{node_name}' 的 file 配置必须是对象")
            return
            
        if "name" not in file_config or "content" not in file_config:
            self.errors.append(f"节点 '{node_name}' 的 file 配置缺少 name 或 content 字段")
    
    def _validate_llm_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证LLM配置"""
        if "modelId" not in configs:
            self.errors.append(f"节点 '{node_name}' 缺少必填配置: modelId")
    
    def _validate_transaction_configs(self, configs: Dict[str, Any], node_name: str) -> None:
        """验证事务配置"""
        # 事务节点的children是必填的
        children = configs.get("children", [])
        if not children:
            self.errors.append(f"节点 '{node_name}' 的事务必须包含子节点")
            return
            
        for i, child in enumerate(children):
            self._validate_transaction_child(child, f"节点 '{node_name}' 的子节点 {i+1}")
    
    def _validate_transaction_child(self, child: Dict[str, Any], context: str) -> None:
        """验证事务子节点"""
        required_fields = ["name", "type", "desc", "order", "inputs", "outputs", "configs"]
        for field in required_fields:
            if field not in child:
                self.errors.append(f"{context} 缺少必填字段: {field}")
                
        child_type = child.get("type")
        if child_type not in {"dbCreate", "dbUpdate", "dbDelete"}:
            self.errors.append(f"{context} 的类型 '{child_type}' 不被支持，事务只支持数据库操作")
    
    def _validate_next_nodes(self, node: Dict[str, Any]) -> None:
        """验证nextNodes字段"""
        node_name = node.get("name", "未知节点")
        node_type = node.get("type")
        next_nodes = node.get("nextNodes", [])
        
        if not isinstance(next_nodes, list):
            self.errors.append(f"节点 '{node_name}' 的 nextNodes 必须是数组")
            
        # 条件节点的nextNodes应该为空
        if node_type == "condition" and next_nodes:
            self.warnings.append(f"条件节点 '{node_name}' 的 nextNodes 应该为空，流向由条件逻辑决定")
            
        # 结束节点的nextNodes应该包含"end"
        if node_type == "workflowEnd" and next_nodes != ["end"]:
            self.errors.append(f"结束节点 '{node_name}' 的 nextNodes 应该是 ['end']")
    
    def _validate_workflow_integrity(self, nodes: List[Dict[str, Any]]) -> None:
        """验证工作流完整性"""
        node_names = [node.get("name") for node in nodes]
        
        # 检查节点名称唯一性
        seen_names = set()
        for name in node_names:
            if name in seen_names:
                self.errors.append(f"节点名称 '{name}' 重复")
            seen_names.add(name)
            
        # 检查是否有开始和结束节点
        has_start = any(node.get("type") == "workflowStart" for node in nodes)
        has_end = any(node.get("type") == "workflowEnd" for node in nodes)
        
        if not has_start:
            self.errors.append("工作流必须包含一个开始节点 (workflowStart)")
        if not has_end:
            self.errors.append("工作流必须包含一个结束节点 (workflowEnd)")
    
    def _validate_data_flow(self, nodes: List[Dict[str, Any]]) -> None:
        """验证数据流"""
        # 简单的数据流验证：检查引用的字段是否存在
        node_outputs = {}
        
        for node in nodes:
            node_name = node.get("name")
            outputs = node.get("outputs", {})
            node_outputs[node_name] = list(outputs.keys())
            
            # 检查输入引用
            inputs = node.get("inputs", {})
            for input_name, input_def in inputs.items():
                value = input_def.get("value", "")
                if isinstance(value, str) and value.startswith("$prevNode.outputs."):
                    field_name = value.split(".")[-1]
                    # 这里需要更复杂的逻辑来验证前一个节点的输出
                    # 简化处理：记录警告
                    self.warnings.append(f"节点 '{node_name}' 引用了前一节点的输出字段 '{field_name}'，请确保数据流正确")
    
    def get_validation_summary(self) -> str:
        """获取验证摘要"""
        summary = []
        
        if self.errors:
            summary.append(f"❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                summary.append(f"  - {error}")
                
        if self.warnings:
            summary.append(f"⚠️ 发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                summary.append(f"  - {warning}")
                
        if not self.errors and not self.warnings:
            summary.append("✅ 工作流验证通过，没有发现问题")
            
        return "\n".join(summary)


def validate_workflow_json(workflow_json: str) -> Tuple[bool, List[str], List[str]]:
    """
    验证工作流JSON字符串
    
    Args:
        workflow_json: 工作流JSON字符串
        
    Returns:
        (is_valid, errors, warnings)
    """
    try:
        workflow = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        return False, [f"JSON格式错误: {str(e)}"], []
    
    validator = WorkflowValidator()
    return validator.validate_workflow(workflow)


def validate_workflow_dict(workflow: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    验证工作流字典
    
    Args:
        workflow: 工作流字典
        
    Returns:
        (is_valid, errors, warnings)
    """
    validator = WorkflowValidator()
    return validator.validate_workflow(workflow) 