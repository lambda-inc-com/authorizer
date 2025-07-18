#!/usr/bin/env python3
"""
节点类型管理器
Node Type Manager

用于统一管理节点类型，处理数据库中的节点类型和代码中硬编码类型之间的映射
"""

import logging
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)


class NodeTypeManager:
    """节点类型管理器"""
    
    def __init__(self):
        # 从数据库加载的实际节点类型
        self._available_db_types: Set[str] = set()
        
        # 节点DSL数据缓存（从数据库加载）
        self._node_dsl_data: Dict[str, Dict[str, Any]] = {}
        
        # 动态构建的概念映射（基于数据库描述）
        self._concept_mapping: Dict[str, List[str]] = {}
        
        # 动态构建的类型映射（基于数据库数据和常见别名）
        self._legacy_to_db_mapping: Dict[str, str] = {}
        self._db_to_legacy_mapping: Dict[str, str] = {}
    
    def update_from_database(self, node_dsl_data: Dict[str, Dict[str, Any]]):
        """从数据库DSL数据更新节点类型管理器"""
        self._node_dsl_data = node_dsl_data
        self._available_db_types = set(node_dsl_data.keys())
        
        # 动态构建概念映射和类型映射
        self._build_dynamic_mappings()
        
        logger.info(f"✅ 从数据库更新节点类型管理器，加载 {len(node_dsl_data)} 个节点类型")
        logger.info(f"📋 可用节点类型: {', '.join(sorted(self._available_db_types))}")
    
    def _build_dynamic_mappings(self):
        """基于数据库DSL数据动态构建映射关系"""
        self._concept_mapping.clear()
        self._legacy_to_db_mapping.clear()
        self._db_to_legacy_mapping.clear()
        
        for node_type, dsl_data in self._node_dsl_data.items():
            description = dsl_data.get('description', '').lower()
            
            # 基于描述构建概念映射
            concepts = [node_type]  # 节点类型本身
            
            # 根据节点类型和描述添加概念关键词
            if node_type == "start" or "开始" in description or "启动" in description:
                concepts.extend(["开始", "启动", "workflowStart", "workflow_start", "begin"])
                self._legacy_to_db_mapping["workflowStart"] = node_type
                
            elif node_type == "end" or "结束" in description or "完成" in description:
                concepts.extend(["结束", "完成", "workflowEnd", "workflow_end", "finish", "complete"])
                self._legacy_to_db_mapping["workflowEnd"] = node_type
                
            elif "查询" in description or "query" in description.lower() or "select" in description.lower():
                concepts.extend(["查询", "select", "query", "search", "find"])
                self._legacy_to_db_mapping["dbQuery"] = node_type
                
            elif "创建" in description or "插入" in description or "create" in description.lower() or "insert" in description.lower():
                concepts.extend(["创建", "插入", "insert", "create", "add"])
                self._legacy_to_db_mapping["dbCreate"] = node_type
                
            elif "更新" in description or "修改" in description or "update" in description.lower():
                concepts.extend(["更新", "修改", "update", "modify", "edit"])
                self._legacy_to_db_mapping["dbUpdate"] = node_type
                
            elif "删除" in description or "delete" in description.lower() or "remove" in description.lower():
                concepts.extend(["删除", "remove", "delete"])
                self._legacy_to_db_mapping["dbDelete"] = node_type
                
            elif "条件" in description or "判断" in description or "condition" in description.lower():
                concepts.extend(["条件", "判断", "if", "branch", "decision"])
                self._legacy_to_db_mapping["condition"] = node_type
                
            elif "http" in description.lower() or "请求" in description or "api" in description.lower():
                concepts.extend(["请求", "api", "http", "web", "rest"])
                self._legacy_to_db_mapping["http"] = node_type
                
            elif "代码" in description or "脚本" in description or "code" in description.lower() or "javascript" in description.lower():
                concepts.extend(["代码", "脚本", "javascript", "js", "script"])
                self._legacy_to_db_mapping["code"] = node_type
                
            elif "llm" in description.lower() or "chat" in description.lower() or "ai" in description.lower():
                concepts.extend(["llm", "chat", "ai", "gpt", "对话"])
                self._legacy_to_db_mapping["chatWithLLM"] = node_type
                
            elif "事务" in description or "transaction" in description.lower():
                concepts.extend(["事务", "transaction", "batch"])
                self._legacy_to_db_mapping["transaction"] = node_type
                
            elif "批量" in description or "batch" in description.lower():
                concepts.extend(["批量", "batch", "bulk"])
                self._legacy_to_db_mapping["batch"] = node_type
                
            elif "工作流" in description or "workflow" in description.lower():
                concepts.extend(["工作流", "workflow", "flow"])
                self._legacy_to_db_mapping["workflow"] = node_type
            
            # 存储概念映射
            self._concept_mapping[node_type] = list(set(concepts))
            
            # 保持向后兼容 - 如果节点类型本身已经是"传统"格式，也添加映射
            if node_type not in self._legacy_to_db_mapping.values():
                self._legacy_to_db_mapping[node_type] = node_type
        
        # 构建反向映射
        self._db_to_legacy_mapping = {v: k for k, v in self._legacy_to_db_mapping.items()}
        
        logger.debug(f"🔄 动态构建映射关系:")
        logger.debug(f"   传统→数据库: {self._legacy_to_db_mapping}")
        logger.debug(f"   概念映射: {dict(list(self._concept_mapping.items())[:3])}...")  # 只显示前3个
    
    def update_available_types(self, db_node_types: List[str]):
        """兼容性方法：更新从数据库加载的可用节点类型"""
        self._available_db_types = set(db_node_types)
        logger.info(f"更新可用节点类型: {', '.join(sorted(db_node_types))}")
    
    def get_db_type(self, legacy_type: str) -> Optional[str]:
        """将硬编码类型转换为数据库类型"""
        if legacy_type in self._available_db_types:
            # 如果已经是数据库类型，直接返回
            return legacy_type
        
        # 查找映射
        db_type = self._legacy_to_db_mapping.get(legacy_type)
        if db_type and db_type in self._available_db_types:
            return db_type
        
        # 模糊匹配
        for db_type in self._available_db_types:
            concepts = self._concept_mapping.get(db_type, [])
            if legacy_type.lower() in [c.lower() for c in concepts]:
                return db_type
        
        logger.warning(f"未找到硬编码类型 '{legacy_type}' 对应的数据库类型")
        return None
    
    def get_legacy_type(self, db_type: str) -> str:
        """将数据库类型转换为硬编码类型（向后兼容）"""
        return self._db_to_legacy_mapping.get(db_type, db_type)
    
    def find_start_node_type(self) -> Optional[str]:
        """查找开始节点类型"""
        candidates = ["start", "workflowStart", "workflow_start"]
        for candidate in candidates:
            if candidate in self._available_db_types:
                return candidate
        return None
    
    def find_end_node_type(self) -> Optional[str]:
        """查找结束节点类型"""
        candidates = ["end", "workflowEnd", "workflow_end"]
        for candidate in candidates:
            if candidate in self._available_db_types:
                return candidate
        return None
    
    def is_start_node(self, node_type: str) -> bool:
        """判断是否为开始节点类型"""
        start_type = self.find_start_node_type()
        if start_type:
            return node_type == start_type
        
        # 回退到硬编码判断
        return node_type in ["start", "workflowStart"]
    
    def is_end_node(self, node_type: str) -> bool:
        """判断是否为结束节点类型"""
        end_type = self.find_end_node_type()
        if end_type:
            return node_type == end_type
        
        # 回退到硬编码判断
        return node_type in ["end", "workflowEnd"]
    
    def get_all_available_types(self) -> List[str]:
        """获取所有可用的数据库节点类型"""
        return sorted(list(self._available_db_types))
    
    def validate_node_type(self, node_type: str) -> bool:
        """验证节点类型是否有效"""
        return node_type in self._available_db_types
    
    def is_condition_like_node(self, node_type: str) -> bool:
        """判断是否是条件类型的节点（不需要outputs和nextNodes）"""
        if node_type in self._node_dsl_data:
            description = self._node_dsl_data[node_type].get('description', '').lower()
            # 基于描述判断是否是条件节点
            return any(keyword in description for keyword in ['条件', '判断', '选择', 'condition', 'decision', 'choice', 'branch'])
        
        # 基于节点类型名称的推断
        condition_keywords = ['condition', 'branch', 'switch', 'if', 'judge', 'decide']
        return any(keyword in node_type.lower() for keyword in condition_keywords)
    
    def normalize_node_type(self, node_type: str) -> str:
        """规范化节点类型（优先使用数据库类型）"""
        db_type = self.get_db_type(node_type)
        return db_type if db_type else node_type
    
    def get_node_type_mapping(self) -> Dict[str, str]:
        """获取完整的类型映射表"""
        return {
            "legacy_to_db": dict(self._legacy_to_db_mapping),
            "db_to_legacy": dict(self._db_to_legacy_mapping),
            "available_db_types": list(self._available_db_types)
        }
    
    def generate_available_node_types_for_llm(self) -> str:
        """生成给LLM的可用节点类型列表（基于数据库数据）"""
        if not self._node_dsl_data:
            return "- 暂无可用节点类型（请检查数据库连接）"
        
        node_type_lines = []
        for node_type, dsl_data in self._node_dsl_data.items():
            description = dsl_data.get('description', '')
            # 提取描述的第一句作为简短说明
            short_desc = description.split('\n')[0].split('。')[0].strip()
            if not short_desc:
                short_desc = f"{node_type}节点"
            
            # 判断是否为必需节点
            is_required = ""
            if self.is_start_node(node_type):
                is_required = "（必需）"
            elif self.is_end_node(node_type):
                is_required = "（必需）"
            
            node_type_lines.append(f"- **{node_type}**: {short_desc}{is_required}")
        
        return "\n".join(sorted(node_type_lines))
    
    def get_node_description(self, node_type: str) -> str:
        """获取节点类型的描述"""
        if node_type in self._node_dsl_data:
            return self._node_dsl_data[node_type].get('description', f"{node_type}节点")
        return f"{node_type}节点"
    
    def get_node_example(self, node_type: str) -> Dict[str, Any]:
        """获取节点类型的示例"""
        if node_type in self._node_dsl_data:
            return self._node_dsl_data[node_type].get('example', {})
        return {}
    
    def get_all_node_dsl_data(self) -> Dict[str, Dict[str, Any]]:
        """获取所有节点的DSL数据"""
        return self._node_dsl_data.copy()
    
    def is_database_loaded(self) -> bool:
        """检查是否已从数据库加载数据"""
        return bool(self._node_dsl_data)
    
    def suggest_similar_types(self, invalid_type: str) -> List[str]:
        """为无效的节点类型建议相似的类型"""
        suggestions = []
        
        # 基于概念映射查找
        for db_type, concepts in self._concept_mapping.items():
            if db_type in self._available_db_types:
                for concept in concepts:
                    if concept.lower() in invalid_type.lower() or invalid_type.lower() in concept.lower():
                        suggestions.append(db_type)
                        break
        
        # 基于字符串相似度查找
        for db_type in self._available_db_types:
            if (len(set(invalid_type.lower()) & set(db_type.lower())) >= 
                min(len(invalid_type), len(db_type)) * 0.5):
                if db_type not in suggestions:
                    suggestions.append(db_type)
        
        return suggestions[:3]  # 最多返回3个建议


# 全局节点类型管理器实例
node_type_manager = NodeTypeManager() 